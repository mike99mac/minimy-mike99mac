import json
import os 
from subprocess import Popen, PIPE

REMOTE_TIMEOUT = 7

def execute_command(command):
  # Local execute command that returns (stdout, stderr) tuple
  p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
  stdout, stderr = p.communicate()
  return (
    str(stdout.decode('utf-8')),
    str(stderr.decode('utf-8')),
    p.returncode
  )

def remote_transcribe_file(wav_filename, return_dict, hub_name, completion_pipe):
  # use whisper to transcribe file on hub timing out after REMOTE_TIMEOUT seconds
  if not os.path.exists(wav_filename):
    print(f"remote_transcribe_file(): ERROR - File does not exist: {wav_filename}", flush=True)
    completion_pipe.send("error")          # signal remote transcription completed
    return
  try:
    cmd = f"curl http://{hub_name}:5002/stt -s -H 'Content-Type: audio/wav' --data-binary @'{wav_filename}' --max-time {REMOTE_TIMEOUT}"
    stdout, stderr, returncode = execute_command(cmd)
    if returncode != 0:
      print(f"RETURN CODE: {returncode}")
      print("remote_transcribe_file(): ERROR - Hub is not reachable")
      completion_pipe.send("error")        # signal remote transcription completed
      return
    if not stdout or stdout.strip() == "":
      print(f"stdout: [{stdout}] stderr: [{stderr}]")
      print("remote_transcribe_file(): ERROR - Empty response from curl", flush=True)
      completion_pipe.send("done")         # signal remote transcription completed
      return
    print(f"DEBUG: Raw curl output: '{stdout}'")
    print(f"DEBUG: Output length: {len(stdout)}")
    res = json.loads(stdout)["text"]       # fix formatting
    if res is not None:
      res = res.strip()
      if res[-1] == '.':
        res = res[:-1]
      print(f"remote_transcribe_file(): cmd: {cmd} res: {res}")
      return_dict['service'] = 'whisper'
      return_dict['text'] = res
      completion_pipe.send("done")         # signal remote transcription completed
    else:
      print("remote_transcribe_file(): ERROR - res is empty", flush=True)
      completion_pipe.send("done")         # signal remote transcription completed
  except Exception as e:                   # catch error if unable to reach remote
    print(f"Remote transcription error: {e}")
    completion_pipe.send("done")          # signal remote transcription completed
  finally:
    completion_pipe.close()
