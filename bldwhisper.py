#!/usr/bin/env python3
import argparse
import time
import sys
import ctranslate2
from faster_whisper import WhisperModel
from framework.util.utils import Config

class WhisperTranscriber:
  """ Build whisper for local STT using the provided model """
 
  def __init__(self, model):
    self.model_name = model                # tiny.en, base.en, or small.en
    self.model = None                      # Will hold the WhisperModel instance
    self.parser = argparse.ArgumentParser(description="Transcribe audio using Whisper.")
    self.parser.add_argument("filename", type=str, help="Path to the audio file")
    self.args = self.parser.parse_args()

  def load_model(self):
    # Check for CUDA GPU to decide device and compute type
    if ctranslate2.get_cuda_device_count() > 0:
      device = "cuda"
      compute_type = "int8_float16"        # Faster on GPU
      print(f"Loading Whisper model {self.model_name} on CUDA GPU...")
    else:
      device = "cpu"
      compute_type = "int8"                # Good performance on CPU
      print(f"Loading Whisper model {self.model_name} on CPU...")
    self.model = WhisperModel(self.model_name, device=device, compute_type=compute_type)

  def transcribe_audio(self, filename):
    print("transcribe_audio(): transcribing audio ...")
    start_time = time.time()
    # faster-whisper transcribe returns a generator of segments and info
    segments, info = self.model.transcribe(filename, beam_size=5)
    # Collect all segment texts
    transcription = " ".join(segment.text for segment in segments)
    end_time = time.time()
    et = end_time - start_time
    print("Transcription: ", transcription)
    print(f"Elapsed time: {et}")

if __name__ == "__main__":
  cfg = Config()                           # Get config file
  try:
    model = cfg.get_cfg_val("Basic.STT.Model")
    if model is None:
      print(f"ERROR Basic.STT.Model not found in config file: {cfg.config_file}")
      sys.exit(1)
  except Exception as e:
    print(f"ERROR calling cfg.get_cfg_val(Basic.STT.Model): {e}")
    sys.exit(1)
  # Create an instance of the WhisperTranscriber class
  transcriber = WhisperTranscriber(model)                 # Create a singleton
  transcriber.load_model()                                # Load the model
  transcriber.transcribe_audio(transcriber.args.filename) # Transcribe a file
