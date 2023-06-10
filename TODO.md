Things TO DO:

- mpc skill:
    - Fix *fallback*: when music is requested and is not found in the music library, there should be a message saying "checking on internet"
There is a callback to speak_lang(), but it does not seem to be working in this case.
    - Finish playlists code
- Add another STT besides Amazon/Polly to avoid the need for an API key
- timedate skill: when the minute is between :01 and :09, there is no "oh" spoken between the hour and minute
- Write a regression test
- The help skill is not finished
- The connectivity skill is not finished
