# constants used by system as message types.

MSG_CONNECTED = 'connected'                # sent by msg bus
MSG_SKILL = 'skill'                        # generic message sent to and received from skills
MSG_UTTERANCE = 'utterance'                # utterance preceeded by the wake word
MSG_RAW = 'raw'                            # utterance not preceeded by the wake word
MSG_MEDIA = 'media'                        # messages to/from the media player
MSG_SYSTEM = 'system'                      # sent by system skill/intent processor for focus requests, oob overrides, etc
MSG_STOP = 'stop'                          # global stop message
MSG_SPEAK = 'speak'                        # handle as base msg types
MSG_REGISTER_INTENT = 'register_intent'    # register_intent() only

# not used 
# MSG_TYPES = [MSG_CONNECTED, MSG_SKILL, MSG_UTTERANCE, MSG_MEDIA, MSG_RAW, MSG_SYSTEM, MSG_STOP, MSG_SPEAK, MSG_REGISTER_INTENT]


