# Things TO DO:

1. ~~Finish playlists code in the mpc skill~~
1. Fix *fallback* in mpc and speak "searching the internet for music".
1. ~~Add a global setting to mmconfig.py - buttons can be (3) buttons, (k)eyboard, or (n)one~~
1. Enable arrow keys on a RasPi 400 to replace the 3 pushbuttons (for (k)eyboard choice above)
1. If stop button is held more than 2 seconds, do a "stop" (clear queue) rather than "pause/resume" (NOTE: initial value of pin is random???)
1. Get screen shots for the README.md document.
1. Fix software volume control - not working related to the ALSA device numbers.
1. Add another STT besides Google/Polly to avoid the need for a Google API key.
1. timedate skill: when the minute is between :01 and :09, there is no "oh" spoken between the hour and minute.
1. Finish the help skill.
1. Finish the connectivity skill.
1. Ask user "Do you want me to search Wikipedia for that?" before going to fallback.
1. ~~Add a minimy.service file so it can be started by systemd.~~
1. Write a regression test.
1. Write a dictionary skill using https://pypi.org/project/PyDictionary/
1. Remove all use of mpg123 and aplay and send all audio to mpc 
1. Add ``Ask wikipedia {question}`` 


