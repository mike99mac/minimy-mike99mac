#!/usr/bin/env python

from subprocess import Popen, PIPE, STDOUT
import os

services = {
        'python framework/services/input/mic.py':'Mic Service',
        'python skills/system_skills/skill_volume.py':'Volume Skill',
        'python skills/system_skills/skill_alarm.py':'Alarm Skill',
        'python skills/system_skills/skill_fallback.py':'SVA Fallback Skill',
        'python skill_system.py':'SVA System Skill',
        'python skills/system_skills/skill_media.py':'SVA Media Skill',
        'python framework/services/output/media_player.py':'Media Player Service',
        'python framework/services/intent/intent.py':'Intent Service',
        'python framework/services/stt/stt.py':'STT Service',
        'python framework/services/tts/tts.py':'TTS Service',
        'python3 -m mimic3':'Local TTS Engine',
        'python server.py':'Local STT Service',
        'MsgBus':'Message Bus',
        }

def kill_service(svc):
      end_indx = line.find(" ",3)
      pid = line[0:end_indx].strip()
      os.system("kill %s" % (pid,))
      print("%s - Killed %s" % (pid,services[svc]))


# kill user skills first
cmd = 'ps a'
p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
output = p.stdout.read()
output = output.decode("utf-8")

print("Kill user skills ...")
lines = output.split("\n")
for line in lines:
    if line.find("python __init__.py") > -1:
        la = line.split(" ")

        pid = la[0].strip()

        try:
            pid = int( pid )
        except:
            pid = 0

        if pid == 0:
            pid = la[1].strip()

            try:
                pid = int( pid )
            except:
                pid = 0

            if pid == 0:
                pid = la[2].strip()

                try:
                    pid = int( pid )
                except:
                    pid = 0

            if pid == 0:
                pid = la[3].strip()

        cmd = "kill %s" % (pid,)
        os.system(cmd)

# next kill services
print("Kill system skills and services ...")
lines = output.split("\n")
for line in lines:
  for service in services:
    if line.find(service) > -1:
        kill_service(service)

# clear temp dirs save_audio, save_text and save_tts here!
# last resort


