import re

class Insight:
  def __init__(self):
    self.proper_nouns = []
    self.tense = 'present'
    self.plural = False
    self.verb = ''
    self.aux_verb = ''
    self.qtype = ''
    self.subject = ''
    self.squal = ''
    self.value = ''
    self.dependent = ''
    self.question = ''
    self.np = ''
    self.vp = ''
    self.concept = ''

class Structure:
  def __init__(self, sentence):
    self.original_tree = ''
    self.tree = ''
    self.nodes = []
    self.shallow = ''

class SentenceInfo:
  def __init__(self, base_dir):
    self.base_dir = base_dir
    self.original_sentence = ''
    self.normalized_sentence = ''
    self.sentence_type = 'U'
    self.insight = Insight()
    self.structure = Structure('')
    self.media_verbs = ['play', 'watch', 'listen']
    qw_file = f"{base_dir}/framework/question_words.txt" if base_dir else "question_words.txt"
    self.question_words = []
    try:
      with open(qw_file) as f:
        for line in f:
          w = line.strip()
          if w:
            self.question_words.append(w.lower())
    except FileNotFoundError:
      self.question_words = ['what', 'where', 'when', 'who', 'why', 'how', 'which', 'is', 'are', 'do', 'does', 'did', 'can', 'could', 'would', 'will', 'should']

  def get_sentence_type(self, sentence):
    first = sentence.strip().lower().split()[0] if sentence.strip() else ''
    if first in self.question_words or sentence.strip().endswith('?'):
      return 'Q'
    if first in self.media_verbs:
      return 'M'
    cmd_verbs = ['play', 'pause', 'resume', 'stop', 'next', 'previous', 'set', 'change', 'increase', 'decrease', 'mute', 'unmute', 'turn', 'create', 'delete', 'list', 'show', 'help', 'cancel', 'snooze']
    if first in cmd_verbs:
      return 'C'
    return 'U'

  def parse_utterance(self, sentence):
    self.original_sentence = sentence
    self.normalized_sentence = sentence.lower().strip()
    self.sentence_type = self.get_sentence_type(sentence)
    self.insight = Insight()
    self.insight.proper_nouns = []
    self._extract_with_regex()
    self.structure.original_tree = ''
    self.structure.tree = ''
    self.structure.nodes = []
    self.structure.shallow = ''

  def _extract_with_regex(self):
    s = self.normalized_sentence
    patterns = [
      (r'^what (?:is the )?capital of (.+)$', 'capital', 'what', 'is', 1),
      (r'^what (?:is the )?time$', 'time', 'what', 'is', None),
      (r'^what (?:is the )?date$', 'date', 'what', 'is', None),
      (r'^what (?:is the )?day$', 'day', 'what', 'is', None),
      (r'^what (?:is the )?weather(?:\s+in\s+(.+))?$', 'weather', 'what', 'is', 1),
      (r'^what (?:is the )?forecast(?:\s+for\s+(.+))?$', 'forecast', 'what', 'is', 1),
      (r'^what (?:is the )?temperature(?:\s+in\s+(.+))?$', 'temperature', 'what', 'is', 1),
      (r'^play (?:(?:music by|song|artist|track|album|radio|station)\s+)?(.+)$', 'play_music', 'play', 'play', 1),
      (r'^pause(?: the music)?$', 'pause', 'pause', 'pause', None),
      (r'^resume(?: the music)?$', 'resume', 'resume', 'resume', None),
      (r'^stop(?: the music)?$', 'stop', 'stop', 'stop', None),
      (r'^next(?: (?:song|track|title))?$', 'next', 'next', 'next', None),
      (r'^previous(?: (?:song|track|title))?$', 'previous', 'previous', 'previous', None),
      (r'^(?:turn up|increase|raise) (?:the )?volume$', 'volume_up', 'increase', 'increase', None),
      (r'^(?:turn down|decrease|lower) (?:the )?volume$', 'volume_down', 'decrease', 'decrease', None),
      (r'^set (?:the )?volume to (\d+)$', 'volume_set', 'set', 'set', 1),
      (r'^mute (?:the )?volume$', 'volume_mute', 'mute', 'mute', None),
      (r'^unmute (?:the )?volume$', 'volume_unmute', 'unmute', 'unmute', None),
      (r'^set (?:an? )?alarm for (.+)$', 'alarm_set', 'set', 'set', 1),
      (r'^(?:delete|remove|cancel) (?:the? )?alarm (?:for )?(.+)$', 'alarm_delete', 'delete', 'delete', 1),
      (r'^(?:list|show) alarms?$', 'alarm_list', 'list', 'list', None),
      (r'^help$', 'help', 'help', 'help', None),
    ]

    for pat, qtype, verb, aux_verb, group_idx in patterns:
      m = re.match(pat, s)
      if m:
        self.insight.qtype = qtype
        self.insight.verb = verb
        self.insight.aux_verb = aux_verb
        self.insight.question = verb if qtype != 'capital' else 'what'
        if group_idx is not None:
          try:
            val = m.group(group_idx)
            self.insight.value = val.strip() if val else ''
          except (IndexError, AttributeError):
            self.insight.value = ''
        # Set subject
        if qtype in ('capital', 'time', 'date', 'day', 'weather', 'forecast', 'temperature'):
          self.insight.subject = qtype
        elif qtype in ('play_music', 'pause', 'resume', 'stop', 'next', 'previous'):
          self.insight.subject = 'music'
        elif qtype.startswith('volume'):
          self.insight.subject = 'volume'
        elif qtype.startswith('alarm'):
          self.insight.subject = 'alarm'
        elif qtype == 'help':
          self.insight.subject = 'help'
        else:
          self.insight.subject = ''
        return

    # Fallback
    words = s.split()
    if words:
      self.insight.verb = words[0]
      self.insight.subject = ' '.join(words[1:3]) if len(words) > 1 else ''
      self.insight.qtype = 'unknown'
