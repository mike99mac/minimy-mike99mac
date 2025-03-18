import datetime
import os
from skills.sva_base import SimpleVoiceAssistant
from threading import Event

class TimeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(skill_id='time_skill', skill_category='system')

  def register_intents(self):
    self.log.debug("TimeSkill.register_intents()")
    self.register_intent('Q', 'what', 'time', self.handle_time_match)
    self.register_intent('Q', 'what', 'date', self.handle_date_match)
    self.register_intent('Q', 'what', 'today', self.handle_date_match)
    self.register_intent('Q', 'what', 'day', self.handle_day_match)

  def handle_date_match(self, msg):
    self.log.debug("TimeSkill.handle_date_match()")
    now = datetime.datetime.now()
    text = now.strftime("%A %B %d %Y")
    self.speak(text)

  def handle_time_match(self, msg):
    now = datetime.datetime.now()
    text = now.strftime("%I %M %p")
    minute = int(text.split(" ")[1])
    hour = int(text.split(" ")[0])
    ampm = text.split(" ")[2]
    if ampm == "AM":
      ampm = "aay em"
    elif ampm == "PM":
      ampm = "pee em"
    if minute > 0 and minute < 10:         # add an "oh" before the minute
      text = f"{hour} oh {minute} {ampm}"
    elif minute == 0:                      # top of the hour
      text = f"{hour} oh clock {ampm}"
    else:                                  # hour as integer
      text = f"{hour} {minute} {ampm}"
    self.log.debug(f"TimeSkill.handle_time_match() hour: {hour} minute: {minute} ampm: {ampm} text: {text}")
    print(f"handle_time_match() text = {text}")  
    self.speak(text)

  def handle_day_match(self,msg):
    now = datetime.datetime.now()
    text = now.strftime("%A")
    self.log.debug(f"TimeSkill.handle_day_match() now: {now} text: {text}")
    self.speak(text)

  def stop(self,msg):
    self.log.info(f"TimeSkill.stop() Do nothing - stop hit")

# main()
if __name__ == '__main__':
  ts = TimeSkill()
  Event().wait()                           # wait forever 

