# from framework.util.utils import execute_command
import json
import os 
from subprocess import Popen, PIPE

REMOTE_TIMEOUT = 7

def execute_command(command):
  # Local execute command that returns (stdout, stderr) tuple
  p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
  stdout, stderr = p.communicate()
  stdout = str(stdout.decode('utf-8'))
  stderr = str(stderr.decode('utf-8'))
  return stdout, stderr

def remote_transcribe_file(wav_filename, return_dict, hub_name, completion_pipe):
  # use whisper to transcribe file on hub timing out after REMOTE_TIMEOUT seconds
  if not os.path.exists(wav_filename):
    print(f"_local_transcribe_file(): ERROR - File does not exist: {wav_filename}", flush=True)
    return

  try:
    cmd = f"curl http://{hub_name}:5002/stt -s -H 'Content-Type: audio/wav' --data-binary @'{wav_filename}' --max-time {REMOTE_TIMEOUT}"
    stdout, stderr = execute_command(cmd)
    if not stdout or stdout.strip() == "":
      print(f"_local_transcribe_file(): ERROR - Empty response from curl", flush=True)
      return
    res = json.loads(stdout)["text"]       # fix formatting
    if res:
      res = res.strip()
      if res[-1] == '.':
        res = res[:-1]
      print(f"remote_transcribe_file(): cmd: {cmd} res: {res}")
      return_dict['service'] = 'whisper'
      return_dict['text'] = res
    else:
      print(f"_local_transcribe_file(): ERROR - res is empty", flush=True)
  except Exception as e:                   # catch error if unable to reach remote
    print(f"Remote transcription error: {e}")
  finally:
    completion_pipe.send("done")           # signal remote transcription completed
    completion_pipe.close()
