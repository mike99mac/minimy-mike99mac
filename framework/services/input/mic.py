import time
from datetime import datetime
import threading, collections, queue, os, os.path
import numpy as np
import pyaudio
import wave
import sys
import webrtcvad
from scipy import signal
from framework.util.utils import Config

# script to read from mic and save utterances in the directory base_dir/tmp/save_audio/ as .wav files
DEFAULT_SAMPLE_RATE = 16000
BARK = False

def log(msg):
  if BARK:
    print(msg)

class Audio(object):
  # Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from.
  FORMAT = pyaudio.paInt16
  RATE_PROCESS = 16000                     # Network/VAD rate-space
  CHANNELS = 1
  BLOCKS_PER_SECOND = 50

  def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS, file=None):
    def proxy_callback(in_data, frame_count, time_info, status):
      #pylint: disable=unused-argument
      if self.chunk is not None:
        in_data = self.wf.readframes(self.chunk)
      callback(in_data)
      return (None, pyaudio.paContinue)
    if callback is None: callback = lambda in_data: self.buffer_queue.put(in_data)
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

    self.stream = self.pa.open(**kwargs)
    self.stream.start_stream()

  def resample(self, data, input_rate):
    """
    Microphone may not support our native processing sampling rate, so
    resample from input_rate to RATE_PROCESS here for webrtcvad and
    deepspeech

    Args:
      data (binary): Input audio stream
      input_rate (int): Input audio rate to resample from
    """
    data16 = np.fromstring(string=data, dtype=np.int16)
    resample_size = int(len(data16) / self.input_rate * self.RATE_PROCESS)
    resample = signal.resample(data16, resample_size)
    resample16 = np.array(resample, dtype=np.int16)
    return resample16.tostring()

  def read_resampled(self):
    # Return a block of audio data resampled to 16000hz, blocking if necessary
    return self.resample(data=self.buffer_queue.get(),
               input_rate=self.input_rate)

  def read(self):
    # Return a block of audio data, blocking if necessary
    return self.buffer_queue.get()

  def destroy(self):
    self.stream.stop_stream()
    self.stream.close()
    self.pa.terminate()

  frame_duration_ms = property(lambda self: 1000 * self.block_size // self.sample_rate)

  def write_wav(self, filename, data):
    log("write wav %s" % (filename))
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
    super().__init__(device=device, input_rate=input_rate, file=file)
    self.vad = webrtcvad.Vad(aggressiveness)

  def frame_generator(self):
    # Generator that yields all audio frames from microphone
    if self.input_rate == self.RATE_PROCESS:
      while True:
        yield self.read()
    else:
      while True:
        yield self.read_resampled()

  def vad_collector(self, padding_ms=300, ratio=0.75, frames=None):
    # Generator that yields series of consecutive audio frames comprising each utterence, separated by yielding a single None.
    # Determines voice activity by ratio of frames in padding_ms.  Uses a buffer to include padding_ms prior to being triggered.
    # Example: (frame, ..., frame, None, frame, ..., frame, None, ...)
    #       |---utterence---|    |---utterence---|
    if frames is None: frames = self.frame_generator()
    num_padding_frames = padding_ms // self.frame_duration_ms
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    for frame in frames:
      if len(frame) < 640:
        return
      is_speech = self.vad.is_speech(frame, self.sample_rate)
      if not triggered:
        ring_buffer.append((frame, is_speech))
        num_voiced = len([f for f, speech in ring_buffer if speech])
        if num_voiced > ratio * ring_buffer.maxlen:
          triggered = True
          for f, s in ring_buffer:
            yield f
          ring_buffer.clear()
      else:
        yield frame
        ring_buffer.append((frame, is_speech))
        num_unvoiced = len([f for f, speech in ring_buffer if not speech])
        if num_unvoiced > ratio * ring_buffer.maxlen:
          triggered = False
          yield None
          ring_buffer.clear()

def main():
  # aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the
  # most aggressive. Default: 3
  # rate 16k, 44k, etc
  base_dir = os.getenv("SVA_BASE_DIR")
  tmp_file_path = base_dir + "/tmp/save_audio/"

  # for now, just grab device index from config file but really need to get all params or its unusable
  # need format, sample rate, etc. Mic should probably have its own cfg file
  cfg = Config()
  device_indx = cfg.get_cfg_val("Advanced.InputDeviceId")
  if device_indx == "":
    device_indx = None
  else:
    try:
      device_indx = int( device_indx )
    except:
      print("Invalid device index = %s, using None!" % (device_indx,))
      device_indx = None
  # general linux 
  # aggressiveness = 2
  # padding = 300
  # ratio = 0.95 # .75 and we split sentences with minor delay

  # mark2
  aggressiveness = 2
  padding = 500
  ratio = 0.5                              # .75 and we split sentences with minor delay
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
  frames = vad_audio.vad_collector(padding_ms=padding, ratio=ratio)
  wav_data = bytearray()                   # Stream from microphone to file
  for frame in frames:
    if frame is not None:
      wav_data.extend(frame)
    else:
      #log("end utterence")
      vad_audio.write_wav(os.path.join(tmp_file_path, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")), wav_data)
      wav_data = bytearray()

if __name__ == "__main__":
  main()

