#!/usr/bin/env python3
from bus.MsgBus import MsgBus
from framework.util.utils import LOG
import os
from signal import pause
import sys
import threading

def is_raspberry_pi():
  try:
    with open("/proc/device-tree/model") as f:
      model = f.read().lower()
    return "raspberry pi" in model
  except Exception:
    return False

def is_jetson():
  """Detect NVIDIA Jetson platforms (e.g., Orin Nano)."""
  try:
    with open("/proc/device-tree/model") as f:
      model = f.read().lower()
    return "nvidia" in model or "jetson" in model or "orin" in model
  except Exception:
    return False


class JetsonButton:
  """
  A simple button class for Jetson.GPIO that provides press and hold callbacks,
  similar to gpiozero's Button.
  """
  def __init__(self, pin, hold_time=1.0):
    import Jetson.GPIO as GPIO
    self.GPIO = GPIO
    self.pin = pin
    self.hold_time = hold_time
    self.when_pressed = None
    self.when_held = None
    self._is_pressed = False
    self._hold_timer = None

    # Configure as input with internal pull-up
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    # Detect both edges to track press/release
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=self._edge_handler)

  def _edge_handler(self, channel):
    # Read current state: 0 = pressed (connected to GND), 1 = released
    if self.GPIO.input(self.pin) == self.GPIO.LOW:
      # Pressed (falling edge)
      self._is_pressed = True
      if self.when_pressed:
        self.when_pressed()
      # Start hold timer
      self._cancel_timer()
      self._hold_timer = threading.Timer(self.hold_time, self._held_callback)
      self._hold_timer.start()
    else:
      # Released (rising edge)
      if self._is_pressed:
        self._is_pressed = False
        self._cancel_timer()

  def _held_callback(self):
    if self._is_pressed and self.when_held:
      self.when_held()

  def _cancel_timer(self):
    if self._hold_timer is not None:
      self._hold_timer.cancel()
      self._hold_timer = None

  def close(self):
    """Clean up GPIO resources for this button."""
    self._cancel_timer()
    try:
      self.GPIO.remove_event_detect(self.pin)
    except Exception:
      pass
    # We do not call GPIO.cleanup() here because other buttons may still be active.
    # A global cleanup will be done in the Buttons destructor.


class Buttons:
  # Trap when GPIO pins 17, 27 and 22 are pressed and call prev_track(), stop() or next_track() in Minimy 
  def __init__(self, ButtonClass, prev_pin, stop_pin, next_pin):
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
    self.prev_button = ButtonClass(prev_pin, hold_time=1.0)
    self.stop_button = ButtonClass(stop_pin, hold_time=1.0)
    self.next_button = ButtonClass(next_pin, hold_time=1.0)
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

  def cleanup(self):
    """Release all button GPIO resources."""
    for btn in (self.prev_button, self.stop_button, self.next_button):
      try:
        btn.close()
      except Exception:
        pass
    if is_jetson():
      try:
        import Jetson.GPIO as GPIO
        GPIO.cleanup()
      except Exception:
        pass


# main()

if __name__ == '__main__':
  if is_raspberry_pi():
    from gpiozero.pins.lgpio import LGPIOFactory
    from gpiozero import Device, Button
    Device.pin_factory = LGPIOFactory(chip=4)
    buttons = Buttons(Button, 17, 27, 22)  # BCM pin numbers
    try:
      pause()                              # loops forever
    except KeyboardInterrupt:
      buttons.cleanup()
  elif is_jetson():
    import Jetson.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)               # Use physical header pin numbers
    # Physical pins: 11 (prev), 13 (stop), 15 (next) – same positions as on the Pi
    buttons = Buttons(JetsonButton, 11, 13, 15)
    try:
      pause()
    except KeyboardInterrupt:
      buttons.cleanup()
  else:
    print("The hardware is not a Raspberry Pi - GPIO buttons disabled")
