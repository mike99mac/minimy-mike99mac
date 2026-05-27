import time
import glob
import os
from bus.MsgBus import MsgBus
from framework.util.utils import LOG, Config, get_wake_words, aplay, normalize_sentence, remove_pleasantries
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo
from framework.services.intent.nlp.shallow_parse.shallow_utils import scrub_sentence, remove_articles

class Intent:
  # English language specific intent parser
  # Monitors the save_text/ dir for utterances to process, if wake words not detected speech is ignored
  # Emits utterance messages. If skill_id is not '' the utterance matched an intent in the skill_id skill
  def __init__(self, bus=None, timeout=5):
    self.skill_id = "intent_service"
    self.bus = MsgBus(self.skill_id)
    self.intents = {}
    self.base_dir = os.getenv("SVA_BASE_DIR")
    self.tmp_file_path = self.base_dir + "/tmp/"
    log_filename = self.base_dir + "/logs/intent.log"
    self.log = LOG(log_filename).log
    self.earcon_filename = self.base_dir + "/framework/assets/earcon_start.wav"
    self.is_running = False
    cfg = Config()
    self.crappy_aec = cfg.get_cfg_val("Advanced.CrappyAEC")
    remote_nlp = cfg.get_cfg_val("Basic.NLP.UseRemote")
    self.use_remote_nlp = True
    if remote_nlp and remote_nlp == "n":
      self.use_remote_nlp = False
    self.recognized_verbs = []
    self.stop_aliases = ["stop", "terminate", "abort", "cancel", "kill", "exit"]
    self.wake_words = []
    wws = get_wake_words()
    for ww in wws:
      self.wake_words.append(ww.lower())
    self.log.debug("Intent.__init__() registering handle_register_intent and handle_system_message")
    self.bus.on("register_intent", self.handle_register_intent)
    self.bus.on("system", self.handle_system_message)

  def handle_system_message(self, msg):
    skill_id = msg["payload"]["skill_id"]
    self.log.debug(f"Intent.handle_system_message() skill_id:  {skill_id}")
    if skill_id == "system_skill":
      subtype = msg["payload"]["subtype"]
      verb = msg["payload"]["verb"]
      self.log.debug(f"Intent.handle_system_message(): subtype: {subtype} verb: {verb}")  
      if subtype == "reserve_oob":
        self.recognized_verbs.append(verb)
      elif subtype == "release_oob":
        if verb in self.recognized_verbs:
          del self.recognized_verbs[verb]

  def is_oob(self, utt):
    ua = utt.split(" ")
    self.log.debug(f"Intent.is_oob(): utt: {utt}")
    self.log.debug(f"Intent.is_oob(): recognized_verbs: {self.recognized_verbs}")
    base_verb = ua[0]
    if base_verb in self.recognized_verbs or base_verb in self.stop_aliases or base_verb == "pause" or base_verb == "resume":
      self.log.debug("Intent.is_oob(): Intent Barge-In Normal OOB Detected")
      return "t"
    elif len(ua) == 2:
      for next_key in self.intents:
        next_key = next_key.split(":")
        if next_key[0] == "O" and ua[0] == next_key[2] and ua[1] == next_key[1]:
          self.log.debug("Intent.is_oob(): two-word OOB detected")
          return "t"
    self.log.debug(f"Intent.is_oob(): crappy_aec = {self.crappy_aec}")
    if self.crappy_aec == 'n':
      self.log.debug("Intent.is_oob(): decent AEC - returning 'f'")
      return "f"
    for ww in self.wake_words:
      for alias in self.stop_aliases:
        oob_phrase = f"{ww} {alias}"
        if oob_phrase.lower() in utt.lower() or ( alias in utt.lower() and ww in utt.lower() ):
          self.log.warning("Intent.is_oob(): ** Maybe ? Intent Barge-In detected - returning 'o'")
          return "o"
    self.log.debug("Intent.is_oob(): fell through - returning 'f'")
    return "f"

  def get_sentence_type(self, utt):
    self.log.debug(f"Intent.get_sentence_type() utt: {utt}")
    vrb = utt.split(" ")[0]
    resp = "I"
    for wrd in self.question_words:
      if utt.startswith(wrd):
        resp = "Q"
        break
    self.log.info(f"Intent.get_sentence_type() resp = {resp}")    
    return resp

  def send_utt(self, utt):
    target = utt.get("skill_id", "*")
    if target == "":
      target = "fallback_skill"
    if utt == "stop":
      target = "system_skill"
    self.log.debug(f"Intent.send_utt() sending utt: {utt} to target: {target}")  
    self.bus.send("utterance", target, {"utt": utt,"subtype":"utt"})
    self.log.debug("Intent.send_utt() after bus.send()")  

  def send_media(self, info):
    self.log.debug("Intent.send_media(): sending media request to message bus")
    self.bus.send("media", "media_skill", info)

  def send_oob_to_system(self, utt, contents):
    info = {"subtype": "oob", 
            "skill_id": "system_skill", 
            "from_skill_id": self.skill_id, 
            "sentence_type": "I", 
            "sentence": contents, 
            "verb": utt, 
            "intent_match": ""
           }
    self.log.debug(f"Intent.send_oob_to_system() info = {info}")     
    self.bus.send("system", "system_skill", info)

  def get_question_intent_match(self, info):
    self.log.debug(f"Intent.get_question_intent_match() info: {info}")
    aplay(self.earcon_filename)
    skill_id = ""
    for intent in self.intents:
      stype, subject, verb = intent.split(":") 
      if stype == "Q" and subject in info["subject"] and verb == info["qword"]:
        info["subject"] = subject
        skill_id = self.intents[intent]["skill_id"]
        self.log.debug(f"Intent.get_question_intent_match() matched skill_id: {skill_id}")
        intent_state = self.intents[intent]["state"]
        return skill_id, intent
    return skill_id, ""

  def get_intent_match(self, info):
    self.log.debug(f"Intent.get_intent_match() info: {info}")  
    aplay(self.earcon_filename)
    skill_id = ""
    intent_type = "C"
    if info["sentence_type"] == "I":
      self.log.warning(f"Intent trying to match an informational statement which it is not designed to do! {info}")
      info["sentence_type"] = "C"
    subject = remove_articles(info["subject"])
    if subject:
      subject = subject.replace(":",";").lower()
      subject = subject.strip()
      verb = info["verb"].lower().strip()
    else:
      verb = ""
    key = f"{intent_type}:{subject}:{verb}"
    self.log.debug(f"Intent.get_intent_match() key: {key}")
    if key in self.intents:
      skill_id = self.intents[key]["skill_id"]
      intent_state = self.intents[key]["state"]
      self.log.debug(f"Intent.get_intent_match(): matched key: {key} skill_id: {skill_id} intent_state: {intent_state}")
      return skill_id, key
    return skill_id, ""

  def handle_register_intent(self, msg):
    subject = msg["payload"]["subject"].replace(":", ";").lower()
    verb = msg["payload"]["verb"]
    intent_type = msg["payload"]["intent_type"]
    key = f"{intent_type}:{subject}:{verb}"
    if key in self.intents:
      skill_id = msg["payload"]["skill_id"]
      self.log.warning(f"Intent.handle_register_intent() Intent clash! key: {key} skill_id: {skill_id}")
    else:
      self.log.info(f"Intent.handle_register_intent() adding key {key} to intents")
      self.intents[key] = {"skill_id": msg["payload"]["skill_id"], "state": "enabled"}

  def run(self):
    self.log.debug(f"Intent.run() intents: {self.intents}")
    si = SentenceInfo(self.base_dir)
    while self.is_running:
      mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_text/*.txt")] )
      if len(mylist) > 0:
        txt_file = mylist[0]
        fh = open(txt_file)
        contents = fh.read()
        fh.close()
        start = contents.find("]")
        utt_type = contents[1:start]
        utt = contents[start+1:]
        utt = scrub_sentence(utt)
        self.log.debug(f"Intent.run() got txt_file: {txt_file} contents: {contents} utt: {utt}")
        oob_type = self.is_oob(utt)
        self.log.debug(f"Intent.run() oob_type: {oob_type} utt_type: {utt_type} utt: {utt}")
        if oob_type == "t":
          self.send_oob_to_system(utt, contents) 
        elif oob_type == "o":
          self.send_oob_to_system("stop", contents) 
        elif utt_type == "RAW":
          if contents:
            self.bus.send("raw", "system_skill", {"subtype": "utt", "utterance": contents[5:]})
        else:
          sentence_type = si.get_sentence_type(utt)
          self.log.debug(f"Intent.run() sentence_type: {sentence_type} utt = {utt}")
          utt = normalize_sentence(utt)
          if sentence_type != "Q":
            utt = remove_pleasantries(utt)
          start_nlp = time.perf_counter()
          si.parse_utterance(utt)
          elapsed_nlp = (time.perf_counter() - start_nlp) * 1000
          self.log.info(f"TIMING NLP parse: {elapsed_nlp:.1f} ms")
          info = {"sentence_type": si.sentence_type, 
                  "sentence": si.original_sentence, 
                  "normalized_sentence": si.normalized_sentence, 
                  "qtype": si.insight.qtype, 
                  "np": si.insight.np, 
                  "vp": si.insight.vp, 
                  "subject": si.insight.subject, 
                  "squal": si.insight.squal, 
                  "question": si.insight.question,
                  "qword": si.insight.question, 
                  "value": si.insight.value, 
                  "raw_input": contents, 
                  "verb": si.insight.verb,
                  "aux_verb": si.insight.aux_verb,
                  "rule": si.structure.shallow,
                  "tree": si.structure.tree,
                  "subtype": "", 
                  "from_skill_id": "", 
                  "skill_id": "", 
                  "intent_match": ""
                 }

          if si.sentence_type == "Q":
            self.log.info(f"Intent.run(): Match Question. key=Q:{si.insight.question}:{si.insight.subject}")
            start_match = time.perf_counter()
            info["skill_id"], info["intent_match"] = self.get_question_intent_match({"subject":info["subject"], "qword":info["question"]})
            elapsed_match = (time.perf_counter() - start_match) * 1000
            self.log.info(f"TIMING intent match (question): {elapsed_match:.1f} ms")
            self.log.info(f'Intent.run(): Match Question. skill_id: {info["skill_id"]} intent_match: {info["intent_match"]}')
            self.send_utt(info) 
          elif si.sentence_type == "C":
            self.log.info("Intent.run(): Match Command")
            start_match = time.perf_counter()
            info["skill_id"], info["intent_match"] = self.get_intent_match(info)
            elapsed_match = (time.perf_counter() - start_match) * 1000
            self.log.info(f"TIMING intent match (command): {elapsed_match:.1f} ms")
            self.send_utt(info) 
          elif si.sentence_type == "M":
            self.log.info("Intent.run(): Media Command")
            info["skill_id"] = "media_skill"
            info["from_skill_id"] = self.skill_id
            info["subtype"] = "media_query"
            self.send_media(info) 
          elif si.sentence_type == "O":
            self.log.info("Intent.run(): OOB Command")
            base_verb = utt.split(" ", 1)[0]
            if base_verb in self.recognized_verbs:
              self.send_oob_to_system(utt, contents)
            else:
              self.log.warning(f"Intent.run() Ignoring unrecognized OOB si.sentence_type {si.sentence_type} not found in {self.recognized_verbs}")
          else:
            self.log.info(f"Intent.run(): Unknown sentence type {si.sentence_type} or Informational sentence")
        os.remove(txt_file)
      time.sleep(0.125)

if __name__ == "__main__":
  up = Intent()
  up.is_running = True
  up.run()
