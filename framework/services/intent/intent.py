import time
import glob
import os
import numpy as np
import subprocess
import json
from urllib import request as urlrequest
from bus.MsgBus import MsgBus
from framework.util.utils import LOG, Config, get_wake_words, aplay, normalize_sentence, remove_pleasantries
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo
from framework.services.intent.nlp.shallow_parse.shallow_utils import scrub_sentence, remove_articles
from skills.sva_base import SimpleVoiceAssistant
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Intent:
  def __init__(self, bus=None, timeout=5):
    self.skill_id = "intent_service"
    self.bus = MsgBus(self.skill_id)
    self.intents = {}
    self.base_dir = os.getenv("SVA_BASE_DIR")
    self.tmp_file_path = self.base_dir + "/tmp/"
    self.speaker = SimpleVoiceAssistant(bus=None, skill_id="intent_speaker")
    log_filename = self.base_dir + "/logs/intent.log"
    self.log = LOG(log_filename).log
    self.earcon_filename = self.base_dir + "/framework/assets/earcon_start.wav"
    self.is_running = False
    cfg = Config()
    self.crappy_aec = cfg.get_cfg_val("Advanced.CrappyAEC")
    self.recognized_verbs = []
    self.stop_aliases = ["stop", "terminate", "abort", "cancel", "kill", "exit"]
    self.question_words_set = set()
    qw_file = f"{self.base_dir}/framework/question_words.txt"
    try:
      with open(qw_file) as f:
        for line in f:
          w = line.strip().lower()
          if w:
            self.question_words_set.add(w)
    except FileNotFoundError:
      # Fallback common question words
      self.question_words_set = {'what', 'where', 'when', 'who', 'why', 'how', 'which', 'is', 'are', 'do', 'does', 'did', 'can', 'could', 'would', 'will', 'should'}
    self.wake_words = []
    wws = get_wake_words()
    for ww in wws:
      self.wake_words.append(ww.lower())
    self.log.debug("Intent.__init__() registering handle_register_intent and handle_system_message")
    self.bus.on("register_intent", self.handle_register_intent)
    self.bus.on("system", self.handle_system_message)

    # TF-IDF fast intent matcher
    self.log.info("Initializing TF-IDF intent matcher...")
    self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, stop_words='english')
    self.intent_patterns = []
    self.intent_keys = []
    self.pattern_embeddings = None
    self.threshold = 0.35
    self.log.info("Intent matcher ready.")

  def register_intent_pattern(self, skill_id, intent_key, example_phrases):
    for phrase in example_phrases:
      norm_phrase = phrase.lower().strip()
      self.intent_patterns.append(norm_phrase)
      self.intent_keys.append((skill_id, intent_key))
      self.log.debug(f"Registered pattern: '{norm_phrase}' -> {skill_id}:{intent_key}")
    self._rebuild_tfidf()

  def _rebuild_tfidf(self):
    if not self.intent_patterns:
      self.pattern_embeddings = None
      return
    self.pattern_embeddings = self.vectorizer.fit_transform(self.intent_patterns)

  def fast_intent_match(self, user_sentence, intent_type=None):
    if self.pattern_embeddings is None or self.pattern_embeddings.shape[0] == 0:
      return None, None, 0.0
    user_vec = self.vectorizer.transform([user_sentence.lower()])
    similarities = cosine_similarity(user_vec, self.pattern_embeddings)[0]
    # Build list of indices matching the requested intent_type (if any)
    valid_indices = []
    for i, (skill_id, key) in enumerate(self.intent_keys):
      if intent_type is None or key.startswith(intent_type + ":"):
        valid_indices.append(i)
    if not valid_indices:
      return None, None, 0.0
    # Find best among valid indices
    best_idx = valid_indices[np.argmax([similarities[i] for i in valid_indices])]
    best_score = float(similarities[best_idx])
    if best_score >= self.threshold:
      skill_id, intent_key = self.intent_keys[best_idx]
      return skill_id, intent_key, best_score
    return None, None, 0.0

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
      target = "fallback_service"
    if utt == "stop":
      target = "system_skill"

    # Send to fallback service via HTTP request
    if target == "fallback_service":
      self.log.debug("Sending HTTP request to fallback service")
      req_body = json.dumps({
        "sentence": utt.get("sentence", ""),
        "raw_input": utt.get("raw_input", "")
      }).encode("utf-8")
      req = urlrequest.Request(
        "http://localhost:5003/fallback",
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST"
      )
      try:
        with urlrequest.urlopen(req, timeout=15) as resp:
          result = json.loads(resp.read().decode("utf-8"))
        if result.get("action") == "rewrite":
          self.bus.send("utterance", "*", {"utt": result["canonical_utterance"], "subtype": "utt"})
        elif result.get("action") == "answer":
          self.speaker.speak(result["answer"])
        else:
          self.log.warning(f"Unknown fallback response: {result}")
      except Exception as e:
        self.log.error(f"Fallback service request failed: {e}")
      return

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
    sentence = info.get("sentence", "").strip().lower()
    words = sentence.split()

    # Ignore single question word or "computer" + question word
    if len(words) == 1 and words[0] in self.question_words_set:
      return "", ""
    if len(words) == 2 and words[0] == "computer" and words[1] in self.question_words_set:
      return "", ""

    # Play earcon asynchronously
    subprocess.Popen(["aplay", self.earcon_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not sentence:
      return "", ""

    if len(words) == 1 and sentence not in ["pause", "stop", "next", "previous", "resume", "help", "mute", "unmute"]:
      self.log.info(f"Short utterance '{sentence}' -> fallback_service")
      return "fallback_service", ""

    skill_id, intent_key, score = self.fast_intent_match(sentence, intent_type="Q")
    if skill_id and score >= 0.5:
      self.log.debug(f"High confidence match: '{sentence}' -> {skill_id} (score {score:.2f})")
      return skill_id, intent_key
    self.log.debug(f"Low confidence ({score:.2f}) or no match -> fallback_service")
    return "fallback_service", ""

  def get_intent_match(self, info):
    sentence = info.get("sentence", "").strip().lower()
    words = sentence.split()

    # Ignore single question word or "computer" + question word
    if len(words) == 1 and words[0] in self.question_words_set:
      return "", ""
    if len(words) == 2 and words[0] == "computer" and words[1] in self.question_words_set:
      return "", ""

    # Play earcon asynchronously
    subprocess.Popen(["aplay", self.earcon_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not sentence:
      return "", ""

    if len(words) == 1 and sentence not in ["pause", "stop", "next", "previous", "resume", "help", "mute", "unmute"]:
      self.log.info(f"Short utterance '{sentence}' -> fallback_service")
      return "fallback_service", ""

    skill_id, intent_key, score = self.fast_intent_match(sentence, intent_type="C")
    if skill_id and score >= 0.5:
      self.log.debug(f"High confidence match: '{sentence}' -> {skill_id} (score {score:.2f})")
      return skill_id, intent_key
    self.log.debug(f"Low confidence ({score:.2f}) or no match -> fallback_service")
    return "fallback_service", ""

  def handle_register_intent(self, msg):
    subject = msg["payload"]["subject"].replace(":", ";").lower()
    verb = msg["payload"]["verb"]
    intent_type = msg["payload"]["intent_type"]
    skill_id = msg["payload"]["skill_id"]
    key = f"{intent_type}:{subject}:{verb}"
    if key in self.intents:
      self.log.warning(f"Intent.handle_register_intent() Intent clash! key: {key} skill_id: {skill_id}")
    else:
      self.log.info(f"Intent.handle_register_intent() adding key {key} to intents")
      self.intents[key] = {"skill_id": skill_id, "state": "enabled"}
      if subject:
        example = f"{verb} {subject}"
      else:
        example = verb
      self.register_intent_pattern(skill_id, key, [example])

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
        # Ignore exactly "computer what" (breaks the echo loop)
        if utt.lower().strip() == "computer what":
          self.log.debug(f"Ignoring 'computer what' utterance")
          os.remove(txt_file)
          continue
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
            self.log.info(f"Intent.run(): Match Question.")
            start_match = time.perf_counter()
            info["skill_id"], info["intent_match"] = self.get_question_intent_match(info)
            elapsed_match = (time.perf_counter() - start_match) * 1000
            self.log.info(f"TIMING intent match (question): {elapsed_match:.1f} ms")
            if info["skill_id"]:
              self.log.info(f'Intent.run(): Matched skill_id: {info["skill_id"]} intent_match: {info["intent_match"]}')
              self.send_utt(info)
            else:
              info["skill_id"] = "fallback_service"
              self.send_utt(info)
          elif si.sentence_type == "C":
            self.log.info("Intent.run(): Match Command")
            start_match = time.perf_counter()
            info["skill_id"], info["intent_match"] = self.get_intent_match(info)
            elapsed_match = (time.perf_counter() - start_match) * 1000
            self.log.info(f"TIMING intent match (command): {elapsed_match:.1f} ms")
            if info["skill_id"]:
              self.send_utt(info)
            else:
              info["skill_id"] = "fallback_service"
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
