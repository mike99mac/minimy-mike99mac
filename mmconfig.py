#!/usr/bin/env python3
import getpass
import sys
from framework.util.utils import Config

def update_value(cfg, key, text):
  val = cfg.get_cfg_val(key)
  inp_val = input(f"{text} [{val}] ---> ")
  if inp_val:
    cfg.set_cfg_val(key, inp_val)
  print(f"Using: {cfg.get_cfg_val(key)}")

def update_secret(cfg, key, text):
  val = cfg.get_cfg_val(key)
  masked = "***" if val else ""
  inp_val = getpass.getpass(f"{text} [{masked}] ---> ")
  if inp_val:
    cfg.set_cfg_val(key, inp_val)
  print(f"Using: {'***' if cfg.get_cfg_val(key) else '(unset)'}")

def handle_basic(cfg):
  print("Basic Settings\n--------------")
  update_value(cfg, "Basic.BaseDir", "Path to Minimy installation (default: $HOME/minimy)")
  update_value(cfg, "Basic.Hub", "Hub Hostname (default: localhost)")
  update_value(cfg, "Basic.WakeWords", "Comma Separated List of Wake Words (default: [computer])")
  update_value(cfg, "Basic.RoomsToHost", "Comma Separated List of Rooms with boomboxes (only needed if you have multiple) (default: [])")

  print("\nSpotify Settings\n----------------")
  update_value(cfg, "Basic.Spotify.ClientId", "Spotify Client ID")
  update_secret(cfg, "Basic.Spotify.ClientSecret", "Spotify Client Secret")
  update_value(cfg, "Basic.Spotify.DeviceName", "Spotify Device Name (default: Smart Boombox)")

  print("\nSTT Settings\n----------------")
  update_value(cfg, "Basic.STT.Model", "STT Model: tiny.en, base.en, or small.en (default: base.en)")
  update_value(cfg, "Basic.STT.UseRemote", "Use Remote STT (y/n)")

  print("\nTTS Settings\n----------------")
  update_value(cfg, "Basic.TTS.LocalVoice", "Local Piper TTS model to use (default: en_US-hfc_male-medium)")
  update_value(cfg, "Basic.TTS.UseRemote", "Use Remote TTS (y/n)")

  print("\nLLM Settings\n----------------")
  update_value(cfg, "Basic.LLM.Model", "LLM GGUF File (default: qwen2.5-1.5b-instruct-q4_k_m.gguf)")
  update_value(cfg, "Basic.LLM.Repo", "LLM HuggingFace Repo (default: Qwen/Qwen2.5-1.5B-Instruct-GGUF)")
  update_value(cfg, "Basic.LLM.UseRemote", "Use Remote LLM (y/n)")

def handle_advanced(cfg):
  print("Advanced Settings\n-----------------")
  update_value(cfg, "Advanced.LogLevel", "Logging Level (d/i/w/e)")
  update_value(cfg, "Advanced.CrappyAEC", "Crappy AEC (y/n)")
  update_value(cfg, "Advanced.AWSId", "AWS ID")
  update_secret(cfg, "Advanced.AWSKey", "AWS Key")
  update_value(cfg, "Advanced.GoogleApiKeyPath", "Google API Key File Location")

def main():
  advanced_options = False
  cfg = Config()
  if len(sys.argv) > 1:
    option = sys.argv[1].strip().lower().lstrip("-")
    if option == "a":
      print("Advanced Options Selected: a")
      advanced_options = True
    else:
      print("Invalid option - expected '' or 'a', ignoring")
  print()
  handle_basic(cfg)
  if advanced_options:
    print()
    handle_advanced(cfg)
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
