import se_tts_constants

class TTSSessionTable:
    def __init__(self):
        self.SE = {
                se_tts_constants.STATE_IDLE                            + ':' + se_tts_constants.EVENT_START:             self._idle_start,

                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.EVENT_STOP:              self._active_stop,
                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.EVENT_SPEAK:             self._active_speak,
                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.EVENT_PAUSE:             self._active_pause,
                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.EVENT_MEDIA_ENDED:       self._active_ended,
                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.EVENT_MEDIA_CANCELLED:   self._active_cancelled,
                se_tts_constants.STATE_ACTIVE                          + ':' + se_tts_constants.INTERNAL_EVENT_ENDED:    self._active_tts_session_ended,

                se_tts_constants.STATE_ACTIVE_WAIT_PAUSED              + ':' + se_tts_constants.EVENT_STOP:              self._ap_stop,
                se_tts_constants.STATE_ACTIVE_WAIT_PAUSED              + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._awp_internal_pause,
                se_tts_constants.STATE_ACTIVE_WAIT_PAUSED              + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._awp_external_pause,

                se_tts_constants.STATE_ACTIVE_WAIT_INTERNAL            + ':' + se_tts_constants.EVENT_STOP:              self._awi_stop,
                se_tts_constants.STATE_ACTIVE_WAIT_INTERNAL            + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._awi_internal_pause,

                se_tts_constants.STATE_ACTIVE_WAIT_EXTERNAL            + ':' + se_tts_constants.EVENT_STOP:              self._awe_stop,
                se_tts_constants.STATE_ACTIVE_WAIT_EXTERNAL            + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._awe_external_pause,

                se_tts_constants.STATE_ACTIVE_PAUSED                   + ':' + se_tts_constants.EVENT_STOP:              self._ap_stop,
                se_tts_constants.STATE_ACTIVE_PAUSED                   + ':' + se_tts_constants.EVENT_RESUME:            self._ap_resume,
                se_tts_constants.STATE_ACTIVE_PAUSED                   + ':' + se_tts_constants.EVENT_SPEAK:             self._ap_speak,

                se_tts_constants.STATE_WAIT_MEDIA_START                + ':' + se_tts_constants.EVENT_STOP:              self._wms_stop,
                se_tts_constants.STATE_WAIT_MEDIA_START                + ':' + se_tts_constants.EVENT_MEDIA_CONFIRMED:   self._wms_confirmed,
                se_tts_constants.STATE_WAIT_MEDIA_START                + ':' + se_tts_constants.EVENT_MEDIA_DECLINED:    self._wms_declined,
                se_tts_constants.STATE_WAIT_MEDIA_START                + ':' + se_tts_constants.EVENT_MEDIA_CANCELLED:   self._wms_declined,

                se_tts_constants.STATE_WAIT_MEDIA_END                  + ':' + se_tts_constants.EVENT_STOP:              self._wme_stop,
                se_tts_constants.STATE_WAIT_MEDIA_END                  + ':' + se_tts_constants.EVENT_MEDIA_ENDED:       self._wme_ended,
                se_tts_constants.STATE_WAIT_MEDIA_END                  + ':' + se_tts_constants.EVENT_MEDIA_CANCELLED:   self._wme_ended,
                se_tts_constants.STATE_WAIT_MEDIA_END                  + ':' + se_tts_constants.EVENT_PAUSE:             self._wme_pause,

                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_PAUSED      + ':' + se_tts_constants.EVENT_STOP:              self._wmewp_stop,
                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_PAUSED      + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._wmewp_internal_pause,
                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_PAUSED      + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._wmewp_external_pause,

                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_INTERNAL    + ':' + se_tts_constants.EVENT_STOP:              self._wmewp_stop,
                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_INTERNAL    + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._wmewi_internal_pause,

                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_EXTERNAL    + ':' + se_tts_constants.EVENT_STOP:              self._wmewp_stop,
                se_tts_constants.STATE_WAIT_MEDIA_END_WAIT_EXTERNAL    + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._wmewe_external_pause,

                se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED           + ':' + se_tts_constants.EVENT_STOP:              self._wmep_stop,
                se_tts_constants.STATE_WAIT_MEDIA_END_PAUSED           + ':' + se_tts_constants.EVENT_RESUME:            self._wmep_resume,

                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_STOP:              self._wma_stop,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_SPEAK:             self._wma_speak,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_MEDIA_CONFIRMED:   self._wma_confirmed,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_MEDIA_DECLINED:    self._wma_declined,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_MEDIA_ENDED:       self._wma_declined,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.EVENT_MEDIA_CANCELLED:   self._wma_declined,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE               + ':' + se_tts_constants.INTERNAL_EVENT_ENDED:    self._wma_declined,

                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_PAUSED   + ':' + se_tts_constants.EVENT_STOP:              self._wmawp_stop,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_PAUSED   + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._wmawp_internal_pause,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_PAUSED   + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._wmawp_external_pause,

                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_INTERNAL + ':' + se_tts_constants.EVENT_STOP:              self._wmawi_stop,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_INTERNAL + ':' + se_tts_constants.EVENT_INTERNAL_PAUSE:    self._wmawi_internal_pause,

                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_EXTERNAL + ':' + se_tts_constants.EVENT_STOP:              self._wmawe_stop,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_WAIT_EXTERNAL + ':' + se_tts_constants.EVENT_MEDIA_PAUSED:      self._wmawe_external_pause,

                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_PAUSED        + ':' + se_tts_constants.EVENT_STOP:              self._wmap_stop,
                se_tts_constants.STATE_WAIT_MEDIA_ACTIVE_PAUSED        + ':' + se_tts_constants.EVENT_RESUME:            self._wmap_resume,

                se_tts_constants.STATE_WAIT_MEDIA_CANCELLED            + ':' + se_tts_constants.EVENT_MEDIA_DECLINED:    self._wmc_ended,
                se_tts_constants.STATE_WAIT_MEDIA_CANCELLED            + ':' + se_tts_constants.EVENT_MEDIA_ENDED:       self._wmc_ended,
                se_tts_constants.STATE_WAIT_MEDIA_CANCELLED            + ':' + se_tts_constants.EVENT_MEDIA_CANCELLED:   self._wmc_ended,
                }

