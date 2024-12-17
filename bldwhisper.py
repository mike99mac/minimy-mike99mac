#!/usr/bin/env python3
import argparse
import numpy as np
import pyaudio
import time
import whisper
import wave

class WhisperTranscriber:
  """ Build whisper for local STT using the base.en model """
 
  def __init__(self):
    self.model = "base.en"                 # tiny.en and small.en are also possible
    #self.model = "tiny.en" 
    self.parser = argparse.ArgumentParser(description="Transcribe audio using Whisper.")
    self.parser.add_argument("filename", type=str, help="Path to the audio file")
    self.args = self.parser.parse_args()

  def load_model(self):
    print("Loading Whisper model ...")
    self.model = whisper.load_model(self.model)  # Load the quantized model

  def transcribe_audio(self, filename):
    print("transcribe_audio(): loading audio ...")
    audio = whisper.load_audio(filename)
    print("transcribe_audio(): pad or trim audio ...")
    audio = whisper.pad_or_trim(audio)
    print("transcribe_audio(): transcribing audio ...")
    start_time = time.time()
    result = self.model.transcribe(audio, fp16=False)  # transcribe to text
    end_time = time.time()
    et = end_time - start_time
    print("Transcription: ", result["text"])
    print(f"Elapsed time: {et}")

if __name__ == "__main__":

  # Create an instance of the WhisperTranscriber class
  transcriber = WhisperTranscriber()                      # create a singleton
  transcriber.load_model()                                # load the model
  transcriber.transcribe_audio(transcriber.args.filename) # transcribe a file
