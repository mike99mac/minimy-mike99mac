import datetime
from skills.sva_base import SimpleVoiceAssistant
from threading import Event

_ORDINALS = {
  1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
  6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
  11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
  15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
  19: "nineteenth", 20: "twentieth", 21: "twenty first",
  22: "twenty second", 23: "twenty third", 24: "twenty fourth",
  25: "twenty fifth", 26: "twenty sixth", 27: "twenty seventh",
  28: "twenty eighth", 29: "twenty ninth", 30: "thirtieth",
  31: "thirty first",
}
_ONES = ["", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen",
         "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty",
         "seventy", "eighty", "ninety"]

def _two_digit_word(n):
  if n < 20:
    return _ONES[n]
  if n % 10 == 0:
    return _TENS[n // 10]
  return _TENS[n // 10] + " " + _ONES[n % 10]

def _year_to_words(year):
  if 2000 <= year <= 2009:
    return "two thousand" if year == 2000 else "two thousand " + _ONES[year - 2000]
  century, rest = divmod(year, 100)
  if rest == 0:
    return _two_digit_word(century) + " hundred"
  if rest < 10:
    return _two_digit_word(century) + " oh " + _ONES[rest]
  return _two_digit_word(century) + " " + _two_digit_word(rest)

class TimeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(skill_id='time_skill', skill_category='system')
    self.log.debug("TimeSkill.__init__(): Registering intents")
    self.register_intent('Q', 'what', 'time', self.handle_time_match)
    self.register_intent('Q', 'what', 'date', self.handle_date_match)
    self.register_intent('Q', 'what', 'today', self.handle_date_match)
    self.register_intent('Q', 'what', 'day', self.handle_day_match)

  def handle_date_match(self, msg):
    self.log.debug("TimeSkill.handle_date_match()")
    now = datetime.datetime.now()
    day_word = _ORDINALS.get(now.day, str(now.day))
    year_word = _year_to_words(now.year)
    text = f"{now.strftime('%A')} {now.strftime('%B')} {day_word} {year_word}"
    self.log.debug(f"TimeSkill.handle_date_match() text: {text}")
    self.speak(text)

  def handle_time_match(self, msg):
    self.log.debug(f"TimeSkill.handle_time_match() msg: {msg}")
    now = datetime.datetime.now()
    text = now.strftime("%I %M %p")
    minute = int(text.split(" ")[1])
    hour = int(text.split(" ")[0])
    ampm = text.split(" ")[2]
    if ampm == "AM":
      ampm = "a-em"
    elif ampm == "PM":
      ampm = "pee em"
    if minute > 0 and minute < 10:
      text = f"{hour} oh {minute} {ampm}"
    elif minute == 0:
      text = f"{hour} oh clock {ampm}"
    else:
      text = f"{hour} {minute} {ampm}"
    self.log.debug(f"TimeSkill.handle_time_match() hour: {hour} minute: {minute} ampm: {ampm} text: {text}")
    self.speak(text)

  def handle_day_match(self, msg):
    now = datetime.datetime.now()
    text = now.strftime("%A")
    self.log.debug(f"TimeSkill.handle_day_match() now: {now} text: {text}")
    self.speak(text)

  def stop(self, msg):
    self.log.info(f"TimeSkill.stop() Do nothing - stop hit")

if __name__ == '__main__':
  ts = TimeSkill()
  Event().wait()
