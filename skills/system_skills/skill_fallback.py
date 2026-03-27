from framework.util.utils import aplay, Config, execute_command
from threading import Event
import json
from skills.sva_base import SimpleVoiceAssistant
import re

try:
  from huggingface_hub import hf_hub_download
  from llama_cpp import Llama
except ImportError:
  hf_hub_download = None
  Llama = None

class FallbackSkill(SimpleVoiceAssistant):
  def __init__(self, bus=None, timeout=5):
    super().__init__(msg_handler=self.handle_message, skill_id="fallback_skill", skill_category="fallback")
    self.cfg = Config()
    self.llm = None
    if Llama is not None and hf_hub_download is not None:
      self.llm_repo = self.cfg.get_cfg_val('Basic.LLMRepo')
      self.llm_file = self.cfg.get_cfg_val('Basic.LLMFile')
      
      if not self.llm_repo or not self.llm_file:
          self.log.error("FallbackSkill: LLM configuration missing (Basic.LLMRepo or Basic.LLMFile) in mmconfig.yml. Cannot load model.")
      else:
          self.log.info(f"FallbackSkill: Downloading/Loading LLM model from {self.llm_repo} ({self.llm_file})")
          try:
            model_path = hf_hub_download(repo_id=self.llm_repo, filename=self.llm_file)
            self.llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
          except Exception as e:
            self.log.error(f"FallbackSkill: Failed to load Llama model: {e}")
    else:
      self.log.error("FallbackSkill: llama_cpp or huggingface_hub not installed")

  def handle_message(self, msg):
    self.log.info(f"FallbackSkill.handle_message() NOT EXPECTING THIS IS EVER CALLED!!!")

  def handle_fallback(self, msg):
    # get an answer from the local LLM
    self.log.debug(f"FallbackSkill:handle_fallback(): msg: \n{json.dumps(msg,indent=2)}")
    ques = msg["payload"]["utt"]["sentence"] # get the question
    
    ans = "I am sorry, my local language model is not available right now due to a configuration error."
    if self.llm:
      try:
        messages = [
          {"role": "system", "content": "You are a helpful and concise voice assistant for a smart boombox. Answer questions clearly and directly. Do not format with Markdown. Only speak in complete sentences that piper can transcribe."},
          {"role": "user", "content": ques}
        ]
        
        # We attempt to safely pass the kwarg to disable thinking internally as per llama.cpp defaults if supported by python bindings
        try:
          output = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=150,
            chat_template_kwargs={"enable_thinking": False}
          )
        except TypeError:
          output = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=150,
          )

        ans = output['choices'][0]['message']['content'].strip()
        print(ans)        
      except Exception as e:
        self.log.error(f"FallbackSkill: Error querying local LLM: {e}")
        ans = "I encountered an error trying to process your request."

    self.log.debug(f"FallbackSkill:handle_fallback(): ans: {ans}")
    self.speak(ans)                        # speak the answer

# main()
if __name__ == "__main__":
  fs = FallbackSkill()
  Event().wait()                           # wait forever

