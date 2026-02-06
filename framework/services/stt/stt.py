from bus.MsgBus import MsgBus
from datetime import datetime
from framework.util.utils import aplay, LOG, Config, get_wake_words
from multiprocessing import Process, Pipe, Manager
from multiprocessing.connection import wait
from subprocess import Popen, PIPE
import numpy as np
import dbm
import glob 
import json
import os
import time
import wave

REMOTE_TIMEOUT = 3
LOCAL_TIMEOUT = 7

def has_speech(wav_filename, energy_threshold=0.001):
  # Check if WAV file contains speech above threshold
  try:
    with wave.open(wav_filename, 'rb') as wav:
      audio_data = wav.readframes(wav.getnframes())
      audio_array = np.frombuffer(audio_data, dtype=np.int16)
      if len(audio_array) == 0:
        return False
      # Normalize and calculate energy
      audio_normalized = audio_array / 32768.0
      energy = np.mean(audio_normalized ** 2)
      # Add logging
      print(f"DEBUG: File {os.path.basename(wav_filename)} energy: {energy:.6f}, threshold: {energy_threshold}")
      return energy > energy_threshold
  except Exception:
    return True

def execute_command(command):
  p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
  stdout, stderr = p.communicate()
  return (
    str(stdout.decode('utf-8')),
    str(stderr.decode('utf-8')),
    p.returncode
  )

def _local_transcribe_file(wav_filename, return_dict, completion_pipe):
  # Use whisper, listening on port 5002, for local STT
  if not os.path.exists(wav_filename):
    print(f"remote_transcribe_file(): ERROR - File does not exist: {wav_filename}", flush=True)
    completion_pipe.send("error")          # signal local transcription completed
    return
  try:
    cmd = f'curl -X POST http://localhost:5002/stt -s -H "Content-Type: audio/wav" --data-binary @"{wav_filename}" --max-time {LOCAL_TIMEOUT}'
    stdout, stderr, returncode = execute_command(cmd)
    if returncode != 0:
      print("remote_transcribe_file(): ERROR - Hub is not reachable")
      completion_pipe.send("error")        # signal local transcription completed
      return
    if not stdout or stdout.strip() == "":
      print(f"stdout: [{stdout}] stderr: [{stderr}]")
      print("remote_transcribe_file(): ERROR - Empty response from curl", flush=True)
      completion_pipe.send("done")         # signal local transcription completed
      return
    print(f"DEBUG: Raw curl output: '{stdout}'")
    print(f"DEBUG: Output length: {len(stdout)}")
    res = json.loads(stdout)["text"]
    if res:
      res = res.strip()
      if res[-1] == '.':
        res = res[:-1]
      print(f"_local_transcribe_file(): cmd: {cmd} res: {res}")
      return_dict['service'] = 'local'
      return_dict['text'] = res
      completion_pipe.send("done")         # signal local transcription completed
    else:
      print("_local_transcribe_file(): ERROR: res not set")
      completion_pipe.send("done")         # signal local transcription completed
  except Exception as e:
    print(f"Local transcription error: {e}")
    completion_pipe.send("done")          # signal local transcription completed
  finally:
    completion_pipe.close()

def handle_utt(ww, utt, tmp_file_path):
  text_path = tmp_file_path + "save_text"
  entry = "[%s]%s" % (ww,utt)
  if ww == '':
    entry = "[%s]%s" % ('RAW',utt)
  fname = "%s/savetxt_%s.txt" % (text_path, datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f"))
  fh = open(fname, 'w')
  fh.write(entry)
  fh.close()

class STTSvc:
  # Monitor the wav file input directory and convert wav files to text strings in files in 
  # the output directory. we stitch so if someone says 'wake word' brief silence, 'bla bla' 
  # we stitch them together before intent matching. this produces two broad categories of 
  # input; raw and wake word qualified. these become "raw" and "utterance"
  def __init__(self, bus=None, no_bus=False):
    # used for skill type messages
    self.skill_id = 'stt_service'
    base_dir = os.getenv('SVA_BASE_DIR')
    if base_dir is None:
      home_dir = os.environ.get('HOME')
      base_dir = f"{home_dir}/minimy"
    self.tmp_file_path = base_dir + "/tmp/"
    l2r_path = base_dir + "/framework/services/stt/db/local2remote.db"
    self.local2remote = dbm.open(l2r_path, 'c')
    self.no_bus = no_bus
    self.bus = None
    if not no_bus:
      if bus is None:
        bus = MsgBus(self.skill_id)
      self.bus = bus
    log_filename = base_dir + '/logs/stt.log'
    self.log = LOG(log_filename).log
    self.waiting_stt = False
    self.manager = Manager()
    self.remote_return_dict = self.manager.dict()
    self.local_return_dict = self.manager.dict()
    self.remote_proc = None
    self.local_proc = None
    self.previous_utterance = ''
    self.previous_utt_was_ww = False
    self.wav_file = None
    self.mute_start_time = 0
    self.wws = get_wake_words()
    base_dir = os.getenv('SVA_BASE_DIR')
    self.beep_loc = "%s/framework/assets/what.wav" % (base_dir,)
    self.cfg = Config()
    self.hub = self.cfg.get_cfg_val("Basic.Hub")
    remote_stt = self.cfg.get_cfg_val('Advanced.STT.UseRemote')
    if remote_stt == 'y':                  # use remote STT
      self.use_remote_stt = True
      remote_stt = self.cfg.get_cfg_val('Advanced.STT.Remote')
      if remote_stt == 'g':                # use google
        # from google.cloud import speech
        from framework.services.stt.remote.google_stt import remote_transcribe_file
        self.remote_transcribe_function = remote_transcribe_file
      else:                                # use whisper
        from framework.services.stt.remote.whisper_stt import remote_transcribe_file
        self.remote_transcribe_function = remote_transcribe_file
    else:
      self.use_remote_stt = False
    self.log.info(f"STTSvc.__init__() use_remote_stt: {self.use_remote_stt} wws: {self.wws}")
    print(f"STTSvc.__init__() use_remote_stt: {self.use_remote_stt} wws: {self.wws}")

  def send_message(self, target, subtype):
    # send a standard skill message on the bus.
    # message must be a dict
    if self.bus is not None:
      info = {
          'from_skill_id': self.skill_id,
          'skill_id': target,
          'source': self.skill_id,
          'target': target,
          'subtype': subtype
      }
      self.bus.send("skill", target, info)

  def send_mute(self):
    self.log.debug("STT: sending mute!")
    self.send_message('volume_skill', 'mute_volume')

  def send_unmute(self):
    self.log.debug("STT: sending unmute!")
    self.send_message('volume_skill', 'unmute_volume')

  def process_stt_result(self, utt):
    if utt:
      self.log.debug(f"STT.process_stt_result(): utt: {utt}")
      wake_word = ''
      for ww in self.wws:
        if utt.lower().find(ww.lower()) > -1:
          wake_word = ww
          break
      if wake_word == "":                  # ww not found in utt
        if self.muted:
          self.muted = False
          self.send_unmute()
        if self.previous_utt_was_ww:
          wake_word = self.previous_utterance
          cmd = utt.replace(wake_word,'').strip()
          if len(cmd) > 2:
            handle_utt(wake_word, cmd, self.tmp_file_path)
          else:
            self.log.info("Too short --->%s" % (cmd,))
            print("Too short --->%s" % (cmd,))
        else:                              # ww not found and previous utt not ww => raw statement
          handle_utt('', utt, self.tmp_file_path)
        self.previous_utt_was_ww = False
      else:                                # otherwise utt contains ww
        if len(utt) == len(wake_word):     # it is just the wake word
          self.previous_utterance = utt.lower()
          self.previous_utt_was_ww = True
          aplay(self.beep_loc)
          if not self.muted:
            self.muted = True
            self.send_mute()
            self.mute_start_time = time.time()
        else:                              # utt contains the wake word and more
          if self.muted:
            self.muted = False
            self.send_unmute()
          cmd = utt.replace(wake_word,'').strip()
          if len(cmd) > 2:
            handle_utt(wake_word, cmd, self.tmp_file_path)
          else:
            self.log.info("Too short --->%s" % (cmd,))
            print("Too short --->%s" % (cmd,))
          self.previous_utt_was_ww = False
      self.previous_utterance = utt

  def run(self):
    self.previous_utterance = ''
    self.previous_utt_was_ww = False
    loop_ctr = 0
    clear_utt_time_in_seconds = 5 # 5 secs at 4 times/sec see sleep at bottom of loop
    clear_utt_time_in_seconds *= 4
    self.muted = False # not necessary if you have good echo cancellation like a headset
    self.mute_start_time = 0
    self.log.debug(f"STT.run(): use_remote_stt: {self.use_remote_stt}")
    while True:
      loop_ctr += 1
      if loop_ctr > clear_utt_time_in_seconds:
        # time out previous utterance - this is so you can't say wake word
        # then a long time later you say something else and we think its 
        # wake word plus utterance - byproduct of wake word to utterance stitching strategy
        self.previous_utterance = ''
        loop_ctr = 0
      if self.muted:
        diff = time.time() - self.mute_start_time
        if diff > 3.5:
          self.muted = False
          self.send_unmute()
      # Get WAV files
      mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_audio/*.wav")] )
      if len(mylist) == 0:                 # If no files present, sleep and continue
        time.sleep(0.025)
        continue
      loop_ctr = 0                         # We have at least one WAV file
      self.wav_file = mylist[0]
      if not has_speech(self.wav_file):
        self.log.debug(f"STT.run(): Skipping low-energy file: {self.wav_file}")
        try:
          os.remove(self.wav_file)
        except Exception:
          pass
        continue
      self.log.debug(f"STT.run(): processing wav_file: {self.wav_file}")
      self.waiting_stt = True
      readers = []
      # Remote STT
      remote_parent_conn = None
      remote_proc = None
      remote_return_dict = self.manager.dict()
      if self.use_remote_stt:
        self.log.debug("STT.run(): sending file to remote STT")
        try:
          remote_parent_conn, remote_child_conn = Pipe()
          readers.append(remote_parent_conn)
          remote_proc = Process(
            target=self.remote_transcribe_function,
            args=(self.wav_file, remote_return_dict, self.hub, remote_child_conn)
          )
          remote_proc.start()
          remote_child_conn.close()
        except Exception as e:
          self.log.error(f"STT.run(): Failed to start remote STT: {e}")
          remote_parent_conn = None
          remote_proc = None
          if remote_parent_conn and remote_parent_conn in readers:
            readers.remove(remote_parent_conn)
      else:
        remote_parent_conn = None
      # Local STT
      local_parent_conn, local_child_conn = Pipe()
      readers.append(local_parent_conn)
      local_return_dict = self.manager.dict()
      local_proc = Process(
        target=_local_transcribe_file,
        args=(self.wav_file, local_return_dict, local_child_conn)
      )
      local_proc.start()
      local_child_conn.close()
      self.log.debug("STT.run(): waiting for fastest process to finish...")
      # Wait for the fastest process to finish, then proceed
      initial_timeout = REMOTE_TIMEOUT if self.use_remote_stt else LOCAL_TIMEOUT
      try:
        ready = wait(readers, timeout=LOCAL_TIMEOUT)
        self.log.error(f"STT.run(): ready: {ready}")
        remote_success = False
        local_success = False
        use_remote_result = False
        # Check if remote succeeded first
        if self.use_remote_stt and remote_parent_conn and remote_parent_conn in ready:
          try:
            msg = remote_parent_conn.recv()
            if msg == "done" and remote_return_dict and len(remote_return_dict) > 0:
              remote_success = True
              use_remote_result = True
              self.log.debug("STT.run(): remote STT succeeded first")
          except Exception as e:
            self.log.error(f"STT.run(): error receiving from remote: {e}")
        # Check local response if remote didn't succeed first
        if not use_remote_result and local_parent_conn in ready:
          try:
            msg = local_parent_conn.recv()
            if msg == "done" and local_return_dict and len(local_return_dict) > 0:
              local_success = True
              use_remote_result = False
              self.log.debug("STT.run(): local STT succeeded first")
          except Exception as e:
            self.log.error(f"STT.run(): error receiving from local: {e}")
        # If neither succeeds during the initial wait, continue waiting on whichever is still alive
        if not remote_success and not local_success:
          self.log.debug("STT.run(): waiting longer for transcription...")
          pending_connections = []         # Build lists of pending connections
          pending_indices = []
          all_connections = []
          if self.use_remote_stt and remote_parent_conn:
            all_connections.append(remote_parent_conn)
          all_connections.append(local_parent_conn)
          # Check which ones weren't ready
          for idx, conn in enumerate(all_connections):
            # Map current index to original index in 'readers' list
            original_idx = idx if (not self.use_remote_stt or remote_parent_conn) else (idx + 1 if idx > 0 else 0)
            if original_idx not in ready:
              pending_connections.append(conn)
              pending_indices.append(original_idx)
          if pending_connections:          # Wait for remaining processes with remaining timeout
            remaining_timeout = LOCAL_TIMEOUT - initial_timeout
            if remaining_timeout > 0:
              # Use the original wait function on the pending connections
              remaining_ready_indices = wait(pending_connections, timeout=remaining_timeout)
              # Process ready connections
              for pending_idx, conn in enumerate(pending_connections):
                if pending_idx in remaining_ready_indices:
                  try:
                    msg = conn.recv()
                    if msg == "done":      # Determine if this is remote or local based on original index
                      original_idx = pending_indices[pending_idx]
                      if (self.use_remote_stt and remote_parent_conn and 
                        original_idx == 0):  # remote is at index 0
                        remote_success = True
                        use_remote_result = True
                        self.log.debug("STT.run(): remote STT succeeded after longer wait")
                      else:                # local
                        local_success = True
                        use_remote_result = False
                        self.log.debug("STT.run(): local STT succeeded after longer wait")
                  except Exception as e:
                    self.log.error(f"STT.run(): error receiving after longer wait: {e}")
        # Store results for later use
        if remote_success and use_remote_result:
          self.remote_return_dict = remote_return_dict
          self.local_return_dict = {}
        elif local_success and not use_remote_result:
          self.local_return_dict = local_return_dict
          self.remote_return_dict = {}
      except Exception as e:
        self.log.error(f"STT.run(): error in process coordination: {e}")
        remote_success = False
        local_success = False
      try:                                 # Process termination
        if local_proc and local_proc.is_alive():
          local_proc.terminate()
          local_proc.join(timeout=0.5)
          if local_proc.is_alive():
            local_proc.kill()
            local_proc.join(timeout=0.5)
      except Exception as e:
        self.log.error(f"STT.run(): error terminating local process: {e}")
      try:
        if remote_proc and remote_proc.is_alive():
          remote_proc.terminate()
          remote_proc.join(timeout=0.5)
          if remote_proc.is_alive():
            remote_proc.kill()
            remote_proc.join(timeout=0.5)
      except Exception as e:
        self.log.error(f"STT.run(): error terminating remote process: {e}")
      if os.path.exists(self.wav_file):    # Safe file deletion
        try:
          self.log.debug(f"STT.run(): removing file {self.wav_file}")
          os.remove(self.wav_file)
        except Exception as e:
          self.log.error(f"Error deleting WAV file: {e}")
          time.sleep(0.05)                 # Try once more after short sleep
          try:
            os.remove(self.wav_file)
          except Exception as e2:
            self.log.error(f"Second attempt failed to delete WAV file: {e2}")
      else:
        self.log.debug(f"STT.run(): file {self.wav_file} already deleted or missing")
        self.wav_file = None
        self.waiting_stt = False
      try:                                 # Handle results
        if remote_success and self.remote_return_dict and 'text' in self.remote_return_dict:
          self.log.debug(f"STT.run(): remote_return_dict: {self.remote_return_dict}")
          self.process_stt_result(self.remote_return_dict['text'])
        elif local_success and self.local_return_dict and 'text' in self.local_return_dict:
          self.log.debug(f"STT.run(): local_return_dict: {self.local_return_dict}")
          local_text = self.local_return_dict['text']
          if local_text in self.local2remote:
            remote_text = self.local2remote[local_text].decode("utf-8")
            self.log.debug(f"STT.run(): CACHE HIT!!! Converted local: {local_text} remote: {remote_text}")
            self.process_stt_result(remote_text)
          else:
            self.process_stt_result(local_text)
        else:
          self.log.info("STT.run(): Can't produce STT from WAV file")
        # Cache update with better validation
        if (remote_success and local_success and
            self.remote_return_dict and 'text' in self.remote_return_dict and
            self.local_return_dict and 'text' in self.local_return_dict):
          local_text = self.local_return_dict['text']
          remote_text = self.remote_return_dict['text']
          if local_text and remote_text:
            self.log.debug(f"STT.run(): new cache entry. local: {local_text} remote: remote_text")
            self.local2remote[local_text] = remote_text
      except Exception as e:
        self.log.error(f"STT.run(): error processing STT results: {e}")
      time.sleep(0.025)                    # Short sleep to save resources

# main()
if __name__ == '__main__':
  stt_svc = STTSvc()
  stt_svc.run()                            # Loop forever
