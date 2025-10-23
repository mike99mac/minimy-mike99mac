from bus.MsgBus import MsgBus
from datetime import datetime
import dbm
from framework.util.utils import aplay, LOG, Config, execute_command, get_wake_words
import glob 
import multiprocessing
import os
import time
import json
from threading import Event

LOCAL_TIMEOUT = 8

def _local_transcribe_file(wav_filename, return_dict, completion_pipe):
  # Use whisper, listening on port 5002, for local STT 
  try:
    cmd = 'curl http://localhost:5002/stt -s -H "Content-Type: audio/wav" --data-binary @"%s"' % (wav_filename)
    out = execute_command(cmd)
    res = json.loads(out)["text"]          # Fix formatting
    if res:
      res = res.strip()
      if res[-1] == '.':
        res = res[:-1]
      print(f"_local_transcribe_file(): cmd: {cmd} res: {res}") 
      return_dict['service'] = 'local'
      return_dict['text'] = res
  except Exception as e:                   # Catch error if unable to reach remote
    print(f"Local transcription error: {e}")
  finally:
    completion_pipe.send("done")           # Signal local transcription completed
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
  def __init__(self, bus=None, timeout=5, no_bus=False):
    # used for skill type messages
    self.skill_id = 'stt_service'
    base_dir = os.getenv('SVA_BASE_DIR')
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
    self.manager = multiprocessing.Manager()
    self.remote_return_dict = self.manager.dict()
    self.local_return_dict = self.manager.dict()
    self.remote_proc = None
    self.local_proc = None
    self.bark = False
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
        from framework.services.stt.remote.google import remote_transcribe_file
        self.remote_transcribe_function = remote_transcribe_file
      else:                                # use whisper
        from framework.services.stt.remote.whisper_stt import remote_transcribe_file
        self.remote_transcribe_function = remote_transcribe_file
    else:
      self.use_remote_stt = False
    self.log.info(f"STTSvc.__init__() use_remote_stt: {self.use_remote_stt} wws: {self.wws}")
    if self.bark:
      print(f"STTSvc.__init__() use_remote_stt: {self.use_remote_stt} wws: {self.wws}")

  def send_message(self, target, subtype):
    # send a standard skill message on the bus.
    # message must be a dict
    if not self.no_bus:
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
            if self.bark:
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
            if self.bark:
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
        # time out previous utterance this is so you can't say wake word
        # then a long time later you say something else and we think its 
        # wake word plus utterance - byproduct of wake word to utterance stitching strategy
        self.previous_utterance = ''
        loop_ctr = 0
      if self.muted:
        diff = time.time() - self.mute_start_time
        if diff > 3.5:
          self.muted = False
          self.send_unmute()
      mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_audio/*.wav")] ) # get wav files 
      if len(mylist) > 0:                  # we have at least one
        loop_ctr = 0
        self.wav_file = mylist[0]
        self.log.debug(f"STT.run(): processing wav_file: {self.wav_file}")
        self.waiting_stt = True
        readers = []

        # Remote STT
        if self.use_remote_stt:
          self.log.debug(f"STT.run(): sending file to remote STT")
          remote_parent_conn, remote_child_conn = multiprocessing.Pipe()
          readers.append(remote_parent_conn)
          self.remote_return_dict = self.manager.dict()
          self.remote_proc = multiprocessing.Process(
            target=self.remote_transcribe_function,
            args=(self.wav_file, self.remote_return_dict, self.hub, remote_child_conn)
          )
          self.remote_proc.start()
          remote_child_conn.close()

        # Local STT
        local_parent_conn, local_child_conn = multiprocessing.Pipe()
        readers.append(local_parent_conn)
        self.local_return_dict = self.manager.dict()
        self.local_proc = multiprocessing.Process(
          target=_local_transcribe_file,
          args=(self.wav_file, self.local_return_dict, local_child_conn)
        )
        self.local_proc.start()
        self.log.debug(f"STT.run(): waiting for fastest process to finish...")
        local_child_conn.close()           
        
        # Wait for the fastest process to finish, then proceed
        ready = multiprocessing.connection.wait(readers, timeout=LOCAL_TIMEOUT)
        if not ready:
          self.log.error(f"STT.run(): timed out waiting for transcription")
          if self.local_proc.is_alive():
            self.local_proc.kill()
            self.local_proc.join(timeout=0.01)
          if self.use_remote_stt and self.remote_proc.is_alive():
            self.remote_proc.kill()
            self.remote_proc.join(timeout=0.01)
        else:
          if self.use_remote_stt and remote_parent_conn in ready:
            self.log.debug("STT.run(): remote STT returned")
            remote_parent_conn.recv()
            if self.local_proc.is_alive():
              self.local_proc.kill()
              self.local_proc.join(timeout=0.01)
            self.remote_proc.join(timeout=0.01)
          else:
            self.log.debug("STT.run(): remote STT did not return")
            local_parent_conn.recv()
            if self.use_remote_stt and self.remote_proc.is_alive():
              self.remote_proc.kill()
              self.remote_proc.join(timeout=0.01)
            self.local_proc.join(timeout=0.01)

        # remove processed file
        if os.path.exists(self.wav_file):
          try:                  
            self.log.debug(f"STT.run(): removing file {self.wav_file}")
            os.remove(self.wav_file)
          except Exception as e:
            self.log.error(f"Error deleting wav file: {e}")
        else:
          self.log.debug(f"STT.run(): file {self.wav_file} already deleted or missing")
        self.wav_file = None

        # handle results
        if self.remote_return_dict or self.local_return_dict:
          self.log.debug(f"STT.run(): remote_return_dict: {self.remote_return_dict} local_return_dict: {self.local_return_dict}")
        if self.remote_return_dict:
          self.process_stt_result(self.remote_return_dict['text'])
        elif self.local_return_dict:       # only have a local result BUT we have a cache hit to use 
          if len(self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8")) > 0:
            remote_text = self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8")
            self.log.error(f"STT.run(): CACHE HIT!!! converted local: {self.local_return_dict['text']} remote: {remote_text}")
            self.process_stt_result(self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8"))
          else:
            self.process_stt_result(self.local_return_dict['text'])
        else:
          self.log.info("STT.run(): Can't produce STT from wav")
        if self.remote_return_dict and self.local_return_dict: # both responses create a new cache entry 
          self.log.error(f"STT.run(): new cache entry. local: {self.local_return_dict['text']} remote: {self.remote_return_dict['text']}")
          self.local2remote[ self.local_return_dict['text'] ] = self.remote_return_dict['text']
      time.sleep(0.025)

# main()
if __name__ == '__main__':
  stt_svc = STTSvc()
  stt_svc.run()
  Event().wait()                           # wait forever

