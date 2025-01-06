import asyncio
from bus.Message import Message
from bus.MsgBusClient import MsgBusClient
from framework.util.utils import LOG, Config, get_wake_words, aplay, normalize_sentence, remove_pleasantries
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo
from framework.services.intent.nlp.shallow_parse.shallow_utils import scrub_sentence, remove_articles
from framework.message_types import (MSG_UTTERANCE, MSG_MEDIA, MSG_RAW, MSG_REGISTER_INTENT, MSG_SYSTEM)
import requests, time, glob, os

class Intent:
  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'intent_service'
    if bus is None:            
      bus = MsgBusClient(self.skill_id)
    self.bus = bus
    self.intents = {}
    self.base_dir = os.getenv('SVA_BASE_DIR')
    self.tmp_file_path = self.base_dir + '/tmp/'
    log_filename = self.base_dir + '/logs/intent.log'
    self.log = LOG(log_filename).log
    self.earcon_filename = self.base_dir + "/framework/assets/earcon_start.wav"
    self.is_running = False        
    cfg = Config()             
    self.crappy_aec = cfg.get_cfg_val('Advanced.CrappyAEC')
    remote_nlp = cfg.get_cfg_val('Advanced.NLP.UseRemote')
    self.use_remote_nlp = True
    if remote_nlp and remote_nlp == 'n':
      self.use_remote_nlp = False
    self.log.debug(f"Intent.__init__() log_filename: {self.log_filename} use_remote_nlp: {self.use_remote_nlp}")
    self.recognized_verbs = []       
    self.stop_aliases = ['stop', 'terminate', 'abort', 'cancel', 'kill', 'exit']
    self.wake_words = []           
    wws = get_wake_words()
    for ww in wws:
      self.log.debug(f"Intent.__init__() registering wakeword {ww}")
      self.wake_words.append(ww.lower())
    self.log.debug(f"Intent.__init__() registering handle_register_intent")
    self.bus.on(MSG_REGISTER_INTENT, self.handle_register_intent) 
    self.bus.on('system', self.handle_system_message)

  def handle_system_message(self, message):
    data = message.data
    self.log.debug(f"Intent.handle_system_message() data = {data}")
    if data['skill_id'] == 'system_skill':
      self.log.debug(f"Intent.handle_system_message() Intent service handle system message {message.data}")
      if data['subtype'] == 'reserve_oob':
        self.recognized_verbs.append(data['verb'])
      if data['subtype'] == 'release_oob':
        self.recognized_verbs.remove(data['verb'])

  def is_oob(self, utt):
    ua = utt.split(" ")
    self.log.debug(f"Intent.is_oob() utt = {utt} ua = {ua}")
    self.log.debug(f"Intent.is_oob() recognized_verbs = {self.recognized_verbs}")
    if len(ua) == 1:
      if ua[0] in self.recognized_verbs or ua[0] in self.stop_aliases or ua[0] == 'pause' or ua[0] == 'resume':
        self.log.debug("Intent.is_oob(): Intent Barge-In Normal OOB Detected")
        return 't'
    elif len(ua) == 2:
      for next_key in self.intents:
        next_key = next_key.split(":")
        if next_key[0] == 'O' and ua[0] == next_key[2] and ua[1] == next_key[1]:
          self.log.debug("Intent.is_oob(): two-word OOB detected")
          return 't'
    self.log.debug(f"Intent.is_oob() crappy_aec = {self.crappy_aec}")
    if not self.crappy_aec:
      self.log.debug("Intent.is_oob(): decent AEC - returning 'f'")
      return 'f'
    for ww in self.wake_words:
      for alias in self.stop_aliases:
        oob_phrase = ww + ' ' + alias
        if oob_phrase.lower() in utt.lower() or (alias in utt.lower() and ww in utt.lower()):
          self.log.warning("Intent.is_oob() ** Maybe ? Intent Barge-In detected - returning 'o'")
          return 'o'
    self.log.debug("Intent.is_oob(): fell through - returning 'f'")
    return 'f'

  def get_sentence_type(self, utt):
    self.log.debug(f"Intent.get_sentence_type() utt = {utt}")
    vrb = utt.split(" ")[0]
    resp = "I"
    for wrd in self.question_words:
      if utt.startswith(wrd):
        resp = "Q"
        break
    self.log.info(f"Intent.get_sentence_type() resp = {resp}")
    return resp

  async def send_utt(self, utt):
    target = utt.get('skill_id', '*')
    if target == '':
      target = '*'
    if utt == 'stop':
      target = 'system_skill'
    self.log.debug(f"Intent.send_utt() sending MSG_UTTERANCE  target = {target}")
    await self.bus.send(MSG_UTTERANCE, target, {'utt': utt, 'subtype': 'utt'})

  async def send_media(self, info):
    self.log.debug(f"Intent.send_media() sending message info: {info}")
    await self.bus.send(MSG_MEDIA, 'media_skill', info)

  async def send_oob_to_system(self, utt, contents):
    info = {
      'error': '',
      'subtype': 'oob',
      'skill_id': 'system_skill',
      'from_skill_id': self.skill_id,
      'sentence_type': 'I',
      'sentence': contents,
      'verb': utt,
      'intent_match': ''
    }
    self.log.debug(f"Intent.send_oob_to_system() info = {info}")
    await self.bus.send(MSG_SYSTEM, 'system_skill', info)

  def get_question_intent_match(self, info):
    self.log.debug(f"Intent.get_question_intent_match(): info: {info}")
    aplay(self.earcon_filename)

    skill_id = ''
    for intent in self.intents:
      self.log.debug(f"Intent.get_question_intent_match(): checking intent: {intent}")
      stype, subject, verb = intent.split(":")
      self.log.debug(f"Intent.get_question_intent_match(): checking stype: {stype} subject: {subject} verb: {verb}")
      if stype == 'Q' and subject in info['subject'] and verb == info['qword']:
        info['subject'] = subject
        skill_id = self.intents[intent]['skill_id']
        intent_state = self.intents[intent]['state']
        self.log.debug(f"Intent.get_question_intent_match(): matched skill_id: {skill_id} intent: {intent}")
        return skill_id, intent
    self.log.debug(f"Intent.get_question_intent_match(): NO MATCH skill_id: {skill_id}")
    return skill_id, ''

  def get_intent_match(self, info):
    self.log.debug("Intent.get_intent_match() ")
    aplay(self.earcon_filename)

    skill_id = ''
    intent_type = 'C'
    if info['sentence_type'] == 'I':
      self.log.warning(f"Intent trying to match an informational statement which it is not designed to do! {info}")
      info['sentence_type'] = 'C'
    subject = remove_articles(info['subject'])
    if subject:
      subject = subject.replace(":", ";")
      subject = subject.strip()
    key = intent_type + ':' + subject.lower() + ':' + info['verb'].lower().strip()
    self.log.debug(f"Intent.get_intent_match() Intent match key: {key}")
    if key in self.intents:
      skill_id = self.intents[key]['skill_id']
      intent_state = self.intents[key]['state']
      self.log.debug(f"Intent.get_intent_match(): key: {key} skill_id: {skill_id} intent_state: {intent_state}")
      return skill_id, key
    return skill_id, ''

  def handle_register_intent(self, msg):
    data = msg.data
    self.log.debug(f"Intent.handle_register_intent() data: {data}")
    subject = data['subject'].replace(":", ";")
    verb = data['verb']
    key = data['intent_type'] + ':' + subject.lower() + ':' + verb
    self.log.warning(f"Intent.handle_register_intent() adding key: {key}")
    if key in self.intents:
      self.log.warning(f"Intent.handle_register_intent() Intent clash! key: {key} skill_id: {data['skill_id']}")
    else:
      self.log.info(f"Intent.handle_register_intent() key {key} is in intent match")
      self.intents[key] = {'skill_id': data['skill_id'], 'state': 'enabled'}

  async def run(self):
    self.log.debug(f"Intent.run() Intent processor started - is_running = {self.is_running}")
    si = SentenceInfo(self.base_dir)

    while self.is_running:
      mylist = sorted([f for f in glob.glob(self.tmp_file_path + "save_text/*.txt")])
      if len(mylist) > 0:
        txt_file = mylist[0]
        with open(txt_file) as fh:
          contents = fh.read()
        start = contents.find("]")
        utt_type = contents[1:start]
        utt = contents[start + 1:]
        utt = scrub_sentence(utt)

        oob_type = self.is_oob(utt)
        self.log.debug(f"Intent.run() oob_type: {oob_type} utt_type: {utt_type} utt: {utt}")
        if oob_type == 't':
          res = await self.send_oob_to_system(utt, contents)
          self.log.debug(f"Intent.run() oob_type t - res: {res}")
        elif oob_type == 'o':
          res = await self.send_oob_to_system('stop', contents)
          self.log.debug(f"Intent.run() oob_type o - res: {res}")
        elif utt_type == 'RAW':
          if contents:
            res = await self.bus.send(MSG_RAW, 'system_skill', {'utterance': contents[5:]})
            self.log.debug(f"Intent.run() utt_type RAW - res: {res}")
        else:
          sentence_type = si.get_sentence_type(utt)
          self.log.debug(f"Intent.run() sentence_type: {sentence_type} utt: {utt}")
          utt = normalize_sentence(utt)
          if sentence_type != 'Q':
            utt = remove_pleasantries(utt)
          si.parse_utterance(utt)
          info = {
            'error': '',
            'sentence_type': si.sentence_type,
            'sentence': si.original_sentence,
            'normalized_sentence': si.normalized_sentence,
            'qtype': si.insight.qtype,
            'np': si.insight.np,
            'vp': si.insight.vp,
            'subject': si.insight.subject,
            'squal': si.insight.squal,
            'question': si.insight.question,
            'qword': si.insight.question,
            'value': si.insight.value,
            'raw_input': contents,
            'verb': si.insight.verb,
            'aux_verb': si.insight.aux_verb,
            'rule': si.structure.shallow,
            'tree': si.structure.tree,
            'subtype': '',
            'from_skill_id': '',
            'skill_id': '',
            'intent_match': ''
          }
          if si.sentence_type == 'Q':
            print(f"Intent.run() Match Question. key: {si.insight.question} subject: {si.insight.subject}")
            info['skill_id'], info['intent_match'] = self.get_question_intent_match({'subject': info['subject'], 'qword': info['question']})
            print(f"Match Question. skill_id: {info['skill_id']} intent_match: {info['intent_match']}")
            await self.send_utt(info)
          elif si.sentence_type == 'C':
            print("Match Command")
            info['skill_id'], info['intent_match'] = self.get_intent_match(info)
            await self.send_utt(info)
          elif si.sentence_type == 'M':
            print("Media Command")
            info['skill_id'] = 'media_skill'
            info['from_skill_id'] = self.skill_id
            info['subtype'] = 'media_query'
            await self.send_media(info)
          elif si.sentence_type == 'O':
            print("OOB Command")
            if utt in self.recognized_verbs:
              await self.send_oob_to_system(utt, contents)
            else:
              self.log.warning(
                f"Intent.run() Ignoring not recognized OOB in intent_service {utt} not found in {self.recognized_verbs}")
          else:
            print(f"Unknown sentence type {si.sentence_type} or Informational sentence")
        os.remove(txt_file)
      await asyncio.sleep(0.125)

if __name__ == '__main__':
  intent = Intent()
  intent.is_running = True
  asyncio.run(intent.run())

