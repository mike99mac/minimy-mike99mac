import os
import urllib3
from framework.util.utils import execute_command

class remote_tts:
  """
  Convert text to speech locally with piper
  Set piper executable in self.piper_cmd
  """
  def __init__(self):
    base_dir = os.getenv('SVA_BASE_DIR')
    self.piper_cmd = f"{base_dir}/framework/services/tts/local/piper/piper"

  def remote_speak(self, text, filename, wait_q):
    status = 'fail'
    command = f"{self.piper_cmd} {text}" 
    try:
      res = execute_command(command)
      status = 'success'
    except:
      pass
    wait_q.put({'service':'remote', 'status':status})

