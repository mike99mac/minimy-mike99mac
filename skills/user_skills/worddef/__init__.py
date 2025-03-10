from framework.message_types import MSG_SYSTEM
from PyDictionary import PyDictionary
from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import time

class WorddefSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    self.skill_id = 'help_skill'
    super().__init__(skill_id='worddef', skill_category='user')
    self.log.debug(f"WorddefSkill.__init__(): skill_base_dir: {self.skill_base_dir}")
    self.register_intent('Q', 'what', 'definition', self.handle_definition)
    self.register_intent('Q', 'what', 'synonym', self.handle_synonyms)
    self.register_intent('Q', 'what', 'antonym', self.handle_antonyms)

  def handle_message(self, msg):
    self.log.debug(f"WorddefSkill.handle_message(): msg: {msg}") 
    data = msg.data
    
  def handle_definition(self, msg):
    word = msg.data.get('word')
    if word:
      definitions = self.dictionary.meaning(word)
      if definitions:
        self.speak(f"The definition of {word} is:")
        for part_of_speech, meaning in definitions.items():
          self.speak(f"{part_of_speech}: {', '.join(meaning)}")
      else:
        self.speak(f"Sorry, I couldn't find a definition for {word}.")
    else:
      self.speak("I'm sorry, I didn't catch the word you said.")

  def handle_synonyms(self, msg):
    word = msg.data.get('word')
    if word:
      synonyms = self.dictionary.synonym(word)
      if synonyms:
        self.speak(f"The synonyms of {word} are: {', '.join(synonyms)}.")
      else:
        self.speak(f"Sorry, I couldn't find synonyms for {word}.")
    else:
      self.speak("I'm sorry, I didn't catch the word you said.")

  def handle_antonyms(self, msg):
    word = msg.data.get('word')
    if word:
      antonyms = self.dictionary.antonym(word)
      if antonyms:
        self.speak(f"The antonyms of {word} are: {', '.join(antonyms)}.")
      else:
        self.speak(f"Sorry, I couldn't find antonyms for {word}.")
    else:
      self.speak("I'm sorry, I didn't catch the word you said.")

  def stop(self):
    pass

if __name__ == '__main__':
  worddefSkill = WorddefSkill()
  Event().wait()                           # wait forever

