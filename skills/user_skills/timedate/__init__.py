from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import os
import datetime

class TimeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(skill_id='time_skill', skill_category='system')
    self.register_intent('Q', 'what', 'time', self.handle_time_match)
    self.register_intent('Q', 'what', 'date', self.handle_date_match)
    self.register_intent('Q', 'what', 'today', self.handle_date_match)
    self.register_intent('Q', 'what', 'day', self.handle_day_match)

  def handle_date_match(self,msg):
    now = datetime.datetime.now()
    text = now.strftime("%A %B %d %Y")
    self.speak(text)

  def handle_time_match(self,msg):
    now = datetime.datetime.now()
    text = now.strftime("%I %M %p")
    minute = int(text.split(" ")[1])
    hour = int(text.split(" ")[0])
    ampm = text.split(" ")[2]
    print(f"handle_time_match() hour = {hour} minute = {minute} ampm = {ampm}")
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
    print(f"handle_time_match() text = {text}")  
    self.speak(text)

  def handle_day_match(self,msg):
    now = datetime.datetime.now()
    text = now.strftime("%A")
    self.speak(text)

  def stop(self,msg):
    print("\n*** Do nothing timedate skill stop hit ***\n")

# main()
if __name__ == '__main__':
  ts = TimeSkill()
  Event().wait()                           # wait forever

