# Things TO DO:

## Software
### Bugs
### Features
1. Add a "move music" intent to the mpc skill - partially done - Mike is working on
1. Fix software volume control related to the ALSA device numbers - allow volume to be 0 - 11.
1. Write a regression test using GitHub actions, workflows and runners.
1. Go to the Internet only when necessary - for example, news, weather and sports scores. Play a chime when accessing the Internet. 
1. Add a skill to answer "Computer what is the {minimy} version?" 
1. Work on "barge in" and microphone directionality 
### Goals for Summer 2026
1. Get directional mic working - Accomplished manually but need to automate
1. Make llama-cpp-python a system service
1. Finish move music intent
1. Work on internet searching skill
### Lower Priority
1. Make logging cleaner - less printing to stdout.
1. Finish the connectivity skill.
1. Write a skill to set global variables in $HOME/install/mmconfig.yml
1. Bluetooth audio is handled by DAC/AMP. Could we implement this in minimy?

## Hardware on the Smart Boombox
### Low Priority
1. If stop button is held more than 2 seconds, do a "stop" (clear queue) rather than "pause/resume"
