from framework.util.utils import LOG
from datetime import datetime
import numpy as np
import collections
import os
import os.path
import sys

# Suppress noisy ALSA C-level error spam before importing pyaudio
import ctypes
try:
  asound = ctypes.CDLL('libasound.so.2')
  @ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
  def _alsa_error_handler(filename, line, function, err, fmt):
    pass
  asound.snd_lib_error_set_handler(_alsa_error_handler)
except Exception:
  pass

import pyaudio
import queue
import threading
import time
import wave
import webrtcvad

HARDWARE_SAMPLE_RATE = 48000
PROCESSING_SAMPLE_RATE = 16000

class Audio(object):
  FORMAT = pyaudio.paInt16
  CHANNELS = 1
  CAPTURE_CHANNELS = 2
  CHANNEL_INDEX = 0                        # Channel 0 is the active reSpeaker AEC feed
  BLOCKS_PER_SECOND = 50

  def __init__(self, input_rate=HARDWARE_SAMPLE_RATE):
    self.base_dir = str(os.getenv("SVA_BASE_DIR"))
    log_filename = self.base_dir + "/logs/audio.log"
    self.log = LOG(log_filename).log
    self.buffer_queue = queue.Queue()

    self.input_rate = input_rate
    self.sample_rate = PROCESSING_SAMPLE_RATE

    self.block_size = int(PROCESSING_SAMPLE_RATE / float(self.BLOCKS_PER_SECOND))
    self.block_size_input = int(self.input_rate / float(self.BLOCKS_PER_SECOND))

    self.pa = pyaudio.PyAudio()
    self._find_hardware_device()

    kwargs = {
      "format": self.FORMAT,
      "channels": self.CAPTURE_CHANNELS,
      "rate": self.input_rate,
      "input": True,
      "input_device_index": self.input_device_index,
      "frames_per_buffer": self.block_size_input
    }
    self.log.debug(f"Audio.__init__() opening direct stream with kwargs: {kwargs}")
    self.stream = self.pa.open(**kwargs)
    self.stream.start_stream()

    self._is_running = True
    self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
    self._capture_thread.start()

  def _find_hardware_device(self):
    target_index = None
    max_channels = 2

    for i in range(self.pa.get_device_count()):
      try:
        dev_info = self.pa.get_device_info_by_index(i)
        name = dev_info.get('name', '')
        in_channels = int(dev_info.get('maxInputChannels', 0))

        if in_channels > 0 and ('hw:' in name or 'respeaker' in name.lower()) and in_channels <= 8:
          if 'respeaker' in name.lower() or target_index is None:
            target_index = i
            max_channels = in_channels
            self.log.info(f"Selected physical audio device: {name} at index {i} with {in_channels} channels")
            if 'respeaker' in name.lower():
              break
      except Exception:
        continue

    if target_index is None:
      target_index = 0
      self.log.warning("No explicit hardware tag matched. Defaulting to device index 0.")

    self.input_device_index = target_index
    self.CAPTURE_CHANNELS = max_channels

    if self.CAPTURE_CHANNELS >= 2:
      self.CHANNEL_INDEX = 0
      self.log.info(f"Multi-channel array detected. Extracting active channel index: {self.CHANNEL_INDEX}")
    else:
      self.CHANNEL_INDEX = None
      self.log.info("Single-channel device detected. Passing mono stream through.")

  def _capture_loop(self):
    self.log.debug("Audio._capture_loop() started.")
    while self._is_running:
      try:
        data = self.stream.read(self.block_size_input, exception_on_overflow=False)
        processed = self._extract_and_resample(data)
        self.buffer_queue.put(processed)
      except Exception as e:
        self.log.error(f"Audio._capture_loop() error: {e}")
        time.sleep(0.01)

  def _extract_and_resample(self, interleaved_bytes):
    samples = np.frombuffer(interleaved_bytes, dtype=np.int16)

    if self.CAPTURE_CHANNELS > 1:
      channels = samples.reshape(-1, self.CAPTURE_CHANNELS)
      if self.CHANNEL_INDEX is None:
        samples = channels.mean(axis=1).astype(np.int16)
      else:
        idx = min(self.CHANNEL_INDEX, self.CAPTURE_CHANNELS - 1)
        samples = channels[:, idx]

    if self.input_rate == 48000:
      float_samples = samples.astype(np.float32)
      kernel = np.ones(3, dtype=np.float32) / 3.0
      filtered = np.convolve(float_samples, kernel, mode="same")
      samples = np.clip(filtered[::3], -32768, 32767).astype(np.int16)

    return samples.tobytes()

  def read(self):
    return self.buffer_queue.get()

  def destroy(self):
    self._is_running = False
    if self.stream.is_active():
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
  def __init__(self, aggressiveness=3, input_rate=None, min_rms=500):
    if input_rate is None:
      input_rate = HARDWARE_SAMPLE_RATE
    super().__init__(input_rate=input_rate)
    self.vad = webrtcvad.Vad(aggressiveness)
    self.min_rms = min_rms

  def _is_loud_enough(self, frame):
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
      return False
    rms = np.sqrt(np.mean(samples ** 2))
    return rms >= self.min_rms

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
      min_frame_bytes = int(self.sample_rate * 0.01 * 2)
      if len(frame) < min_frame_bytes:
        continue
      is_speech = self._is_loud_enough(frame) and self.vad.is_speech(frame, self.sample_rate)
      if not triggered:
        ring_buffer.append((frame, is_speech))
        num_voiced = len([f for f, speech in ring_buffer if speech])
        if num_voiced > ratio * ring_buffer.maxlen:
          triggered = True
          utterance_start_time = time.time()
          self.log.debug("VAD TRIGGERED: Speech detected, starting utterance collection.")
          for f, _ in ring_buffer:
            collected_frames.append(f)
          ring_buffer.clear()
      else:
        if utterance_start_time and (time.time() - utterance_start_time) > max_utterance_sec:
          triggered = False
          self.log.debug(f"VAD TIMEOUT: Max utterance duration reached, yielding {len(collected_frames)} frames.")
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
          self.log.debug(f"VAD END: Speech ended, yielding {len(collected_frames)} frames.")
          for f in collected_frames:
            yield f
          yield None
          collected_frames = []
          ring_buffer.clear()
    if collected_frames:
      self.log.debug(f"VAD EOF: Yielding remaining {len(collected_frames)} frames.")
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

  print("mic.py.main() Initialized with Channel 0 AEC extraction and software gain boost")

  aggressiveness = 3
  padding = 300
  ratio = 0.85
  max_utterance_sec = 4.0
  min_rms = 500

  try:
    vad_audio = VADAudio(aggressiveness=aggressiveness,
                         input_rate=HARDWARE_SAMPLE_RATE,
                         min_rms=min_rms)
  except Exception as e:
    print(f"\nError - Mic Not Started!\n\n{e}\n\nAborting!")
    sys.exit(-1)

  print(f"mic.py.main() aggressive:{aggressiveness}, padding:{padding}, ratio:{ratio}, min_rms:{min_rms}")
  print("mic.py.main() Listening (ctrl-C to exit)...")

  frames = vad_audio.vad_collector(padding_ms=padding, ratio=ratio, max_utterance_sec=max_utterance_sec)
  wav_data = bytearray()
  for frame in frames:
    if frame is not None:
      wav_data.extend(frame)
    else:
      if len(wav_data) > 0:
        duration_sec = len(wav_data) / (2 * PROCESSING_SAMPLE_RATE)
        if 0.3 <= duration_sec <= max_utterance_sec:
          filename = os.path.join(
            tmp_file_path,
            datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav")
          )
          vad_audio.write_wav(filename, wav_data)
          log.info(f"SAVED UTTERANCE WAV: {filename} (duration: {duration_sec:.2f}s)")
        else:
          log.debug(f"mic.py.main() Discarded utterance: {duration_sec:.2f}s")
      wav_data = bytearray()
  if len(wav_data) > 0:
    duration_sec = len(wav_data) / (2 * PROCESSING_SAMPLE_RATE)
    if 0.3 <= duration_sec <= max_utterance_sec:
      filename = os.path.join(tmp_file_path, datetime.now().strftime("savewav_%Y-%m-%d_%H-%M-%S_%f.wav"))
      vad_audio.write_wav(filename, wav_data)
      log.info(f"SAVED UTTERANCE WAV: {filename} (duration: {duration_sec:.2f}s)")

if __name__ == "__main__":
  main()
