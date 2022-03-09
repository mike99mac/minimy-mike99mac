TTS, Speak and Associated Life Cycle

When a skill calls its 'speak' method the base class (sva_base.py) goes through a number of steps. First, it sends a message to the system skill requesting output focus. If this is confirmed, the base class then requests a TTS session from the TTS service. Once the TTS session has been acquired one or more 'speak' messages are sent to the TTS service over the message bus. When the TTS session and associated media session have completed, the base class sends a message to the system skill releasing output focus. It is at this point the skill is considered done with the speak request and its callback method will be invoked.

The base class will also handle pause and resume requests as well as stop messages on behalf of the skill without the skill being aware of any of this.

The TTS service consists of a base TTS Engine which manages one or more 'TTS Sessions'. A TTS session converts an array of sentences into a series of .wav files and sends them to the media service which ultimately plays them. TTS sessions and media sessions may be paused, stopped, resumed or interrupted at any time. It is the responsibility of the TTS session to maintain synchronization with the media service for its TTS sessions.

The TTS service and the media service do not deny requests. They both stack requests by first pausing the session and then saving it to a LIFO queue. It is the responsibility of the 'system skill' to manage output focus. This is accomplished by the skill base class requesting output focus. The system skill evaluates output focus requests and returns one of the following results ...

1) Stop - the currently active skill and then grant output focus to the new skill
2) Pause - the currently active skill and then grant output focus to the new skill
3) Mix - the audio from the new skill with the existing skill's output
4) Deny - output focus to the requesting skill

The system skill makes it's determination based on the category of the currently active skill and the category of the requesting skill. 

The TTS service is implemented as a couple of state/event machines (TTS Engine and TTS Session). There are two images which represent the state event trasnition diagrams for the sessions of the TTS service. There is no such diagram for the TTS Engine as it is a relatively simple branch table.

The tts_pause_states.png file shows the various states associated with pausing a session. This is the same for all states. What this image demonstrates is that a TTS session can not be considered paused until both the TTS session producer thread and the associated media session have both confirmed they are paused. 

The TTS session creates an internal pause confirmation event while the media service sends a message which is converted to an external pause confirmation event. When both these events have been received the session can transition to the paused state at which point it communicates this event to the TTS Engine. A similar flow occurs in response to 'stop' requests.

The file tts_session_states.png shows a simlified version of the TTS session states without the associated pause states described above. This state event transition diagram shows the TTS session basically transitions from 'Idle' to 'Wait Media Start' upon reception of a 'start' request. If a negative response is received from the media service the requestor is notified and the session returns to the 'Idle' state. Upon reception of a positive response from the media service the session notifies the TTS Engine who sends out a TTS session confirmation to the requesting skill. At this point 'speak' messages may be sent to the TTS service.

The 'Wait Media Active' state is necessary because sometimes the media service will complete playing its queue before the TTS session can produce the next .wav file. When the TTS session attempts to send the next .wav file to the media service it will find the media session has completed and so it will need to renegotiate a new one before it may play the next .wav file. While it is waiting for the new media session it is in the 'Wait Media Active' state. Once the new media session has been acquired the session will return to the 'Active' state.

The complexity of the TTS service arises from the fact that any event may be received while in any state. So for example, while the TTS service is attempting to acquie a media session it may be interrupted by a new 'start' request. This could happen in the 'Active' state, the 'Wait Media Active' state, any of the pause states, etc. 


TTS Session Happy Path

The happy path of a TTS Session is depicted by image file 'tts_happy_paths.jpg'. This file attempts to demonstrate the following ...

Upon reception of a 'start' request while in the 'idle' state the session must first attempt to acquire a media session to play its TTS so a message is sent to the media service requesting a new session. The state is changed to 'waiting_active' to indicate the session is now in the process of going active but awaiting confirmation from the media service.

Upon reception of a 'session confirm' response while in the 'wait_active' state the session changes to the 'active' state and then sends a positive confirmation TTS session response with the new TTS session ID to the requestor of the new TTS session.

Upon reception of a 'speak' message while in the 'active' state the session appends the request to the end of the internal TTS session queue. Note it is because we have a local TTS session which has a queue as well as an associated media session which itself has an internal queue, that when we issue a 'stop' or 'pause' request we must wait for BOTH to respond before we may signal to the TTS Engine that the session has actually completed the request. These surface in the code as the constants INTERNAL_EVENT_PAUSED and INTERNAL_EVENT_STOPPED.

At some point the TTS session will have depleted its queue. At this point it will generate an internal done event which will cause it to transition to the 'wait_media_end' state. The session is now waiting for the media service to send a message indicating it too has depleted its queue which means the TTS session has entirely completed.

Upon reception of a 'media_end' event while in the 'wait_media_end' state, the session will transition to the 'idle' state and generate an internal TTS session ended event which will be handled by the TTS Engine. 

This is the basic life cycle of a TTS session, except for pause. 

The happy path also shows a simple pause process flow but this is a very simplified depiction of a much more complicated process. The actual process of handling pause consists of about 5 differen states and may bee seen in more detail in the file named 'tts_pause_states.png'. Keep in mind, any state which responds to a pause message must ultimately have these additional 5 states as well which complicates things considerably. The state event transition diagram depicted by 'tts_session_states.png' also does not include associated pause state detail.







