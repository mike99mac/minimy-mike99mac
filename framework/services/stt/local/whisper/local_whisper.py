import io
import os
import sys
import time
import wave
import numpy as np
import ctranslate2
from faster_whisper import WhisperModel
from quart import Quart, request

home_dir = os.environ.get("HOME")
sys.path.append(f"{home_dir}/minimy")
from framework.util.utils import Config

app = Quart(__name__)
cfg = Config()
try:
  model = cfg.get_cfg_val("Basic.STT.Model")
  if model is None:
    print(f"ERROR Basic.STT.Model not found in config file: {cfg.config_file}")
    sys.exit(1)
except Exception as e:
  print(f"ERROR calling cfg.get_cfg_val(Basic.STT.Model): {e}")
if ctranslate2.get_cuda_device_count() > 0:
  print(f"Starting Whisper using CUDA GPU with model {model}...")
  model = WhisperModel(
    model, device="cuda", compute_type="int8_float16"
  )
else:
  print(f"Starting Whisper using CPU with model {model}...")
  model = WhisperModel(model, device="cpu", compute_type="int8")


@app.route("/stt", methods=["POST"])
async def transcribe():
  wav_bytes = await request.data
  try:
    start_time = time.perf_counter()
    with io.BytesIO(wav_bytes) as wav_io:
      with wave.open(wav_io, "rb") as wav_file:
        audio_bytes = wav_file.readframes(
          wav_file.getnframes()
        )
        audio_array = (
          np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            / 32768.0
        )
    segments, info = model.transcribe(
      audio_array, beam_size=5
    )
    transcription = ""
    for segment in segments:
      transcription += (
        segment.text.lower().lstrip().replace(",", "").replace("?", "")
      )
    elapsed = (time.perf_counter() - start_time) * 1000
    print(f"TIMING STT transcription: {elapsed:.1f} ms")
    if transcription:
      print(f"whisper.transcribe() Transcription: {transcription}")
    return {"text": transcription}
  except Exception as e:
    print(f"whisper.transcribe(): Error during transcription: {e}")
    return {"error": str(e)}, 400


@app.route("/stream", methods=["POST"])
async def stream_transcription():
  model_stream = model.create_stream()
  try:
    async for chunk in request.body:
      chunk_array = (
        np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
      )
      model_stream.feed_audio(chunk_array)
    transcription = model_stream.finish()
    return {"text": transcription}
  except Exception as e:
    return {"error": str(e)}, 400


if __name__ == "__main__":
  import asyncio
  from hypercorn.asyncio import serve
  from hypercorn.config import Config as HyperConfig
  config = HyperConfig()
  config.bind = ["0.0.0.0:5002"]
  config.use_reloader = False
  config.debug = False
  asyncio.run(serve(app, config))
