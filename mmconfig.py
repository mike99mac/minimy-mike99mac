#!/usr/bin/env python
import os, sys, yaml
from framework.util.utils import Config

def update_value(cfg, key, text):
    #print()
    val = cfg.get_cfg_val(key)
    inp_val = input(text + " [%s] --->" % (val,))
    if inp_val:
        cfg.set_cfg_val(key, inp_val)
    print("Using: %s" % (cfg.get_cfg_val(key),))

def handle_super_advanced(cfg):
    print("Super Advanced Settings\n-----------------------")
    update_value(cfg, 'Advanced.Platform', "Linux (l), PiOS (p) or Markii (m)")
    update_value(cfg, 'Advanced.TTS.Local', "Local TTS (e)speak, (c)oqui, or (m)imic3")
    update_value(cfg, 'Advanced.TTS.Remote', "Remote TTS (p)olly, (m)imic2")
    update_value(cfg, 'Advanced.InputDeviceId', "Input Device ID (0 means use default)")
    update_value(cfg, 'Advanced.OutputDeviceName', "Output Device Name (empty string means use default)")

def handle_advanced(cfg):
    print("Advanced Settings\n-----------------")
    update_value(cfg, 'Advanced.STT.UseRemote', "Use Remote STT (y/n)")
    update_value(cfg, 'Advanced.TTS.UseRemote', "Use Remote TTS (y/n)")
    update_value(cfg, 'Advanced.NLP.UseRemote', "Use Remote NLP (y/n)")
    update_value(cfg, 'Advanced.LogLevel', "Logging Level (e,w,i,d)")
    update_value(cfg, 'Advanced.CrappyAEC', "Crappy AEC (y/n)")

def handle_basic(cfg):
    print("Basic Settings\n--------------")
    update_value(cfg, 'Basic.GoogleApiKeyPath', "Google API Key File Location")
    update_value(cfg, 'Basic.AWSId', "AWS ID")
    update_value(cfg, 'Basic.AWSKey', "AWS Key")
    update_value(cfg, 'Basic.WakeWords', "Comma Separated List of Wake Words")


if __name__ == "__main__":
    # missing validation
    advanced_options = False
    option = ''
    cfg = Config()
    if len(sys.argv) > 1:
        option = sys.argv[1].replace("-","")
        if option == 'a' or option == 'sa':
            print("Advanced Options Selected %s" % (option,))
            advanced_options = True
        else:
            print("Invalid option - not 'a' or 'sa', ignoring")

    print()
    handle_basic(cfg)

    if advanced_options:
        if option == 'a':
            print()
            handle_advanced(cfg)
        else:
            # otherwise sa
            print()
            handle_advanced(cfg)
            print()
            handle_super_advanced(cfg)

    print()
    res = input("Save Changes?")
    if res and res.lower() == 'y':
        cfg.save_cfg()
        print("Configuration Updated")
    else:
        print("Changes Abandoned")

    cfg.dump_cfg()
