from framework.util.utils import Config, LOG
from datetime import datetime
from scipy import signal
import numpy as np
import collections
import os
import os.path
import pyaudio
import queue 
import sys
import time
import wave
import webrtcvad

# script to read from mic and save utterances in the directory base_dir/tmp/save_audio/ as .wav files
DEFAULT_SAMPLE_RATE = 16000
BARK = False

  # def log(msg):
  # if BARK:
  #   print(msg)

class Audio(object):
  # Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from.
  FORMAT = pyaudio.paInt16
  RATE_PROCESS = 16000                     # Network/VAD rate-space
  CHANNELS = 1
  BLOCKS_PER_SECOND = 50

  def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS, file=None): 
    if callback is None:
      def default_callback(in_data, frame_count, time_info, status):
        #pylint: disable=unused-argument
        self.buffer_queue.put(in_data)
      callback = default_callback
    def proxy_callback(in_data, frame_count, time_info, status):
      if self.chunk is not None:
        in_data = self.wf.readframes(self.chunk)
      if callback is not None:
        callback(in_data, frame_count, time_info, status)
      return (None, pyaudio.paContinue)
    self.base_dir = str(os.getenv("SVA_BASE_DIR"))
    log_filename = self.base_dir + "/logs/audio.log"
    self.log = LOG(log_filename).log
    self.buffer_queue = queue.Queue()
    self.device = device
    self.input_rate = input_rate
    self.sample_rate = self.RATE_PROCESS
    self.block_size = int(self.RATE_PROCESS / float(self.BLOCKS_PER_SECOND))
    self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECOND))
    self.pa = pyaudio.PyAudio()
    kwargs = {"format": self.FORMAT,
              "channels": self.CHANNELS,
              "rate": self.input_rate,
              "input": True,
              "frames_per_buffer": self.block_size_input,
              "stream_callback": proxy_callback
             }
    self.chunk = None
    if self.device:                        # not default device
      kwargs["input_device_index"] = self.device
    elif file is not None:
      self.chunk = 320
      self.wf = wave.open(file, "rb")
    self.log.debug(f"Audio.__init__() kwargs: {kwargs}")
    self.stream = self.pa.open(**kwargs)
    self.stream.start_stream()

  def resample(self, data):
    # Microphone may not support our native processing sampling rate, so
    # resample from input_rate to RATE_PROCESS here for webrtcvad and deepspeech
    # Args:
    #   data (binary): Input audio stream
    #   input_rate (int): Input audio rate to resample from
    data16 = np.frombuffer(data, dtype=np.int16)
    resample_size = int(len(data16) / self.input_rate * self.RATE_PROCESS)
    resample = signal.resample(data16, resample_size)
    resample16 = np.array(resample, dtype=np.int16)
    return resample16.tobytes()

  def read_resampled(self):
    # Return a block of audio data resampled to 16000hz, blocking if necessary
    return self.resample(data=self.buffer_queue.get())

  def read(self):
    # Return a block of audio data, blocking if necessary
    return self.buffer_queue.get()

  def destroy(self):
    self.stream.stop_stream()
    self.stream.close()
    self.pa.terminate()

  frame_duration_ms = property(lambda self: 1000 * self.block_size // self.sample_rate)

  def write_wav(self, filename, data):
    self.log.debug(f"Audio.write_wav(): writing filename: {filename}")
    wf = wave.open(filename, "wb")
    wf.setnchannels(self.CHANNELS)
    # wf.setsampwidth(self.pa.get_sample_size(FORMAT))
    assert self.FORMAT == pyaudio.paInt16
    wf.setsampwidth(2)
    wf.setframerate(self.sample_rate)
    wf.writeframes(data)
    wf.close()

class VADAudio(Audio):
  # Filter & segment audio with voice activity detection

  def __init__(self, aggressiveness=3, device=None, input_rate=None, file=None):
    if input_rate is None:
      input_rate = self.RATE_PROCESS
    super().__init__(device=device, input_rate=input_rate, file=file)
    os.environ["ALSA_CARD"] = "0"          # prevent warning messages
    self.vad = webrtcvad.Vad(aggressiveness)

  def frame_generator(self):
    # Generator that yields all audio frames from microphone
    if self.input_rate == self.RATE_PROCESS:
      while True:
        yield self.read()
    else:
      while True:
        yield self.read_resampled()

  def vad_collector(self, padding_ms=300, ratio=0.75, frames=None, max_utterance_sec=4.0):
    # Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
    # Determines voice activity by ratio of frames in padding_ms.  Uses a buffer to include padding_ms prior to being triggered.
    # Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
    #       |---utterence---|    |---utterence---|
    if frames is None:
      frames = self.frame_generator()
    num_padding_frames = padding_ms // self.frame_duration_ms
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    assert ring_buffer.maxlen is not None
    triggered = False
    utterance_start_time = None
    collected_frames = []
    for frame in frames:
      if len(frame) < 640:
        continue
      is_speech = self.vad.is_speech(frame, self.sample_rate)
      if not triggered:
        ring_buffer.append((frame, is_speech))
        num_voiced = len([f for f, speech in ring_buffer if speech])
        if num_voiced > ratio * ring_buffer.maxlen:
          triggered = True
          utterance_start_time = time.time()
          for f, _ in ring_buffer:         # Yield buffered frames
            collected_frames.append(f)
          ring_buffer.clear()
      else:                                # Check if we've exceeded maximum utterance length
        if utterance_start_time and (time.time() - utterance_start_time) > max_utterance_sec:
          triggered = False                # End utterance
          if collected_frames:
            for f in collected_frames:
              yield f
            yield None
          collected_frames = []
          ring_buffer.clear()
          continue
        collected_frames.append(frame)
        ring_buffer.append((frame, is_speech))
        num_unvoiced = len([f for f, speech in ring_buffer if not speech])
        if num_unvoiced > ratio * ring_buffer.maxlen:
          triggered = False
          for f in collected_frames:
            yield f
          yield None
          collected_frames = []
          ring_buffer.clear()
    if collected_frames:                   # Handle any remaining frames
      for f in collected_frames:
        yield f
      yield None

def main():
  # aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the
  # most aggressive. Default: 3
  # rate 16k, 44k, etc
  base_dir = os.getenv("SVA_BASE_DIR")
  if base_dir is None:
    print("ERROR: SVA_BASE_DIR environment variable not set!")
    sys.exit(1)
  tmp_file_path = base_dir + "/tmp/save_audio/"

  # for now, just grab device index from config file but really need to get all params or its unusable
  # need format, sample rate, etc. Mic should probably have its own cfg file
  cfg = Config()
  device_indx = cfg.get_cfg_val("Advanced.InputDeviceId")
  if device_indx == "":
    device_indx = None
  else:
    try:
      device_indx = int(str(device_indx))
    except Exception:
      print("Invalid device index = %s, using None!" % (device_indx,))
      device_indx = None
  # general linux 
  # aggressiveness = 2
  # padding = 300
  # ratio = 0.95 
  aggressiveness = 3                       # Previously 2
  padding = 300                            # Previously 500
  ratio = 0.85                             # Previously 0.5, want higher confidence level # .75 and we split sentences with minor delay
  max_utterance_sec = 4.0                  # Maximum 4 second utterance, modify if necessary
  try:                                     # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=aggressiveness,
             device=device_indx,
             input_rate=DEFAULT_SAMPLE_RATE,
             file=None)
  except Exception as e:
    print("\nError - Mic Not Started!\n\n%s\n\nAborting!" % (e,))
    sys.exit(-1)
  print("Using device index %s, aggressive:%s, padding:%s, ratio:%s" % (device_indx,aggressiveness, padding, ratio))
  print("Listening (ctrl-C to exit)...")
  frames = vad_audio.vad_collector(
    padding_ms = padding,
    ratio = ratio,
    max_utterance_sec = max_utterance_sec
  )
  wav_data = bytearray()                   # Stream from microphone to file
  for frame in frames:
    if frame is not None:
      wav_data.extend(frame)
    else:
      if len(wav_data) > 0:
        # Calculate duration in seconds
        # Bytes / (2 bytes per sample * sample rate)
        duration_sec = len(wav_data) / (2 * DEFAULT_SAMPLE_RATE)
        if 0.3 <= duration_sec <= max_utterance_sec:
          filename = os.path.join(
            tmp_file_path,
            datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")
          )
          vad_audio.write_wav(filename, wav_data)
        else:
          base_dir = str(os.getenv("SVA_BASE_DIR"))
          log_filename = base_dir + "/logs/audio.log"
          log = LOG(log_filename).log
          log.debug(f"Discarded utterance: {duration_sec:.2f}s (outside 0.3 - {max_utterance_sec}s range)")
      wav_data = bytearray()
  if len(wav_data) > 0:                    # Handle any remaining data
    duration_sec = len(wav_data) / (2 * DEFAULT_SAMPLE_RATE)
    if 0.3 <= duration_sec <= max_utterance_sec:
      filename = os.path.join(
        tmp_file_path,
        datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")
      )
      vad_audio.write_wav(filename, wav_data)

if __name__ == "__main__":
  main()
