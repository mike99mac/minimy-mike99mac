# constants used by system as message types.

"connected" = 'connected'                # sent by msg bus
"skill" = 'skill'                        # generic message sent to and received from skills
"utterance" = 'utterance'                # utterance preceeded by the wake word
"raw" = 'raw'                            # utterance not preceeded by the wake word
"media" = 'media'                        # messages to/from the media player
"system" = 'system'                      # sent by system skill/intent processor for focus requests, oob overrides, etc
"stop" = 'stop'                          # global stop message
"speak" = 'speak'                        # handle as base msg types
"register_intent" = 'register_intent'    # register_intent() only

# not used 
# MSG_TYPES = ["connected", "skill", "utterance", "media", "raw", "system", "stop", "speak", "register_intent"]


