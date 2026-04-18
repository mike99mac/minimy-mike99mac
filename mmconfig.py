#!/usr/bin/env python3
import sys
from framework.util.utils import Config

def update_value(cfg, key, text):
  val = cfg.get_cfg_val(key)
  inp_val = input(f"{text} [{val}] ---> ")
  if inp_val:
    cfg.set_cfg_val(key, inp_val)
  print(f"Using: {cfg.get_cfg_val(key)}")

def handle_basic(cfg):
  print("Basic Settings\n--------------")
  update_value(cfg, "Basic.WakeWords", "Comma Separated List of Wake Words")
  update_value(cfg, "Basic.Hub", "Hub Hostname")
  update_value(cfg, "Basic.STT.Model", "STT Model: tiny.en, base.en, or small.en")
  update_value(cfg, "Basic.LLMRepo", "LLM HuggingFace Repo")
  update_value(cfg, "Basic.LLMFile", "LLM GGUF File")

def handle_advanced(cfg):
  print("Advanced Settings\n-----------------")
  update_value(cfg, "Basic.STT.UseRemote", "Use Remote STT (y/n)")
  update_value(cfg, "Basic.TTS.UseRemote", "Use Remote TTS (y/n)")
  update_value(cfg, "Basic.NLP.UseRemote", "Use Remote NLP (y/n)")
  update_value(cfg, "Basic.LLM.UseRemote", "Use Remote LLM (y/n)")
  update_value(cfg, "Advanced.CrappyAEC", "Crappy AEC (y/n)")
  update_value(cfg, "Advanced.GoogleApiKeyPath", "Google API Key File Location")
  update_value(cfg, "Advanced.AWSId", "AWS ID")
  update_value(cfg, "Advanced.AWSKey", "AWS Key")

def handle_super_advanced(cfg):
  print("Super Advanced Settings\n-----------------------")
  update_value(cfg, "Advanced.LogLevel", "Logging Level (e,w,i,d)")
  update_value(cfg, "Basic.TTS.Local", "Local TTS (e)speak, (c)oqui, or (m)imic3")
  update_value(cfg, "Basic.TTS.Remote", "Remote TTS (p)olly, (m)imic2")
  update_value(cfg, "Advanced.InputDeviceId", "Input Device ID (0 means use default)")
  update_value(
    cfg,
    "Advanced.OutputDeviceName",
    "Output Device Name (empty string means use default)",
  )
  update_value(
    cfg,
    "Advanced.InputLevelControlName",
    "Input Level Control Name (typically Record or Mic)",
  )
  update_value(
    cfg,
    "Advanced.OutputLevelControlName",
    "Output Level Control Name (typically Playback or Speaker)",
  )

def main():
  advanced_options = False
  super_advanced_options = False
  cfg = Config()
  if len(sys.argv) > 1:
    option = sys.argv[1].strip().lower().lstrip("-")
    if option == "a":
      print("Advanced Options Selected: a")
      advanced_options = True
    elif option == "sa":
      print("Advanced Options Selected: sa")
      advanced_options = True
      super_advanced_options = True
    else:
      print("Invalid option - expected 'a' or 'sa', ignoring")
  print()
  handle_basic(cfg)
  if advanced_options:
    print()
    handle_advanced(cfg)
  if super_advanced_options:
    print()
    handle_super_advanced(cfg)
  print()
  res = input("Save Changes? ")
  if res and res.lower() == "y":
    cfg.save_cfg()
    print("Configuration Updated")
  else:
    print("Changes Abandoned")
  cfg.dump_cfg()

if __name__ == "__main__":
  main()
