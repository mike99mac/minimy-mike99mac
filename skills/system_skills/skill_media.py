from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from framework.util.utils import aplay

class SVAMediaSkill(SimpleVoiceAssistant):
  # determine who should handle a media request when tell that skill to handle it 
  def __init__(self, bus=None, timeout=5):
    super().__init__(msg_handler=self.handle_message, skill_id="media_skill", skill_category="media")
    self.skill_id = "media_skill"
    self.log.debug(f"SVAMediaSkill.__init__() skill_id: {self.skill_id} skill_base_dir: {self.skill_base_dir}") 
    self.media_skills = []       # array of registered media skill handlers
    self.active_media_skill = None
    self.tick_file_name = self.base_dir + "/framework/assets/tick.wav"
    info = {"subtype": "reserve_oob", 
            "skill_id": "system_skill", 
            "from_skill_id": self.skill_id, 
            "verb": "pause"
           }
    self.bus.send("system", "system_skill", info)
    info["verb"] = "resume"
    self.bus.send("system", "system_skill", info)
    info["verb"] = "previous"
    self.bus.send("system", "system_skill", info)
    info["verb"] = "next"
    self.bus.send("system", "system_skill", info)
    info["verb"] = "stop"
    self.bus.send("system", "system_skill", info)
    self.log.debug("SVAMediaSkill.__init__(): registering OOB intents") 
    self.register_intent("O", "next", "song", self.handle_next)
    self.register_intent("O", "next", "station", self.handle_next)
    self.register_intent("O", "next", "title", self.handle_next)
    self.register_intent("O", "next", "track", self.handle_next)
    self.register_intent("O", "previous", "song", self.handle_prev)
    self.register_intent("O", "previous", "station", self.handle_prev)
    self.register_intent("O", "previous", "title", self.handle_prev)
    self.register_intent("O", "previous", "track", self.handle_prev)
    self.register_intent("O", "pause", "music", self.handle_pause)
    self.register_intent("O", "resume", "music", self.handle_resume)
    self.register_intent("O", "stop", "music", self.handle_stop)

  def handle_oob_detected(self, msg):
    self.log.debug(f"SVAMediaSkill.handle_oob_detected() OOB detected - msg: {msg}")
    if self.active_media_skill == None:    # nothing is playing
      aplay(self.tick_file_name)           # just play a short tick sound
    else:                                  # something is playing
      oob_type = msg["payload"]["verb"]
      self.log.debug(f"SVAMediaSkill.handle_oob_detected(): oob_type = {oob_type}")
      match oob_type:
        case "previous":
          self.handle_prev(msg)
        case "next":
          self.handle_next(msg)
        case "pause":
          self.handle_pause(msg)
        case "resume":
          self.handle_resume(msg)
        case "stop":
          self.handle_stop(msg)
        case _:
          self.log.error(f"SVAMediaSkill.handle_oob_detected() unexpected OOB: {oob_type}")

  def handle_register_media(self, msg):
    skill_id = msg["payload"]["media_skill_id"]
    if skill_id not in self.media_skills:
      self.media_skills.append(skill_id)   # add to the list
      self.log.debug(f"SVAMediaSkill.handle_register_media() registered media skill: {skill_id}")
    else:
      self.log.warning(f"SVAMediaSkill.handle_register_media() {skill_id} already registered")

  def handle_media_response(self, msg):
    self.log.debug(f"SVAMediaSkill.handle_media_response() msg: {msg}")
    # gather responses and decide who will handle the media then send message to that skill_id to play the media
    # if error play default fail earcon.
    skill_id = msg["payload"]["from_skill_id"]
    msg_out = {"subtype": "media_play", 
               "skill_id": skill_id,
               "from_skill_id": self.skill_id, 
               "skill_data": msg["payload"]["skill_data"]
              }
    self.active_media_skill = skill_id     # this skill is now active
    self.send_message(skill_id, msg_out)   # send the message
    self.log.info(f"SVAMediaSkill.handle_media_response() media skill {skill_id} going active")

  def handle_query(self, msg):
    self.log.debug("SVAMediaSkill.handle_query() hit!")
    # send out message to all media skills saying you got 3 seconds to give me 
    # your confidence level. all media skills need to respond to the "get_confidence"
    # message and the "media_play" message
    for skill_id in self.media_skills:
      self.log.debug(f"SVAMediaSkill.handle_query(): sent media_get_confidence to {skill_id}")
      info = {"subtype": "media_get_confidence",
              "skill_id": skill_id,
              "from_skill_id": self.skill_id,
              "msg_sentence": msg["payload"]["sentence"]
             }
      self.bus.send("skill", skill_id, info)

  def handle_command(self, msg):
    # Handle a media command
    self.log.debug(f"SVAMediaSkill.handle_command(): active media is {self.active_media_skill}")
    msg["payload"]["skill_id"] = "media_player_service"
    msg["payload"]["subtype"] = "media_player_command"
    self.send_message("media_player_service", msg["payload"])

  def handle_message(self, msg):
    # Handle a media message
    self.log.debug(f"SVAMediaSkill.handle_message(): active media: {self.active_media_skill} msg: {msg}")
    subtype = msg["payload"]["subtype"]
    if subtype == "media_register_request":
      return self.handle_register_media(msg)
    elif subtype  == "media_confidence_response":
      return self.handle_media_response(msg)
    elif subtype == "media_query":
      return self.handle_query(msg)
    elif subtype == "media_command":
      return self.handle_command(msg)
    elif subtype == "oob_detect":
      return self.handle_oob_detected(msg)
    else:
      from_skill_id = msg["payload"]["from_skill_id"]
      response = msg["payload"]["response"]
      if from_skill_id == "media_player_service" and subtype == "media_player_command_response" and response == "session_ended" and self.active_media_skill == skill_id:
        self.log.debug(f"SVAMediaSkill.handle_message() media session ended for {self.active_media_skill}")
        self.active_media_skill = None
      else:
        self.log.warning(f"SVAMediaSkill.handle_message() unrecognized subtype: {subtype}")

  def handle_prev(self, msg):
    # Play previous track or station
    self.log.debug("SVAMediaSkill.handle_prev() - calling mpc_cmd(prev)")
    self.mpc_cmd("prev")

  def handle_next(self, message):
    # Play next track or station - called by the playback control skill
    self.log.debug("SVAMediaSkill.handle_next() - calling mpc_cmd(next)")
    self.mpc_cmd("next")

  def handle_pause(self, msg):
    # Pause what is playing
    self.log.info("SVAMediaSkill.handle_pause() - calling mpc_cmd(toggle)")
    self.mpc_cmd("toggle")    # toggle between play and pause

  def handle_resume(self, msg):
    # Resume what was playing
    self.log.info("SVAMediaSkill.handle_resume() - calling mpc_cmd(toggle)")
    self.mpc_cmd("toggle")    # toggle between play and pause

  def handle_stop(self, msg):
    # Clear the mpc queue 
    self.log.info("SVAMediaSkill.handle_resume() - calling mpc_cmd(clear)")
    self.mpc_cmd("clear") 

  def stop(self, message):
    self.log.info("SVAMediaSkill.stop() - pausing music")
    self.mpc_cmd("pause")    

if __name__ == "__main__":
  sva_ms = SVAMediaSkill()
  Event().wait()                           # wait forever

