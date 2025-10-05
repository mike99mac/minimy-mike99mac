from framework.util.utils import execute_command
import json

def remote_transcribe_file(wav_filename, return_dict, hub_name, completion_pipe):
  try:
    cmd = f"curl http://{hub_name}:5002/stt -s -H 'Content-Type: audio/wav' --data-binary @'{wav_filename}'"
    out = execute_command(cmd)
    res = json.loads(out)["text"]          # Fix formatting
    if res:
      res = res.strip()
      if res[-1] == '.':
        res = res[:-1]
      print(f"remote_transcribe_file(): cmd: {cmd} res: {res}")
      return_dict['service'] = 'whisper'
      return_dict['text'] = res
  except Exception as e:                   # Catch error if unable to reach remote
    print(f"Remote transcription error: {e}")
  finally:
    completion_pipe.send("done")           # Signal remote transcription completed
    completion_pipe.close()
