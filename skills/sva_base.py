import logging
from bus.MsgBusClient import MsgBusClient
import os
from skills.sva_control import SkillControl
from framework.message_types import (
  MSG_UTTERANCE, MSG_SPEAK, MSG_REGISTER_INTENT, MSG_MEDIA, MSG_SYSTEM, MSG_RAW, MSG_SKILL)

class SimpleVoiceAssistant:
  def __init__(self, skill_id=None, skill_category=None, timeout=5):
    print(f"SimpleVoiceAssistant.__init__() skill_id: {skill_id}")
    self.intents = {}
    self.log = logging.getLogger(__name__)
    print(f"SimpleVoiceAssistant.__init__() creating bus skill_id: {skill_id}")
    self.bus = MsgBusClient("SimpleVoiceAssistant")
    self.skill_control = SkillControl()
    self.skill_control.skill_id = skill_id
    self.skill_control.category = skill_category
    self.base_dir = str(os.getenv('SVA_BASE_DIR'))
    log_filename = self.base_dir + '/logs/skills.log'
    self.log.debug(f"SimpleVoiceAssistant.__init__() skill_id: {skill_id}")

  def register_intent(self, intent_type, verb, subject, callback):
    """
    Bind a sentence type, subject, and verb to a callback and send on message bus to intent service.
    """
    self.log.debug(f"SimpleVoiceAssistant.register_intent() intent_type: {intent_type} verb: {verb} subject: {subject}")
    subjects = subject
    verbs = verb
    if type(subject) is not list:
      subjects = [subject]
    if type(verb) is not list:
      verbs = [verb]
    for subject in subjects:
      for verb in verbs:
        key = intent_type + ':' + subject + ':' + verb
        self.intents[key] = callback
        self.log.debug(f"SimpleVoiceAssistant.register_intent() added intent: {key}")
        # Send message to intent service
        info = {
                'intent_type': intent_type,
                'subject': subject,
                'verb': verb,
                'skill_id':self.skill_control.skill_id
               }
        self.bus.send(MSG_REGISTER_INTENT, 'intent_service', info)

  # don't think this is called
  # def check_intent(self, info):
  #   self.bus.send("check_intent", info)

