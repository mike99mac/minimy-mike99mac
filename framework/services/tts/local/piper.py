import os
import time
import requests
import subprocess
from quart import Quart, request, Response
from framework.util.utils import Config, LOG

base_dir = os.getenv("SVA_BASE_DIR", os.path.expanduser("~/minimy"))
log_filename = os.path.join(base_dir, "logs/piper.log")
log = LOG(log_filename).log

cfg = Config()
model_file = cfg.get_cfg_val("Basic.TTS.LocalVoice")
if model_file is None:
  model_file = "en_US-hfc_male-medium.onnx"
model_file = str(model_file)
model_path = os.path.join(base_dir, "framework/services/tts/local/piper", model_file + ".onnx")
piper_dir = os.path.join(base_dir, "framework/services/tts/local/piper")

log.info(f"Piper: using binary {piper_dir}/piper with model {model_path}")

app = Quart(__name__)

@app.route("/tts", methods=["POST"])
async def tts():
  log.info("Received TTS request")
  data = await request.get_json()
  text = data.get("text", "")
  if not text:
    log.warning("Empty text received")
    return {"error": "Missing 'text' field"}, 400

  log.info(f"Synthesizing: {text[:50]}...")
  start_time = time.perf_counter()

  try:
    temp_wav = "/tmp/speech.wav"
    cmd = f'echo "{text}" | {piper_dir}/piper --quiet --model {model_path} --output_file {temp_wav}'
    subprocess.run(cmd, shell=True, check=True)

    with open(temp_wav, "rb") as f:
      audio_data = f.read()
    os.remove(temp_wav)

    elapsed = (time.perf_counter() - start_time) * 1000
    log.info(f"Synthesis completed in {elapsed:.1f} ms")

    return Response(audio_data, mimetype="audio/wav")
  except subprocess.CalledProcessError as e:
    log.error(f"Piper binary failed: {e}")
    return {"error": "Synthesis failed"}, 500

@app.route("/health", methods=["GET"])
async def health():
  return {"status": "ok", "model": model_path}

def local_speak_dialog(text, _file_name, wait_q):
  log.info(f"TTS request: {text[:50]}...")
  start_time = time.perf_counter()

  try:
    resp = requests.post(
      "http://localhost:5004/tts",
      json={"text": text},
      timeout=10.0
    )
    if resp.status_code == 200:
      audio_data = resp.content
      temp_wav = "/tmp/speech.wav"
      with open(temp_wav, "wb") as f:
        f.write(audio_data)
      subprocess.run(["aplay", temp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      os.remove(temp_wav)
      elapsed = (time.perf_counter() - start_time) * 1000
      log.info(f"TTS server completed in {elapsed:.1f} ms")
      wait_q.put({'service': 'local', 'status': 'success'})
      return
    else:
      log.error(f"TTS server returned {resp.status_code}: {resp.text}")
  except requests.exceptions.ConnectionError:
    log.error("TTS server not running – is piper.service started?")
  except Exception as e:
    log.error(f"TTS server error: {e}")

  # No fallback – just fail
  log.error("TTS failed")
  wait_q.put({'service': 'local', 'status': 'error', 'msg': 'TTS server unavailable'})

if __name__ == "__main__":
  import asyncio
  from hypercorn.asyncio import serve
  from hypercorn.config import Config as HyperConfig

  config = HyperConfig()
  config.bind = ["0.0.0.0:5004"]
  config.use_reloader = False
  config.debug = False
  # Suppress Hypercorn's default access/error logs (they go to stderr)
  config.accesslog = None
  config.errorlog = None
  asyncio.run(serve(app, config))
