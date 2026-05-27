#!/usr/bin/env python3
#
# find_respeaker.py - Check if reSpeaker mic array is present
#
import pyaudio
import sys

def get_respeaker_index():
  p = pyaudio.PyAudio()
  for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0 and "reSpeaker XVF3800" in info['name']:
      p.terminate()
      return i
    p.terminate()
    return None

if __name__ == "__main__":
  idx = get_respeaker_index()
  if idx is not None:
    print(idx)
    else:
      sys.exit(1)
