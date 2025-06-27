import io
from framework.util.utils import Config, execute_command

def remote_transcribe_file(speech_file):
  # TO DO: get hub host name from config file
  cmd = 'curl http://papabear:5002/stt -H "Content-Type: audio/wav" --data-binary @"%s"' % (wav_filename,)
  out = execute_command(cmd)
  res = out.strip()
  print(f"_local_transcribe_file(): cmd: {cmd} res: {res}")
  if res != '':
    return_dict['service'] = 'whisper'
    return_dict['text'] = res

