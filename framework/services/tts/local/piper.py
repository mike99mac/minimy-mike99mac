import os
import time
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

log.info(f"Piper server: using binary {piper_dir}/piper with model {model_path}")

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
