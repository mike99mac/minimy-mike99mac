import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))
from framework.util.utils import LOG
import io
import numpy as np
from quart import Quart, request
import torch
import wave
import whisper

base_dir = os.getenv('SVA_BASE_DIR')
log_filename = base_dir + '/logs/whisper.log'
log = LOG(log_filename).log
log.debug("fasterWhisper.__init__() starting")
app = Quart(__name__)                      # Initialize the Quart app
model_name = "tiny.en"                     # others to try: tiny.en, small.en
log.debug(f"fasterWhisper.__init__(): loading model: {model_name}")
original_load = torch.load                 # load Whisper model and override
torch.load = lambda f, *args, **kwargs: original_load(f, *args, weights_only=True, **kwargs)
model = whisper.load_model(model_name)     # load model

@app.route("/stt", methods=["POST"])
async def transcribe():
  """ 
  STT transcription - expects raw WAV file data in the request body 
  """
  wav_bytes = await request.data
  try:                                     # to load WAV data
    with io.BytesIO(wav_bytes) as wav_io:
      with wave.open(wav_io, "rb") as wav_file: # Ensure correct WAV format
        audio_bytes = wav_file.readframes(wav_file.getnframes()) # read audio frames and convert to NumPy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0  # Normalize audio
    result = model.transcribe(audio_array, fp16=False) # transcribe audio using Whisper

    # fold text to lower case, remove leading spaces, ','s and '?'s
    transcription = result["text"].lower().lstrip().replace(",", "").replace("?", "")
    log.debug(f"whisper.transcribe() Transcription: {transcription}")
    return {"text": transcription}
  except Exception as e:
    log.debug(f"whisper.transcribe(): Error during transcription: {e}")
    return {"error": str(e)}, 400

@app.route("/stream", methods=["POST"])
async def stream_transcription():
  """ 
  Handle streaming audio transcription.  Expects raw audio chunks in the request body. 
  """
  model_stream = model.create_stream()
  try:
    async for chunk in request.body:       # convert chunk to NumPy array and feed into model
      chunk_array = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
      model_stream.feed_audio(chunk_array)
    transcription = model_stream.finish()  # Finalize transcription
    log.debug(f"whisper.stream_transcription(): {transcription}")
    return {"text": transcription}
  except Exception as e:
    log.debug(f"whisper.stream_transcription(): Error during stream transcription: {e}")
    return {"error": str(e)}, 400

# main()  
if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0", port=5002)

