from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import time

class HelpSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    self.skill_id = "help_skill"
    super().__init__(msg_handler=self.handle_message, skill_id="help_skill", skill_category="user")
    info = {
            "subtype": "reserve_oob",
            "skill_id": "system_skill",
            "from_skill_id": self.skill_id,
            "verb": "help"
           }
    self.bus.send("system", "system_skill", info) # register OOBs 

  def handle_message(self, msg):
    if msg["payload"]["subtype"] == "oob_detect":
      print("\n\nHELP REQUESTED\n\n")
      self.speak("What can I help you with?")
      self.speak("You can say things like general help, or help with alarms or ask me for a list of topics.", wait=True)
      topic = self.get_raw_input()
      self.speak(f"Playing help for {topic}")

  def stop(self):
    pass

if __name__ == "__main__":
  hlp = HelpSkill()
  Event().wait()                           # wait forever

