#!/usr/bin/env python3 
#
# fw.py - build the faster-whisper model
#
from faster_whisper import WhisperModel
import os

model_size = "tiny.en"
model = WhisperModel(model_size, device="cpu", compute_type="int8") # run on CPU with INT8
home_dir = os.environ.get('HOME')
segments, info = model.transcribe(f"{home_dir}/minimy-mike99mac/jfk.wav", beam_size=5)
print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

