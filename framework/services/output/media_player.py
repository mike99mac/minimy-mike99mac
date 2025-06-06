from threading import Event
from bus.MsgBus import MsgBus
import time, os
from subprocess import Popen, PIPE, STDOUT
from framework.util.utils import CommandExecutor, LOG, Config, MediaSession, get_hal_obj

class SVAMediaPlayerSkill:
  # The media player plays wav and mp3 files. it has several interesting features. first it can pause an active media
  # session and play a new one. it stacks these in the paused_sessions queue. 
  # The media player does not have a paused state as such. 
  def __init__(self, timeout=5):
    self.skill_id = "media_player_service"
    self.bus = MsgBus(self.skill_id)
    base_dir = os.getenv("SVA_BASE_DIR")
    log_filename = base_dir + "/logs/media_player.log"
    self.log = LOG(log_filename).log
    self.log.debug("SVAMediaPlayerSkill.__init__() starting")
    self.is_running = False
    self.next_session_id = 0
    self.current_session = MediaSession(0, None)
    self.paused_sessions = []
    self.state = "idle"        # states = idle, playing or paused
    self.hal = get_hal_obj("l")
    self.bus.on("media", self.handle_message)

  def send_message(self, target, msg):
    # send a standard skill message on the bus 
    self.log.debug(f"SVAMediaPlayerSkill.send_message() msg: {msg}")
    msg["from_skill_id"] = self.skill_id   # set to this from skill
    self.bus.send("skill", target, msg)

  def pause(self, msg):
    self.log.info(f"SVAMediaPlayerSkill.pause() state: {self.state} msg: {msg}")
    if self.state == "playing":
      self.current_session.correlator = msg["payload"]["correlator"]
      self.state = "paused"      # send signal to run()
    else:                # must ack pause request or other events won"t trigger
      if len(self.paused_sessions) > 0:
        tmp = self.paused_sessions[len(self.paused_sessions) - 1]
        self.send_session_paused(tmp.session_id, tmp.owner)

  def resume(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.resume() state = {self.state}")
    if self.state == "paused":
      self.state = "resumed"
      self.current_session = self.paused_sessions.pop()
      if self.current_session.ce.proc is not None:
        if self.current_session.media_type == "wav": # we have an active process, resume it
          self.current.session.ce.send(" ")
        else:
          if self.current_session.media_type == "mp3":
            self.current.session.ce.send("s")
          else:
            os.system("dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause")
      else:
        self.log.error("SVAMediaPlayerSkill.resume() BUG????? resume but no session.ce.proc!!!!!")
        pass
    elif self.state == "idle":
      if len(self.paused_sessions) > 0:
        self.log.debug("SVAMediaPlayerSkill.resume() was idle but there are paused sessions to restart")
        self.current_session = self.paused_sessions.pop()
        if self.current_session.ce.proc is not None: # we have an active process, resume it
          if self.current_session.media_type == "wav":
            self.current_session.ce.send(" ")
          else:
            if self.current_session.media_type == "mp3":
              self.current_session.ce.send("s")
            else:
              os.system("dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause")
        self.state = "resumed"
    else:
      self.log.debug(f"SVAMediaPlayerSkill.resume() resume Ignored - state = {self.state}")

  def clear_q(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.clear_q() state: {self.state} current_session: {self.current_session}")
    self.state = "idle"
    local_q = self.current_session.media_queue
    for mentry in local_q:
      next_uri = mentry["file_uri"]
      self.log.error(f"SVAMediaPlayerSkill.clear_q() BUG! ClearQ must deal with this: {next_uri}")
    self.current_session.media_queue = []

  def reset_session(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.reset_session(), state: {self.state} current_session is: {self.current_session}")
    if not self.current_session:
      self.resume(msg)
      time.sleep(0.01)
    if self.current_session.ce.proc is not None:
      try:
        self.current_session.ce.kill()
      except:
        self.log.warning("SVAMediaPlayerSkill.reset_session() Exception in media player killing existing proc")
    else:
      self.log.error("SVAMediaPlayerSkill:reset_session(): no currently executing command!")
    self.clear_q(msg)
    return self.play_file(msg)

  def play_file(self, msg):
    # add file to end of queue if not playing change state to playing
    self.log.debug(f"SVAMediaPlayerSkill.play_file() msg: {msg}")
    from_skill = msg["payload"]["from_skill_id"]
    file_uri = msg["payload"]["file_uri"]
    play_session_id = msg["payload"]["session_id"]
    media_type = msg["payload"]["media_type"]
    self.log.info(f"SVAMediaPlayerSkill.play_file(): MediaType: {media_type} PlaySID: {play_session_id} CurrentSID: {self.current_session.session_id} file_uri: {file_uri}")
    if play_session_id == self.current_session.session_id:
      media_entry = {"file_uri": file_uri,
                     "media_type": media_type,
                     "delete_on_complete": msg["payload"]["delete_on_complete"],
                     "from_skill_id": from_skill
                    }
      self.current_session.media_queue.append(media_entry)
      if self.state == "idle":
        self.state = "playing"
    else:
      self.log.warning("SVAMediaPlayerSkill.play_file()! Play file request from non active session ignored!!!")

  def send_session_end_notify(self, reason):
    self.log.debug(f"SVAMediaPlayerSkill.send_session_end_notify() reason: {reason}")
    info = {"subtype": "media_player_command_response",
            "response": "session_ended",
            "correlator": self.current_session.correlator,
            "reason": reason,
            "session_id": self.current_session.session_id,
            "skill_id": self.current_session.owner,
            "from_skill_id": "media_player_service"
           }
    tmp_target = self.current_session.owner
    self.current_session.owner = None
    self.log.info(f"MediaPlayer send_session_end_notify() - setting current_session.id to 0, it was {self.current_session.session_id}")
    self.current_session.session_id = 0
    self.current_session.media_queue = []
    return self.send_message(tmp_target, info)

  def send_session_reject(self, reason, msg):
    # Send session reject message on bus
    self.log.debug(f"SVAMediaPlayerSkill.send_session_reject() reason: {reason} msg: {msg}")
    info = {"error": reason,
            "subtype": "media_player_command_response",
            "response": "session_reject",
            "correlator": self.current_session.correlator,
            "skill_id": msg["payload"]["from_skill_id"],
            "from_skill_id": "media_player_service"
           }
    return self.send_message(data["from_skill_id"], info)

  def send_session_paused(self, session_id, target):
    self.log.debug(f"SVAMediaPlayerSkill.send_session_paused() session_id: {session_id} target: {target}")
    info = {"subtype":"media_player_command_response",
            "response":"session_paused",
            "correlator":self.current_session.correlator,
            "session_id":session_id,
            "skill_id":target,
            "from_skill_id":"media_player_service",
           }
    return self.send_message(target, info)

  def send_session_confirm(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.send_session_confirm() msg: {msg}")
    info = {"subtype": "media_player_command_response",
            "response": "session_confirm",
            "correlator": self.current_session.correlator,
            "session_id": self.current_session.session_id,
            "skill_id": msg["payload"]["from_skill_id"],
            "from_skill_id": "media_player_service"
           }
    return self.send_message(msg["payload"]["from_skill_id"], info)

  def get_paused_session(self, paused_sid):
    self.log.debug(f"SVAMediaPlayerSkill.get_paused_session() paused_sid: {paused_sid}")
    for session in self.paused_sessions:
      if session.session_id == paused_sid:
        return session
    return None

  def remove_paused_entry(self, paused_entry):
    self.log.debug(f"SVAMediaPlayerSkill.remove_paused_entry() paused_entry: {paused_entry}")
    tmp_paused_sessions = []
    for session in self.paused_sessions:
      if session.session_id != paused_entry.session_id:
        tmp_paused_sessions.append(session)
    self.paused_sessions = tmp_paused_sessions

  def cancel_session(self, msg):
    self.log.debug("SVAMediaPlayerSkill.cancel_session() starting")
    cancel_sid = msg["payload"]["session_id"]  # could be paused or active
    if self.current_session and self.current_session.session_id == cancel_sid:
      if self.current_session.session_id == cancel_sid:
        if self.current_session.ce.proc is not None:
          try:
            self.current_session.ce.kill()
          except:
            self.log.warning("SVAMediaPlayerSkill.cancel_session() Exception in media player killing wav play")
        else:
          self.log.warning("SVAMediaPlayerSkill.cancel_session(): no currently executing command!")
      self.current_session.owner = None
      self.log.info(f"SVAMediaPlayerSkill.cancel_session() setting current_session.sid to 0, it was {self.current_session.session_id}")
      self.current_session.session_id = 0
      self.current_session.time_out_ctr = 0
      return self.clear_q(msg)
    else:
      paused_session = self.get_paused_session(cancel_sid)
      if not paused_session:     # cancel non existent media session ignored for now
        return 
      local_q = paused_session.media_queue # otherwise remove it from the paused q after draining its q and stopping its process
      for mentry in local_q:
        next_uri = mentry["file_uri"]
        self.log.error(f"SVAMediaPlayerSkill.cancel_session(): BUG! ClearQ must deal with this: {next_uri}")
      paused_session.media_queue = []
      if paused_session.ce.proc is not None:
        try:
          paused_session.ce.kill()
        except:
          self.log.warning("Exception in media player killing paused session player")
      else:
        self.log.warning(f"MediaPlayer:cancel_session(): no currently executing command for paused session: {cancel_sid}")
      self.remove_paused_entry(paused_session)

  def stop_session(self, msg):
    sid_to_stop = msg["payload"]["session_id"]
    self.log.info(f"SVAMediaPlayerSkill.stop_session() state: {self.state} session_id: {self.current_session.session_id} sid_to_stop: {sid_to_stop}")
    sid_owner = msg["payload"]["from_skill_id"]
    if self.current_session is None or self.current_session.session_id == 0: # no current session to stop, maybe he means a paused session?
      paused_session = self.get_paused_session(sid_to_stop)
      if paused_session:
        if paused_session.owner == sid_owner:  # make it the current session
          self.current_session = paused_session
          self.remove_paused_entry(paused_session)
        else:
          self.log.error(f"SVAMediaPlayerSkill.stop_session() BUG: session owner is {paused_session_owner} but {sid_owner} is asking to stop session!!!")
      else:              # session not active or paused maybe send a message
        self.log.warning(f"SVAMediaPlayerSkill.stop_session() cannot find sid to stop: {sid_to_stop}")
    if msg["payload"]["from_skill_id"] != self.current_session.owner: # active session is not owner's
      sid = msg["payload"]["session_id"]
      target = msg["payload"]["from_skill_id"]
      self.log.warning(f"SVAMediaPlayerSkill.stop_session() owner: {self.current_session.owner} not the requester: {target}")
      info = {"subtype": "media_player_command_response",
              "response": "session_ended",
              "correlator": sid,
              "reason": "killed",
              "session_id": sid,
              "skill_id": target,
              "from_skill_id": "media_player_service"
             }
      return self.send_message(target, info)
    else:
      if self.current_session.ce is not None:
        if self.current_session.media_type == "wav":
          try:
            self.current_session.ce.kill()
          except:
            self.log.warning("SVAMediaPlayerSkill.stop_session() Exception in media player killing wav play")
        else:
          try:
            self.current_session.ce.kill()
          except:
            self.log.warning("SVAMediaPlayerSkill.stop_session() Exception in media player killing mp3 play")
      else:
        self.log.debug("SVAMediaPlayerSkill.stop_session(): no currently executing command!")
        pass
      self.send_session_end_notify("killed")
      self.current_session.owner = None
      self.log.info(f"SVAMediaPlayerSkill.stop_session() setting current_session.sid to 0, it was {self.current_session.session_id}")
      self.current_session.session_id = 0
      self.current_session.time_out_ctr = 0
      return self.clear_q(msg)

  def start_session(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.start_session() sid = {self.current_session.session_id} msg: {msg}")
    from_skill_id = msg["payload"]["from_skill_id"]
    correlator = msg["payload"]["correlator"]
    if from_skill_id is None or from_skill_id == "":
      self.log.warning(f"SVAMediaPlayerSkill.start_session() Cannot start session with no from_skill_id")
      reason = "session_unknown_source"
      return self.send_session_reject(reason, msg)
    if self.current_session.owner is None:
      self.current_session.owner = from_skill_id
      self.next_session_id += 1
      self.current_session.session_id = self.next_session_id
      self.current_session_time_out_ctr = 0
      self.current_session.correlator = correlator
      return self.send_session_confirm(msg)
    reason = "session_busy"
    if self.current_session.owner == from_skill_id: # its owner doing the requesting
      self.next_session_id += 1
      self.current_session.session_id = self.next_session_id
      self.current_session_time_out_ctr = 0
      self.current_session.correlator = correlator
      return self.send_session_confirm(msg)
    self.log.info(f"SVAMediaPlayerSkill.stop_session() is busy, owner: {self.current_session.owner} requester: {from_skill_id}")
    return self.send_session_reject(reason, msg)

  def handle_message(self, msg):
    self.log.debug(f"SVAMediaPlayerSkill.handle_message() msg: {msg}")
    if msg["payload"]["subtype"] == "media_player_command":
      command = msg["payload"]["command"]
      if command == "play_media":
        return self.play_file(msg)
      elif command == "pause_session":
        return self.pause(msg)
      elif command == "resume_session":
        return self.resume(msg)
      elif command == "clear_q":
        return self.clear_q(msg)
      elif command == "start_session":
        return self.start_session(msg)
      elif command == "stop_session":
        return self.stop_session(msg)
      elif command == "reset_session":
        return self.reset_session(msg)
      elif command == "cancel_session":
        return self.cancel_session(msg)
      else:
        self.log.error(f"SVAMediaPlayerSkill.handle_message() - Unrecognized command: {command}")

  def wait_for_end_play(self, media_entry):
    self.log.debug(f"MediaPlayer:wait_for_end_play() media_entry: {media_entry}")
    while not self.current_session.ce.is_completed() and self.state == "playing":
      time.sleep(0.01)
    file_uri = media_entry["file_uri"]
    self.log.info(f"MediaPlayer:wait_for_end_play() state: {self.state} owner: {self.current_session.owner} file_uri: {file_uri}")
    if self.state == "paused":
      self.log.info("MediaPlayer:wait_for_end_play() Pausing current session")
      if self.current_session.ce.proc is not None:
        # if we have an active process, pause it
        if self.current_session.media_type == "wav":
          self.current_session.ce.send(" ")
          self.log.info("MediaPlayer:wait_for_end_play() Paused WAV playback")
        else:
          if self.current_session.media_type == "mp3":
            self.log.info("MediaPlayer:wait_for_end_play() Paused MP3 playback")
            self.current_session.ce.send("s")
          else:
            self.log.info("MediaPlayer:wait_for_end_play() Paused vlc stream playback")
            os.system("dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.vlc /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause")
        time.sleep(0.001)  # give ce a chance

      # push media entry onto paused stack
      # emulate deepcopy because of stupid thread.lock on process in cs
      ms_copy = MediaSession(self.current_session.session_id, self.current_session.owner)
      ms_copy.correlator = self.current_session.correlator
      ms_copy.media_queue = self.current_session.media_queue
      ms_copy.ce = self.current_session.ce
      ms_copy.time_out_ctr = self.current_session.time_out_ctr
      ms_copy.media_type = self.current_session.media_type
      self.paused_sessions.append( ms_copy )
      self.send_session_paused(self.current_session.session_id, self.current_session.owner)
    elif self.state == "resumed":
      self.log.warning("MediaPlayer.wait_for_end_play() ILLEGAL STATE TRANSITION playing to resumed!")
    else:
      process_exit_code = self.current_session.ce.get_return_code()
      self.log.debug(f"MediaPlayer.wait_for_end_play() end of play detected, process_exit_code: {process_exit_code} state: {self.state}")
      if process_exit_code != -9:  # remove from q if not killed
        self.current_session.media_queue = self.current_session.media_queue[1:]
        if media_entry["delete_on_complete"] == "true": # remove from file system if requested
          cmd = f'if [ -f {media_entry["file_uri"]} ]; then rm {media_entry["file_uri"]}; fi'
          os.system(cmd)
        if len(self.current_session.media_queue) == 0:
          self.state = "idle"
          self.log.info("MediaPlayer:wait_for_end_play() going idle because process ended and no more files to play for this session")
          self.send_session_end_notify("eof")
      else:
        self.log.info("MediaPlayer:wait_for_end_play() process was killed (-9)")
        if media_entry["delete_on_complete"] == "true":
          cmd = f'rm {media_entry["file_uri"]}'
          os.system(cmd)

  def run(self):
    self.log.debug(f"SVAMediaPlayerSkill.run() is_running: {self.is_running}")
    while self.is_running:
      if self.state == "playing":          # get next file to play for the current media session
        if self.current_session is None:   # no current session
          break
        if len(self.current_session.media_queue) == 0:  # no current file to play
          self.current_session_time_out_ctr += 1
          break
        media_entry = self.current_session.media_queue[0]
        file_uri = media_entry["file_uri"]
        media_type = media_entry["media_type"]
        self.log.debug(f"SVAMediaPlayerSkill.run() file_uri: {file_uri} media_type: {media_type}")
        fa = file_uri.split(".")
        file_ext = fa[len(fa) - 1]
        cfg = Config()
        device_id = cfg.get_cfg_val("Advanced.OutputDeviceName")
        cmd = ""
        if media_type is None or media_type == "":
          self.log.warning(f"SVAMediaPlayerSkill.run() invalid media type: {media_type}")
          self.current_session.media_type = "mp3"
          cmd = "mpg123 %s" % (file_uri,)  
          if device_id is not None:
            cmd = "mpg123 -a " + device_id + " " + file_uri
            if file_ext == "wav":
              cmd = "aplay " + file_uri
              if device_id is not None and device_id != "":
                cmd = "aplay -D" + device_id + " " + file_uri
              self.current_session.media_type = "wav"
          self.log.warning(f"SVAMediaPlayerSkill.run() derived media_type: {media_type}")
        else:                              # media type is known so use it to get cmd line from hal cfg file
          self.current_session.media_type = media_type
          media_player_cfg = self.hal.get("play_media", None)
          if media_player_cfg:
            cmd = media_player_cfg.get(self.current_session.media_type,"")
          if cmd == "":
            self.log.error("SVAMediaPlayerSkill.run() invalid media player command line !")
            return 
          else:
            cmd = cmd % (file_uri,)
        self.log.info("cmd = %s" % (cmd,))
        self.current_session.ce = CommandExecutor(cmd)
        self.wait_for_end_play(media_entry)
      if self.state == "resumed":
        self.state = "playing"
        self.wait_for_end_play(media_entry)
      if self.state == "paused":   # clear current media entry
        self.current_session.owner = None
        self.current_session.ce = None
        self.log.info(f"SVAMediaPlayerSkill.run() run() - setting current_session.sid to 0, it was {self.current_session.session_id}")
        self.current_session.session_id = 0
        self.current_session.time_out_ctr = 0
        self.current_session.media_queue = []
        self.current_session.state = "idle"
        self.log.debug("SVAMediaPlayerSkill.run() - Paused Signal causing me to transition to idle!")
        self.state = "idle"
      time.sleep(0.01)

# main()
if __name__ == "__main__":
  sva_mps = SVAMediaPlayerSkill()
  sva_mps.is_running = True
  sva_mps.run()
  Event().wait()                           # wait forever

