import threading, time, os, re
from threading import Event, Thread
import se_tts_constants
from datetime import datetime
from queue import Queue
from framework.util.utils import Config, chunk_text
from bus.MsgBusClient import MsgBusClient
from framework.message_types import MSG_MEDIA, MSG_SKILL
from se_tts_session_table import TTSSessionTable
from se_tts_session_methods import TTSSessionMethods

class TTSSession(TTSSessionTable, TTSSessionMethods, threading.Thread):
    def __init__(self, owner, tts_sid, msid, session_data, internal_event_callback, log):
        self.log = log
        super(TTSSession, self).__init__()
        threading.Thread.__init__(self)
        self.skill_id = "tts_session"
        self.bus = MsgBusClient(self.skill_id)
        self.state = 'idle'
        self.exit_flag = False
        self.paused = False
        self.pause_ack = False
        self.owner = owner
        self.tts_sid = tts_sid
        self.msid = msid
        self.session_data = session_data
        self.index = 0
        self.internal_event_callback = internal_event_callback
        self.paused_requestor = None
        self.lock = threading.RLock()

        # we run remote and local tts in parallel. this will hold maybe
        # both responses, maybe one or maybe none. None would be a time out
        self.tts_wait_q_local = Queue()
        self.tts_wait_q_remote = Queue()

        self.state = se_tts_constants.STATE_IDLE
        self.valid_states = se_tts_constants.valid_states
        self.valid_events = se_tts_constants.valid_events

        cfg = Config()
        # we always fall back if remote fails but local only means 
        # don't even try remote which will be faster than a local
        # fall back which is effectively a remote time out.
        self.remote_tts = None
        self.use_remote_tts = False
        #remote_tts_flag = get_cfg_val('remote_tts')
        remote_tts_flag = cfg.get_cfg_val('Advanced.TTS.UseRemote')
        if remote_tts_flag and remote_tts_flag == 'y':
            self.use_remote_tts = True
            # we don't bother with fancy configs or modules
            # this is your modular architecture right here
            which_remote_tts = cfg.get_cfg_val('Advanced.TTS.Remote')
            #which_remote_tts = get_cfg_val('remote_tts_type')
            if which_remote_tts == 'm':
                # mimic2
                from framework.services.tts.remote.mimic2 import remote_tts
            else:
                # remote default is polly
                from framework.services.tts.remote.polly import remote_tts
            self.remote_tts = remote_tts()
        self.log.info("Using remote TTS=%s, tts_obj=%s" % (self.use_remote_tts,self.remote_tts))

        # which local tts engine to use. 
        self.which_local_tts = 'e'
        #if get_cfg_val('local_tts') == 'c':
        if cfg.get_cfg_val('Advanced.TTS.Local') == 'c':
            from framework.services.tts.local.coqui_tts import local_speak_dialog
            self.which_local_tts = 'c'
        elif cfg.get_cfg_val('Advanced.TTS.Local') == 'm':
            from framework.services.tts.local.mimic3 import local_speak_dialog
            self.which_local_tts = 'm'
        else:
            from framework.services.tts.local.espeak import local_speak_dialog
        self.local_speak = local_speak_dialog

        self.tmp_file_path = os.getenv('SVA_BASE_DIR') + '/tmp'
        self.remote_filename = ''
        self.local_filename = ''

        self.bus.on(MSG_SKILL, self.handle_skill_msg)

    def wait_paused(self, requestor):
        # set up to handle pause responses from
        # both local and remote processes
        self.internal_pause = False
        self.external_pause = False
        self.paused = True
        self.paused_requestor = requestor
        # tell media player too
        self.send_session_pause()
        # this will cause an internal event to fire once
        self.pause_ack = True

    def play_file(self,filename):
        self.log.debug("TTSSession play_file() state=%s, self.msid=%s, curr_sess.msid=%s, filename=%s" % (self.state, self.msid, self.msid, filename))
        if self.state == se_tts_constants.STATE_ACTIVE:
            if self.msid == 0:
                self.log.info("TTSSession Warning, invalid session ID (0). Must reestablish media session!")
                self.paused_filename = filename
                self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_START)
                self.send_media_session_request()
            else:
                info = {
                    'file_uri':filename,
                    'subtype':'media_player_command',
                    'command':'play_media',
                    'correlator':self.correlator,
                    'session_id':self.msid,
                    'skill_id':'media_player_service',
                    'from_skill_id':self.skill_id,
                    'delete_on_complete':'true'
                    }
                self.bus.send(MSG_MEDIA, 'media_player_service', info)
                self.log.debug("TTSSession play_file() exit - play state=%s, filename = %s" % (self.state, filename))
        else:
            self.log.warning("Play file refusing to play because state is not active ---> %s" % (self.state,))

    def get_remote_tts(self, chunk):
        # TODO these do not need to be instance variables 
        self.remote_filename = datetime.now().strftime("save_tts/remote_outfile_%Y-%m-%d_%H-%M-%S_%f.wav")
        self.remote_filename = "%s/%s" % (self.tmp_file_path, self.remote_filename)

        self.local_filename = datetime.now().strftime("save_tts/local_outfile_%Y-%m-%d_%H-%M-%S_%f.wav")
        self.local_filename = "%s/%s" % (self.tmp_file_path, self.local_filename)

        # start 2 threads and return result = remote if possible, else local
        if self.use_remote_tts:
            th1 = Thread(target=self.remote_tts.remote_speak, args=(chunk, self.remote_filename, self.tts_wait_q_remote))
            th1.daemon = True
            th1.start()

        th2 = None
        th2 = Thread(target=self.local_speak, args=(chunk, self.local_filename, self.tts_wait_q_local))
        th2.daemon = True
        th2.start()
        result = ''

        if self.use_remote_tts:
            try:
                result = self.tts_wait_q_remote.get(block=True, timeout=se_tts_constants.REMOTE_TIMEOUT)
            except:
                self.log.debug("TTSSession remote timed out!")

        if result and result != '' and result['status'] == 'success' and result['service'] == 'remote':
            self.log.debug("TTSSession got remote response %s" % (result,))
        else:
            self.log.debug("TTSSession did not get remote response, trying get local ...")
            try:
                result = self.tts_wait_q_local.get(block=True, timeout=se_tts_constants.REMOTE_TIMEOUT)
            except:
                self.log.warning("Creepy Internal Error 101 - TTSSession local timed out too!")
                return False

        if result['service'] == 'remote':
            filename = self.remote_filename
            os.system("rm %s" % (self.local_filename,))
        else:
            filename = self.local_filename
            os.system("rm %s" % (self.remote_filename,))

        self.log.debug("TTSSession create wave file, Final result: {}, text:{}, filename:{}".format(result,chunk,filename))
        return filename

    def send_media_session_request(self):
        info = {
            'error':'',
            'subtype':'media_player_command',
            'command':'start_session',
            'correlator':self.correlator,
            'skill_id':'media_player_service',
            'from_skill_id':self.skill_id
            }
        self.bus.send(MSG_MEDIA, 'media_player_service', info)

    def stop_media_session(self):
        self.paused = True
        self.log.debug("TTSSession told to stop media session!, state=%s, mpsid:%s" % (self.state, self.msid))

        if self.msid != 0:
            info = {
                    'error':'',
                    'subtype':'media_player_command',
                    'command':'stop_session',
                    'correlator':self.correlator,
                    'session_id':self.msid,
                    'skill_id':'media_player_service',
                    'from_skill_id':self.skill_id,
                    }
            self.bus.send(MSG_MEDIA, 'media_player_service', info)
            self.msid = 0
        else:
            # else no active media session to stop
            self.log.warning("TTSSession no media player session to stop (id=%s)" % (self.msid,))

        self.session_data = []
        self.index = 0

    def send_session_pause(self):
        info = {
                'error':'',
                'subtype':'media_player_command',
                'command':'pause_session',
                'correlator':self.correlator,
                'session_id':self.msid,
                'skill_id':'media_player_service',
                'from_skill_id':self.skill_id,
                }
        self.bus.send(MSG_MEDIA, 'media_player_service', info)

    def send_session_resume(self):
        info = {
                'error':'',
                'subtype':'media_player_command',
                'command':'resume_session',
                'correlator':self.correlator,
                'session_id':self.msid,
                'skill_id':'media_player_service',
                'from_skill_id':self.skill_id,
                }
        self.bus.send(MSG_MEDIA, 'media_player_service', info)

    def add(self, i):
        with self.lock:
            self.session_data.extend(i)

    def remove(self, i):
        with self.lock:
            self.session_data.remove(i)

    def reset(self, owner):
        with self.lock:
            self.owner = owner
            self.session_data = []
            self.index = 0
            self.msid = 0
            self.tts_sid = 0
            self.correlator = 0
            self.paused = True
            self.state = se_tts_constants.STATE_IDLE

    def run(self):
        while not self.exit_flag:
            #print("TIC paused=%s, index=%s, data=%s" % (self.paused,self.index, self.session_data))
            if self.pause_ack:
                self.pause_ack = False
                self.handle_event(se_tts_constants.EVENT_INTERNAL_PAUSE, {'tsid':self.tts_sid, 'msid':self.msid})
            if not self.paused:
                if len(self.session_data) == self.index and self.index != 0:
                    # End of q reached!
                    self.index = 0
                    self.session_data = []
                    self.handle_event(se_tts_constants.INTERNAL_EVENT_ENDED, {'tsid':self.tts_sid, 'msid':self.msid})
                else:
                    if len(self.session_data) > 0:
                        sentence = self.session_data[self.index]
                        # TODO handle local only config 
                        tmp_file = self.get_remote_tts(sentence)
                        if not self.paused:
                            self.play_file( tmp_file )
                            self.index += 1
            time.sleep(0.01)

    def handle_skill_msg(self,msg):
        data = msg.data
        msg_correlator = data.get("correlator","")

        if data['skill_id'] == self.skill_id:

            if data['subtype'] == 'media_player_command_response':
                # these come to us from the media service

                if self.correlator != self.tts_sid:
                    self.log.debug("TTSSession Internal issue. self.cor [%s] <> self.curr_sess.tts_sid [%s]" % (self.correlator, self.tts_sid))

                if self.correlator != msg_correlator:
                    self.log.error("TTSSession correlators dont match! Ignoring message. self.cor[%s] <> msg.cor[%s]" % (self.correlator, msg_correlator))
                    return False

                if msg.data['response'] == 'session_confirm':
                    self.handle_event(se_tts_constants.EVENT_MEDIA_CONFIRMED, data)

                elif msg.data['response'] == 'session_reject':
                    self.handle_event(se_tts_constants.EVENT_MEDIA_DECLINED, data)

                elif msg.data['response'] == 'session_paused':
                    self.handle_event(se_tts_constants.EVENT_MEDIA_PAUSED, data)

                elif msg.data['response'] == 'session_ended':
                    if msg.data['reason'] == 'eof':
                        self.handle_event(se_tts_constants.EVENT_MEDIA_ENDED, data)
                    else:
                        self.handle_event(se_tts_constants.EVENT_MEDIA_CANCELLED, data)

                elif msg.data['response'] == 'stop_session':
                    self.log.warning("TTSSession Creepy Internal Error 102 - the media player reported stop_session for no reason.")

                else:
                    self.log.warning("TTSSession Creepy Internal Error 103 - unknown media response = %s" % (msg.data['response'],))

