#
# testhubstt.py - test the Hub's STT engine
#
import os
import subprocess
import sys
from framework.util.utils import Config
home_dir = os.environ.get('HOME')
sys.path.append(f"{home_dir}/minimy")

def test_hub_stt(wav_filename, hub):
  cmd = [
    "curl",
    f"http://{hub}:5002/stt",
    "-s",
    "-H", "Content-Type: audio/wav",
    "--data-binary", f"@{wav_filename}"
  ]
  try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("=== Hub STT Response ===")
    print(result.stdout.strip())
    if result.stderr:
      print("=== STDERR ===")
      print(result.stderr.strip())
  except Exception as e:
    print(f"Error testing hub STT: {e}")

if __name__ == "__main__":
  wav_file = f"{home_dir}/minimy/jfk.wav"
  cfg = Config()                         # get config file
  cfg_val = "Basic.Hub"
  try:
    hub = cfg.get_cfg_val(cfg_val)
    print(f"hub: {hub}")
    if hub is None:
      print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
      sys.exit(1)
    test_hub_stt(wav_file, hub)
  except Exception as e:
    print(f"ERROR calling cfg.get_cfg_val(Basic.Hub): {e}")
