#
# This code is distributed under the Apache License, v2.0
#
"""
 Trap when GPIO pins 17, 27 and 22 are pressed and pass messages on to Minimy

 GPIO pin layout - odd pins are toward the inside of the Pi:
  '!' shows the pins used
       3V3  (1)  (2)  5V
     GPIO2  (3)  (4)  5V
     GPIO3  (5)  (6)  GND
     GPIO4  (7)  (8)  GPIO14
       GND  (9)! (10) GPIO15
    GPIO17 (11)! (12) GPIO18
    GPIO27 (13)! (14) GND
    GPIO22 (15)! (16) GPIO23
       3V3 (17)  (18) GPIO24
    GPIO10 (19)  (20) GND
     GPIO9 (21)  (22) GPIO25
    GPIO11 (23)  (24) GPIO8
       GND (25)  (26) GPIO7
     GPIO0 (27)  (28) GPIO1
     GPIO5 (29)  (30) GND
     GPIO6 (31)  (32) GPIO12
    GPIO13 (33)  (34) GND
    GPIO19 (35)  (36) GPIO16
    GPIO26 (37)  (38) GPIO20
       GND (39)  (40) GPIO21
"""
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.util.utils import LOG
import os
import RPi.GPIO as GPIO
from skills.sva_base import SimpleVoiceAssistant
# from skills.sva_media_skill_base import MediaSkill
import signal
import subprocess
import sys
from threading import Event
from framework.message_types import (MSG_UTTERANCE, MSG_MEDIA, MSG_SKILL, MSG_SYSTEM)

class Buttons(SimpleVoiceAssistant):  
  """
  Trap when buttons are pressed and perform 'previous', 'pause/resume' or 'next' actions
  """
  prev_button: int
  stop_button: int
  next_button: int
  message:     Message

  def __init__(self):
    self.skill_id = 'button_service'
    super().__init__(skill_id='button_service', skill_category='media')
    log_filename = "skills.log"
    self.log = LOG(log_filename).log
    self.log.debug(f"Buttons.__init__() log_filename: {log_filename}")
    self.prev_button = 17
    self.stop_button = 27
    self.next_button = 22

  def monitor_buttons(self):
    self.log.debug("Buttons.monitor_buttons()")
    GPIO.setmode(GPIO.BCM)                 # set GPIO numbering
    GPIO.setup(self.prev_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(self.stop_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(self.next_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(self.prev_button, GPIO.FALLING, callback=self.button_pressed, bouncetime=300)
    GPIO.add_event_detect(self.stop_button, GPIO.FALLING, callback=self.button_pressed, bouncetime=300)
    GPIO.add_event_detect(self.next_button, GPIO.FALLING, callback=self.button_pressed, bouncetime=300)
    signal.signal(signal.SIGINT, self.signal_handler)
    signal.pause()

  def signal_handler(self, sig, frame):
    """
    Trap Ctrl-C and cleanup before exiting
    """
    self.log.debug(f"Buttons.signal_handler() sig: {sig} frame: {frame}") 
    GPIO.cleanup()
    sys.exit(0)

  def button_pressed(self, channel):
    """
    Perform action when one of the buttons is pressed
    """
    self.log.debug(f"Buttons.button_pressed() channel: {channel}") 
    match channel:
      case self.prev_button:
        self.log.debug(f"Buttons.button_pressed() previous")
        verb = "previous"
      case self.stop_button:
        self.log.debug(f"Buttons.button_pressed() pause/resume")
        verb = "pause"
      case self.next_button:
        self.log.debug(f"Buttons.button_pressed() next")
        verb = "next"
      case _:                              # not expected
        self.log.error(f"Buttons.button_pressed() UNEXPECTED channel: {channel}")
        self.log.debug(f"Did not expect channel: {channel}")
    info = { 
	          'subtype': 'oob_detect',
		        'skill_id': 'media_skill',
		        'from_skill_id': self.skill_id,
		        'verb': verb
           }    
    self.bus.send(MSG_SKILL, "media_skill", info)

# main()
if __name__ == '__main__':
    buttons = Buttons()
    buttons.monitor_buttons()
    Event().wait()                         # Wait forever
