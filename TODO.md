# Things TO DO:

## Software
1. Fix software volume control related to the ALSA device numbers.
1. Finish the help skill - should give hints as to "what you can say".
1. Finish the connectivity skill.
1. Write a regression test using GitHub actions, workflows and runners.
1. Complete the hub/spoke model where:
  - Whisper on the hub is used before whisper on localhost
  - Ollama on the hub is the fallback skill
  - If the hub is not reachable, spokes can still play music, NPR news, date, time, weather, but no fallback 
  - Rewrite Google STT? (would need an API key)

## Hardware on the smart boombox
1. Enable arrow keys on a RasPi 400 to replace the 3 pushbuttons (for (k)eyboard choice above)
1. If stop button is held more than 2 seconds, do a "stop" (clear queue) rather than "pause/resume" 
