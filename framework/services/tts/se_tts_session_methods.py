import se_tts_constants

class TTSSessionMethods:
  def __init__(self):
    pass

  def handle_event(self, event, msg):
    self.log.info(f"TTSSessionMethods.handle_event() state: {self.state} event: {event} owner: {self.owner} tts_sid: {self.tts_sid} msid: {self.msid}")
    if event in self.valid_events:
      branch_key = self.state + ':' + event
      if branch_key in self.SE:
        return self.SE[branch_key](msg)
      else:
        self.log.warning(f"TTSSession Error - no State/Event entry. state: {self.state} event: {event}")
    return False

  def __change_state(self, new_state):
    if new_state == self.state:
      self.log.warning(f"TTSSessionMethods.change_state() - warning illogical state change from {self.state} to {new_state}")
      return False
    if new_state not in self.valid_states:
      self.log.warning("TTSSession change_state() - warning invalid state change '%s' not a valid state, ignored" % (new_state,))
      return False
    self.log.info("TTSSessionMethods.__change_state() - from '%s' to '%s'. owner:%s, tts_sid:%s, msid:%s" % (self.state, new_state, self.owner, self.tts_sid, self.msid))
    self.state = new_state
    return True

  def _idle_start(self, msg):
    # idle state 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_START)
    self.correlator = msg['correlator']
    self.send_media_session_request()

  def _wms_stop(self, msg):
    # wait media start state - pause is ignored
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wms_confirmed(self, msg):
    # going from wait active to active
    self.__change_state(se_tts_constants.STATE_ACTIVE)
    self.msid = msg['session_id']
    self.index = 0
    self.paused = False
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_ACTIVATED, msg)

  def _wms_declined(self, msg):
    self.__change_state(se_tts_constants.STATE_IDLE)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_REJECTED, msg)

  def _active_pause(self, msg):
    # active state 
    self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_PAUSED)
    self.paused = True
    self.wait_paused(msg['from_skill_id'])

  def _active_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _active_speak(self, msg):
    if msg['skill_id'] != self.owner:
      self.log.warning("TTSSession play request from invalid source. source:%s, current_owner:%s" % (msg['skill_id'], self.owner))
      return False
    self.add(chunk_text(msg['text']))  # add the text to the active speak 

  def _active_ended(self, msg):
    self.send_media_session_request()
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_ACTIVE)

  def _active_cancelled(self, msg):
    self.__change_state(se_tts_constants.STATE_IDLE)

  def _active_tts_session_ended(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END)

  def _awp_external_pause(self, msg):
    # active paused states 
    self.external_pause = True             # we got an external pause confirm
    if self.internal_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_INTERNAL)

  def _awp_internal_pause(self, msg):
    self.internal_pause = True
    if self.external_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_EXTERNAL)

  def _awi_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _awi_internal_pause(self, msg):
    self.__change_state(se_tts_constants.STATE_ACTIVE_PAUSED)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)

  def _awe_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _awe_external_pause(self, msg):
    self.__change_state(se_tts_constants.STATE_ACTIVE_PAUSED)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)

  def _ap_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _ap_resume(self, msg):
    self.__change_state(se_tts_constants.STATE_ACTIVE)
    self.paused = False
    self.send_session_resume()

  def _ap_speak(self, msg):
    # add the text to the active speak q
    self.add( chunk_text( msg['text'] ) )

  def _wma_stop(self, msg):
    # wait media active state 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wma_speak(self, msg):
    # add the text to the active speak 
    self.add( chunk_text( msg['text'] ) )

  def _wma_confirmed(self, msg):
    self.__change_state(se_tts_constants.STATE_ACTIVE)
    self.msid = msg['session_id']

  def _wma_declined(self, msg):
    self.__change_state(se_tts_constants.STATE_IDLE)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_REJECTED,msg)

  def _wmawi_stop(self, msg):
    # wait media active paused states 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmawi_internal_pause(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_PAUSED)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)

  def _wmawe_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmawe_external_pause(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_PAUSED)
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)

  def _wmawp_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmawp_internal_pause(self, msg):
    self.internal_pause = True
    if self.external_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession._wmawp_internal_pause() got internal, waiting for external pause")
      self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_EXTERNAL)

  def _wmawp_external_pause(self, msg):
    self.external_pause = True
    if self.internal_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession._wmawp_external_pause() - waiting for internal pause")
      self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_INTERNAL)

  def _wmap_pause(self, msg):
    self.external_pause = True             # we got an external pause confirm
    if self.internal_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession._wmap_pause(): waiting for internal pause")

  def _wmap_internal_pause(self, msg):
    self.internal_pause = True
    if self.external_pause:
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession._wmap_internal_pause(): waiting for external pause")

  def _wmap_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmap_resume(self, msg):
    self.__change_state(se_tts_constants.STATE_ACTIVE)
    self.paused = False
    self.send_session_resume()

  def _wmc_ended(self, msg):
    # wait media cancelled state 
    self.__change_state(se_tts_constants.STATE_IDLE)
    self.session_data = []
    self.index = 0
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_CANCELLED,msg)

  def _wmc_pause(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_PAUSE_CANCELLED)
    self.paused = True
    self.wait_paused(msg['from_skill_id'])

  def _wmcp_resume(self, msg):
    # wait media cancelled paused state 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.paused = False
    self.send_session_resume()

  def _wme_pause(self, msg):
    # wait media end state 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_PAUSED)
    self.wait_paused(msg['from_skill_id'])

  def _wme_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wme_ended(self, msg):
    self.__change_state(se_tts_constants.STATE_IDLE)
    self.session_data = []
    self.index = 0
    self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_ENDED,msg)

  def _wmewp_stop(self, msg):
    # wait media end paused states 
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmewp_internal_pause(self, msg):
    self.internal_pause = True
    if self.external_pause:
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED)
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession got internal, waiting for external pause")
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_EXTERNAL)

  def _wmewp_external_pause(self, msg):
    self.external_pause = True
    if self.internal_pause:
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED)
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession got external, waiting for internal pause")
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_INTERNAL)

  def _wmewi_internal_pause(self, msg):
    self.internal_pause = True
    if self.external_pause:
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED)
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_EXTERNAL)

  def _wmewe_external_pause(self, msg):
    self.external_pause = True
    if self.internal_pause:
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED)
      self.external_pause = False
      self.internal_pause = False
      self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
    else:
      self.log.debug("TTSSession got external, waiting for internal pause")
      self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_INTERNAL)

  def _wmep_stop(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
    self.stop_media_session()

  def _wmep_resume(self, msg):
    self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END)
    self.paused = False
    self.send_session_resume()

