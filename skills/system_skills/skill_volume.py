import asyncio
from framework.message_types import MSG_SYSTEM
from framework.util.utils import execute_command, Config
from framework.hal.hal import Hal
import lingua_franca
from skills.sva_base import SimpleVoiceAssistant
from threading import Event
from lingua_franca import parse
import os

class VolumeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'volume_skill'
    super().__init__(msg_handler=self.handle_message, skill_id=self.skill_id, skill_category='system')
    lingua_franca.load_language('en')
    cfg = Config()
    input_device_id = cfg.get_cfg_val('Advanced.InputDeviceId')
    input_level_control_name = cfg.get_cfg_val('Advanced.InputLevelControlName')
    output_device_name = cfg.get_cfg_val('Advanced.OutputDeviceName')
    output_level_control_name = cfg.get_cfg_val('Advanced.OutputLevelControlName')
    cfg_platform = cfg.get_cfg_val('Advanced.Platform') # workaround until config file can hold the actual module name
    if cfg_platform == 'p':
      from framework.hal.executables.pios import Platform
    else:   
      from framework.hal.executables.ubuntu import Platform
    self.hal = Platform(input_device_id, input_level_control_name, output_device_name, output_level_control_name)

    # we use existing system settings but we could also set them here and overide the system initalization code.
    self.volume_level = 70
    self.set_volume(self.volume_level)
    self.muted_volume = self.volume_level
    self.mic_level = 67
    self.set_mic_level(self.mic_level)

  async def register_intents(self):
    subjects = ['microphone', 'mic', 'input']
    commands = ['set', 'change', 'modify']
    questions = ['what', 'how']
    inactive_state_intents = []            # register intents - subject:verb pairs

    # input volume
    for subject in subjects:
      for command in commands:
        await self.register_intent('C', command, subject, self.handle_change_mic)
        inactive_state_intents.append( 'C' + ':' + subject + ':' + command )
    for subject in subjects:
      for question in questions:
        await self.register_intent('Q', question, subject, self.handle_query_mic)
        inactive_state_intents.append( 'Q' + ':' + subject + ':' + question )

    # output volume
    subject = 'volume'
    await self.register_intent('C', 'turn', subject, self.handle_change)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'turn' )
    await self.register_intent('C', 'set', subject, self.handle_change)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'set' )
    await self.register_intent('C', 'change', subject, self.handle_change)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'change' )
    await self.register_intent('C', 'increase', subject, self.handle_increase)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'increase' )
    await self.register_intent('C', 'decrease', subject, self.handle_decrease)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'decrease' )
    await self.register_intent('C', 'mute', subject, self.handle_mute)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'mute' )
    await self.register_intent('C', 'unmute', subject, self.handle_unmute)
    inactive_state_intents.append( 'C' + ':' + subject + ':' + 'unmute' )

    # if we want a single entry point we can set them programmatically
    for question in questions:
      await self.register_intent('Q', question, subject, self.handle_intent_match)
      inactive_state_intents.append( 'Q' + ':' + subject + ':' + question )

  def get_num(self, v1, v2, v3):
    num = parse.extract_number(v1)
    if not num:
      num = parse.extract_number(v2)
      if not num:
        num = parse.extract_number(v3)
    return num

  def get_mic_level(self):                 # microphone
    self.mic_level = self.hal.get_intput_level()
    return self.mic_level

  def set_mic_level(self, new_level):
    self.mic_level = new_level
    self.hal.set_input_level(self.mic_level)
    return self.mic_level

  def handle_change_mic(self,msg):
    val = msg.data['utt']['value']
    subject = msg.data['utt']['subject']
    squal = msg.data['utt']['squal']
    num = self.get_num(val, subject, squal)
    text = "No value given, level not changed"
    if num:
      text = f"mic level changed to {num} percent"
      self.set_mic_level(num)
      self.speak(text)

  def handle_query_mic(self, message):
    text = f"the microphone is currently set to {self.mic_level} percent"
    self.speak(text)

  def set_volume(self, new_volume):        # speaker 
    self.volume_level = new_volume
    self.hal.set_output_level(self.volume_level)
    return self.volume_level

  def get_volume(self):
    return self.hal.get_output_level()

  # handle volume mute and volume unmute messages
  def handle_message(self, message):
    self.log.debug(f"VolumeSkill.handle_message() data: {message.data}")
    data = message.data
    if data['subtype'] == 'mute_volume':
      self.handle_mute(None)
    if data['subtype'] == 'unmute_volume':
      self.handle_unmute(None)

  def handle_intent_match(self, message):       # for questions only right now
    self.log.debug(f"VolumeSkill.handle_intent_match() data: {message.data}")
    text = f"the volume is currently set to {self.get_volume()} percent" 
    self.speak(text)

  def handle_change(self, message):
    self.log.debug(f"VolumeSkill.handle_change() data: {message.data}")
    val = msg.data['utt']['value']
    subject = msg.data['utt']['subject']
    squal = msg.data['utt']['squal']
    num = self.get_num(val, subject, squal)
    text = "No value given, volume not changed"
    if num:
      text = f"volume changed to {new_volume} percent" 
      self.set_volume(num)
      self.speak(text)

  def handle_increase(self, message):
    self.log.debug(f"VolumeSkill.handle_increase() data: {message.data}")
    if self.volume_level < 91:
      new_volume = self.volume_level + 10
      text = f"volume changed to {new_volume} percent" 
    else:
      new_volume = 100
      text = f"volume is maxed out at {new_volume} percent" 
    self.set_volume(new_volume)
    self.speak(text)

  def handle_decrease(self,msg):
    self.log.debug(f"VolumeSkill.handle_increase() data: {message.data}")
    if self.volume_level > 9:
      new_volume = self.volume_level - 10
      text = f"volume changed to {new_volume} percent" 
    else: 
      new_volume = 0
      text = f"volume is minimum at {new_volume} percent" 
    self.set_volume(new_volume)
    self.speak(text)

  def handle_mute(self, message):
    self.muted_volume = self.volume_level
    self.log.debug(f"VolumeSkill.handle_mute() saving volume: {self.muted_volume} then muting")
    self.volume_level = 0
    self.set_volume(self.volume_level)

  def handle_unmute(self, message):
    self.volume_level = self.muted_volume
    self.log.debug(f"VolumeSkill.handle_unmute() restoring volume: {self.volume_level}")
    self.set_volume(self.volume_level)

  def stop(self, message = None):
    self.log.debug(f"VolumeSkill.stop() message: {message}")

  async def initialize(self):
    await self.register_intents()
    # self.register_intents()

# main()
if __name__ == '__main__':
  vs = VolumeSkill()
  asyncio.run(vs.initialize())
  Event().wait()                           # wait forever

