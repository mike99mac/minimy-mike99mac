from framework.util.utils import Config
import os
import time
import logging

# Setup logger for TTS timing
home_dir = os.environ.get("HOME")
log_file = os.path.join(home_dir, "minimy/logs/tts.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
tts_logger = logging.getLogger("tts.timing")

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
  os.system(cmd)
  elapsed = (time.perf_counter() - start_time) * 1000
  tts_logger.info(f"TIMING TTS synthesis + playback: {elapsed:.1f} ms")
  os.system("rm speech.wav")
  wait_q.put({'service':'local', 'status':'success'})
