from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import lingua_franca
from lingua_franca import parse
import os
from framework.util.utils import execute_command, Config
from framework.hal.hal import Hal

class VolumeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    self.skill_id = "volume_skill"
    super().__init__(msg_handler=self.handle_message, skill_id=self.skill_id, skill_category="system")
    lingua_franca.load_language("en")
    cfg = Config()
    input_device_id = cfg.get_cfg_val("Advanced.InputDeviceId")
    input_level_control_name = cfg.get_cfg_val("Advanced.InputLevelControlName")
    output_device_name = cfg.get_cfg_val("Advanced.OutputDeviceName")
    output_level_control_name = cfg.get_cfg_val("Advanced.OutputLevelControlName")
    cfg_platform = cfg.get_cfg_val("Advanced.Platform")
    if cfg_platform == "p":
      from framework.hal.executables.pios import Platform
    else:   
      from framework.hal.executables.ubuntu import Platform
    self.hal = Platform(input_device_id, input_level_control_name, output_device_name, output_level_control_name)
    self.volume_level = 70
    self.set_volume(self.volume_level)
    self.muted_volume = self.volume_level
    self.mic_level = 67
    self.set_mic_level(self.mic_level)
    inactive_state_intents = []
    questions = ["what", "how"]
    commands = ["set", "change", "modify"]
    subjects = ["microphone", "mic", "input"]
    for subject in subjects:
      for command in commands:
        self.register_intent("C", command, subject, self.handle_change_mic)
        inactive_state_intents.append(f"C:{subject}:{command}")
    for subject in subjects:
      for question in questions:
        self.register_intent("Q", question, subject, self.handle_query_mic)
        inactive_state_intents.append(f"Q:{subject}:{question}")
    subject = "volume"
    self.register_intent("C", "turn", subject, self.handle_change)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "turn" )
    self.register_intent("C", "set", subject, self.handle_change)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "set" )
    self.register_intent("C", "change", subject, self.handle_change)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "change" )
    self.register_intent("C", "increase", subject, self.handle_increase)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "increase" )
    self.register_intent("C", "decrease", subject, self.handle_decrease)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "decrease" )
    self.register_intent("C", "mute", subject, self.handle_mute)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "mute" )
    self.register_intent("C", "unmute", subject, self.handle_unmute)
    inactive_state_intents.append( "C" + ":" + subject + ":" + "unmute" )
    for question in questions:
      self.register_intent("Q", question, subject, self.handle_intent_match)
      inactive_state_intents.append( "Q" + ":" + subject + ":" + question )

  def get_num(self,v1, v2, v3):
    num = parse.extract_number(v1)
    if not num:
      num = parse.extract_number(v2)
      if not num:
        num = parse.extract_number(v3)
    return num

  def get_mic_level(self):
    self.mic_level = self.hal.get_intput_level()
    return self.mic_level

  def set_mic_level(self, new_level):
    self.mic_level = new_level
    self.hal.set_input_level(self.mic_level)
    return self.mic_level

  def handle_change_mic(self,msg):
    val = msg["payload"]["utt"]["value"]
    subject = msg["payload"]["utt"]["subject"]
    squal = msg["payload"]["utt"]["squal"]
    num = self.get_num(val, subject, squal)
    text = "No value given, level not changed"
    if num:
      text = "mic level changed to %s percent" % (num,)
      self.set_mic_level(num)
      self.speak(text)

  def handle_query_mic(self, message):
    # for questions only right now
    text = "the microphone is currently set to %s percent" % (self.mic_level,)
    self.speak(text)

  def set_volume(self, new_volume):
    self.volume_level = new_volume
    self.hal.set_output_level(self.volume_level)
    return self.volume_level

  def get_volume(self):
    return self.hal.get_output_level()

  def handle_message(self, msg):
    # also handle volume mute and volume unmute messages
    self.log.debug(f"VolumeSkill.handle_message() msg: {msg}")
    if msg["payload"]["subtype"] == "mute_volume":
      self.handle_mute(None)
    if msg["payload"]["subtype"] == "unmute_volume":
      self.handle_unmute(None)

  def handle_intent_match(self,msg):       # for questions only right now
    text = "the volume is currently set to %s percent" % (self.get_volume(),)
    self.speak(text)

  def handle_change(self,msg):
    val = msg["payload"]["utt"]["value"]
    subject = msg["payload"]["utt"]["subject"]
    squal = msg["payload"]["utt"]["squal"]
    num = self.get_num(val, subject, squal)
    text = "No value given, volume not changed"
    if num:
      text = f"volume changed to {num} percent"
      self.set_volume(num)
    self.speak(text)

  def handle_increase(self,msg):
    if self.volume_level < 91:
      new_volume = self.volume_level + 10
      self.set_volume(new_volume)
      text = "volume changed to %s percent" % (new_volume,)
      self.speak(text)

  def handle_decrease(self,msg):
    if self.volume_level > 9:
      new_volume = self.volume_level - 10
      self.set_volume(new_volume)
      text = "volume changed to %s percent" % (new_volume,)
      self.speak(text)

  def handle_mute(self,msg):
    self.log.debug("Inside handle mute!")
    self.muted_volume = self.volume_level
    self.log.debug("** handle_mute() saving volume is %s**" % (self.muted_volume,))
    self.volume_level = 0
    self.set_volume(self.volume_level)

  def handle_unmute(self,msg):
    self.log.debug("Inside handle unmute!")
    self.volume_level = self.muted_volume
    self.log.debug(f"handle_unmute() restoring volume is %s**" % (self.muted_volume,))
    self.set_volume(self.volume_level)

  def stop(self,msg=None):
    self.log.debug(f"Volume skill stop() method called WITH message {msg}")

if __name__ == "__main__":
  vs = VolumeSkill()
  Event().wait()                           # wait forever

