import os
import requests
import subprocess
import io
import wave
import numpy as np
from quart import Quart, request, Response
from framework.util.utils import LOG
from piper import PiperVoice

base_dir = os.getenv("SVA_BASE_DIR", os.path.expanduser("~/minimy"))
log_filename = os.path.join(base_dir, "logs/piper.log")
log = LOG(log_filename).log

app = Quart(__name__)

model_path = os.path.expanduser("~/.local/share/piper-plus/voices/en_US-hfc_male-medium/en_US-hfc_male-medium.onnx")
voice = PiperVoice.load(model_path)
log.info("Piper server: model loaded")

# Pre-warm: force lazy initialization (phonemizer, NLTK, etc.) before server starts
log.info("Pre-warming TTS engine...")
list(voice.synthesize_stream_raw("Warming up."))
log.info("Pre-warm complete")

@app.route("/tts", methods=["POST"])
async def tts():
  log.info("Received TTS request")
  data = await request.get_json()
  text = data.get("text", "")
  if not text:
    log.warning("Empty text received")
    return {"error": "Missing 'text' field"}, 400

  log.info(f"Synthesizing: {text[:50]}...")
  audio = b"".join(voice.synthesize_stream_raw(text))

  wav_io = io.BytesIO()
  with wave.open(wav_io, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(22050)
    wf.writeframes(np.frombuffer(audio, dtype=np.int16).tobytes())

  log.info("Synthesis complete")
  return Response(wav_io.getvalue(), mimetype="audio/wav")

@app.route("/health", methods=["GET"])
async def health():
  return {"status": "ok", "model": "en_US-hfc_male-medium"}

def local_speak_dialog(text, _file_name, wait_q):
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

if __name__ == "__main__":
  import asyncio
  from hypercorn.asyncio import serve
  from hypercorn.config import Config as HyperConfig

  config = HyperConfig()
  config.bind = ["0.0.0.0:5004"]
  config.use_reloader = False
  config.debug = False
  config.accesslog = None
  config.errorlog = None
  asyncio.run(serve(app, config))
