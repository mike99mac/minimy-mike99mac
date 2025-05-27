from skills.sva_base import SimpleVoiceAssistant
from framework.util.utils import Config, aplay
from threading import Event
import os
import time

INTERNAL_PAUSE = 1
EXTERNAL_PAUSE = 2

class SystemSkill(SimpleVoiceAssistant):
  # The system skill provides several important functions:

  # 1) It handles out of band (oob) messages which are basically single word verbs. Typically these are things
  # like "stop", "terminate", etc but it also handles common media commands like "pause", "rewind", etc. skills may
  # also register new single verb oobs as well as overide defaults. for example, the alarm skill overides the 
  # stop class of verbs when it has an active alarm. it should be noted that "stop" is a special class of oob
  # and has aliases and is always handled a bit different.

  # 2) It handles the coordination of skills and focus. Skills may request focus of the 
  # speaker and based on overall system activity the system skill may grant or decline focus. it will also
  # handle any side effects arising from this like cancelling or pausing other active skills based on
  # the categories of skills involved at the time.

  # 3) It manages the active skills array and the conversant skills arrays which help
  # it make system level decisions during the course of its execution. 

  # 4) It responds to the get_sys_info message which provides system information on demand.

  def __init__(self, bus=None, timeout=5):
    self.skill_id = "system_skill"
    super().__init__(msg_handler=self.handle_message, skill_id=self.skill_id, skill_category="system")
    self.log.debug("SystemSkill:__init__()")
    self.active_skills = []
    self.conversant_skills = []
    self.stop_aliases = ["stop", "terminate", "abort", "cancel", "kill", "exit"]
    self.recognized_verbs = {}             # out of band messages
    self.stop_overide = None
    self.pause_requestor = None
    self.pause_requesting_skill_category = None
    self.pause_reason = None
    cfg = Config()                         # get config file
    self.cfg_remote_stt = cfg.get_cfg_val("Advanced.STT.UseRemote")
    self.cfg_remote_tts = cfg.get_cfg_val("Advanced.TTS.UseRemote")
    self.cfg_remote_nlp = cfg.get_cfg_val("Advanced.NLP.UseRemote")
    self.cfg_platform = cfg.get_cfg_val("Advanced.Platform")
    self.cfg_version = cfg.get_cfg_val("Basic.Version")
    self.cfg_wake_words = cfg.get_cfg_val("Basic.WakeWords")
    self.base_dir = cfg.get_cfg_val("Basic.BaseDir")
    self.play_filename = self.base_dir + "/framework/assets/stop.wav"

  def send_pause(self, target_skill):
    self.log.debug(f"SystemSkill:send_pause() target_skill: {target_skill}")
    subtype = "pause"
    if self.pause_reason == INTERNAL_PAUSE:
      subtype = "pause_internal"
    info = {"error": "",
            "subtype": subtype,
            "skill_id": target_skill,
            "from_skill_id": self.skill_id
           }
    self.bus.send("system", target_skill, info)

  def send_resume(self, target_skill):
    self.log.debug(f"SystemSkill:send_pause() target_skill: {target_skill}")
    info = {"error":"",
            "subtype": "resume",
            "skill_id": target_skill,
            "from_skill_id": self.skill_id
           }
    self.bus.send("system", target_skill, info)

  def respond_sys_info(self, payload):
    self.log.debug("SystemSkill:respond_sys_info()")
    info = {"error": "",
            "subtype": "sys_info_response",
            "skill_id": payload["from_skill_id"],
            "from_skill_id": self.skill_id,
            "remote_stt": self.cfg_remote_stt,
            "remote_tts": self.cfg_remote_tts,
            "remote_nlp": self.cfg_remote_nlp,
            "platform": self.cfg_platform,
            "wake_words": self.cfg_wake_words
           }
    self.bus.send("skill", payload["from_skill_id"], info)

  def reserve_oob(self, payload):
    oob_verb = payload["verb"]
    if oob_verb in self.stop_aliases:      # special handling for stop
      self.log.info(f'SystemSkill.reserve_oob() system stop acquired by {payload["from_skill_id"]}')
      self.stop_overide = payload["from_skill_id"]
    else:
      self.recognized_verbs[oob_verb] = payload["from_skill_id"]
      self.log.debug(f"SystemSkill:reserve_oob() added verb: {verb} to recognized_verbs")

  def release_oob(self, payload):
    self.log.debug("SystemSkill.release_oob()")
    oob_verb = payload["verb"]
    if oob_verb in self.stop_aliases:      # special handling for stop
      self.log.info(f'SystemSkill.release_oob(): system stop released by {payload["from_skill_id"]}')
      self.stop_overide = None
    else:
      if payload["verb"] in self.recognized_verbs:
        del self.recognized_verbs[ payload["verb"] ]
      else:
        self.log.warning(f'SystemSkill.release_oob(): skill_id: payload["from_skill_id"] release unrecognized verb: payload["verb"]')

  def find_active_skill(self, skill_id):
    self.log.debug(f"SystemSkill:find_active_skill() skill_id: {skill_id}")
    for skill in self.active_skills:
      if skill["skill_id"] == skill_id:
        self.log.debug(f"SystemSkill:find_active_skill() skill_id: {skill_id} is active")
        return skill
    return None

  def input_focus_determination(self, new_skill_cat):
    self.log.debug(f"SystemSkill:input_focus_determination() new_skill_cat: {new_skill_cat}")
    return True

  def output_focus_determination(self, new_skill_cat):
    # A skill is requesting focus. determine if this request should honored or denied and what 
    # should happen as a result of this action.
    last_active_skill_id = self.active_skills[len(self.active_skills) - 1]["skill_id"]
    last_active_skill_category = self.active_skills[len(self.active_skills) - 1]["skill_category"]
    self.log.debug(f"SystemSkill:output_focus_determination() last_id: {last_active_skill_id} last_cat {last_active_skill_category} new_cat: {new_skill_cat}")
    if last_active_skill_category == "media": # media skills are paused except by a new media request which terminates current skill
      if new_skill_cat == "media":
        return "cancel"
      else:
        return "pause"
    if last_active_skill_category == "qna": # qna skills are paused by everything except media skills which terminate them
      if new_skill_cat == "media":
        return "cancel"
      else:
        return "pause"
    if last_active_skill_category == "user":
      if new_skill_cat == "system":
        return "pause"
      return "cancel"
    return "deny"

  def handle_raw(self, msg):
    self.log.debug(f"SystemSkill:handle_raw() msg: {msg}")
    if len(self.conversant_skills) > 0:
      tmp_obj = self.conversant_skills[len(self.conversant_skills)-1]
      target_skill = tmp_obj["skill_id"]
      self.bus.send("raw", target_skill, msg["payload"]) # forward message onto apprpriate skill
    else:
      self.log.warning(f"SystemSkill:handle_raw(): ignoring raw with no converse active! msg: {msg}")

  def handle_message(self, msg):
    # handle system messages and also raw messages to manage input focus
    msg_type = msg["msg_type"]
    subtype = msg["payload"]["subtype"]
    self.log.debug(f"SystemSkill:handle_message() msg: {msg}")
    if msg_type == "raw":
      return self.handle_raw(msg)
    if msg["msg_type"] != "system":        # only handle system messages and the raw exception above
      self.log.debug(f"SystemSkill:handle_message() msg_type = {msg_type} is not system - returning False")
      return False
    if subtype == "oob":                   # single word verb ...
      verb = msg["payload"]["verb"]
      verb = verb.split(" ", 1)[0]         # use just first word - i.e. "next track" just means "next"  -MM
      self.log.debug(f"SystemSkill:handle_message() verb = {verb}")
      if verb in self.stop_aliases:
        self.log.info(f"SystemSkill.handle_message(): Detected System Level Stop, active_skills = {self.active_skills}")
        aplay(self.play_filename)
        if len(self.conversant_skills) > 0: # deal with conversants
          self.log.info(f"SystemSkill:handle_message() conversand_skills: {self.conversant_skills}")
          self.log.info("FYI doing nothing about it for now, but should probably stop them too!")
        if self.stop_overide is not None:  # handle stop overide
          skill_id = self.stop_overide     # stop has been overidden by a skill, send stop to that skill only.
          self.log.info(f"SystemSkill.handle_message(): STOP OVERIDE! Sending stop to {skill_id}")
          info = {"error": "",
                  "subtype": "stop",
                  "skill_id": skill_id,
                  "from_skill_id": self.skill_id
                 }
          self.bus.send("system", skill_id, info)
          return                           # and consume the event
        if len(self.active_skills) > 0:    # fall thru to active skills
          skill_id = self.active_skills[len(self.active_skills)-1]["skill_id"]
          self.log.info(f"SystemSkill.handle_message(): Sending stop to skill: {skill_id}")
          info = {"error": "",
                  "subtype": "stop",
                  "skill_id": skill_id,
                  "from_skill_id": self.skill_id
                 }
          self.bus.send("system", skill_id, info)
        else:                              # ignore stop oob
          self.log.info("SystemSkill.handle_message() Stop Ignored Because active_skills array empty")
      elif verb in self.recognized_verbs: # if oob recognized
        skill_id = self.recognized_verbs[verb]
        info = {"error": "",
                "subtype": "oob_detect",
                "skill_id": skill_id,
                "from_skill_id": self.skill_id,
                "verb": verb
               }
        self.log.debug(f"SystemSkill.handle_message(): skill_id: {skill_id} sending info: {info}")
        self.bus.send("skill", skill_id, info)
      else:                                # special case pause and resume
        if verb == "pause":
          if len(self.active_skills) > 0:
            last_active_skill_id = self.active_skills[len(self.active_skills) - 1]["skill_id"]
            self.log.debug("SystemSkill.handle_message(): EXTERNAL PAUSE")
            self.pause_reason = EXTERNAL_PAUSE
            self.send_pause(last_active_skill_id)
        elif verb == "resume":
          if len(self.active_skills) > 0:
            last_active_skill_id = self.active_skills[len(self.active_skills) - 1]["skill_id"]
            self.log.debug(f"SystemSkill.handle_message(): EXTERNAL RESUME skill: {last_active_skill_id} active_skills: {self.active_skills}")
            self.send_resume(last_active_skill_id)
        else:                              # unrecognized oob 
          self.log.info(f"SystemSkill.handle_message(): Unrecognized verb {verb}")
          verb, subject = verb.split(" ")
          utt = {"error": "", 
                 "verb": verb, 
                 "value": "derived from verb", 
                 "subject": subject, 
                 "squal": "", 
                 "tree": "(VP)", 
                 "structure": "VP", 
                 "sentence_type": "I", 
                 "sentence": msg["payload"]["sentence"], 
                 "skill_id": "???????????", 
                 "intent_match": ""
                }
          self.bus.send("utterance", "*", {"utt": utt, "subtype": "utt"})
    elif subtype == "request_output_focus":
      from_skill_id = msg["payload"]["from_skill_id"]
      requesting_skill_category = msg["payload"]["skill_category"]
      allowed_to_activate = True
      focus_response = ""
      if len(self.active_skills) != 0:
        # A skill is requsting to go active, but we already have an active skill or two so we hit a focus
        # inflection point. We may deny the activate request, we may stop the previously active skill
        # and then approve the activate request or we may pause the currently active skill, and 
        # then approve the activate request.
        last_active_skill_id = self.active_skills[len(self.active_skills) - 1]["skill_id"]
        focus_response = self.output_focus_determination(requesting_skill_category)
        self.log.info(f"SystemSkill.handle_message(): focus_response: {focus_response} last_active_skill_id: {last_active_skill_id} requesting_skill_category: {requesting_skill_category} from_skill_id:{from_skill_id}") 
        if focus_response == "cancel":
          self.log.info(f"SystemSkill.handle_message(): Stopping skill {last_active_skill_id}")
          info = {"error": "",
                  "subtype": "stop",
                  "skill_id": last_active_skill_id,
                  "from_skill_id": self.skill_id
                 }
          self.bus.send("system", last_active_skill_id, info)
          self.active_skills = self.active_skills[:-1] # remove from active skills array
          self.log.debug("SystemSkill.handle_message(): Send activate accepted message")
          allowed_to_activate = True
        elif focus_response == "pause":
          self.pause_requestor = from_skill_id
          self.pause_requesting_skill_category = requesting_skill_category
          active_skill_entry = self.find_active_skill(self.pause_requestor)
          if active_skill_entry is None:
            self.active_skills.append( {"skill_id":self.pause_requestor, "skill_category":self.pause_requesting_skill_category} )
            self.log.debug(f"SystemSkill.handle_message(): activated: {self.pause_requestor} active_skills: {self.active_skills}")
          else:
            self.active_skills.append( {"skill_id":self.pause_requestor, "skill_category":self.pause_requesting_skill_category} )
            self.log.warning(f"SystemSkill.handle_message(): Warning skill already active: {self.pause_requestor}")
          self.log.debug("SystemSkill.handle_message(): INTERNAL PAUSE")
          self.pause_reason = INTERNAL_PAUSE
          self.send_pause(last_active_skill_id)
          return 
        elif focus_response == "deny":
          allowed_to_activate = False
          self.log.info("SystemSkill.handle_message(): Send activate declined message")
        else:
          allowed_to_activate = False
          self.log.warning(f"SystemSkill.handle_message(): Creepy Error 102 - undefined focus_response: {focus_response}")
          self.log.warning("SystemSkill.handle_message(): Send activate declined message")
      if not allowed_to_activate:
        self.log.warning(f"SystemSkill.handle_message(): Sending negative activate_response to {from_skill_id}")
        info = {"error": "focus denied",
                "subtype": "request_output_focus_response",
                "status": "denied",
                "skill_id": from_skill_id,
                "from_skill_id": self.skill_id
               }
        self.bus.send("system", from_skill_id, info)
      else:  
        info = {"error": "",
                "subtype": "request_output_focus_response",
                "status": "confirm",
                "skill_id": from_skill_id,
                "from_skill_id": self.skill_id
               }
        self.log.debug(f"SystemSkill.handle_message(): Sending activate_response from_skill_id: {from_skill_id} info: {info}")
        self.bus.send("system", from_skill_id, info)
        active_skill_entry = self.find_active_skill(from_skill_id)
        if active_skill_entry is None:
          self.active_skills.append( {"skill_id":from_skill_id, "skill_category":requesting_skill_category} )
          self.log.debug(f"SystemSkill.handle_message(): activated: {from_skill_id}  active_skills: {self.active_skills}")
        else:
          self.active_skills.append({"skill_id": from_skill_id, "skill_category": requesting_skill_category})
          self.log.warning(f"SystemSkill.handle_message(): from_skill already active: {from_skill_id}")
    elif subtype == "pause_confirmed":
      self.log.debug(f"SystemSkill.handle_message(): pause confirmed - reason: {self.pause_reason} msg: {msg}")
      if self.pause_reason == INTERNAL_PAUSE:
        self.log.debug("SystemSkill.handle_message(): INTERNAL_PAUSE confirmed, sending confirm output focus")
        self.pause_reason = None
        info = {"error": "",
                "subtype": "request_output_focus_response",
                "status": "confirm",
                "skill_id": self.pause_requestor,
                "from_skill_id": self.skill_id
               }
        time.sleep(3)                      # give media a chance to pause
        self.bus.send("system", self.pause_requestor, info)
      elif self.pause_reason == EXTERNAL_PAUSE:
        self.pause_reason = None
        self.log.debug("SystemSkill.handle_message(): EXTERNAL_PAUSE confirmed, doing nothing")
      else:
        self.log.debug("SystemSkill.handle_message(): Creepy Error 103 - got paused confirmed with no reason!")
    elif subtype == "release_output_focus":
      from_skill_id = msg["payload"]["from_skill_id"]
      active_skill_entry = self.find_active_skill(from_skill_id)
      if active_skill_entry is not None:
        self.active_skills.pop(self.active_skills.index(active_skill_entry))
        self.log.info(f"SystemSkill.handle_message(): deactivate {from_skill_id} remaining: {self.active_skills}")
        if len(self.active_skills) > 0:    # resume any previously paused skills
          skill_id = self.active_skills[len(self.active_skills) - 1]["skill_id"]
          self.log.debug(f"SystemSkill.handle_message(): Resuming skill: {skill_id}")
          self.send_resume(skill_id)
    elif subtype == "request_input_focus": # handle converse 
      if len(self.conversant_skills) > 0:
        self.log.warning(f"SystemSkill.handle_message(): Warning already in conversant mode: {self.conversant_skills}")
      requesting_skill_category = msg["payload"]["skill_category"]
      if self.input_focus_determination(requesting_skill_category):
        # add skill to converse array
        tmp_obj = {"skill_id": msg["payload"]["from_skill_id"], "skill_category": msg["payload"]["skill_category"]}
        self.conversant_skills.append( tmp_obj )
        self.log.info(f"SystemSkill.handle_message(): Added {tmp_obj} to conversant skills: {self.conversant_skills}")
        info = {"error": "",
                "subtype": "request_input_focus_response",
                "status": "confirm",
                "skill_id": msg["payload"]["from_skill_id"],
                "from_skill_id": self.skill_id
               }
        self.log.debug(f'SystemSkill.handle_message(): Sending positive input focus_response to: {msg["payload"]["from_skill_id"]}')
        time.sleep(1)                      # for inferior audio input devices
        self.bus.send("system", msg["payload"]["from_skill_id"], info)
      else:
        info = {"error": "focus denied",
                "subtype": "request_input_focus_response",
                "status": "denied",
                "skill_id": msg["payload"]["from_skill_id"],
                "from_skill_id": self.skill_id
               }
        self.log.warning(f'SystemSkill.handle_message(): Sending negative input focus_response to: {msg["payload"]["from_skill_id"]}')
        self.bus.send("system", msg["payload"]["from_skill_id"], info)
    elif subtype == "release_input_focus": # remove skill from converse array
      if len(self.conversant_skills) == 0:
        self.log.warning("SystemSkill.handle_message(): end empty converse array!")
      tmp_obj = {"skill_id": msg["payload"]["from_skill_id"], "skill_category": msg["payload"]["skill_category"]}
      try:
        self.conversant_skills.pop(self.conversant_skills.index(tmp_obj))
      except:
        self.log.error("SystemSkill.handle_message(): exception on conversant skills pop!")
      self.log.info(f"SystemSkill.handle_message(): Removed {tmp_obj} from conversant skills: {self.conversant_skills}")
    elif subtype == "reserve_oob":
      self.reserve_oob(msg["payload"])
    elif subtype == "release_oob":
      self.release_oob(msg["payload"])
    elif subtype == "sys_info_request":
      self.respond_sys_info(msg["payload"])
    else:
      self.log.warning(f"SystemSkill.handle_message(): Unrecognized message: {msg}")

if __name__ == "__main__":
  ss = SystemSkill()
  Event().wait()                           # wait forever

