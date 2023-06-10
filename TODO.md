Things TO DO:

- mpc skill:
    - Fix *fallback*: when music is requested but not found in the music library, there should be a message saying "searching the internet"
There is a callback to speak_lang(), but it does not seem to be working in this case.
    - Finish playlists code
- Add another STT besides Amazon/Polly to avoid the need for an API key
- timedate skill: when the minute is between :01 and :09, there is no "oh" spoken between the hour and minute
- The help skill is not finished
- The connectivity skill is not finished
- Add code to buttons.py that enables the arrow keys on a RasPi 400 to replace the 3 pushbuttons 
- If I ask "What's my IP address", there is no such skill - so it falls back to Wikipedia.
Add a converse: "Do you want me to search Wikipedia for that?"
- Add vocabulary: "Ask wikipedia {question}"
- Write a regression test
