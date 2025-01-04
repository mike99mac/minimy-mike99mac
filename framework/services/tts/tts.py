import threading, urllib3, time, os, re
from se_tts_session import TTSSession
from threading import Event, Thread
from framework.util.utils import LOG, chunk_text, aplay
from bus.MsgBusClient import MsgBusClient
from framework.message_types import MSG_SPEAK, MSG_SKILL, MSG_MEDIA
# TTS internally generated events. specifically, these
# are generated by the tts session and handled in the 
# internal_event_handler() in the base engine class
from se_tts_constants import (
    INTERNAL_EVENT_PAUSED,
    INTERNAL_EVENT_ACTIVATED,
    INTERNAL_EVENT_CANCELLED, 
    INTERNAL_EVENT_ENDED
    )
# the engine pushes these events to the session
from se_tts_constants import EVENT_STOP as SESSION_EVENT_STOP
from se_tts_constants import EVENT_PAUSE as SESSION_EVENT_PAUSE
from se_tts_constants import EVENT_RESUME as SESSION_EVENT_RESUME

# TTS Engine states
STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'
STATE_WAIT_ACTIVE = 'wait_active'
STATE_PAUSED = 'paused'
STATE_WAIT_PAUSED_START = 'wait_paused_start'
STATE_WAIT_PAUSED = 'wait_paused'
STATE_WAIT_STOPPED = 'wait_stopped'

# TTS Engine events
EVENT_SPEAK = 'speak'
EVENT_START = 'start'
EVENT_STOP = 'stop'
EVENT_PAUSE = 'pause'
EVENT_RESUME = 'resume'
EVENT_RESET = 'reset'

class TTSEngine:
  """ 
  the TTS Engine manages TTS Sessions in response to user/skill requests. note the difference between 
  states 'wait_paused' and 'wait_paused_start' is that wait_paused assumes this is a simple pause/resume
  while wait_paused_start assumes you are pausing the current session because you want to start a new one
  """

  def internal_event_handler(self, event, info):
    # handle events generated by the session
    self.log.debug(f"TTSEngine.internal_event_handler() event: {event} info: {info}")
    self.handle_event(event, info)

  def get_session_guts(self):
    # poor man's deepcopy
    session_guts = {}
    session_guts['state'] = self.current_session.state
    session_guts['index'] = self.current_session.index
    session_guts['owner'] = self.current_session.owner
    session_guts['tts_sid'] = self.current_session.tts_sid
    session_guts['msid'] = self.current_session.msid
    session_guts['correlator'] = self.current_session.correlator
    session_guts['session_data'] = self.current_session.session_data
    return session_guts

  def set_session_guts(self, session_guts):
    self.current_session.state = session_guts['state']
    self.current_session.index = session_guts['index']
    self.current_session.owner = session_guts['owner']
    self.current_session.tts_sid = session_guts['tts_sid']
    self.current_session.msid = session_guts['msid'] 
    self.current_session.correlator = session_guts['correlator'] 
    self.current_session.session_data = session_guts['session_data']

  # state/event helpers 
  def handle_event(self, event, msg):
    self.log.info(f"TTSEngine.handle_event() state: {self.state} event: {event} owner: {self.current_session.owner} tts_sid: {self.current_session.tts_sid} msid: {self.current_session.msid}")
    if event in self.valid_events:
      branch_key = self.state + ':' + event
      if branch_key in self.SE:
        return self.SE[branch_key](msg)
      else:
        self.log.warning(f"TTSEngine.handle_event() Error - no State/Event entry. state: {self.state} event: {event} msg: {msg}")
    return False

  def __change_state(self, new_state):
    if new_state == self.state:
      self.log.warning(f"TTSEngine.change_state() warning illogical state change from {self.state} to {new_state} ignored")
      return False

    if new_state not in self.valid_states:
      self.log.warning(f"TTSEngine.change_state() warning invalid state change {new_state} not a valid state, ignored")
      return False

    self.log.info(f"TTSEngine.change_state() from state: {self.state} to '%s'. owner: {self.current_session.owner} ttsid: {self.current_s} msid: {self.current_session.msid}")
    self.state = new_state
    return True

  # TTS session messages. these are ecxchanged between
  # the TTS Engine and the user/skill 
  def send_paused_confirmed_message(self, target, tts_sid):
    self.log.debug(f"TTSEngine.send_paused_confirmed_message() target: {target} tts_sid: {tts_sid}")
    info = {
        'error':'',
        'subtype':'tts_service_command_response',
        'response':'paused_confirmed',
        'session_id':tts_sid,
        'skill_id':target,
        'from_skill_id':self.skill_id,
        }
    self.bus.send(MSG_SKILL, target, info)

  def send_session_confirm(self, target, sid):
    self.log.debug(f"TTSEngine.send_session_confirm() target: {target} sid: {sid}")
    info = {
        'error':'',
        'subtype':'tts_service_command_response',
        'response':'session_confirm',
        'session_id':sid,
        'skill_id':target,
        'from_skill_id':self.skill_id,
        }
    self.bus.send(MSG_SKILL, target, info)

  def send_session_reject(self,reason,target):
    info = {
        'error':reason,
        'subtype':'tts_service_command_response',
        'response':'session_reject',
        'skill_id':target,
        'from_skill_id':self.skill_id,
        }
    self.bus.send(MSG_SKILL, target, info)

  def send_session_end_notify(self, skill_id):
    self.log.debug(f"TTSEngine.send_session_end_notify() skill_id: {skill_id}")
    info = {
        'error':'',
        'subtype':'tts_service_command_response',
        'response':'session_ended',
        'session_id':self.current_session.tts_sid,
        'skill_id':skill_id,
        'from_skill_id':self.skill_id,
        }
    self.current_session.owner = None
    self.bus.send(MSG_SKILL, skill_id, info)

  # state/event handlers
  def _idle_start(self, msg):
    self.__change_state(STATE_WAIT_ACTIVE)
    self.current_session.reset( msg['from_skill_id'] )
    self.current_session_id += 1
    self.current_session.tts_sid = self.current_session_id
    self.current_session.correlator = self.current_session_id
    msg['correlator'] = self.current_session_id
    self.current_session.handle_event(EVENT_START, msg)

  def _idle_pause(self, msg):
    aplay(self.aplay_filename)
    self.send_paused_confirmed_message(self.current_session.owner, self.current_session.tts_sid)

  def _active_start(self, msg):
    self.__change_state(STATE_WAIT_PAUSED_START)
    self.possible_new_session_owner = msg['from_skill_id'] 
    self.log.info(f"TTSEngine._active_start(): skill {self.possible_new_session_owner} is interrupting active skill {self.current_session.owner}")
    self.current_session.handle_event(SESSION_EVENT_PAUSE, msg)

  def _active_stop(self, msg):
    self.__change_state(STATE_WAIT_STOPPED)
    # stop current session
    self.log.debug(f"TTSEngine._active_stop() telling session to stop. current_tts_sid: {self.current_session.tts_sid} correlator: {self.current_session} owner: {self.current_session.owner}")
    self.current_session.handle_event(SESSION_EVENT_STOP, msg)

  def _active_speak(self, msg):
    if msg['skill_id'] != self.current_session.owner:
      self.log.warning(f"TTSEngine._active_speak(): play request from invalid skill_id: {msg['skill_id']} current_owner: {self.current_session.owner}")
      return False
    # otherwise, add the text to the active speak q
    self.current_session.add( chunk_text( msg['text'] ) )
    self.current_session.paused = False

  def _active_ended(self, msg):
    self.send_session_end_notify(self.current_session.owner)
    if len(self.saved_tts_sessions) > 0:
      self.__change_state(STATE_ACTIVE)
      # restore paused session
      saved_tts_session = self.saved_tts_sessions.pop()
      self.log.debug(f"TTSEngine._active_ended() just restored session: {saved_tts_session}")
      self.set_session_guts( saved_tts_session )
    else:
      self.__change_state(STATE_IDLE)

  def _active_pause(self, msg):
    self.__change_state(STATE_WAIT_PAUSED)
    self.current_session.handle_event(SESSION_EVENT_PAUSE, msg)

  def _active_resume(self, msg):
    self.current_session.handle_event(SESSION_EVENT_RESUME, msg)

  def _wait_active_activated(self, msg):
    self.__change_state(STATE_ACTIVE)
    self.current_session.correlator = self.current_session_id
    self.current_session.tts_sid = self.current_session_id
    self.log.debug(f"TTSEngine._wait_active_activated() owner: {self.current_session.owner} tts_sid: {self.current_session.tts_sid} msid: {self.current_session.msid} correlator: {self.current_session.correlator}")
    self.send_session_confirm(self.current_session.owner, self.current_session.tts_sid)

  def _wait_active_rejected(self, msg):
    self.__change_state(STATE_IDLE)
    self.send_session_reject('media_reject', self.current_session.owner)

  def _wait_active_start(self, msg):
    self.send_session_reject('tts_busy', msg['from_skill_id'])

  def _wait_active_stop(self, msg):
    self.__change_state(STATE_WAIT_STOPPED)
    self.current_session.handle_event(SESSION_EVENT_STOP, msg)

  def _wait_active_ended(self, msg):
    self.__change_state(STATE_IDLE)

  def _wp_start(self, msg):
    self.__change_state(STATE_WAIT_PAUSED_START)
    self.possible_new_session_owner = msg['from_skill_id'] 

  def _wp_stop(self, msg):
    self.__change_state(STATE_WAIT_STOPPED)
    self.current_session.handle_event(SESSION_EVENT_STOP, msg)

  def _wp_paused(self, msg):
    # the current session has been paused. 
    self.__change_state(STATE_PAUSED)
    self.log.debug("TTSEngine._wp_paused() Session Paused")
    aplay(self.aplay_filename)
    self.send_paused_confirmed_message(self.current_session.owner, self.current_session.tts_sid)

  def _wp_resume(self, msg):
    self.__change_state(STATE_ACTIVE)
    self.current_session.handle_event(SESSION_EVENT_RESUME, msg)

  def _wp_speak(self, msg):
    if msg['skill_id'] != self.current_session.owner:
      self.log.warning(f"TTSEngine._wp_speak(): ignoring play request from invalid source: {msg['skill_id']} current_owner: {self.current_session.owner}")
      return False
    # otherwise, add the text to the active speak q
    self.current_session.add( chunk_text( msg['text'] ) )

  def _wp_ended(self, msg):
    self.__change_state(STATE_IDLE)

  def _paused_reset(self, msg):
    # clear tts session
    self.current_session.handle_event(SESSION_EVENT_RESUME, msg)
    self.current_session.session_data = []
    self.current_session.index = 0
    # clear associated media session
    info = {
        'error':'',
        'subtype':'media_player_command',
        'command':'reset_session',
        'session_id':self.current_session.msid,
        'skill_id':'media_player_service',
        'from_skill_id':self.current_session.owner
        }
    self.bus.send(MSG_MEDIA, 'media_player_service', info)

  def _paused_resume(self, msg):
    self.__change_state(STATE_ACTIVE)
    self.log.debug(f"TTSEngine._paused_resume() owner: {self.current_session.owner} saved_tts_sessions: {self.saved_tts_sessions}")
    self.current_session.handle_event(SESSION_EVENT_RESUME, msg)

  def _paused_speak(self, msg):
    if msg['skill_id'] != self.current_session.owner:
      self.log.warning(f"TTSEngine._paused_speak() ignoring play request from invalid source: {msg['skill_id']} owner: {self.current_session.owner}")
      return False
    # otherwise, add the text to the active speak q
    self.current_session.add( chunk_text( msg['text'] ) )
    
  def _paused_stop(self, msg):
    self.log.debug(f"TTSEngine._paused_stop()")
    self.__change_state(STATE_WAIT_STOPPED)
    self.current_session.handle_event(SESSION_EVENT_STOP, msg)

  def _paused_start(self, msg):
    self.log.debug(f"TTSEngine._paused_start()")
    self.__change_state(STATE_WAIT_ACTIVE)
    self.saved_tts_sessions.append(self.get_session_guts() )
    self.current_session.reset(msg['from_skill_id'] )
    self.current_session_id += 1
    msg['correlator'] = self.current_session_id
    self.current_session.handle_event(EVENT_START, msg)

  def _ws_start(self, msg):
    # we are waiting for our current session to end but we are asked to start a new session
    self.log.error("TTSEngine._ws_start() MAYBE BUG wait_end start not supported yet! calling idle start")
    #self.send_session_reject('tts_busy', msg['from_skill_id'])
    return self._idle_start(msg)

  def _ws_done(self, msg):
    self.log.debug(f"TTSEngine._ws_done()")
    self.send_session_end_notify(self.current_session.owner)
    if len(self.saved_tts_sessions) > 0:
      self.__change_state(STATE_ACTIVE)
      # restore paused session
      saved_tts_session = self.saved_tts_sessions.pop()
      self.log.debug(f"TTSEngine._ws_done() restored session: {saved_tts_session}")
      self.set_session_guts( saved_tts_session )
    else:
      self.__change_state(STATE_IDLE)

  def _wps_paused(self, msg):
    self.log.debug(f"TTSEngine._ws_paused()")
    # current session has confirmed it is paused
    # we notify the requestor
    self.send_paused_confirmed_message(self.current_session.owner, self.current_session.tts_sid)

  def _wps_start(self, msg):
    self.log.debug(f"TTSEngine._wps_start()")
    self.saved_tts_sessions.append( self.get_session_guts() )
    self.current_session.reset( self.possible_new_session_owner )
    self.current_session_id += 1
    self.current_session.correlator = self.current_session_id
    self.current_session.tts_sid = self.current_session_id
    msg['correlator'] = self.current_session_id
    self.current_session.handle_event(EVENT_START, msg)

  def _wps_resume(self, msg):
    self.log.error("TTSEngine._wps_resume() BUG not handled wps_resume!!!!")

  def _wps_stop(self, msg):
    # while waiting for paused with a stacked start request
    # we get a stop command. this is ambiguous but we can use
    # the tts session ID to determine which session to stop
    self.log.error("TTSEngine_wps_stop() BUG not handled wps_stop!!!!")

  def _wps_done(self, msg):
    # while waiting for the session to pause with a 
    # stacked start request it reports it is done.
    self.log.error("TTSEngine_wps_stop() BUG not handled wps_done!!!!")

  # engine constructor
  def __init__(self):
    self.skill_id = 'tts_service'
    self.bus = MsgBusClient(self.skill_id)
    base_dir = os.getenv('SVA_BASE_DIR')
    log_filename = base_dir + '/logs/tts.log'
    self.log = LOG(log_filename).log
    self.log.info("Starting TTS Service")
    self.aplay_filename = base_dir + "/framework/assets/ding.wav"

    # these relate to tts sessions
    self.current_session_id = 0
    self.paused_filename = None
    self.paused_requestor = None

    # tts session lifo
    self.saved_tts_sessions = []

    # the current session
    self.current_session = TTSSession(None, 0, 0, [], self.internal_event_handler, self.log)
    self.current_session_thread = threading.Thread(target=self.current_session.run)
    self.current_session_thread.start()

    self.state = STATE_IDLE

    self.valid_states = [STATE_IDLE,
      STATE_ACTIVE,
      STATE_WAIT_ACTIVE,
      STATE_PAUSED,
      STATE_WAIT_PAUSED_START,
      STATE_WAIT_PAUSED,
      STATE_WAIT_STOPPED]

    self.valid_events = [EVENT_START,
      EVENT_STOP,
      EVENT_SPEAK,
      EVENT_PAUSE,
      EVENT_RESUME,
      INTERNAL_EVENT_ACTIVATED,
      INTERNAL_EVENT_CANCELLED,
      INTERNAL_EVENT_ENDED,
      INTERNAL_EVENT_PAUSED]
    self.SE = {
        STATE_IDLE         + ':' + EVENT_START:        self._idle_start,
        STATE_IDLE         + ':' + EVENT_PAUSE:        self._idle_pause,

        STATE_WAIT_ACTIVE    + ':' + EVENT_START:        self._wait_active_start,
        STATE_WAIT_ACTIVE    + ':' + EVENT_STOP:         self._wait_active_stop,
        STATE_WAIT_ACTIVE    + ':' + INTERNAL_EVENT_ACTIVATED: self._wait_active_activated,
        STATE_WAIT_ACTIVE    + ':' + INTERNAL_EVENT_CANCELLED: self._wait_active_ended,
        STATE_WAIT_ACTIVE    + ':' + INTERNAL_EVENT_ENDED:   self._wait_active_ended,

        STATE_ACTIVE       + ':' + EVENT_START:        self._active_start,
        STATE_ACTIVE       + ':' + EVENT_STOP:         self._active_stop,
        STATE_ACTIVE       + ':' + EVENT_RESET:        self._paused_reset,
        STATE_ACTIVE       + ':' + EVENT_SPEAK:        self._active_speak,
        STATE_ACTIVE       + ':' + EVENT_PAUSE:        self._active_pause,
        STATE_ACTIVE       + ':' + EVENT_RESUME:       self._active_resume,
        STATE_ACTIVE       + ':' + INTERNAL_EVENT_ENDED:   self._active_ended,

        STATE_WAIT_PAUSED    + ':' + EVENT_START:        self._wp_start,
        STATE_WAIT_PAUSED    + ':' + EVENT_STOP:         self._wp_stop,
        STATE_WAIT_PAUSED    + ':' + INTERNAL_EVENT_PAUSED:  self._wp_paused,
        STATE_WAIT_PAUSED    + ':' + EVENT_RESUME:       self._wp_resume,
        STATE_WAIT_PAUSED    + ':' + EVENT_SPEAK:        self._wp_speak,
        STATE_WAIT_PAUSED    + ':' + INTERNAL_EVENT_ENDED:   self._wp_ended,
        STATE_WAIT_PAUSED    + ':' + INTERNAL_EVENT_CANCELLED: self._wp_ended,

        STATE_PAUSED       + ':' + EVENT_START:        self._paused_start,
        STATE_PAUSED       + ':' + EVENT_STOP:         self._paused_stop,
        STATE_PAUSED       + ':' + EVENT_RESUME:       self._paused_resume,
        STATE_PAUSED       + ':' + EVENT_SPEAK:        self._paused_speak,
        STATE_PAUSED       + ':' + EVENT_RESET:        self._paused_reset,

        STATE_WAIT_STOPPED     + ':' + EVENT_START:        self._ws_start,
        STATE_WAIT_STOPPED     + ':' + INTERNAL_EVENT_ENDED:   self._ws_done,
        STATE_WAIT_STOPPED     + ':' + INTERNAL_EVENT_CANCELLED: self._ws_done,

        STATE_WAIT_PAUSED_START  + ':' + EVENT_START:        self._wps_start,
        STATE_WAIT_PAUSED_START  + ':' + EVENT_STOP:         self._wps_stop,
        STATE_WAIT_PAUSED_START  + ':' + EVENT_RESUME:       self._wps_resume,
        STATE_WAIT_PAUSED_START  + ':' + INTERNAL_EVENT_ENDED:   self._wps_done,
        STATE_WAIT_PAUSED_START  + ':' + INTERNAL_EVENT_CANCELLED: self._wps_done,
        STATE_WAIT_PAUSED_START  + ':' + INTERNAL_EVENT_PAUSED:  self._wps_paused,
        }
    self.bus.on(MSG_SKILL, self.handle_skill_msg)
    self.bus.on(MSG_SPEAK, self.handle_speak_msg)

    self.log.info("TTSEngine.__init__() Initialized")

  def handle_speak_msg(self, msg):
    self.log.debug(f"TTSEngine.handle_speak_msg() data: {msg.data}")
    self.handle_event(EVENT_SPEAK, msg.data)

  def handle_skill_msg(self,msg):
    data = msg.data
    self.log.debug(f"TTSEngine.handle_skill_msg() received skill msg. state: {self.state} msid: {self.current_session.msid} data: {data}")
    if data['skill_id'] == self.skill_id:
      if data['subtype'] == 'tts_service_command':
        # these come from our users
        if data['command'] == 'start_session':
          return self.handle_event(EVENT_START, data)
        if data['command'] == 'stop_session':
          return self.handle_event(EVENT_STOP, data)
        if data['command'] == 'pause_session':
          return self.handle_event(EVENT_PAUSE, data)
        if data['command'] == 'resume_session':
          return self.handle_event(EVENT_RESUME, data)
        if data['command'] == 'reset_session':
          self.log.warning("handle_skill_msg() TTS ENG NEW RESET HIT!")
          # TO DO - it is disturbing that the direct call works but the handle_event call does not!!!!
          # fix it!
          #return self.handle_event(EVENT_RESET, data)
          return self._paused_reset(data)

# main()
if __name__ == '__main__':
  tts_eng = TTSEngine()
  Event().wait()                           # wait forever

