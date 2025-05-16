from threading import Event
from skills.sva_base import SimpleVoiceAssistant
from framework.util.utils import aplay, Config

class FallbackSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(msg_handler=self.handle_message, skill_id="fallback_skill", skill_category="fallback")
    self.qna_skills = []                   # array of registered qna skill handlers
    cfg = Config()
    base_dir = cfg.get_cfg_val("Basic.BaseDir")
    self.boing_filename = base_dir + "/framework/assets/boing.wav"

  def handle_register_qna(self, msg):
    skill_id = msg["payload"]["qna_skill_id"]
    self.log.info(f"FallbackSkill.handle_register_qna() Registered as a Q&A skill: {skill_id}")
    if skill_id not in self.qna_skills:
      self.qna_skills.append(skill_id)

  def handle_qna_response(self, msg):
    # gather responses and decide who handles question, then send message to that skill_id to play the answer
    msg_out = {"subtype": "qna_answer_question", 
               "skill_id": msg["payload"]["from_skill_id"], 
               "skill_data": msg["payload"]["skill_data"]
              }
    self.log.info(f"FallbackSkill.handle_qna_response() msg_out: {msg_out}")
    self.send_message(msg["payload"]["from_skill_id"], msg_out) # for now assume the only skill to answer gets it

  def handle_message(self, msg):
    self.log.info(f"FallbackSkill.handle_message()")
    subtype = msg["payload"]["subtype"]
    if subtype == "qna_register_request":
      return self.handle_register_qna(msg)
    elif subtype == "qna_confidence_response":
      return self.handle_qna_response(msg)
    else:
      self.log.warning(f"FallbackSkill.handle_message(): unexpected subtype: {subtype}")

  def handle_fallback(self, msg):
    self.log.debug("FallbackSkill:handle_fallback(): hit!")
    data = msg["payload"]["utt"]
    if data["sentence_type"] == "Q":       # for questions only right now
      # send message to all Q&A skills saying you have 3 seconds to give me your confidence level 
      # All Q&A skills need to respond to the "get_confidence" message and the "play_qna_answer" message
      for skill_id in self.qna_skills:
        # send "q" getconf qna
        self.log.debug(f"FallbackSkill:handle_fallback(): sending qna_get_confidence to {skill_id}")
        info = {"subtype": "qna_get_confidence",
                "skill_id": skill_id,
                "sentence_type": "Q",
                "qword": "getconf",
                "np": "qna",
                "intent_match": "Q:getconf:qna",
                "msg_np": data["np"],
                "msg_vp": data["vp"],
                "msg_aux": data["aux_verb"],
                "msg_qword": data["qword"],
                "msg_rule": data["rule"],
                "msg_tree": data["tree"],
                "msg_sentence": data["sentence"]
               }
        self.bus.send("skill", skill_id, info)
    else:
      self.log.debug("** Fallback Skill only handles sentences of type Question for now!, Utterance ignored! **")
      msg_out = {"subtype": "unrecognized_utterance", 
                 "skill_id": "system_monitor_skill", 
                 "skill_data": data
                }
      self.send_message("system_monitor_skill", msg_out)
      aplay(self.boing_filename)

# main()
if __name__ == "__main__":
  fs = FallbackSkill()
  Event().wait()             # Wait forever

