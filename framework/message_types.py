# manifest constants used by the system
# as message types.

# sent by msg bus
MSG_CONNECTED = 'connected'

# generic message sent to 
# and received from skills
MSG_SKILL = 'skill'

# an utterance which has been 
# preceeded by the wake word
MSG_UTTERANCE = 'utterance'

# an utterance which has not been
# preceeded by the wake word
MSG_RAW = 'raw'

# messages to/from the media player
MSG_MEDIA = 'media'

# sent by the system skill
# and the intent processor
# used for focus requests,
# oob overrides and such
MSG_SYSTEM = 'system'

# global stop message
MSG_STOP = 'stop'

# technically, these could be 
# subtypes of type 'skill' but 
# I found it more efficient to
# handle them as base msg types
MSG_SPEAK = 'speak'

# register_intent() only
MSG_REGISTER_INTENT = 'register_intent'

# someday this could be used for validation
MSG_TYPES = [
        MSG_CONNECTED,
        MSG_SKILL,
        MSG_UTTERANCE,
        MSG_MEDIA,
        MSG_RAW,
        MSG_SYSTEM,
        MSG_STOP,
        MSG_SPEAK,
        MSG_REGISTER_INTENT
        ]

## TODO subtypes 

