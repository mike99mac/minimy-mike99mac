#!/usr/bin/env python3
import argparse
import time
import whisper
import sys
import socket
import torch
from framework.util.utils import Config

class WhisperTranscriber:
  """ Build whisper for local STT using the base.en model """
 
  def __init__(self, model):
    self.model = model                     # tiny.en, base.en, or small.en
    self.parser = argparse.ArgumentParser(description="Transcribe audio using Whisper.")
    self.parser.add_argument("filename", type=str, help="Path to the audio file")
    self.args = self.parser.parse_args()

  def load_model(self):
    print("Loading Whisper model ...")
    if torch.cuda.is_available():          # Check for CUDA GPU to use
      self.model = whisper.load_model(model, device="cuda") # load model on GPU
    else:
      self.model = whisper.load_model(model) # load model on CPU

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
  cfg = Config()                           # get config file
  cfg_val = "Basic.Hub"
  try:
    hub = cfg.get_cfg_val(cfg_val)
    if hub is None:
      print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
      sys.exit(1)
  except Exception as e:
    print(f"ERROR calling cfg.get_cfg_val(Basic.Hub): {e}")
  if hub == socket.gethostname() or hub == "localhost":
    cfg_val = "Basic.HubModel"
  else:
    cfg_val = "Basic.SpokeModel"
  try:
    model = cfg.get_cfg_val(cfg_val)
    if model is None:
      print(f"ERROR {cfg_val} not found in config file: {cfg.config_file}")
      sys.exit(1)
    if model == "t":
      model = "tiny.en"
    elif model == "b":
      model = "base.en"
    elif model == "s":
      model = "small.en"
  except Exception as e:
    print(f"ERROR calling cfg.get_cfg_val({cfg_val}): {e}")
    sys.exit(1)
  # Create an instance of the WhisperTranscriber class
  transcriber = WhisperTranscriber(model)                 # create a singleton
  transcriber.load_model()                                # load the model
  transcriber.transcribe_audio(transcriber.args.filename) # transcribe a file
