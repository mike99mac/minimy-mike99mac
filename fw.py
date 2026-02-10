#!/usr/bin/env python3 
#
# fw.py - build the faster-whisper model
#
from faster_whisper import WhisperModel
import os
import sys
import socket
from framework.util.utils import Config

# Read the model from config file
cfg = Config()                             # Get config file
cfg_val = "Basic.Hub"
try:
  hub = cfg.get_cfg_val(cfg_val)
  if hub is None:
    print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
    sys.exit(1)
except Exception as e:
  print(f"ERROR calling cfg.get_cfg_val(Basic.Hub): {e}")
if hub == socket.gethostname() or hub == "localhost":
  cfg_val = "Basic.HubModel"
else:
  cfg_val = "Basic.SpokeModel"
try:
  model = cfg.get_cfg_val(cfg_val)
  if model is None:
    print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
    sys.exit(1)
except Exception as e:
  print(f"ERROR calling cfg.get_cfg_val({cfg_val}): {e}")
model = WhisperModel(model, device="cpu", compute_type="int8") # run on CPU with INT8
home_dir = os.environ.get('HOME')
segments, info = model.transcribe(f"{home_dir}/minimy-mike99mac/jfk.wav", beam_size=5)
print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
for segment in segments:
  print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
