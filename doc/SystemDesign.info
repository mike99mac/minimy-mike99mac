GENERAL
-------
The system assumes a linux environment and is written entirely 
in the Python programming language. Many skills rely on the 
presence of 'wget', 'ffmpeg' and other standard linux system 
utilities. Specifically these are ...

mpg123 - play mp3 files
aplay - play wav files
wget - get web pages
curl - get API results
ffmpeg - convert files between audio formats

The system is easily ported to custom hardware environments. The
ability to capture input and control output volume are basically
all that are needed to successfully deploy the system to a 
new hardware evironment. 

The file mic.py is used to detect user utterances. It listens for
silence and then writes a time stamped audio file to a well known
location on the file system. Replacing this file is all that is
needed to port the system to a custom 'input hardware' environment. 

Likewise the system needs the ability to control the volume of the 
output device. This is typically accomplished using the linux 
'amixer' command, however the system also supports a Mycroft Mark2
device by default, and this hardware requires a custom driver to
control the TI Amplifier. If you look in the configuration files
under the hal directory you will see an executables directory
which contains any user created programs which may be used to control
the hardware (output device) for the environment. The file hal.cfg
contains the mapping between user supplied commands and the system.

So from a high level the system needs an input driver (mic.py) 
which writes audio files to a well known file location using a 
standardized file naming convention and when the system needs
to control the volume of the output device it uses the hal.cfg 
file to determine what commands are used to control the output 
device volume.


BARGE-IN
--------
The system supports barge-in but the end results will be as good 
as your echo and noise cancellation. Devices like the Mark2 or a
good headset will work very well. Laptops relying on their built
in mic and speaker will need some special attention. This basically
consists of correctly adjusting the microphone and speaker levels.

The system already differentiates between "wake word utterance" and
"wake word (short delay) utterance" by playing an audible beep when
a wake word by itself is detected. At this point, the system 
will duck the output briefly (max 3 seconds) so the user may give
a command without the background media playing. This tends to reduce
false positives and improve barge-in behavior.


SKILLS
------
Basically, everything could have been implemented as a skill. 
If you look in the system_skills/directory you will see the volume
skill for example, there is no reason this could not be a user
skill. The media service was initially a user skill but I 
discovered that with the system skill and the media service, the
base (sva_base.py) class had too many if then elses in the main
code path so I broke them out into a system skill which does not
inherit from SimpleVoiceAssistant() then sva_base was a lot cleaner.

The primary goal of this framework is to provide a simple run-time
environment which facilitates the development of voice enabled 
applications.


VERIFICATION
------------
To verify your speaker and microphone are working
correctly execute this command on your computer.

arecord test.wav

and say something, then hit CTL+C. Then execute this command

aplay test.wav

and if you hear yourself you are good to go for basic input and
output. If not, get this fixed before proceeding.



OLDER DOCUMENTATION
-------------------

The script configure.py modifies the sva.cfg file. This file is used
at run time to determine whether to use local or remote STT and/or TTS
as well as what the wake word(s) will be. You should run this and then
the test_reconition.sh script to experiment with different combinations
of local and remote TTS and STT. 

General Usage
-------------
Typically if you try to stop an active skill saying the wake word followed
by the word 'stop' does not work very well partially because the recognizers
have difficulty with short words. Wake word followed by the word ' terminate'
usually works better.

Barge in works however, if you don't have good echo cancellation like that
provided by a headset you may get poor recognition because of the speaker
feeding back into the microphone. To help combat this the system will mute
the output if you just say the wake word and wait a second. This often helps
to interrupt an active skill that is producing a lot of loud output like a
media skill playing a song or long running Q&A skill.


Implementation
--------------
The directory 'save_audio/' is used by the mic.py script to store wav files.
the stt.py script reads from this directory and converts these to
text strings which it writes to 'save_text/' directory where the nlp
intent processor will pick them up and try to interpret them. Each file name
includes a timestamp so when used in this manner these directories provide
a rudimentary queue which may shared by any process using standard
unix file sharing mechanisms without the need for shared memory. 

Informational utterances are not supported. Commands and questions are.
Central to the NLP system is the concept of sentence type. Sentences are
broadly categorized as follows ...

  Commands 
  WH type questions
  Yes/No type questions
  Conversational questions (could you please do bla)
  Informational sentences. 

Of these, informational sentences are largely ignored when detected.

The system also categorizes utterances as 'wake word qualified' and 'raw'
input. Any utterance which is not immediately preceeded by a wake word
is considered a raw utterance. Raw utterances are largely ignored by the
system except when active skills are in a conversant state. Conversant mode
is a state where a skill registers to receive raw utterances. 

There is also the concept of an out of band message, common in many 
communication protocols. An out of band message is typically defined as a
single word verb which is used to relay a system level command. Examples of
out of band commands are 'stop' (and its aliases 'terminate', 'cancel' and
'abort'), 'pause', 'resume', 'help' and other media related commands like 
'skip', 'rewind', 'snooze', etc.


System Components
-----------------
The system is comprised of a message bus, audio input (mic.py), speech to 
text (stt.py) text to speech (tts.py) and finally to intent matching and 
skills. Intent matching is accomplished using shallow natural language
parsing.

Skills are the executables which actually perform tasks, respond to 
input, etc.

There are four basic types of skills ...

1) System skills
2) Media skills
3) Question and Answer skills
4) User skills

System skills help coordinate the environment. For example, when a skill 
wishes to use the system output device (typically the speaker) it must
request focus from the system skill. These skills may be found in the 

skills/system_skills/

subdirectory.

Media skills are skills which play media like audio files (music, videos).
The Youtube skill is an example of a media skill.

Question and answer skills are skills which can respond to questions. 
The Wiki skill is an example of a Q&A skill. Both may be found under the

skills/user_skills/

subdirectory.

User skills are skills which do not wish to play media or respond to 
generic questions. 

Central to the concept of skills is the concept of an intent match. An intent
match occurs when an intent a skill registers with the system is matched as a
response to audio input. 

Intents are specifically a match of three components ...

1) Sentence type
2) Subject
3) Verb

Sentence type is either 'Q' for question, 'C' for command or 'I' for 
informational. Informational sentences are currently ignored.

Typically a skill will register an intent for something it controls or
something it wishes to respond to. So for example, a skill which will
control the lights in a house might register the following intents ...

C - set, light
C - change, light
C - turn, light

Then, when any utterance was recognized which was a command for the light
the skill which registered these intents would be executed. Notice the skill
did not recognize invalid combinations, so for example, while the skill 
supports setting, changing and turning on/off a light, it does not 
support running or playing a light because these would make no logical, and
by extension grammatical sense.

The same 'light' skill might also want to respond to questions about the 
lights it controls. In this case it might also register the following intent ...

Q - what, light

Now any questions like 'what is the hall light set to' would cause the 'light'
skill to be executed. 

In this context, the term 'executed' means the skill will be called at the 
callback for the intent it provided when it registered the intent with 
the system.

Intents are registered with the system 'intent service' and communicated over
the message bus. When the 'intent service' detects an utterances which matches
the intent it will send a message to the skill using the message bus and the 
call the skill registered with the intent will be invoked. 

The intent service is based on natural language processing and as a result is
extremely English language specific. 

Skills also handle message bus messages. The message bus is the primary
method of inter skill communication. Skill developers do not need to
concern themselves with the system architecture as the speak() and play_media()
calls take care of all the underlying processing. See the Skill Developer API
document for more information on built-in capabilities of skills.


Shallow Parsing
---------------
See the README in the shallow_parse directory on how to produce
grammatical rules and associated parsers.

Note shallow_parse/command_rule_handlers.py is where the 
grammar handlers for command style utterances are.

The parse_sentence.py and parse_question.py files are
the high level parsers. 


System Monitor
-------------
monitor/system_monitor.html is a web page that will show the various attributes of
the system, like the message bus, dialogs, etc. open it using any standard
browser once you have started the system. If running on a different device you 
can point to that device using the system monitor by clicking on the MiniMy logo
at the top right corner of the screen.


