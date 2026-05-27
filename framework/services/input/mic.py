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

class Audio(object):
  # Streams raw audio from microphone. Data is received in a separate thread, and stored in a buffer, to be read from.
  FORMAT = pyaudio.paInt16
  RATE_PROCESS = 16000                     # Network/VAD rate-space
  CHANNELS = 1
  BLOCKS_PER_SECOND = 50

  def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS, file=None): 
    if callback is None:
      def default_callback(in_data, frame_count, time_info, status):
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
    if self.device is not None:
      kwargs["input_device_index"] = self.device
    elif file is not None:
      self.chunk = 320
      self.wf = wave.open(file, "rb")
    self.log.debug(f"Audio.__init__() kwargs: {kwargs}")
    self.stream = self.pa.open(**kwargs)
    self.stream.start_stream()

  def resample(self, data):
    data16 = np.frombuffer(data, dtype=np.int16)
    resample_size = int(len(data16) / self.input_rate * self.RATE_PROCESS)
    resample = signal.resample(data16, resample_size)
    resample16 = np.array(resample, dtype=np.int16)
    return resample16.tobytes()

  def read_resampled(self):
    return self.resample(data=self.buffer_queue.get())

  def read(self):
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
    assert self.FORMAT == pyaudio.paInt16
    wf.setsampwidth(2)
    wf.setframerate(self.sample_rate)
    wf.writeframes(data)
    wf.close()

class VADAudio(Audio):
  def __init__(self, aggressiveness=3, device=None, input_rate=None, file=None):
    if input_rate is None:
      input_rate = self.RATE_PROCESS
    super().__init__(device=device, input_rate=input_rate, file=file)
    self.vad = webrtcvad.Vad(aggressiveness)

  def frame_generator(self):
    if self.input_rate == self.RATE_PROCESS:
      while True:
        yield self.read()
    else:
      while True:
        yield self.read_resampled()

  def vad_collector(self, padding_ms=300, ratio=0.75, frames=None, max_utterance_sec=4.0):
    if frames is None:
      frames = self.frame_generator()
    num_padding_frames = padding_ms // self.frame_duration_ms
    ring_buffer = collections.deque(maxlen=num_padding_frames)
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
          for f, _ in ring_buffer:
            collected_frames.append(f)
          ring_buffer.clear()
      else:
        if utterance_start_time and (time.time() - utterance_start_time) > max_utterance_sec:
          triggered = False
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
    if collected_frames:
      for f in collected_frames:
        yield f
      yield None

def main():
  base_dir = os.getenv("SVA_BASE_DIR")
  if base_dir is None:
    print("mic.py.main() ERROR: SVA_BASE_DIR environment variable not set!")
    sys.exit(1)
  tmp_file_path = base_dir + "/tmp/save_audio/"
  log_filename = base_dir + "/logs/audio.log"
  log = LOG(log_filename).log

  # Always use the system default input device (managed by PipeWire).
  # The default source should be set via PipeWire (pactl set-default-source).
  device_indx = None
  print("mic.py.main() Using system default input (PipeWire pulse device)")

  aggressiveness = 3
  padding = 300
  ratio = 0.85
  max_utterance_sec = 4.0

  # Suppress stderr ALSA warnings
  saved_stderr = os.dup(2)
  devnull = os.open(os.devnull, os.O_WRONLY)
  os.dup2(devnull, 2)
  os.close(devnull)

  try:
    vad_audio = VADAudio(aggressiveness=aggressiveness,
                         device=device_indx,
                         input_rate=DEFAULT_SAMPLE_RATE,
                         file=None)
  except Exception as e:
    os.dup2(saved_stderr, 2)
    os.close(saved_stderr)
    print("\nError - Mic Not Started!\n\n%s\n\nAborting!" % (e,))
    sys.exit(-1)

  os.dup2(saved_stderr, 2)
  os.close(saved_stderr)

  print("mic.py.main() aggressive:%s, padding:%s, ratio:%s" % (aggressiveness, padding, ratio))
  print("mic.py.main() Listening (ctrl-C to exit)...")

  frames = vad_audio.vad_collector(padding_ms=padding, ratio=ratio, max_utterance_sec=max_utterance_sec)
  wav_data = bytearray()
  for frame in frames:
    if frame is not None:
      wav_data.extend(frame)
    else:
      if len(wav_data) > 0:
        duration_sec = len(wav_data) / (2 * DEFAULT_SAMPLE_RATE)
        if 0.3 <= duration_sec <= max_utterance_sec:
          filename = os.path.join(
            tmp_file_path,
            datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")
          )
          vad_audio.write_wav(filename, wav_data)
        else:
          log.debug(f"mic.py.main() Discarded utterance: {duration_sec:.2f}s")
      wav_data = bytearray()
  if len(wav_data) > 0:
    duration_sec = len(wav_data) / (2 * DEFAULT_SAMPLE_RATE)
    if 0.3 <= duration_sec <= max_utterance_sec:
      filename = os.path.join(tmp_file_path, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav"))
      vad_audio.write_wav(filename, wav_data)

if __name__ == "__main__":
  main()
