from skills.sva_base import SimpleVoiceAssistant
from threading import Event
import lingua_franca
from lingua_franca import parse
import subprocess
import re

class VolumeSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    self.skill_id = "volume_skill"
    super().__init__(msg_handler=self.handle_message, skill_id=self.skill_id, skill_category="system")
    lingua_franca.load_language("en")

    # No config reads – everything uses PipeWire/PulseAudio defaults
    self.volume_level = self._get_volume()
    self.muted_volume = self.volume_level
    self.mic_level = self._get_mic_level()

    # Register intents
    inactive_state_intents = []
    subjects = ["microphone", "mic", "input"]
    commands = ["set", "change", "modify"]
    questions = ["what", "how"]
    for subject in subjects:
      for command in commands:
        self.register_intent("C", command, subject, self.handle_change_mic)
        inactive_state_intents.append(f"C:{subject}:{command}")
    for subject in subjects:
      for question in questions:
        self.register_intent("Q", question, subject, self.handle_query_mic)
        inactive_state_intents.append(f"Q:{subject}:{question}")
    subject = "volume"
    for cmd in ["turn", "set", "change"]:
      self.register_intent("C", cmd, subject, self.handle_change)
      inactive_state_intents.append(f"C:{subject}:{cmd}")
    for cmd in ["increase", "decrease"]:
      self.register_intent("C", cmd, subject, getattr(self, f"handle_{cmd}"))
      inactive_state_intents.append(f"C:{subject}:{cmd}")
    for cmd in ["mute", "unmute"]:
      self.register_intent("C", cmd, subject, getattr(self, f"handle_{cmd}"))
      inactive_state_intents.append(f"C:{subject}:{cmd}")
    for question in questions:
      self.register_intent("Q", question, subject, self.handle_intent_match)
      inactive_state_intents.append(f"Q:{subject}:{question}")

  def _get_volume(self):
    """Return current default sink volume as integer percentage."""
    result = subprocess.run(
      ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
      capture_output=True, text=True
    )
    # Output example: "Volume: front-left: 32768 /  50% / ..."
    match = re.search(r"(\d+)%", result.stdout)
    if match:
      return int(match.group(1))
    return 70  # fallback

  def set_volume(self, new_volume):
    new_volume = max(0, min(100, new_volume))
    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{new_volume}%"])
    self.volume_level = new_volume
    return self.volume_level

  def get_volume(self):
    return self._get_volume()

  def _get_mic_level(self):
    """Return current default source volume as integer percentage."""
    result = subprocess.run(
      ["pactl", "get-source-volume", "@DEFAULT_SOURCE@"],
      capture_output=True, text=True
    )
    match = re.search(r"(\d+)%", result.stdout)
    if match:
      return int(match.group(1))
    return 67  # fallback

  def set_mic_level(self, new_level):
    new_level = max(0, min(100, new_level))
    subprocess.run(["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{new_level}%"])
    self.mic_level = new_level
    return self.mic_level

  def get_mic_level(self):
    return self._get_mic_level()

  def get_num(self, v1, v2, v3):
    num = parse.extract_number(v1)
    if not num:
      num = parse.extract_number(v2)
      if not num:
        num = parse.extract_number(v3)
    return num

  def handle_change_mic(self, msg):
    val = msg["payload"]["utt"]["value"]
    subject = msg["payload"]["utt"]["subject"]
    squal = msg["payload"]["utt"]["squal"]
    num = self.get_num(val, subject, squal)
    text = "No value given, level not changed"
    if num:
      text = f"mic level changed to {num} percent"
      self.set_mic_level(num)
    self.speak(text)

  def handle_query_mic(self, message):
    text = f"the microphone is currently set to {self.get_mic_level()} percent"
    self.speak(text)

  def handle_message(self, msg):
    self.log.debug(f"VolumeSkill.handle_message() msg: {msg}")
    if msg["payload"]["subtype"] == "mute_volume":
      self.handle_mute(None)
    if msg["payload"]["subtype"] == "unmute_volume":
      self.handle_unmute(None)

  def handle_intent_match(self, msg):
    text = f"the volume is currently set to {self.get_volume()} percent"
    self.speak(text)

  def handle_change(self, msg):
    val = msg["payload"]["utt"]["value"]
    subject = msg["payload"]["utt"]["subject"]
    squal = msg["payload"]["utt"]["squal"]
    num = self.get_num(val, subject, squal)
    text = "No value given, volume not changed"
    if num:
      text = f"volume changed to {num} percent"
      self.set_volume(num)
    self.speak(text)

  def handle_increase(self, msg):
    new_volume = min(100, self.get_volume() + 10)
    self.set_volume(new_volume)
    self.speak(f"volume increased to {new_volume} percent")

  def handle_decrease(self, msg):
    new_volume = max(0, self.get_volume() - 10)
    self.set_volume(new_volume)
    self.speak(f"volume decreased to {new_volume} percent")

  def handle_mute(self, msg):
    self.log.debug("Inside handle mute!")
    self.muted_volume = self.get_volume()
    self.set_volume(0)

  def handle_unmute(self, msg):
    self.log.debug("Inside handle unmute!")
    self.set_volume(self.muted_volume)

  def stop(self, msg=None):
    self.log.debug(f"Volume skill stop() method called WITH message {msg}")

if __name__ == "__main__":
  vs = VolumeSkill()
  Event().wait()
