#!/usr/bin/env python3
from bus.MsgBus import MsgBus
from framework.message_types import (MSG_UTTERANCE, MSG_SPEAK, MSG_REGISTER_INTENT, MSG_MEDIA, MSG_SYSTEM, MSG_RAW, MSG_SKILL)
from framework.util.utils import LOG, Config
import os
from signal import pause
import subprocess
import sys
from time import sleep
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device, PWMLED, Button
Device.pin_factory = LGPIOFactory(chip=4)

class Buttons:
  """
  trap when GPIO pins 17, 27 and 22 are pressed and call prev_track(), stop() or next_track() in Minimy 
  """
  def __init__(self):
    """
    GPIO pin layout - odd pins are toward the inside of the Pi:
    '!' shows the 4 pins used - 1 common ground and 3 buttons
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
    self.bus = MsgBus("buttons")
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/buttons.log'
    self.log = LOG(log_filename).log
    self.prev_button = Button(17)      
    self.stop_button = Button(27)     
    self.next_button = Button(22)    
    self.log.debug(f"Buttons.__init__(): initializing 3 buttons log_filename: {log_filename}")
    
  def monitor_buttons(self):               # wait for button presses     
    while True:                            # loop forever waiting for button presses or holds
      if self.prev_button.is_held:
        self.log.debug("prev button held") 
        sleep(1)
      elif self.stop_button.is_held:
        self.log.debug("stop button held") 
        print("stop button held")
        sleep(1)
      elif self.next_button.is_held:
        self.log.debug("next button held") 
        sleep(1)
      elif self.prev_button.is_pressed:
        self.log.debug("prev button pressed")
        self.bus.on(MSG_MEDIA, "mycroft.audio.service.prev")
        print("prev button pressed")
        sleep(1)
      elif self.stop_button.is_pressed:
        self.log.debug("stop button pressed")
        print("stop button pressed")
        self.bus.on(MSG_MEDIA, "mycroft.audio.service.toggle") # toggle between pause and resume
        sleep(1)
      elif self.next_button.is_pressed:
        self.log.debug("next button pressed")
        self.bus.on(MSG_MEDIA, "mycroft.audio.service.next")
        print("next button pressed")
        sleep(1) 
      sleep(.1)                            # cool it?  
  
  def signal_handler(self, sig, frame):    # Trap Ctrl-C and cleanup before exiting
    sys.exit(0)
          
# main()
if __name__ == '__main__':
  buttons = Buttons()                        # create the singleton
  try:
    buttons.monitor_buttons()                # loops forever
  except KeyboardInterrupt:
    ws.bus.client.disconnect()

