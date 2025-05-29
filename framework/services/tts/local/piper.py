from framework.util.utils import execute_command, Config
import os

def local_speak_dialog(text, file_name, wait_q):
  # convert text to speech locally using piper 
  print(f"local_speak_dialog() text: {text} file_name: {file_name} ")
  base_dir = os.getenv('SVA_BASE_DIR')
  model_file = get_cfg_val('Advanced.TTS.LocalVoice')
  if model_file == None:                   # voice not found in config file
    model_file = "en_US-hfc_male-medium.onnx"
  piper_dir = f"{base_dir}/framework/services/tts/local/piper"
  config_file = f"{base_dir}/install/mmconfig.yml"
  cmd = f"echo {text} | {piper_dir}/piper --model {piper_dir}/{model_file}.onnx --output_file speech.wav; aplay speech.wav"
  print(f"local_speak_dialog() cmd: {cmd}")
  os.system(cmd)                           # piper creates speech.wav then plays it
  os.system("rm speech.wav")
  wait_q.put({'service':'local', 'status':'success'})
    
