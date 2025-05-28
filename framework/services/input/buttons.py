#!/usr/bin/env python3
from bus.MsgBus import MsgBus
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
       GND  (9)! (10) GPIO15     common ground
    GPIO17 (11)! (12) GPIO18     prev
    GPIO27 (13)! (14) GND        stop
    GPIO22 (15)! (16) GPIO23     next
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
    info = {"subtype": "oob_detect",
            "skill_id": "media_skill",
            "verb": "????"
           }
    while True:                            # loop forever waiting for button presses or holds
      if self.prev_button.is_held:
        self.log.debug("Buttons.monitor_buttons(): prev button held")
        print("prev button held")
        info["verb"] = "rewind"            # move to start of playlist/album
        sleep(1)
      elif self.stop_button.is_held:
        self.log.debug("Buttons.monitor_buttons(): stop button held")
        print("stop button held")
        info["verb"] = "stop"              # clear playlist
        self.bus.send("media", "media_skill", info)
        sleep(1)
      elif self.next_button.is_held:
        self.log.debug("Buttons.monitor_buttons(): next button held")
        print("next button held")
        info["verb"] = "stop"              # clear playlist
        self.bus.send("media", "media_skill", info)
        sleep(1)
      elif self.prev_button.is_pressed:
        self.log.debug("Buttons.monitor_buttons(): prev button pressed")
        info["verb"] = "prev"              # previous track
        self.bus.send("media", "media_skill", info)
        print("prev button pressed")
        sleep(1)
      elif self.stop_button.is_pressed:
        self.log.debug("Buttons.monitor_buttons(): stop button pressed")
        print("stop button pressed")
        info["verb"] = "pause"             # keep song where it was 
        self.bus.send("media", "media_skill", info)
        sleep(1)
      elif self.next_button.is_pressed:
        self.log.debug("Buttons.monitor_buttons(): next button pressed")
        info["verb"] = "next"              # next track    
        self.bus.send("media", "media_skill", info)
        print("next button pressed")
        sleep(1) 
      sleep(.1)                            # cool it?  
  
  def signal_handler(self, sig, frame):    # Trap Ctrl-C and cleanup before exiting
    sys.exit(0)
          
# main()
if __name__ == '__main__':
  buttons = Buttons()                      # create the singleton
  try:
    buttons.monitor_buttons()              # loops forever
  except KeyboardInterrupt:
    ws.bus.client.disconnect()

