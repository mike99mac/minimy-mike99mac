# Things TO DO:

1. mpc skill:
    - Fix *fallback*: when music is requested but not found in the music library, there should be a message saying "searching the internet".
There is a callback to speak_lang(), but it does not seem to be working.
    - Finish playlists code
1. Add a global setting to mmconfig.py - buttons can be:
    - (3) buttons, 
    - (k)eyboard, or
    - (n)one
1. Enable arrow keys on a RasPi 400 to replace the 3 pushbuttons (for (k)eyboard choice above)
1. ~~If stop button is held more than 2 seconds, do a "stop" (clear queue) rather than "pause/resume"~~
1. Get screen shots for the README.md document.
1. Fix software volume control - not working related to the ALSA device numbers.
1. Add another STT besides Google/Polly to avoid the need for a Google API key.
1. timedate skill: when the minute is between :01 and :09, there is no "oh" spoken between the hour and minute.
1. Finish the help skill.
1. Finish the connectivity skill.
1. If I ask "What's my IP address", there is no such skill - so it falls back to Wikipedia.
Usually that is not what the user wants. Add a converse: "Do you want me to search Wikipedia for that?"
1. Add vocabulary: "Ask wikipedia {question}"
1. Write a .service file so Minimy is started by systemd.
1. Write a regression test.

