from bus.MsgBus import MsgBus
from datetime import datetime
import dbm
from framework.util.utils import LOG, Config, aplay, get_wake_words
import glob 
from google.cloud import speech
import io
import json
import multiprocessing
import os
from subprocess import Popen, PIPE, STDOUT
import sys
import time

REMOTE_TIMEOUT = 3
LOCAL_TIMEOUT = 5

def execute_command(command):
  p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
  stdout, stderr = p.communicate()
  stdout = str( stdout.decode('utf-8') )
  stderr = str( stderr.decode('utf-8') )
  return stdout, stderr

def _local_transcribe_file(wav_filename, return_dict):
  start_time = time.time()
  cmd = 'curl http://localhost:5002/stt -H "Content-Type: audio/wav" --data-binary @"%s"' % (wav_filename,)
  out, err = execute_command(cmd)
  res = out.strip()
  if res != '':
    return_dict['service'] = 'local'
    return_dict['text'] = res

def _remote_transcribe_file(speech_file, return_dict):
  start_time = time.time()
  client = speech.SpeechClient()
  with io.open(speech_file, "rb") as audio_file:
    content = audio_file.read()
  audio = speech.RecognitionAudio(content=content)
  config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="en-US",
  )
  response = client.recognize(config=config, audio=audio)
  for result in response.results:
    return_dict['service'] = 'goog'
    return_dict['text'] = result.alternatives[0].transcript
    break

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
  """
  Monitor the wav file input directory and convert wav files to text strings in files in the output directory. we stitch so if
  someone says 'wake word' brief silence, 'bla bla' we stitch them together before intent matching. this produces two broad 
  categories of input; raw and wake word qualified. these become "raw" and "utterance"
  """
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
    base_dir = os.getenv('SVA_BASE_DIR')
    log_filename = base_dir + '/logs/stt.log'
    self.log = LOG(log_filename).log
    self.waiting_stt = False
    self.manager = multiprocessing.Manager()
    self.goog_return_dict = self.manager.dict()
    self.local_return_dict = self.manager.dict()
    self.goog_proc = None
    self.local_proc = None
    self.bark = True
    self.bark = False
    self.previous_utterance = ''
    self.previous_utt_was_ww = False
    self.wav_file = None
    self.mute_start_time = 0
    self.wws = get_wake_words()

    # hard wire wake words - TODO - fix -MM
    self.wws = ["computer", "hey boombox"] 
    base_dir = os.getenv('SVA_BASE_DIR')
    self.beep_loc = "%s/framework/assets/what.wav" % (base_dir,)
    cfg = Config()
    self.use_remote_stt = True
    remote_stt = cfg.get_cfg_val('Advanced.STT.UseRemote')
    self.log.info(f"STTSvc.__init__() use_remote_stt: {self.use_remote_stt} wws: {self.wws}")
    if remote_stt and remote_stt == 'n':
      self.use_remote_stt = False
    if self.bark:
      self.log.info(f"STT:Remote=%s, wake word(s)=%s" % (self.use_remote_stt, self.wws))
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
    # we want the wake word but if we don't have it maybe
    # it was the previous utterance so handle that too.
    try:                                 # parse nested JSON string
      parsed_text = json.loads(utt)
      utt = parsed_text.get("text", "").strip()
    except json.JSONDecodeError as e:
      self.log.error(f"STT.process_stt_result(): failed to parse local STT result: {e}")
      utt = ""
    self.log.info(f"STT.process_stt_result() utt: {utt}")
    if utt:
      utt = utt.strip()
      wake_word = ''
      for ww in self.wws:
        if utt.lower().find(ww.lower()) > -1:
          wake_word = ww
          break
      if wake_word == '':      # ww not found in utt
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
        else:            # ww not found and previous utt not ww => raw statement
          handle_utt('', utt, self.tmp_file_path)
        self.previous_utt_was_ww = False
      else:              # otherwise utt contains ww
        if len(utt) == len(wake_word): # it is just the wake word
          self.previous_utterance = utt.lower()
          self.previous_utt_was_ww = True
          #os.system(self.beep_cmd)
          aplay(self.beep_loc)
          if not self.muted:
            self.muted = True
            self.send_mute()
            self.mute_start_time = time.time()
        else:            # utt contains the wake word and more
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
    self.log.debug(f"STT.run() use_remote_stt: {self.use_remote_stt}")
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

      # get all wav files in the input directory
      mylist = sorted( [f for f in glob.glob(self.tmp_file_path + "save_audio/*.wav")] )

      # if we have at least one
      if len(mylist) > 0:      # take the first
        loop_ctr = 0
        self.wav_file = mylist[0]
        # TODO reject files too small and maybe too large!
        file_size = os.path.getsize(self.wav_file)
        self.log.debug(f"STT.run() wav_file: {self.wav_file} file_size: {file_size}")
        utt = ''                           # convert it to text
        self.waiting_stt = True
        if self.use_remote_stt:            # remote stt with failover
          self.goog_return_dict = self.manager.dict()
          self.local_return_dict = self.manager.dict()
          self.goog_proc = multiprocessing.Process(target=_remote_transcribe_file, args=(self.wav_file, self.goog_return_dict))
          self.goog_proc.start()
          self.local_proc = multiprocessing.Process(target=_local_transcribe_file, args=(self.wav_file, self.local_return_dict))
          self.local_proc.start()
          self.goog_proc.join(REMOTE_TIMEOUT)
          if self.goog_proc:
            self.goog_proc.kill()
          self.local_proc.join(2)
          if self.local_proc:
            self.local_proc.kill()
        else:                              # local stt
          self.local_return_dict = self.manager.dict()
          self.local_proc = multiprocessing.Process(target=_local_transcribe_file, args=(self.wav_file, self.local_return_dict))
          self.local_proc.start()
          self.local_proc.join(LOCAL_TIMEOUT)
          if self.local_proc:
            self.local_proc.kill()
        try:                               # to remove input file
          os.remove(self.wav_file)
        except:
          pass
        self.wav_file = None
        self.log.debug(f"STT.run(): goog_return_dict: {self.goog_return_dict} local_return_dict: {self.local_return_dict}")
        if self.goog_return_dict:
          self.process_stt_result(self.goog_return_dict['text'])
        elif self.local_return_dict:       # only have a local result BUT we have a cache hit to use 
          if len( self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8") ) > 0:
            self.log.error("STT.run() CACHE HIT!!! converted local=%s  to remote=%s" % (self.local_return_dict['text'], self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8")))
            self.process_stt_result(self.local2remote.get(self.local_return_dict['text'], b'').decode("utf-8"))
          else:
            self.process_stt_result(self.local_return_dict['text'])
        else:
          self.log.info("STT.run() Can't produce STT from wav")
        if self.goog_return_dict and self.local_return_dict: # both responses create a new cache entry 
          self.log.error("STT new cache entry. local=%s, remote=%s" % (self.local_return_dict['text'], self.goog_return_dict['text']))
          self.local2remote[ self.local_return_dict['text'] ] = self.goog_return_dict['text']
      time.sleep(0.025)

# main()
if __name__ == '__main__':
  stt_svc = STTSvc()
  stt_svc.run()
  Event().wait()                           # wait forever

