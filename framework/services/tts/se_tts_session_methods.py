import se_tts_constants

class TTSSessionMethods:
    def __init__(self):
        pass

    def handle_event(self, event, msg):
        self.log.info("TTSSession handle_event. state=%s, event=%s. owner:%s, tts_sid:%s, msid:%s" % (self.state, event, self.owner, self.tts_sid, self.msid))
        if event in self.valid_events:
            branch_key = self.state + ':' + event
            if branch_key in self.SE:
                return self.SE[branch_key](msg)
            else:
                self.log.warning("TTSSession Error - no State/Event entry. state=%s, event=%s" % (self.state, event))
        return False

    def __change_state(self, new_state):
        if new_state == self.state:
            self.log.warning("TTSSession change_state() - warning illogical state change from '%s' to '%s' ignored" % (self.state, new_state))
            return False

        if new_state not in self.valid_states:
            self.log.warning("TTSSession change_state() - warning invalid state change '%s' not a valid state, ignored" % (new_state,))
            return False

        self.log.info("TTSSession change_state() - from '%s' to '%s'. owner:%s, tts_sid:%s, msid:%s" % (self.state, new_state, self.owner, self.tts_sid, self.msid))
        self.state = new_state
        return True

    #################### 
    ## the idle state ##
    #################### 
    def _idle_start(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_START)
        self.correlator = msg['correlator']
        self.send_media_session_request()

    ################################
    ## the wait media start state ##
    ## note we ignore pause       ##
    ################################
    def _wms_stop(self, msg):
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
        self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_REJECTED,msg)

    ######################
    ## the active state ##
    ######################
    def _active_pause(self, msg):
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
        # add the text to the active speak q
        self.add( chunk_text( msg['text'] ) )

    def _active_ended(self, msg):
        self.send_media_session_request()
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_ACTIVE)

    def _active_cancelled(self, msg):
        self.__change_state(se_tts_constants.STATE_IDLE)

    def _active_tts_session_ended(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_END)

    ##########################
    ## active paused states ##
    ##########################
    def _awp_external_pause(self, msg):
        # we got an external pause confirm
        self.external_pause = True
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

    #################################
    ## the wait media active state ##
    #################################
    def _wma_stop(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
        self.stop_media_session()

    def _wma_speak(self, msg):
        # add the text to the active speak q
        self.add( chunk_text( msg['text'] ) )

    def _wma_confirmed(self, msg):
        self.__change_state(se_tts_constants.STATE_ACTIVE)
        self.msid = msg['session_id']

    def _wma_declined(self, msg):
        self.__change_state(se_tts_constants.STATE_IDLE)
        self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_REJECTED,msg)

    #########################################
    ## the wait media active paused states ##
    #########################################
    def _wmawi_stop(self, msg):
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
            self.log.debug("TTSSession got internal, waiting for external pause")
            self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_EXTERNAL)

    def _wmawp_external_pause(self, msg):
        self.external_pause = True
        if self.internal_pause:
            self.external_pause = False
            self.internal_pause = False
            self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
        else:
            self.log.debug("TTSSession got external, waiting for internal pause")
            self.__change_state(se_tts_constants.STATE_ACTIVE_WAIT_INTERNAL)

    def _wmap_pause(self, msg):
        # we got an external pause confirm
        self.external_pause = True
        if self.internal_pause:
            self.external_pause = False
            self.internal_pause = False
            self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
        else:
            self.log.debug("TTSSession got external, waiting for internal pause")

    def _wmap_internal_pause(self, msg):
        self.internal_pause = True
        if self.external_pause:
            self.external_pause = False
            self.internal_pause = False
            self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_PAUSED,msg)
        else:
            self.log.debug("TTSSession got internal, waiting for external pause")

    def _wmap_stop(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
        self.stop_media_session()

    def _wmap_resume(self, msg):
        self.__change_state(se_tts_constants.STATE_ACTIVE)
        self.paused = False
        self.send_session_resume()

    ####################################
    ## the wait media cancelled state ##
    ####################################
    def _wmc_ended(self, msg):
        self.__change_state(se_tts_constants.STATE_IDLE)
        self.session_data = []
        self.index = 0
        self.internal_event_callback(se_tts_constants.INTERNAL_EVENT_CANCELLED,msg)

    def _wmc_pause(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_PAUSE_CANCELLED)
        self.paused = True
        self.wait_paused(msg['from_skill_id'])

    ###########################################
    ## the wait media cancelled paused state ##
    ###########################################
    def _wmcp_resume(self, msg):
        self.__change_state(se_tts_constants.STATE_WAIT_MEDIA_CANCELLED)
        self.paused = False
        self.send_session_resume()

    ##############################
    ## the wait media end state ##
    ##############################
    def _wme_pause(self, msg):
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

    ######################################
    ## the wait media end paused states ##
    ######################################
    def _wmewp_stop(self, msg):
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

