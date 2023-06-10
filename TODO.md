# Things TO DO:

1. mpc skill:
    - Fix *fallback*: when music is requested but not found in the music library, there should be a message saying "searching the internet"
There is a callback to speak_lang(), but it does not seem to be working in this case.
    - Finish playlists code
1. Fix software volume control - not working related to the ALSA device numbers
1. Add another STT besides Amazon/Polly to avoid the need for an API key
1. timedate skill: when the minute is between :01 and :09, there is no "oh" spoken between the hour and minute
1. The help skill is not finished
1. The connectivity skill is not finished
1. Add code to buttons.py that enables the arrow keys on a RasPi 400 to replace the 3 pushbuttons
1. If I ask "What's my IP address", there is no such skill - so it falls back to Wikipedia.
Add a converse: "Do you want me to search Wikipedia for that?"
1. Add vocabulary: "Ask wikipedia {question}"
1. Write a regression test

