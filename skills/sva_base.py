from bus.MsgBus import MsgBus
from framework.util.utils import LOG, Config, execute_command
import os 
from skills.sva_control import SkillControl
import subprocess
from threading import Event, Thread
import time 

class SimpleVoiceAssistant:
  def __init__(self, msg_handler=None, skill_id=None, skill_category=None, bus=None, timeout=5):
    # Most user skills at some point in their lifecycles will want to speak() and/or play_media(). These
    # require acquisition of a session and associated error logic which is shared among all skills by
    # placing it here. 

    # Skills wishing to play media call their play_media() method which handles initiating a session with the
    # media service and playing the media. Establishing a session with the media player also causes a skill to
    # go active and remain active until either the media session is terminated or it ends normally. 

    # A great deal of trouble went into supporting the ability to interrupt oneself. For example, while 
    # speaking an answer a user may wish to ask wiki yet another question. The intended behavior in this case
    # is to stack the TTS output so when the new qustion has been answered the old question will automatically
    # be resumed. While this behavior may not be desirable to the developer it may be easily overridden in the 
    # system skill (see the methods input_focus_determination() and output_focus_determination() in the system skill 
    # for more detailed information) making it far easier for the developer to disable than to implement.

    # It is the same process with the tts service. A skill enters the active state upon initiating a session with
    # the tts service. In this case the tts service itself establishes a session with the media service. The skill
    # calling the speak() method will enter the 'active' state upon successful negotiation of the session with the tts
    # service. It will remain in the active state until both the session with the tts service and the underlying 
    # session with the medai service have been terminated. This all happens automatically in this base class. 

    # The base class maintains the last session response and current session id for both the tts service and the media 
    # service.

    self.skill_control = SkillControl()
    self.skill_control.skill_id = skill_id
    self.skill_control.category = skill_category
    if bus is None:
      bus = MsgBus(self.skill_control.skill_id)
    self.bus = bus
    self.base_dir = str(os.getenv("SVA_BASE_DIR"))
    log_filename = self.base_dir + "/logs/skills.log"
    self.log = LOG(log_filename).log
    self.skill_base_dir = os.getcwd()
    self.handle_message = msg_handler
    self.log.debug(f"SimpleVoiceAssistant.__init__() skill_id = {skill_id} skill_category = {skill_category}")
    self.focus_mode = "speech"
    self.user_callback = None
    self.speak_callback = None
    self.bridge = Event()
    self.watchdog_thread = None
    self.i_am_active = False
    self.i_am_paused = False       # this skill has been paused by the user
    # self.i_am_paused = True        # override for now
    self.i_am_conversed = False
    self.done_speaking = True
    self.ignore_raw_ctr = 0
    cfg = Config()
    self.crappy_aec = cfg.get_cfg_val("Advanced.CrappyAEC")
    self.model_file = cfg.get_cfg_val('Advanced.TTS.LocalVoice')
    self._converse_callback = None
    self.activate_response = ""
    self.tts_session_response = ""
    self.tts_service_session_id = 0
    self.tts_service_session_ids = []
    self.media_session_response = ""
    self.media_player_session_id = 0
    self.stt_is_active = False
    self.waiting_for_input_focus = False
    self.intents = {}
    self.bus.on("utterance", self.handle_utterance)
    self.bus.on("skill", self.handle_skill_msg)
    self.bus.on("system", self.handle_system_msg)
    self.bus.on("raw", self.handle_raw_msg)

    # need a special handler for media but not Q&A because media handles system level single verb utterances but Q&A does not.
    self.bus.on("media", self.handle_media_msg)
    self.lang = "en-us"

  def mpc_cmd(self, arg1, arg2=None):
    # Run any mpc command that takes one or two arguments
    # Param: arg 1 - such as "clear" or "play"
    #    arg 2 - args to commands such as "add" or "load" 
    # Return: mpc return code
    cmd = "/usr/bin/mpc "+arg1
    if arg2 != None:   
      cmd = cmd+" "+arg2
    try:
      self.log.debug(f"SimpleVoiceAssistant.mpc_cmd(): running command: {cmd}")
      result = subprocess.check_output(cmd, shell=True) 
      return 0             # success
    except subprocess.CalledProcessError as e:  
      self.log.error(f"SimpleVoiceAssistant.mpc_cmd(): cmd: {cmd} returned e.returncode: {e.returncode}")
      return e.returncode

  def start_watchdog(self, timeout, callback):
  # watchdog timer
    timeout = int(timeout) * 1000
    while timeout > 0:
      time.sleep(0.001)
      timeout -= 1
      if self.bridge.is_set():
        self.log.debug("SimpleVoiceAssistant.start_watchdog() bridge is set - watchdog cancelled")
        self.bridge.clear()
        break
    self.log.debug(f"SimpleVoiceAssistant.start_watchdog() timeout {timeout}")
    if timeout == 0:
      self.log.debug("SimpleVoiceAssistant.start_watchdog() watchdog timed out")
      callback()
    self.log.debug("SimpleVoiceAssistant.start_watchdog() watchdog ended")

  def watchdog_timeout(self):
    self.log.debug("SimpleVoiceAssistant.watchdog_timeout() starting")
    self.i_am_conversed = False
    info = {"subtype":"release_input_focus",
            "skill_category":self.skill_control.category,
            "skill_id":"system_skill",
            "from_skill_id":self.skill_control.skill_id
           }
    self.bus.send("system", "system_skill", info)
    if self.user_timeout_callback:
      self.user_timeout_callback()

  def cancel_watchdog(self):
    self.log.debug("SimpleVoiceAssistant.cancel_watchdog() stop watchdog thread")
    self.bridge.set()

  # special case confirm (yes/no) converse type path
  def confirm_converse_callback(self, response):
    self.log.debug("SimpleVoiceAssistant.confirm_converse_callback() confirm converse type path")
    self.cancel_watchdog()
    if response.lower() in ["yes", "yea", "yeah", "yup", "sure", "ok", "o.k.", "correct", "right"]:
      return self.user_callback("yes")
    if response.lower() in ["no", "nope", "nah", "not"]:
      return self.user_callback("no")
    return self.user_callback("")

  def confirm_callback(self):
    self.log.debug("SimpleVoiceAssistant.confirm_callback() confirm converse type path")
    time.sleep(0.01)
    self.watchdog_thread = Thread(target=self.start_watchdog, args=(10,self.watchdog_timeout)).start()
    self.converse(self.confirm_converse_callback)

  def get_user_confirmation(self, callback, prompt=None, timeout_callback=None):
    self.log.debug("SimpleVoiceAssistant.get_user_confirmation() starting")

    # just a special case of get_user_input() but could be extended later to handle different approaches 
    self.user_callback = callback
    self.user_timeout_callback = timeout_callback
    if prompt:
      self.speak(prompt, wait_callback=self.confirm_callback)
    else:
      self.confirm_callback()

  # standard converse type path
  def converse_callback(self, data):
    self.log.debug("SimpleVoiceAssistant.converse_callback() starting")
    self.cancel_watchdog()
    self.user_callback(data)

  def prompt_callback(self):
    self.log.debug("SimpleVoiceAssistant.prompt_callback() starting")
    self.converse(self.converse_callback)

  def get_user_input(self, callback, prompt=None, timeout_callback=None):
    self.log.debug("SimpleVoiceAssistant.get_user_input() starting")
    self.user_callback = callback
    self.user_timeout_callback = timeout_callback
    self.watchdog_thread = Thread(target=self.start_watchdog, args=(10,self.watchdog_timeout)).start()
    if prompt:
      self.speak(prompt, wait_callback=self.prompt_callback)
    else:
      self.prompt_callback()

  def handle_raw_msg(self, msg):
    self.log.debug(f"SimpleVoiceAssistant.handle_raw_msg() skill_control.skill_id: {self.skill_control.skill_id} msg: {msg}")
    if self.skill_control.skill_id == "system_skill": # special handling for the system skill 
      self.handle_message(msg)
      return True
    if self.i_am_conversed:                # raw messages are ignored unless in converse mode
      if self.crappy_aec == "y":
        # ignore first stt on bad systems because it is probably what you just said
        self.log.info(f"SimpleVoiceAssistant.handle_raw_msg() skill_id: {self.skill_control.skill_id}")
        if self.ignore_raw_ctr == 0:
          self.ignore_raw_ctr += 1
          return False
        self.ignore_raw_ctr = 0
      self.i_am_conversed = False
      info = {"subtype": "release_input_focus",
              "skill_category": self.skill_control.category,
              "skill_id": "system_skill",
              "from_skill_id": self.skill_control.skill_id
             }
      self.bus.send("system", "system_skill", info)
      self._converse_callback(msg["payload"]["utterance"])

  def send_message(self, target, msg):
    self.log.debug(f"SimpleVoiceAssistant.send_message() target: {target} msg: {msg}")
    from_skill_id = self.skill_control.skill_id
    msg["from_skill_id"] = from_skill_id
    self.bus.send("skill", target, msg)

  def play_media(self, file_uri, delete_on_complete="false", media_type=None):
    self.log.debug(f"SimpleVoiceAssistant.play_media() file_uri: {file_uri} delete_on_complete: {delete_on_complete}")
    from_skill_id = self.skill_control.skill_id # try to acquire a media player session and play a media file
    from_skill_category = self.skill_control.category
    if self.i_am_paused:
      if self.media_player_session_id: # paused with active msid and play request need to reset paused session and reset pause
        info = {"subtype": "media_player_command",
                "command": "cancel_session",
                "session_id": self.media_player_session_id,
                "skill_id": "media_player_service",
                "from_skill_id": from_skill_id
               }
        self.bus.send("media", "media_player_service", info)
        self.i_am_paused = False
        self.media_player_session_id = 0
        time.sleep(0.1)
    if self.media_player_session_id != 0: # already active msid and play request - need to reset active session and reset pause
      self.log.warning(f"SimpleVoiceAssistant.play_media() {self.skill_control.skill_id} ** {from_skill_id} already has an active media session id - reusing {self.media_player_session_id}")
      info = {"subtype": "media_player_command",
              "command": "reset_session",
              "file_uri": file_uri,
              "session_id": self.media_player_session_id,
              "skill_id": "media_player_service",
              "from_skill_id": from_skill_id,
              "media_type": media_type,
              "delete_on_complete":delete_on_complete
             }
      self.bus.send("media", "media_player_service", info)
      return True
    # else we need to acquire a media session BUG - these probably need to be stacked !!!
    self.log.warning(f"SimpleVoiceAssistant.play_media(): setting file_uri to {file_uri} media_type to {media_type}")
    self.file_uri = file_uri
    self.media_type = media_type
    self.delete_on_complete = delete_on_complete
    self.focus_mode = "media"
    info = {"subtype": "request_output_focus",
            "skill_id": "system_skill",
            "from_skill_id": from_skill_id,
            "skill_category": from_skill_category
           }
    self.bus.send("system", "system_skill", info)
    return True

  def speak(self, text, wait_callback=None):
    # Short-circuited to directly call piper then return -MM
    text = text.replace('\n', ' ')           # remove trailing newline
    text_file = f"{self.base_dir}/tmp/save_text/speech.wav"
    piper_dir = f"{self.base_dir}/framework/services/tts/local/piper"
    cmd = f'echo "{text}" | {piper_dir}/piper --model {piper_dir}/{self.model_file}.onnx --output_file {text_file}; aplay {text_file}'
    self.log.debug(f"SimpleVoiceAssistant.speak() piper cmd: {cmd}")
    try:                                   # writing file to ~/minimy/tmp/save_text
      self.log.debug(f"SimpleVoiceAssistant.speak(): running command: {cmd}")
      result = subprocess.check_output(["bash", "-c", cmd])
    except subprocess.CalledProcessError as e:
      self.log.error(f"SimpleVoiceAssistant.mpc_cmd(): cmd: {cmd} returned e.returncode: {e.returncode}")
      return e.returncode
    os.system(f"rm {text_file}")
    return                                 # nothing below is being called -MM

    self.log.debug(f"SimpleVoiceAssistant.speak() text: {text} wait_callback: {wait_callback} i_am_paused: {self.i_am_paused}")
    if self.i_am_paused:                   # send text to tts service
      self.log.debug(f"SimpleVoiceAssistant.speak(): tts_service_session_id: {self.tts_service_session_id}") 
      if self.tts_service_session_id != 0:
        info = {"subtype": "tts_service_command",
                "command": "reset_session",
                "session_id": self.tts_service_session_id,
                "skill_id": "tts_service",
                "from_skill_id": self.skill_control.skill_id
               }
        self.send_message("tts_service", info)
        self.log.debug(f"SimpleVoiceAssistant.speak() sending reset_session message to tts_service")
        time.sleep(0.1)
        info = {"subtype": "tts_service_command",
                "command": "resume_session",
                "session_id": self.tts_service_session_id,
                "skill_id":"tts_service",
                "from_skill_id": self.skill_control.skill_id
               }
        self.send_message("tts_service", info)
        self.log.debug(f"SimpleVoiceAssistant.speak() sending resume_session message to tts_service")
        time.sleep(0.1)
        info = {"text": text, 
                "skill_id": self.skill_control.skill_id
               }
        self.log.debug(f"SimpleVoiceAssistant.speak() calling bus.send with info: {info}")
        self.bus.send("speak", "tts_service", info)
        self.i_am_paused = False
        return True
    self.focus_mode = "speech"
    self.text = text
    info = {"subtype": "request_output_focus",
            "skill_id": "system_skill",
            "from_skill_id": self.skill_control.skill_id,
            "skill_category": self.skill_control.category
           }
    self.speak_callback = wait_callback
    self.log.debug(f"SimpleVoiceAssistant.speak() sending message to speak with info: {info}")
    self.bus.send("system", "system_skill", info)
    return True

  def speak_lang(self, base_dir: str, mesg_file: str, mesg_info: dict, wait_callback=None):
    # Speak text from a file so as to support other languages 
    # replace variables in the message file with their corresponding values in mesg_info dictionary
    # parm 1: skill's base directory
    # parm 2: message file name (without .dialog suffix)
    # parm 3: values to be plugged in
    # parm 4: callback function called after speaking
    self.log.debug(f"SimpleVoiceAssistant.speak_lang() mesg_file = {mesg_file} mesg_info = {mesg_info}")
    fqdn_name = f"{base_dir}/dialog/{self.lang}/{mesg_file}.dialog"
    if os.path.exists(fqdn_name) == False:
      self.log.error(f"SimpleVoiceAssistant.speak_lang(): file {fqdn_name} not found") 
      return False
    fh = open(fqdn_name, "r")
    text = fh.read() 
    fh.close()
    if mesg_info != None:
      for key in mesg_info:                # replace variables in the message with their corresponding values
        variable = "{"+key+"}"             # variables are surrounded by {braces}
        text = text.replace(variable, str(mesg_info[key]))
    self.log.debug(f"SimpleVoiceAssistant.speak_lang() speaking message: {text}")
    self.speak(text, wait_callback)        # speak the message then call the callback

  def register_intent(self, intent_type, verb, subject, callback):
    # bind a sentence type, subject and verb to a callback and send on message bus to intent service.
    self.log.debug(f"SimpleVoiceAssistant.register_intent() intent_type: {intent_type} verb: {verb} subject: {subject}")
    subjects = subject
    verbs = verb
    if type(subject) is not list:
      subjects = [subject]
    if type(verb) is not list:
      verbs = [verb]
    for subject in subjects:
      for verb in verbs:
        key = intent_type + ":" + subject + ":" + verb
        if key in self.intents:
          self.log.warning(f"impleVoiceAssistant.register_intent() **{self.skill_control.skill_id}** error - duplicate key {self.skill_control.skill_id, key}")
        else:
          self.intents[key] = callback 
          info = {"intent_type": intent_type,
                  "subject": subject,
                  "verb": verb,
                  "skill_id": self.skill_control.skill_id
                 }
          self.bus.send("register_intent", "intent_service", info)

  def handle_utterance(self, msg):
    # invokes callback based on verb:subject
    self.log.debug(f"SimpleVoiceAssistant.handle_utterance() msg: {msg}")
    skill_id = msg["target"]
    utt = msg["payload"]["utt"]
    if self.skill_control.category == "fallback":
      if skill_id == "":                   # special handling for fallback/Q&A skills
        if self.handle_fallback:
          self.log.info(f"SimpleVoiceAssistant.handle_utterance() skill_id: {self.skill_control.skill_id} calling handle_fallback()")
          self.handle_fallback(msg)
        else:
          self.log.error(f"SimpleVoiceAssistant.handle_utterance() skill_id: {self.skill_control.skill_id} has no handle_fallback()")
    else:                                  # not a fallback skill
      self.log.debug(f"SimpleVoiceAssistant.handle_utterance() skill_id: {skill_id}")
      if skill_id == self.skill_control.skill_id:
        subject = ""
        verb = ""
        intent_type = "C"
        if msg["payload"]["utt"]["sentence_type"] == "Q":
          intent_type = "Q"
          subject = msg["payload"]["utt"]["np"]
          verb = msg["payload"]["utt"]["qword"]
        else:
          subject = msg["payload"]["utt"]["subject"]
          verb = msg["payload"]["utt"]["verb"]
        subject = subject.replace(" the","")
        subject = subject.replace("the ","")
        key = msg["payload"]["utt"]["intent_match"]
        if key in self.intents:
          self.log.debug(f"SimpleVoiceAssistant.handle_utterance() skill base class intent match: {key}")
          (self.intents[key](msg))

  def converse(self, callback):
    # a skill in the conversant state will get a single raw utterance and then exit the 
    # conversant state. the raw utterance is returned to the caller
    self.log.debug("SimpleVoiceAssistant.converse() starting")
    self.waiting_for_input_focus = True
    self._converse_callback = callback
    # inform the system skill of our intentions
    info = {"subtype": "request_input_focus",
            "skill_id": "system_skill",
            "skill_category": self.skill_control.category,
            "from_skill_id": self.skill_control.skill_id,
           }
    self.bus.send("system", "system_skill", info)
    return True

  def send_release_output_focus(self):
    self.log.debug("SimpleVoiceAssistant.send_release_output_focus() starting")
    self.media_player_session_id = 0
    self.i_am_active = False
    info = {"subtype": "release_output_focus",
            "skill_id": "system_skill",
            "from_skill_id": self.skill_control.skill_id
           }
    self.bus.send("system", "system_skill", info)

  # message bus handlers 
  def handle_skill_msg(self, msg):
    self.log.debug(f"SimpleVoiceAssistant.handle_skill_msg() self.skill_control.skill_id: {self.skill_control.skill_id} msg: {msg}")
    if msg["payload"]["skill_id"] == self.skill_control.skill_id:
      if msg["payload"]["subtype"] == "media_player_command_response":
        self.media_session_response = msg["payload"]["response"]
        if self.media_session_response == "session_ended":
          self.send_release_output_focus()
        elif self.media_session_response == "session_paused":
          info = {"subtype": "pause_confirmed",
                  "skill_id": "system_skill",
                  "from_skill_id": self.skill_control.skill_id
                 }
          self.bus.send("system", "system_skill", info)
        elif self.media_session_response == "session_confirm":
          self.media_player_session_id = msg["payload"]["session_id"]
          self.log.info(f"SimpleVoiceAssistant.handle_skill_msg() Play media {self.skill_control.skill_id}")
          self.i_am_active = True
          info = {"subtype": "media_player_command",
                  "command": "play_media",
                  "file_uri": self.file_uri,
                  "session_id": self.media_player_session_id,
                  "skill_id": "media_player_service",
                  "from_skill_id": self.skill_control.skill_id,
                  "media_type": self.media_type,
                  "delete_on_complete": self.delete_on_complete
                 }
          self.bus.send("media", "media_player_service", info)
      if msg["payload"]["subtype"] == "tts_service_command_response":
        self.tts_session_response = msg["payload"]["response"]
        if self.tts_session_response == "session_ended":
          if len(self.tts_service_session_ids) > 0:
            self.tts_service_session_id = self.tts_service_session_ids.pop() # get last session
            self.log.debug(f"SimpleVoiceAssistant.handle_skill_msg() restoring session: {self.tts_service_session_id}") 
          else:
            self.i_am_active = False
          info = {"subtype": "release_output_focus",
                  "skill_id": "system_skill",
                  "from_skill_id": self.skill_control.skill_id
                 }
          self.bus.send("system", "system_skill", info)
          self.done_speaking = True
          if self.speak_callback:
            self.speak_callback()
        elif self.tts_session_response == "paused_confirmed":
          info = {"subtype": "pause_confirmed",
                  "skill_id": "system_skill",
                  "from_skill_id": self.skill_control.skill_id
                 }
          self.bus.send("system", "system_skill", info)
        elif self.tts_session_response == "session_confirm":
          if self.tts_service_session_id != msg["payload"]["session_id"] and self.tts_service_session_id != 0:
            self.tts_service_session_ids.append(self.tts_service_session_id)
          self.tts_service_session_id = msg["payload"]["session_id"]
          info = {"text": self.text,
                  "skill_id":self.skill_control.skill_id
                 }
          self.bus.send("speak", "tts_service", info)
      if self.handle_message is not None:
        self.handle_message(msg)
    else:                                  # else could be a stt_start/end notification which is useful for converse()
      if msg["payload"]["subtype"] == "stt_start":
        self.stt_is_active = True
      if msg["payload"]["subtype"] == "stt_end":
        self.stt_is_active = False

  def handle_media_msg(self, msg):
    self.log.debug(f"SimpleVoiceAssistant.handle_media_msg() msg = {msg}")
    if msg["payload"]["skill_id"] == self.skill_control.skill_id:
      if self.handle_message is not None:
        self.handle_message(msg)

  def pause_sessions(self):
    # pause any active media sessions
    self.log.debug(f"SimpleVoiceAssistant.pause_sessions() media_player_session_id = {self.media_player_session_id}")
    if self.media_player_session_id != 0:
      info = {"subtype": "media_player_command",
              "command": "pause_session",
              "session_id": self.media_player_session_id,
              "skill_id": "media_player_service",
              "from_skill_id": self.skill_control.skill_id
             }
      self.bus.send("media", "media_player_service", info)
      self.i_am_paused = True
    if self.tts_service_session_id != 0:   # pause any active tts sessions
      info = {"subtype": "tts_service_command",
              "command": "pause_session",
              "session_id": self.tts_service_session_id,
              "skill_id": "tts_service",
              "from_skill_id": self.skill_control.skill_id
             }
      self.send_message("tts_service", info)
      self.i_am_paused = True

  def handle_system_msg(self, msg):
    self.log.debug(f"SimpleVoiceAssistant.handle_system_msg() skill_control.skill_id: {self.skill_control.skill_id} msg: {msg}")
    msg_type = msg.get("msg_type")
    source = msg.get("source")
    payload = msg.get("payload") 
    subtype = payload.get("subtype")
    from_skill_id = payload.get("skill_id")
    if from_skill_id == self.skill_control.skill_id:
      self.log.info(f"SimpleVoiceAssistant.handle_system_msg() from_skill_id: {from_skill_id} matches control skill ID - subtype: {subtype}")
      match subtype:
        case "stop" | "stock":             # "stop" is often heard as "stock"
          self.log.debug(f"SimpleVoiceAssistant.handle_system_msg() stop detected - calling 'mpc clear'")
          self.mpc_cmd("clear")            # clear the MPC queue
          self.i_am_paused = False
          self.waiting_for_input_focus = False
          self.i_am_conversed = True
          self.ignore_raw_ctr = 0
        case "request_output_focus_response": 
          status = msg["payload"]["status"]
          self.log.info(f"SimpleVoiceAssistant.handle_system_msg() request_output_focus_response status: {status}")
          if status == "confirm":          # state speak 
            if self.focus_mode == "speech":
              self.tts_session_response = ""
              info = {"subtype": "tts_service_command",
                      "command": "start_session",
                      "skill_id": "tts_service",
                      "from_skill_id": self.skill_control.skill_id
                     }
              self.send_message("tts_service", info)
            else:                          # must be state media
              info = {"subtype": "media_player_command",
                      "command": "start_session",
                      "skill_id": "media_player_service",
                      "from_skill_id": self.skill_control.skill_id
                     }
              self.bus.send("media", "media_player_service", info)
          else:
            self.log.warning(f"SimpleVoiceAssistant.handle_system_msg() {self.skill_control.skill_id} cannot acquire output focus!")
        case "pause":
          if self.i_am_paused:
            self.log.debug("SimpleVoiceAssistant.handle_system_msg() IGNORE PAUSE BECAUSE ALREADY PAUSED!!!!!")
            return
          return self.pause_sessions()
        case "pause_internal":
          self.log.debug("SimpleVoiceAssistant.handle_system_msg() ALREADY PAUSED BUT CANT IGNORE INTERNAL PAUSE !!!!")
          return self.pause_sessions()
        case "resume":                     # resume any active media sessions
          if self.media_player_session_id != 0:
            info = {"subtype": "media_player_command",
                    "command": "resume_session",
                    "session_id": self.media_player_session_id,
                    "skill_id": "media_player_service",
                    "from_skill_id": self.skill_control.skill_id
                   }
            self.bus.send("media", "media_player_service", info)
            self.i_am_paused = False
            if self.tts_service_session_id != 0:  # resume any active tts sessions
              info = {"subtype": "tts_service_command",
                      "command": "resume_session",
                      "session_id": self.tts_service_session_id,
                      "skill_id": "tts_service",
                      "from_skill_id": self.skill_control.skill_id
                     }
              self.send_message("tts_service", info)
              self.i_am_paused = False
      if self.handle_message is not None:  # honor any registered message handlers
        self.log.debug(f"SimpleVoiceAssistant.handle_system_msg() calling self.handle_message() msg: {msg}")
        self.handle_message(msg)

