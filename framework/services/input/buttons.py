#!/usr/bin/env python3
from bus.MsgBus import MsgBus
from framework.util.utils import LOG, Config
import os
import platform
from signal import pause
import subprocess
import sys
from time import sleep
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device, PWMLED, Button

def is_raspberry_pi():
  try:
    with open("/proc/device-tree/model") as f:
      model = f.read().lower()
    return "raspberry pi" in model
  except Exception:
    return False

class Buttons:
  # Trap when GPIO pins 17, 27 and 22 are pressed and call prev_track(), stop() or next_track() in Minimy 
  def __init__(self):
    # GPIO pin layout - odd pins are toward the inside of the Pi:
    #  '!' shows the 4 pins used - 1 common ground and 3 buttons
    #    3V3  (1)  (2)  5V
    #  GPIO2  (3)  (4)  5V
    #  GPIO3  (5)  (6)  GND
    #  GPIO4  (7)  (8)  GPIO14
    #    GND  (9)! (10) GPIO15     common ground
    # GPIO17 (11)! (12) GPIO18     prev
    # GPIO27 (13)! (14) GND        stop
    # GPIO22 (15)! (16) GPIO23     next
    #    3V3 (17)  (18) GPIO24
    # GPIO10 (19)  (20) GND
    #  GPIO9 (21)  (22) GPIO25
    # GPIO11 (23)  (24) GPIO8
    #    GND (25)  (26) GPIO7
    #  GPIO0 (27)  (28) GPIO1
    #  GPIO5 (29)  (30) GND
    #  GPIO6 (31)  (32) GPIO12
    # GPIO13 (33)  (34) GND
    # GPIO19 (35)  (36) GPIO16
    # GPIO26 (37)  (38) GPIO20
    #    GND (39)  (40) GPIO21

    self.bus = MsgBus("buttons")
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/buttons.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"Buttons.__init__(): initializing 3 buttons log_filename: {log_filename}")
    self.prev_button = Button(17, hold_time=1.0)      
    self.stop_button = Button(27, hold_time=1.0) 
    self.next_button = Button(22, hold_time=1.0)   
    self.prev_button.when_pressed = self.prev_pressed
    self.prev_button.when_held = self.prev_held
    self.stop_button.when_pressed = self.stop_pressed
    self.stop_button.when_held = self.stop_held
    self.next_button.when_pressed = self.next_pressed
    self.next_button.when_held = self.next_held

  def prev_pressed(self):
    self.log.debug("Buttons.prev_pressed() prev button pressed")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "prev"}
    self.bus.send("media", "media_skill", info)
  
  def prev_held(self):
    self.log.debug("Buttons.prev_held(): prev button held")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "rewind"}
    self.bus.send("media", "media_skill", info)
  
  def stop_pressed(self):
    self.log.debug("Buttons.stop_pressed(): stop button pressed")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "pause"}
    self.bus.send("media", "media_skill", info)
  
  def stop_held(self):
    self.log.debug("Buttons.stop_held(): stop button held")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "stop"}
    self.bus.send("media", "media_skill", info)
  
  def next_pressed(self):
    self.log.debug("Buttons.next_pressed(): next button pressed")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "next"}
    self.bus.send("media", "media_skill", info)
  
  def next_held(self):
    self.log.debug("Buttons.next_held(): next button held")
    print("")
    info = {"subtype": "oob_detect", "skill_id": "media_skill", "verb": "stop"}
    self.bus.send("media", "media_skill", info)

  def signal_handler(self, sig, frame):    
    # Trap Ctrl-C and cleanup before exiting
    sys.exit(0)
          
# main()
# TO DO: Get buttons working on Nvidia Jetson Nano
# Their own package for GPIO: Jetson.GPIO (based on the RPi.GPIO API).
#   sudo apt install python3-pip
#   sudo pip3 install Jetson.GPIO
# 

if __name__ == '__main__':
  if is_raspberry_pi():
    Device.pin_factory = LGPIOFactory(chip=4)
    buttons = Buttons()                      # create the singleton
    try:
      pause()                                # loops forever
    except KeyboardInterrupt:
      ws.bus.client.disconnect()
  else:
    print("The hardware is not a Raspberry Pi - GPIO buttons disabled")

