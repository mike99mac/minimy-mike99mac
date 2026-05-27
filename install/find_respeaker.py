#!/usr/bin/env python3
#
# find_respeaker.py - Check if reSpeaker mic array is present
#
import sys
import os
import pyaudio

def get_respeaker_index():
  # Suppress ALSA error messages by redirecting stderr temporarily
  stderr_fileno = sys.stderr.fileno()
  devnull = os.open(os.devnull, os.O_WRONLY)
  saved_stderr = os.dup(stderr_fileno)
  os.dup2(devnull, stderr_fileno)

  p = pyaudio.PyAudio()
  idx = None
  for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if "reSpeaker XVF3800" in info['name']:
      idx = i
      break
  p.terminate()

  # Restore stderr
  os.dup2(saved_stderr, stderr_fileno)
  os.close(devnull)
  os.close(saved_stderr)
  return idx

if __name__ == "__main__":
  idx = get_respeaker_index()
  if idx is not None:
    print(idx)
  else:
    sys.exit(1)
