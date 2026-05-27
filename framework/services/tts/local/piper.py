from framework.util.utils import Config
import os
import time
import logging
import subprocess

# Ensure log directory exists
home_dir = os.environ.get("HOME", "/home/pi")
log_dir = os.path.join(home_dir, "minimy/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "tts.log")

logger = logging.getLogger("tts_timing")
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

def local_speak_dialog(text, file_name, wait_q):
  print(f"local_speak_dialog() text: {text} file_name: {file_name} ")
  base_dir = os.getenv('SVA_BASE_DIR')
  cfg = Config()
  model_file = cfg.get_cfg_val('Basic.TTS.LocalVoice')
  if model_file == None:
    model_file = "en_US-hfc_male-medium.onnx"
  piper_dir = f"{base_dir}/framework/services/tts/local/piper"
  cmd = f"echo {text} | {piper_dir}/piper --quiet --model {piper_dir}/{model_file}.onnx --output_file speech.wav; aplay speech.wav"
  print(f"local_speak_dialog() cmd: {cmd}")
  start_time = time.perf_counter()
  subprocess.run(cmd, shell=True)
  elapsed = (time.perf_counter() - start_time) * 1000
  logger.info(f"TIMING TTS synthesis + playback: {elapsed:.1f} ms")
  os.system("rm speech.wav")
  wait_q.put({'service':'local', 'status':'success'})
