import threading, time, os, re
from threading import Event, Thread
import se_tts_constants
from datetime import datetime
from queue import Queue
from framework.util.utils import Config, chunk_text
from bus.MsgBus import MsgBus
from se_tts_session_table import TTSSessionTable
from se_tts_session_methods import TTSSessionMethods

class TTSSession(TTSSessionTable, TTSSessionMethods, threading.Thread):
  def __init__(self, owner, tts_sid, msid, session_data, internal_event_callback, log):
    # Run remote and local tts in parallel. this will hold maybe both responses, maybe one or maybe none => a time out
    self.log = log
    self.log.debug(f"TTSSession.__init__() owner: {owner} tts_sid: {tts_sid} msid: {msid}")
    super(TTSSession, self).__init__()
    threading.Thread.__init__(self)
    self.skill_id = "tts_session"
    self.bus = MsgBus(self.skill_id)
    self.state = "idle"
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
    self.tts_wait_q_local = Queue()
    self.tts_wait_q_remote = Queue()
    self.state = se_tts_constants.STATE_IDLE
    self.valid_states = se_tts_constants.valid_states
    self.valid_events = se_tts_constants.valid_events
    cfg = Config()

    # always fall back if remote fails but local only means don"t even try remote which will be faster 
    # than a local fall back which is effectively a remote time out.
    self.remote_tts = None
    self.use_remote_tts = False
    remote_tts_flag = cfg.get_cfg_val("Advanced.TTS.UseRemote")
    self.log.debug(f"TTSSession.__init__() remote_tts_flag: {remote_tts_flag}")
    if remote_tts_flag and remote_tts_flag == "y":
      self.use_remote_tts = True
      which_remote_tts = cfg.get_cfg_val("Advanced.TTS.Remote")
      if which_remote_tts == "m":          # mimic
        from framework.services.tts.remote.mimic2 import remote_tts
      else:                                # remote default is polly
        from framework.services.tts.remote.polly import remote_tts
      self.remote_tts = remote_tts()
    self.log.info(f"TTSSession.__init__() use_remote_tts: {self.use_remote_tts} remote_tts: {self.remote_tts}")
    self.which_local_tts = "e"             # which local tts engine to use. 
    if cfg.get_cfg_val("Advanced.TTS.Local") == "c": # coqui
      from framework.services.tts.local.coqui_tts import local_speak_dialog
      self.which_local_tts = "c"
    elif cfg.get_cfg_val("Advanced.TTS.Local") == "p": # piper
      from framework.services.tts.local.piper import local_speak_dialog
      self.which_local_tts = "p"
    else:
      from framework.services.tts.local.espeak import local_speak_dialog
    self.local_speak = local_speak_dialog
    self.tmp_file_path = os.getenv("SVA_BASE_DIR") + "/tmp"
    self.remote_file_name = ""
    self.local_file_name = ""
    self.bus.on("skill", self.handle_skill_msg)

  def wait_paused(self, requestor):
    # set up to handle pause responses from both local and remote processes
    self.log.debug(f"TTSSession.wait_paused() requestor: {requestor}")  
    self.internal_pause = False
    self.external_pause = False
    self.paused = True
    self.paused_requestor = requestor
    self.send_session_pause()              # tell media player too
    self.pause_ack = True                  # this will cause an internal event to fire once

  def play_file(self, file_name):
    self.log.debug(f"TTSSession.play_file() state: {self.state} self.msid: {self.msid} file_name: {file_name}")
    if self.state == se_tts_constants.STATE_ACTIVE:
      if self.msid == 0:
        self.log.info("TTSSession Warning, invalid session ID (0). Must reestablish media session!")
        self.paused_file_name = file_name
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_START)
        self.send_media_session_request()
      else:
        info = {"file_uri": file_name,
                "subtype": "media_player_command",
                "command": "play_media",
                "correlator": self.correlator,
                "session_id": self.msid,
                "skill_id": "media_player_service",
                "from_skill_id": self.skill_id,
                "delete_on_complete": "true"
               }
        self.bus.send("media", "media_player_service", info)
        self.log.debug(f"TTSSession play_file() exit - play state: {self.state} file_name: {file_name}")
    else:
      self.log.warning(f"TTSSession play_file() cannot play file because state is not active: {self.state}")

  def get_remote_tts(self, chunk):
    # start 1 or 2 threads and return result = remote if possible, else local
    self.log.debug(f"TTSSession.get_remote_tts() chunk: {chunk}")
    self.local_file_name = datetime.now().strftime("save_tts/local_outfile_%Y-%m-%d_%H-%M-%S_%f.wav")
    self.local_file_name = f"{self.tmp_file_path}/{self.local_file_name}"
    self.log.debug(f"TTSSession.get_remote_tts() local_file_name: {self.local_file_name}")
    if self.use_remote_tts:                # start thread for remote speak
      self.remote_file_name = datetime.now().strftime("save_tts/remote_outfile_%Y-%m-%d_%H-%M-%S_%f.wav")
      self.remote_file_name = f"{self.tmp_file_path}/{self.remote_file_name}"
      self.log.debug(f"TTSSession.get_remote_tts() remote_file_name: {self.remote_file_name}")
      th1 = Thread(target=self.remote_tts.remote_speak, args=(chunk, self.remote_file_name, self.tts_wait_q_remote))
      th1.daemon = True
      th1.start()
    th2 = None                             # always start thread for local speak
    th2 = Thread(target=self.local_speak, args=(chunk, self.local_file_name, self.tts_wait_q_local))
    th2.daemon = True
    th2.start()
    result = ""
    if self.use_remote_tts:                # get remote speech file
      try:
        result = self.tts_wait_q_remote.get(block=True, timeout=se_tts_constants.REMOTE_TIMEOUT)
      except:
        self.log.debug(f"TTSSession.get_remote_tts() remote timed out - timeout: {se_tts_constants.REMOTE_TIMEOUT}")
    self.log.debug(f"TTSSession.get_remote_tts() result: {result}")    
    if result and result != "" and result["status"] == "success" and result["service"] == "remote":
      self.log.debug(f"TTSSession.get_remote_tts() got remote response {result}")
    else:
      self.log.debug(f"TTSSession.get_remote_tts() trying get local - LOCAL_TIMEOUT: {se_tts_constants.LOCAL_TIMEOUT}")
      try:
        # result = self.tts_wait_q_local.get(block=True, timeout=se_tts_constants.REMOTE_TIMEOUT)
        result = self.tts_wait_q_local.get(block=True, timeout=se_tts_constants.LOCAL_TIMEOUT)
      except Exception as e:
        self.log.warning(f"TTSSession.get_remote_tts() Creepy internal Error 101 - local timed out - e:{e}")
        return self.local_file_name        # maybe this will work?
    if result["service"] == "remote":
      file_name = self.remote_file_name
      os.system(f"if [ -f {self.local_file_name}; then rm {self.local_file_name}; fi")
    else:
      file_name = self.local_file_name
      os.system(f"if [ -f {self.remote_file_name} ]; then rm {self.remote_file_name}; fi")
    self.log.debug(f"TTSSession.get_remote_tts() result: {result}, chunk: {chunk} file_name: {file_name}")
    return file_name

  def send_media_session_request(self):
    self.log.debug("TTSSession.send_media_session_request()") 
    info = {
        "error":"",
        "subtype":"media_player_command",
        "command":"start_session",
        "correlator":self.correlator,
        "skill_id":"media_player_service",
        "from_skill_id":self.skill_id
         }
    self.bus.send("media", "media_player_service", info)

  def stop_media_session(self):
    self.log.debug(f"TTSSession.stop_media_session() state: {self.state} msid: {self.msid}")
    self.paused = True
    if self.msid != 0:
      info = {"error": "",
              "subtype": "media_player_command",
              "command": "stop_session",
              "correlator": self.correlator,
              "session_id": self.msid,
              "skill_id": "media_player_service",
              "from_skill_id": self.skill_id
              }
      self.bus.send("media", "media_player_service", info)
      self.msid = 0
    else:                                  # no active media session to stop
      self.log.warning(f"TTSSession no media player session to stop msid: {self.msid}")
    self.session_data = []
    self.index = 0

  def send_session_pause(self):
    self.log.debug("TTSSession.send_session_pause()") 
    info = {"error": "",
            "subtype": "media_player_command",
            "command": "pause_session",
            "correlator": self.correlator,
            "session_id": self.msid,
            "skill_id": "media_player_service",
            "from_skill_id": self.skill_id
           }
    self.bus.send("media", "media_player_service", info)

  def send_session_resume(self):
    self.log.debug("TTSSession.send_session_resume()") 
    info = {"error": "",
            "subtype": "media_player_command",
            "command": "resume_session",
            "correlator": self.correlator,
            "session_id": self.msid,
            "skill_id": "media_player_service",
            "from_skill_id": self.skill_id
           }
    self.bus.send("media", "media_player_service", info)

  def add(self, i):
    self.log.debug("TTSSession.add()") 
    with self.lock:
      self.session_data.extend(i)

  def remove(self, i):
    self.log.debug("TTSSession.remove()") 
    with self.lock:
      self.session_data.remove(i)

  def reset(self, owner):
    self.log.debug("TTSSession.reset()") 
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
    self.log.debug("TTSSession.run()") 
    while not self.exit_flag:      # loop forever waiting till it out turn to speak
      if self.pause_ack:
        self.pause_ack = False
        self.handle_event(se_tts_constants.EVENT_INTERNAL_PAUSE, {"tsid":self.tts_sid, "msid":self.msid})
      if not self.paused:
        if len(self.session_data) == self.index and self.index != 0: # End of queue reached!
          self.index = 0
          self.session_data = []
          self.handle_event(se_tts_constants.INTERNAL_EVENT_ENDED, {"tsid":self.tts_sid, "msid":self.msid})
        else:
          if len(self.session_data) > 0:
            sentence = self.session_data[self.index]
            # TO DO handle local only config 
            tmp_file = self.get_remote_tts(sentence)
            self.log.debug(f"TTSSession.run() tmp_file: {tmp_file} sentence: {sentence}") 
            if not self.paused:
              self.play_file(tmp_file)
              self.index += 1
      time.sleep(0.01)

  def handle_skill_msg(self, msg):
    self.log.debug(f"TTSSession.handle_skill_msg() msg: {msg}") 
    msg_correlator = msg["payload"]["correlator"]
    skill_id = msg["payload"]["skill_id"]
    if "skill_id" == self.skill_id:
      if data["subtype"] == "media_player_command_response": # these come to us from the media service
        response = msg["payload"]["response"]
        if self.correlator != self.tts_sid:
          self.log.debug(f"TTSSession.handle_skill_msg() Internal issue. correlator: {self.correlator}  <> tts_sid: {self.tts_sid}")
        if self.correlator != msg_correlator:
          self.log.error(f"TTSSession.handle_skill_msg() correlators dont match! correlator: {self.correlator} msg_correlator: {self.msg_correlator}")
          return False
        if response == "session_confirm":
          self.handle_event(se_tts_constants.EVENT_MEDIA_CONFIRMED, data)
        elif response == "session_reject":
          self.handle_event(se_tts_constants.EVENT_MEDIA_DECLINED, data)
        elif response == "session_paused":
          self.handle_event(se_tts_constants.EVENT_MEDIA_PAUSED, data)
        elif response == "session_ended":
          if msg["payload"]["reason"] == "eof":
            self.handle_event(se_tts_constants.EVENT_MEDIA_ENDED, data)
          else:
            self.handle_event(se_tts_constants.EVENT_MEDIA_CANCELLED, data)
        elif response == "stop_session":
          self.log.warning("TTSSession.handle_skill_msg() Internal Error 102 - the media player reported stop_session for no reason.")
        else:                              # not expected
          self.log.warning(f"TTSSession.handle_skill_msg() Internal Error 103 - unknown media response: {response}")

