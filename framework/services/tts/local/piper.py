import os
import requests
import subprocess
from framework.util.utils import LOG

base_dir = os.getenv("SVA_BASE_DIR", os.path.expanduser("~/minimy"))
log_filename = os.path.join(base_dir, "logs/tts.log")
log = LOG(log_filename).log

def local_speak_dialog(text, _file_name, wait_q):
  # Client function used by tts.py session system. Calls the Piper server.
  log.info(f"Session TTS request: {text[:50]}...")
  try:
    resp = requests.post(
      "http://localhost:5004/tts",
      json={"text": text},
      timeout=10.0
    )
    if resp.status_code != 200:
      log.error(f"TTS server returned {resp.status_code}")
      wait_q.put({'service': 'local', 'status': 'error', 'msg': f"Server error {resp.status_code}"})
      return

    audio_data = resp.content
    temp_wav = "/tmp/speech.wav"
    with open(temp_wav, "wb") as f:
      f.write(audio_data)
    subprocess.run(["aplay", temp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(temp_wav)
    log.info("Session TTS via server succeeded")
    wait_q.put({'service': 'local', 'status': 'success'})
  except requests.exceptions.ConnectionError:
    log.error("Session TTS: Piper server not running – start piper.service")
    wait_q.put({'service': 'local', 'status': 'error', 'msg': 'Server not running'})
  except Exception as e:
    log.error(f"Session TTS error: {e}")
    wait_q.put({'service': 'local', 'status': 'error', 'msg': str(e)})
