from framework.util.utils import Config
import os

def local_speak_dialog(text, file_name, wait_q):
  # convert text to speech locally using piper 
  print(f"local_speak_dialog() text: {text} file_name: {file_name} ")
  base_dir = os.getenv('SVA_BASE_DIR')
  cfg = Config()
  model_file = cfg.get_cfg_val('Basic.TTS.LocalVoice')
  if model_file == None:                   # voice not found in config file
    model_file = "en_US-hfc_male-medium.onnx"
  piper_dir = f"{base_dir}/framework/services/tts/local/piper"
  cmd = f"echo {text} | {piper_dir}/piper --quiet --model {piper_dir}/{model_file}.onnx --output_file speech.wav; aplay speech.wav"
  print(f"local_speak_dialog() cmd: {cmd}")
  os.system(cmd)                           # piper creates speech.wav then plays it
  os.system("rm speech.wav")
  wait_q.put({'service':'local', 'status':'success'})
