import os
import time
import wave
import io
import requests
import subprocess
from quart import Quart, request, Response
import numpy as np
from framework.util.utils import Config, LOG

base_dir = os.getenv("SVA_BASE_DIR", os.path.expanduser("~/minimy"))
log_filename = os.path.join(base_dir, "logs/tts.log")
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
  data = await request.get_json()
  text = data.get("text", "")
  if not text:
    return {"error": "Missing 'text' field"}, 400

  temp_wav = "/tmp/speech.wav"
  cmd = f'echo "{text}" | {piper_dir}/piper --quiet --model {model_path} --output_file {temp_wav}'

  try:
    subprocess.run(cmd, shell=True, check=True)
    with open(temp_wav, "rb") as f:
      audio_data = f.read()
    os.remove(temp_wav)

    # Convert to WAV for consistent output
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
      wf.setnchannels(1)
      wf.setsampwidth(2)
      wf.setframerate(16000)
      wf.writeframes(np.frombuffer(audio_data, dtype=np.int16).tobytes())

    return Response(wav_io.getvalue(), mimetype="audio/wav")
  except subprocess.CalledProcessError as e:
    log.error(f"Piper synthesis failed: {e}")
    return {"error": "Synthesis failed"}, 500

@app.route("/health", methods=["GET"])
async def health():
  return {"status": "ok", "model": model_path}

def log_timing(msg):
  timing_log = os.path.join(base_dir, "logs/tts_timing.log")
  os.makedirs(os.path.dirname(timing_log), exist_ok=True)
  with open(timing_log, "a") as f:
    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def local_speak_dialog(text, _file_name, wait_q):
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
      log_timing(f"TIMING TTS (server) + playback: {elapsed:.1f} ms")
      wait_q.put({'service': 'local', 'status': 'success'})
      return
  except Exception:
    pass

  # Fallback: direct binary call
  cfg = Config()
  model_file = cfg.get_cfg_val("Basic.TTS.LocalVoice")
  if model_file is None:
    model_file = "en_US-hfc_male-medium.onnx"
  model_file = str(model_file)
  piper_dir = f"{base_dir}/framework/services/tts/local/piper"
  cmd = f'echo "{text}" | {piper_dir}/piper --quiet --model {piper_dir}/{model_file}.onnx --output_file speech.wav'
  subprocess.run(cmd, shell=True)
  subprocess.run(["aplay", "speech.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  elapsed = (time.perf_counter() - start_time) * 1000
  log_timing(f"TIMING TTS (fallback) + playback: {elapsed:.1f} ms")
  os.remove("speech.wav")
  wait_q.put({'service': 'local', 'status': 'success'})

if __name__ == "__main__":
  import asyncio
  from hypercorn.asyncio import serve
  from hypercorn.config import Config as HyperConfig

  config = HyperConfig()
  config.bind = ["0.0.0.0:5004"]
  config.use_reloader = False
  config.debug = False
  asyncio.run(serve(app, config))
