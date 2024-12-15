#!/usr/bin/env python3
import io
import wave
import whisper
import numpy as np
from quart import Quart, request

app = Quart(__name__)                      # Initialize the Quart app
MODEL_NAME = "base.en"                     # others to try: tiny.en, small.en
print(f"Loading Whisper model: {MODEL_NAME}")
model = whisper.load_model(MODEL_NAME)

@app.route("/stt", methods=["POST"])
async def transcribe():
  """ Handle speech-to-text transcription.  Expects raw WAV file data in the request body.  """
  wav_bytes = await request.data
  try:                                     # to load WAV data
    with io.BytesIO(wav_bytes) as wav_io:
      with wave.open(wav_io, "rb") as wav_file: # Ensure correct WAV format
        # TO DO: comment out next 3 checks if they are always correct
        assert wav_file.getnchannels() == 1, "Only mono audio supported."
        assert wav_file.getsampwidth() == 2, "Only 16-bit PCM WAV supported."
        assert wav_file.getframerate() == 16000, "Only 16 kHz audio supported."
        audio_bytes = wav_file.readframes(wav_file.getnframes()) # Read audio frames and convert to NumPy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0  # Normalize audio
    result = model.transcribe(audio_array, fp16=False) # Transcribe audio using Whisper
    transcription = result["text"]
    print(f"Transcription: {transcription}")
    return {"text": transcription}
  except Exception as e:
    print(f"Error during transcription: {e}")
    return {"error": str(e)}, 400

@app.route("/stream", methods=["POST"])
async def stream_transcription():
  """ Handle streaming audio transcription.  Expects raw audio chunks in the request body. """
  model_stream = model.create_stream()
  try:
    async for chunk in request.body: # convert chunk to NumPy array and feed into model
      chunk_array = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
      model_stream.feed_audio(chunk_array)
    transcription = model_stream.finish()  # Finalize transcription
    print(f"Stream Transcription: {transcription}")
    return {"text": transcription}
  except Exception as e:
    print(f"Error during stream transcription: {e}")
    return {"error": str(e)}, 400

# main()  
if __name__ == "__main__":
  app.run(debug=True, host="0.0.0.0", port=5002)

