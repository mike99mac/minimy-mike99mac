#!/home/pi/minimy/minimy_venv/bin/python3
#
# testspoke.py - test localhost's STT engine
#
import os
import subprocess
import sys

def test_hub_stt(wav_filename):
  cmd = [
    "curl",
    f"http://localhost:5002/stt",
    "-s",
    "-H", "Content-Type: audio/wav",
    "--data-binary", f"@{wav_filename}"
  ]
  print(f"cmd: {cmd}")
  try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("=== localhost STT Response ===")
    print(result.stdout.strip())
    if result.stderr:
      print("=== STDERR ===")
      print(result.stderr.strip())
  except Exception as e:
    print(f"Error testing hub STT: {e}")

if __name__ == "__main__":
  wav_file = "/home/pi/minimy/jfk.wav"
  wav_file = "/home/pi/minimy/whattime.wav"
  test_hub_stt(wav_file)

