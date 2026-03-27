# Things TO DO:

## Software
### Bugs
1. Fix media skill "radio station name station name of genre station genre" bug. - Ryan is working on
1. Fix "stop" OOB msgbus_processorloop() error message.
### Features
1. Update Piper to 1.4.1 to enable GPU support - Ryan is working on
1. Add variables HubLLMmodel and SpokeLLMmodel to config file
1. Add a "move music" intent to the mpc skill - partially done - Mike is working on
1. Fix software volume control related to the ALSA device numbers - allow volume to be 0 - 11.
1. Finish the help skill - should give hints as to "what you can say". - Luca is working on
1. Write a regression test using GitHub actions, workflows and runners.
1. Go to the Internet only when necessary - for example, news, weather and sports scores. Play a chime when accessing the Internet. 
1. Add a skill to answer "Computer what is the {minimy} version?" 
1. Work on "barge in" and microphone directionality 
### Lower Priority
1. Make logging cleaner - less printing to stdout.
1. Improve TTS number pronuncaition.
1. Finish the connectivity skill.
1. Write a skill to set global variables in $HOME/install/mmconfig.yml
1. Bluetooth audio is handled by DAC/AMP. Could we implement this in minimy?

## Hardware on the Smart Boombox
### Low Priority
1. If stop button is held more than 2 seconds, do a "stop" (clear queue) rather than "pause/resume"
