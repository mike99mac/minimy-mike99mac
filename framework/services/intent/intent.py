import requests, time, glob, os
from bus.MsgBus import MsgBus
from framework.util.utils import LOG, Config, get_wake_words, aplay, normalize_sentence, remove_pleasantries
from framework.services.intent.nlp.shallow_parse.nlu import SentenceInfo
from framework.services.intent.nlp.shallow_parse.shallow_utils import scrub_sentence, remove_articles

class Intent:
  """
  English language specific intent parser. Monitors the save_text/ FIFO 
  for utterances to process. Emits utterance messages. If skill_id
  is not '' the utterance matched an intent in the skill_id skill.
  """
  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'intent_service'
    self.bus = MsgBus(self.skill_id)
    self.intents = {}
    self.base_dir = os.getenv('SVA_BASE_DIR') # set up logging into intent.log
    self.tmp_file_path = self.base_dir + '/tmp/'
    log_filename = self.base_dir + '/logs/intent.log'
    self.log = LOG(log_filename).log
    self.log.debug(f"Intent:__init__() base_dir = {self.base_dir}")
    self.earcon_filename = self.base_dir + "/framework/assets/earcon_start.wav"
    self.is_running = False                # set to True before calling run()
    cfg = Config()                         # get configuration
    self.crappy_aec = cfg.get_cfg_val('Advanced.CrappyAEC')
    remote_nlp = cfg.get_cfg_val('Advanced.NLP.UseRemote')
    self.use_remote_nlp = True
    if remote_nlp and remote_nlp == 'n':
      self.use_remote_nlp = False
    self.recognized_verbs = []             # keep in sync with system skill to limit OOBs to registered verbs
    self.stop_aliases = ['stop', 'terminate', 'abort', 'cancel', 'kill', 'exit']
    self.wake_words = []                   # establish wake word(s)
    wws = get_wake_words()
    for ww in wws:
      self.wake_words.append(ww.lower())
    self.log.debug(f"Intent:__init__() registering handle_register_intent and handle_system_message")
    self.bus.on('register_intent', self.handle_register_intent) # register message handlers
    self.bus.on('system', self.handle_system_message)

  def handle_system_message(self, message):
    # stay in-sync with the system skill regarding OOBs
    data = message.data
    self.log.debug(f"Intent:handle_system_message() data = {data}")
    if data['skill_id'] == 'system_skill': # we only care about system messages - reserve and release oob
      self.log.debug(f"Intent service handle system message {message.data}")
      if data['subtype'] == 'reserve_oob':
        self.recognized_verbs.append( data['verb'] )
      if data['subtype'] == 'release_oob':
        del self.recognized_verbs[ data['verb'] ]

  def is_oob(self, utt):
    """
    we don't just match hard oobs, we also look for oobs using special handling to overcome poor hardware
    return values:
     't' - normal oob detected
     'o' - aec oob detected
     'f' - no oob detected
    """ 
    ua = utt.split(" ")
    self.log.debug(f"Intent:is_oob() utt: {utt}")
    self.log.debug(f"Intent:is_oob() recognized_verbs: {self.recognized_verbs}")

    # add tests for two-word OOBs -MM
    if len(ua) == 1:           # one word utterance
      if ua[0] in self.recognized_verbs or ua[0] in self.stop_aliases or ua[0] == 'pause' or ua[0] == 'resume':
        self.log.debug("Intent:is_oob(): Intent Barge-In Normal OOB Detected")
        return 't'
    elif len(ua) == 2:         # check for two-word OOBs
      for next_key in self.intents:
        next_key = next_key.split(":") # split next key into words
        if next_key[0] == 'O' and ua[0] == next_key[2] and ua[1] == next_key[1]:
          self.log.debug("Intent:is_oob(): two-word OOB detected")
          return 't'
    # end -MM      
 
    # in a system with decent aec you can just return 'f' here
    self.log.debug(f"Intent:is_oob() crappy_aec = {self.crappy_aec}")
    if not self.crappy_aec:
      self.log.debug("Intent:is_oob(): decent AEC - returning 'f'")
      return 'f'

    """
    Deal with poor quality input (IE no AEC). You can disable this on a device with good AEC. 
    also see sva_base for other code which would use this config value
    if it were available (poor audio input quality indicator)
    """
    for ww in self.wake_words:
      for alias in self.stop_aliases:
        oob_phrase = ww + ' ' + alias
        if oob_phrase.lower() in utt.lower() or ( alias in utt.lower() and ww in utt.lower() ):
          self.log.warning("Intent:is_oob() ** Maybe ? Intent Barge-In detected - returning 'o'")
          return 'o'
    self.log.debug("Intent:is_oob(): fell through - returning 'f'")
    return 'f'

  def get_sentence_type(self, utt):
    self.log.debug(f"Intent:get_sentence_type() utt = {utt}")
    # very rough is question or not TODO - improve upon this
    vrb = utt.split(" ")[0]
    resp = "I"
    for wrd in self.question_words:
      if utt.startswith(wrd):
        resp = "Q"
        break
    self.log.info(f"Intent:get_sentence_type() resp = {resp}")    
    return resp

  def send_utt(self, utt):
    # sends an utterance to a target and handles edge cases
    target = utt.get('skill_id','*')
    if target == '':
      target = '*'
    if utt == 'stop':
      target = 'system_skill'
    self.log.debug(f"Intent:send_utt() target: {target}")  
    self.bus.send("utterance", target, {'utt': utt,'subtype':'utt'})

  def send_media(self, info):
    self.log.debug("Intent:send_media()")
    self.bus.send("media", 'media_skill', info)

  def send_oob_to_system(self, utt, contents):
    info = {
        'error':'', 
        'subtype':'oob', 
        'skill_id':'system_skill', 
        'from_skill_id':self.skill_id, 
        'sentence_type':'I', 
        'sentence':contents, 
        'verb':utt, 
        'intent_match':''
         }
    self.log.debug(f"Intent:send_oob_to_system() info = {info}")     
    self.bus.send("system", 'system_skill', info)

  def get_question_intent_match(self, info):
    self.log.debug(f"Intent:get_question_intent_match() info: {info}")
    self.log.debug(f"Intent:get_question_intent_match() intents: {self.intents}")
    aplay(self.earcon_filename)            # should be configurable
    skill_id = ''                          # see if a quation matches an intent.
    for intent in self.intents:
      stype, subject, verb = intent.split(":") 
      if stype == 'Q' and subject in info['subject'] and verb == info['qword']:
        self.log.debug(f"Intent:get_question_intent_match() matched skill_id: {skill_id}")
        info['subject'] = subject          # fuzzy match - improve upon this
        skill_id = self.intents[intent]['skill_id']
        intent_state = self.intents[intent]['state']
        return skill_id, intent
    return skill_id, ''

  def get_intent_match(self, info):
    # for utterances of type command an intent match is a subject:verb and we don't fuzzy match
    self.log.debug("Intent:get_intent_match() ")  
    aplay(self.earcon_filename)  # should be configurable
    skill_id = ''
    intent_type = 'C'
    if info['sentence_type'] == 'I':
      self.log.warning(f"Intent trying to match an informational statement which it is not designed to do! {info}")
      # info['sentence_type'] == 'C'  -MM
      info['sentence_type'] = 'C'
    subject = remove_articles(info['subject'])
    if subject:
      subject = subject.replace(":",";")
      subject = subject.strip()
    key = intent_type + ':' + subject.lower() + ':' + info['verb'].lower().strip()
    self.log.debug(f"Intent match key = {key}")
    if key in self.intents:
      skill_id = self.intents[key]['skill_id']
      intent_state = self.intents[key]['state']
      self.log.debug(f"Intent:get_intent_match(): key: {key} skill_id: {skill_id} intent_state: {intent_state}")
      return skill_id, key
    return skill_id, ''        # no match will return ('','')

  def handle_register_intent(self, msg):
    data = msg.get("payload")
    subject = data['subject'].replace(":", ";") # convert colons to semicolons
    verb = data['verb']
    key = data['intent_type'] + ':' + subject.lower() + ':' + verb
    # try adding to recognized_verbs - it is not getting set -MM
    # if verb not in self.recognized_verbs:
    #   self.recognized_verbs.append(data['verb'])
    # end -MM  
    if key in self.intents:
      self.log.warning(f"Intent:handle_register_intent() Intent clash! key={key} skill_id=%{data['skill_id']}")
    else:
      self.log.info(f"Intent:handle_register_intent() adding key {key} to intents")
      self.intents[key] = {'skill_id':data['skill_id'], 'state':'enabled'}

  def run(self):
    self.log.debug(f"Intent.run() intents: {self.intents}")
    si = SentenceInfo(self.base_dir)
    while self.is_running:                 # get all text files in the input directory
      mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_text/*.txt")] )
      if len(mylist) > 0:                  # we have at least one 
        txt_file = mylist[0]               # take first
        fh = open(txt_file)                # grab contents
        contents = fh.read()
        fh.close()
        start = contents.find("]")         # clean up input
        utt_type = contents[1:start]
        utt = contents[start+1:]
        utt = scrub_sentence(utt)
        self.log.debug(f"Intent.run() got txt_file: {txt_file} contents: {contents} utt: {utt}")
        oob_type = self.is_oob(utt)        # special case OOBs 
        self.log.debug(f"Intent.run() oob_type: {oob_type} utt_type: {utt_type} utt: {utt}")
        if oob_type == 't':
          res = self.send_oob_to_system(utt, contents) 
        elif oob_type == 'o':
          res = self.send_oob_to_system('stop', contents) 
        elif utt_type == 'RAW':            # send raw messages to system skill 
          if contents:
            self.bus.send("raw", 'system_skill', {'utterance': contents[5:]})
        else:
          sentence_type = si.get_sentence_type(utt)
          self.log.debug(f"Intent.run() sentence_type: {sentence_type} utt = {utt}")
          utt = normalize_sentence(utt)
          if sentence_type != 'Q':
            utt = remove_pleasantries(utt)
          si.parse_utterance(utt)
          info = {
              'error':'', 
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
              'subtype':'', 
              'from_skill_id':'', 
              'skill_id':'', 
              'intent_match':''
               }

          # sentence types 
          # Q - question
          # C - command
          # I - info (currently unsupported)
          # U - unknown sentence structure
          # M - media request
          # O - oob (out of band) request
          if si.sentence_type == 'Q':
            print("Match Question. key=Q:%s:%s" % (si.insight.question,si.insight.subject))
            info['skill_id'], info['intent_match'] = self.get_question_intent_match({'subject':info['subject'], 'qword':info['question']})
            print("Match Question. skid:%s, im:%s" % (info['skill_id'], info['intent_match']))
            res = self.send_utt(info) 
          elif si.sentence_type == 'C':
            print("Match Command")
            info['skill_id'], info['intent_match'] = self.get_intent_match(info)
            res = self.send_utt(info) 
          elif si.sentence_type == 'M':
            print("Media Command")
            info['skill_id'] = 'media_skill'
            info['from_skill_id'] = self.skill_id
            info['subtype'] = 'media_query'
            res = self.send_media(info) 
          elif si.sentence_type == 'O':
            print("OOB Command")
            if utt in self.recognized_verbs:
              self.send_oob_to_system(utt, contents)
            else:
              self.log.warning(f"Intent.run() Ignoring unrecognized OOB si.sentence_type {si.sentence_type} not found in {self.recognized_verbs}")
          else:
            print(f"Unknown sentence type {si.sentence_type} or Informational sentence")
        os.remove(txt_file)    # remove input file from file system
      time.sleep(0.125)

if __name__ == '__main__':
  up = Intent()
  up.is_running = True
  up.run()
