# how long we wait for a remote 
# response before we timeout
REMOTE_TIMEOUT = 7

# these are communicated from the session to 
# the engine via the internal_event_callback
INTERNAL_EVENT_PAUSED = 'ie_paused'
INTERNAL_EVENT_ACTIVATED = 'ie_activated'
INTERNAL_EVENT_REJECTED = 'ie_rejected'
INTERNAL_EVENT_CANCELLED = 'ie_cancelled'
INTERNAL_EVENT_ENDED = 'ie_ended'

# session states
STATE_IDLE = 'idle'

STATE_ACTIVE = 'active'
STATE_ACTIVE_WAIT_PAUSED = 'active_wait_paused'
STATE_ACTIVE_WAIT_INTERNAL = 'active_wait_internal'
STATE_ACTIVE_WAIT_EXTERNAL = 'active_wait_external'
STATE_ACTIVE_PAUSED = 'active_paused'

STATE_WAIT_MEDIA_END = 'wait_media_end'
STATE_WAIT_MEDIA_END_WAIT_PAUSED = 'wait_media_end_wait_paused'
STATE_WAIT_MEDIA_END_WAIT_INTERNAL = 'wait_media_end_wait_internal'
STATE_WAIT_MEDIA_END_WAIT_EXTERNAL = 'wait_media_end_wait_external'
STATE_WAIT_MEDIA_END_PAUSED = 'wait_media_end_paused'

STATE_WAIT_MEDIA_START = 'wait_media_start'

STATE_WAIT_MEDIA_ACTIVE = 'wait_media_active'
STATE_WAIT_MEDIA_ACTIVE_WAIT_PAUSED = 'wait_media_active_wait_paused'
STATE_WAIT_MEDIA_ACTIVE_WAIT_INTERNAL = 'wait_media_active_wait_internal'
STATE_WAIT_MEDIA_ACTIVE_WAIT_EXTERNAL = 'wait_media_active_wait_external'
STATE_WAIT_MEDIA_ACTIVE_PAUSED = 'wait_media_active_paused'

STATE_WAIT_MEDIA_CANCELLED = 'wait_media_cancelled'
STATE_WAIT_MEDIA_CANCELLED_PAUSED = 'wait_media_cancelled_paused'

# session events
EVENT_START = 'start'
EVENT_STOP = 'stop'
EVENT_SPEAK = 'speak'
EVENT_PAUSE = 'pause'
EVENT_RESUME = 'resume'
EVENT_MEDIA_ENDED = 'media_ended'
EVENT_MEDIA_PAUSED = 'media_paused'
EVENT_MEDIA_CONFIRMED = 'media_confirmed'
EVENT_MEDIA_DECLINED = 'media_declined'
EVENT_MEDIA_CANCELLED = 'media_cancelled'
EVENT_INTERNAL_PAUSE = 'internal_pause'

valid_states = (
                STATE_IDLE,
                STATE_ACTIVE,
                STATE_ACTIVE_WAIT_PAUSED,
                STATE_ACTIVE_WAIT_INTERNAL,
                STATE_ACTIVE_WAIT_EXTERNAL,
                STATE_ACTIVE_PAUSED,
                STATE_WAIT_MEDIA_END,
                STATE_WAIT_MEDIA_END_WAIT_PAUSED,
                STATE_WAIT_MEDIA_END_WAIT_INTERNAL,
                STATE_WAIT_MEDIA_END_WAIT_EXTERNAL,
                STATE_WAIT_MEDIA_END_PAUSED,
                STATE_WAIT_MEDIA_START,
                STATE_WAIT_MEDIA_ACTIVE,
                STATE_WAIT_MEDIA_ACTIVE_WAIT_PAUSED,
                STATE_WAIT_MEDIA_ACTIVE_WAIT_INTERNAL,
                STATE_WAIT_MEDIA_ACTIVE_WAIT_EXTERNAL,
                STATE_WAIT_MEDIA_ACTIVE_PAUSED,
                STATE_WAIT_MEDIA_CANCELLED,
                STATE_WAIT_MEDIA_CANCELLED_PAUSED
                )
valid_events = (
                INTERNAL_EVENT_ENDED,
                EVENT_SPEAK,
                EVENT_START,
                EVENT_STOP,
                EVENT_PAUSE,
                EVENT_RESUME,
                EVENT_MEDIA_ENDED,
                EVENT_MEDIA_PAUSED,
                EVENT_MEDIA_CONFIRMED,
                EVENT_MEDIA_DECLINED,
                EVENT_MEDIA_CANCELLED,
                EVENT_INTERNAL_PAUSE
                )

