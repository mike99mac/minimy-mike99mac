#!/usr/bin/env /home/pi/minimy/venv_ngv/lib/python3.11
#
# fw.py - build the faster-whisper model
#
from faster_whisper import WhisperModel

model_size = "tiny.en"
model = WhisperModel(model_size, device="cpu", compute_type="int8") # run on CPU with INT8
segments, info = model.transcribe("/home/pi/minimy-mike99mac/jfk.wav", beam_size=5)
print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

