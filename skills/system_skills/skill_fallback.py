from framework.util.utils import aplay, Config, execute_command
from threading import Event
import json
from skills.sva_base import SimpleVoiceAssistant

class FallbackSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(msg_handler=self.handle_message, skill_id="fallback_skill", skill_category="fallback")

  def handle_message(self, msg):
    self.log.info(f"FallbackSkill.handle_message() NOT EXPECTING THIS IS EVER CALLED!!!")

  def handle_fallback(self, msg):
    # get an answer from the Ollama server
    self.log.debug(f"FallbackSkill:handle_fallback(): msg: \n{json.dumps(msg,indent=2)}")
    ques = msg["payload"]["utt"]["sentence"] # get the question
    cmd = f"/usr/local/sbin/qa.py {ques}"
    self.log.debug(f"FallbackSkill:handle_fallback(): calling cmd: {cmd}")
    ans = execute_command(cmd)             # get answer from command
    self.log.debug(f"FallbackSkill:handle_fallback(): ans: {ans}")
    self.speak(ans)                        # speak the answer

# main()
if __name__ == "__main__":
  fs = FallbackSkill()
  Event().wait()                           # wait forever

