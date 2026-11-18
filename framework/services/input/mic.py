from framework.util.utils import LOG
from datetime import datetime
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
DEFAULT_SAMPLE_RATE = 48000  # Updated to match the reSpeaker 48kHz firmware rate

class Audio(object):
  # Streams raw audio from microphone. Data is received in a separate thread and stored in a buffer to be read from.
  FORMAT = pyaudio.paInt16
  RATE_PROCESS = 48000                     # Network/VAD/Playback sync rate-space
  CHANNELS = 1                             # logical output channels (mono)
  CAPTURE_CHANNELS = 2                     # will be adjusted dynamically by probe
  CHANNEL_INDEX = 1                        # set at runtime by _probe_channels()
  BLOCKS_PER_SECTION = 50

  def __init__(self, callback=None, input_rate=RATE_PROCESS):
    if callback is None:
      def default_callback(in_data, frame_count, time_info, status):
        self.buffer_queue.put(self._extract_channel(in_data))
      callback = default_callback
    def proxy_callback(in_data, frame_count, time_info, status):
      if callback is not None:
        callback(in_data, frame_count, time_info, status)
      return (None, pyaudio.paContinue)
    self.base_dir = str(os.getenv("SVA_BASE_DIR"))
    log_filename = self.base_dir + "/logs/audio.log"
    self.log = LOG(log_filename).log
    self.buffer_queue = queue.Queue()
    
    self.pa = pyaudio.PyAudio()
    self._probe_device_caps(input_rate)

    self.block_size = int(self.sample_rate / float(self.BLOCKS_PER_SECTION))
    self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECTION))

    kwargs = {"format": self.FORMAT,
              "channels": self.CAPTURE_CHANNELS,
              "rate": self.input_rate,
              "input": True,
              "frames_per_buffer": self.block_size_input,
              "stream_callback": proxy_callback
             }
    self.log.debug(f"Audio.__init__() kwargs: {kwargs}")
    self.stream = self.pa.open(**kwargs)
    self.stream.start_stream()

  def _probe_device_caps(self, requested_rate):
    # Dynamically inspect default input device to support both 2-ch reSpeaker and 1-ch headsets plug-and-play
    self.input_rate = requested_rate
    self.sample_rate = requested_rate
    try:
      default_info = self.pa.get_default_input_device_info()
      max_channels = int(default_info.get("maxInputChannels", 1))
      dev_name = default_info.get("name", "")
      self.log.debug(f"Audio._probe_device_caps(): device='{dev_name}', maxInputChannels={max_channels}")
      
      if "reSpeaker" in dev_name or max_channels >= 2:
        self.CAPTURE_CHANNELS = 2
        env_idx = os.getenv("SVA_MIC_CHANNEL")
        if env_idx is not None and env_idx.strip().lstrip("-").isdigit():
          idx = int(env_idx)
          self.CHANNEL_INDEX = None if idx < 0 else idx
        else:
          self.CHANNEL_INDEX = 1  # ReSpeaker ASR-optimized channel
      else:
        self.CAPTURE_CHANNELS = 1
        self.CHANNEL_INDEX = 0
    except Exception as e:
      self.log.debug(f"Audio._probe_device_caps() error querying device: {e}. Falling back to mono.")
      self.CAPTURE_CHANNELS = 1
      self.CHANNEL_INDEX = 0

  def _extract_channel(self, interleaved_bytes):
    if self.CAPTURE_CHANNELS == 1:
      return interleaved_bytes
    samples = np.frombuffer(interleaved_bytes, dtype=np.int16)
    channels = samples.reshape(-1, self.CAPTURE_CHANNELS)
    if self.CHANNEL_INDEX is None:
      return channels.mean(axis=1).astype(np.int16).tobytes()
    return channels[:, self.CHANNEL_INDEX].tobytes()

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
  def __init__(self, aggressiveness=3, input_rate=None):
    if input_rate is None:
      input_rate = self.RATE_PROCESS
    super().__init__(input_rate=input_rate)
    self.vad = webrtcvad.Vad(aggressiveness)

  def frame_generator(self):
    while True:
      yield self.read()

  def vad_collector(self, padding_ms=300, ratio=0.75, frames=None, max_utterance_sec=10.0):
    if frames is None:
      frames = self.frame_generator()
    num_padding_frames = padding_ms // self.frame_duration_ms
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    utterance_start_time = None
    collected_frames = []
    for frame in frames:
      # webrtcvad requires 10, 20, or 30 ms frames at 8k, 16k, 32k, or 48k
      min_frame_bytes = int(self.sample_rate * 0.01 * 2) # 10ms frame size in bytes
      if len(frame) < min_frame_bytes:
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
                         input_rate=DEFAULT_SAMPLE_RATE)
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
        duration_sec = len(wav_data) / (2 * vad_audio.sample_rate)
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
    duration_sec = len(wav_data) / (2 * vad_audio.sample_rate)
    if 0.3 <= duration_sec <= max_utterance_sec:
      filename = os.path.join(tmp_file_path, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav"))
      vad_audio.write_wav(filename, wav_data)

if __name__ == "__main__":
  main()
