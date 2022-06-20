Voice Assistant Framework

Components

1) Message Bus
The message bus is a combination WebSocket server and associated client
library which provides direct targeted messaging and broadcast capabilities
to WebSocket clients. Support for groups/targets is easily added. There
already exists a 'carve out' for the system monitor.

2) Input Channel (Mic)
The Mic is a python process that monitors the input channel for silence.
When a non null voice input is detected it writes a file with a timestamped
name to a well known location.

3) STT
The STT service is a python process that monitors the Mic output directory
and reads Mic output files in timestamped filename order and converts them
to text file with a timestamped name to a well known location.

4) Intent Service
The Intent service monitors the STT output directory and reads STT output
files and attempts to match them against end-points which have previously
registered with the intent service. The output of the intent service is a always
a message of either type RAW or WAKE WORD QUALIFIED. Qualified messages
(messages preceded by the wake word) are further delineated by being either
INTENT MATCHED or UNMATCHED in which case they are broadcast on the
message bus.

5) Output Channel (Media Service)
The media service responds to message bus requests. It provides the output
channel and associated management in the form of media sessions. A typical
media session request might be to play a file or media stream. The media
service never denies a new media session request, it simply stacks the
sessions. This decision is made above at a higher level. The media service
always ignores requests not originated by the current session owner.

6) TTS Service
The TTS service responds to message bus requests to convert text to wav
files. It is interruptible and manages multiple simultaneous requests using
a unique sessionID. Like the media service, the TTS service never denies a
request for a new session, it simply stacks them. It also ignores requests
from anyone with an invalid session ID.

7) System Skill
The system skill manages the interaction of skills within the system.
It handles focus requests and out of band (OOB) messaging necessary
to provide a consistent response to system level input events. It is
driven completely by the message bus.

8) Skill Library
The skill library is a collection of intrinsic functions available to all
skills which inherit from the base class. This includes such things as
'speak()', 'get_user_input()', 'converse()' and other utilities which make
it easier to voice augment existing applications. The library is an
extension of the base class and honors system level protocols for channel
focus and related activities.

9) Skills
Skills are Linux processes which interact with the system using the
message bus. They augment existing applications by utilizing the voice
assistant framework to convert text input and output to audio input
and output. Currently the system framework base class has only been
ported to the Python programming language.


Foundational Concepts

A) Channels
Central to the framework is the concept of a channel. A channel may be
either input or output based. For example, typically the Mic program  
manages the input channel and the media player manages the output
channel.

B) Sessions
A session is a unique ID created by the TTS service and the Media service.
The service will only honor requests from the owner of the currently
active session so for example if a skill which does not own the current
session requests the media player to play a file it will be ignored.

C) Focus
An audio channel is a critical resource in that only one source should be
able to control it at a given point in time. Audio channel usage is serialized
by skills requesting focus from the system skill.

D) Activities
An activity is a well defined system level event which has a start and end
time associated with it. Activities are user level contracts which help the
system to determine the overall state of the system.

A typical activity might
be the 'speak' event triggered by a skill invoking its 'speak' method. This
'speak' method includes not only the text to speak, but a callback method
which the skill will have called when the speak activity has ended. The activity
object passed to the skill will contain the results of the activity. For example
'success', 'timed-out', 'rejected', etc.

Theory of Operation

The framework is constructed around the concept of audio channels. An
audio channel can be either an input or output channel. The system skill
is concerned with managing control of the audio channels among all the
competing entities by restricting access to the channels using the concept
of an audio session.

Access to an audio channel requires a skill to request a channel session
from the system skill using the message bus. This is all accomplished
behind the scenes by the skill base class which honors the protocol
where sessions are requested from the system skill and direct access
to the channels is restricted.

The system skill uses the skill category to determine what to do with
audio channel requests. One of four possible outcomes may occur …

1) Request Denied
2) Request Causes Current Session to be Terminated and New Session to be Played
3) Request Causes Current Session to be Paused and New Session to be Played
4) Request Causes New Session to be Mixed With Current Session

This behavior is consistent across input and output channels.

Out of band messages are typically (but not always) single word verbs like
'stop' or 'pause', 'resume', etc.

These OOBs are handled differently for several reasons but the bottom line
is they are handled by the system skill which handles default behavior and
also allows skills to override this default behavior.

The typical example of why one might want to override the system's default
behavior is the alarm skill which when active, plays an annoying sound which
the OOB verb 'stop' should cause to discontinue. This type of dynamic
interception of the 'stop' OOB and associated management is handled by the
system skill.


This is what the happy path looks like when a skill invokes its 'speak()' 
method. Note the speak method lives in the base class and its signature is

speak(text,callback)

Where callback is optional. When supplied it is the function which will be 
invoked when the speak has completed and the skill can once again be considered 
idle.

When a skill executes 'speak('bla bla bla') the following happy path steps are taken ...

    The skill base class 'speak' method sends a 'request output focus' message to the system skill.

    The system skill sends back a 'focus granted' message (remember, this is the happy path).

    The skill base class requests a TTS session from the TTS service.

    The TTS service requests a media session from the media service.

    The media service sends back a new media session id to the TTS service.

    The TTS service sends back a TTS 'session confimed' message which contains the new TTS session id.

    The skill base class uses this id in the 'speak' message it sends out.

    The TTS service converts the text from the 'speak' message into .wav files and sends them to the media player.

    The media player informs the TTS service it has completed playing the files when the last file has ended.

    The TTS service informs the skill the session has ended.

    The skill base class notifies the system skill it is releasing output focus.

    The skill base class invokes the skill callback method if one was provided.

One reason for the complexity arises from the ability to stack skills which requires 
the media service to manage sessions as well as the TTS service. In fact, the skill 
base class must also maintain a LIFO so skills may interrupt themselves. For example, 
I might want to be able to say 'wiki tell me about the war of 1812' and while listening 
to the answer ask 'what was the 7 years war' and while that is responding I might ask 
yet another question. I should be able to stack these requests and associated responses 
infinitely. At least the underlying system should not arbitrarily restrict this capability.

Adding 'pause' and 'resume' also requires some dexterity on behalf of the system to manage 
not only the commands 'pause' and 'resume' but the internal pausing and resuming the system 
may do in order to interrupt one skill and launch another.

But perhaps the main reason for the complexity lies in the fact that the happy path while 
complicated enough will rarely be taken. For example, it is often the case while the TTS 
service is converting text to wav files and sending them to the media player the media 
player may exhaust its play queue for this session (underrun) which will cause it to send 
a ‘session ended’ message to the TTS service which will need to acquire a new one before 
it may resume streaming to the media service.   


Advanced Topics

- Intent clash for media type is handled by Media Abstraction (old CPS)
- Intent clash for question and answer type is handled by QnA Abstraction (old CQS)
- System Skill Interactions (currently decision is static, category based, could be expanded)
- Dynamic OOB Handling (take over an OOB verb for a period of time)
- Skill Self Interruption Modes (1=default/stack, 2=terminate, 3=ignore, etc)
- Dynamic Intents (simple but currently not supported, related to like Dynamic OOB)
- Intent Types (currently NLP/NLU what would it take to integrate regex, others)






