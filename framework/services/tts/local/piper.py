import os

def local_speak_dialog(text, filename, wait_q):
  print(f"local_speak_dialog() text = {text} filename = {filename} ")
  base_dir = os.getenv('SVA_BASE_DIR')
  if base_dir is None:
    base_dir = os.getcwd()
    print("Warning, SVA_BASE_DIR environment variable is not set. Defaulting it to %s" % (base_dir,))
  config_file = base_dir + '/install/mmconfig.yml'
  cmd = f"echo {text} | piper --model {base_dir}/voice/en_US-lessac-medium.onnx --output_file speech.wav;aplay speech.wav"
  os.system(cmd)
  os.system("rm speech.wav")
  wait_q.put({'service':'local', 'status':'success'})
    
