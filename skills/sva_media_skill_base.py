from skills.sva_base import SimpleVoiceAssistant
from bus.MsgBus import MsgBus
import time

class MediaSkill(SimpleVoiceAssistant):
  def __init__(self, skill_id=None, skill_category=None, bus=None, timeout=5):
    """
    All user media skills inheret from the MediaSkill. A user media
    skill must have at least two methods defined; get_media_confidence()
    and media_play(). A media skill is called first to return the 
    confidence level it has regarding a media play request. If its 
    confidence is the highest it is later called to play that media. 
    """
    super().__init__(msg_handler=self.handle_message, skill_id=skill_id, skill_category=skill_category)
    time.sleep(1)            # give fall back skill a chance to initialize
    self.log.debug("MediaSkill.__init__()")
    info = {               # register with the system media skill
      "subtype": "media_register_request",
      "skill_id": "media_skill",
      "media_skill_id": skill_id
      }
    self.bus.send("skill", "media_skill", info)

  def handle_message(self, msg):
    self.log.debug(f"MediaSkill.handle_message() msg: {msg}")
    subtype = msg["payload"]["subtype"]
    if subtype == "media_get_confidence":
      skill_data = self.get_media_confidence(msg)
      info = {"subtype": "media_confidence_response", "skill_id": "media_skill", "skill_data": skill_data}
      self.send_message("media_skill", info)
    if subtype == "media_play":
      self.media_play(msg)

