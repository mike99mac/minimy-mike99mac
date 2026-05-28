import re

def scrub_sentence(sentence):
  if not sentence:
    return ""
  sentence = re.sub(r'\s+', ' ', sentence.strip())
  return sentence

def remove_articles(phrase):
  if not phrase:
    return phrase
  words = phrase.split()
  if words and words[0].lower() in ('a', 'an', 'the'):
    words = words[1:]
  return ' '.join(words)
