#!/usr/bin/env python3
#
# testhub.py - test Minimy's hub STT engine
#
import os
import subprocess
import sys
home_dir = os.environ.get('HOME')
venv_python = os.path.join(home_dir, 'minimy', 'minimy_venv', 'bin', 'python3')
if sys.executable != venv_python: # not running under the venv Python, re-execute with it
  if not os.path.exists(venv_python):
    print(f"ERROR: Virtual environment Python not found at {venv_python}")
    sys.exit(1)
  os.execv(venv_python, [venv_python] + sys.argv) # re-execute this script with the venv Python
sys.path.append(f"{home_dir}/minimy") # running under the venv Python, import modules
from framework.util.utils import Config

def test_hub_stt(wav_filename, hub):

  cmd = [
    "curl",
    f"http://{hub}:5002/stt",
    "-s",
    "--connect-timeout", "5",
    "--max-time", "10",
    "-H", "Content-Type: audio/wav",
    "--data-binary", f"@{wav_filename}" 
  ]
  try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"executing cmd: {" ".join(cmd)}")
    print(result.stdout.strip())
    if result.returncode != 0:
      print(f"Return code: {result.returncode}")
    if result.stderr:
      print("STDERR:")
      print(result.stderr.strip())
  except Exception as e:
    print(f"Error testing hub STT: {e}")

if __name__ == "__main__":
  wav_file = f"{home_dir}/minimy/jfk.wav"  # wav file to get text from
  cfg = Config()                           # get config file
  cfg_val = "Basic.Hub"
  try:
    hub = cfg.get_cfg_val(cfg_val)
    if hub is None:
      print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
      sys.exit(1)
    test_hub_stt(wav_file, hub)
  except Exception as e:
    print(f"ERROR calling cfg.get_cfg_val(Basic.Hub): {e}")
