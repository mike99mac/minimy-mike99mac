import io
import os
import select
import subprocess
import threading
import time
import wave

import requests
from quart import Quart, request, Response

from framework.util.utils import Config, LOG

base_dir = os.getenv("SVA_BASE_DIR", os.path.expanduser("~/minimy"))
log_filename = os.path.join(base_dir, "logs/piper.log")
log = LOG(log_filename).log

# Original MIT piper binary + model (installed by installminimy)
PIPER_BIN = os.path.join(base_dir, "framework/services/tts/local/piper/piper")
MODEL_PATH = os.path.join(
    base_dir,
    "framework/services/tts/local/piper/en_US-hfc_male-medium.onnx",
)
SAMPLE_RATE = 22050
SILENCE_GAP = 0.5           # seconds of quiet = end of utterance
MAX_UTTERANCE_SEC = 30.0    # safety cap


# -------------------------------------------------
# Client interface — imported by se_tts_session.py.
# -------------------------------------------------
def local_speak_dialog(text, _file_name, wait_q):
    log.info(f"Session TTS request: {text[:50]}...")
    try:
        resp = requests.post(
            "http://localhost:5004/tts",
            json={"text": text},
            timeout=30.0,
        )
        if resp.status_code != 200:
            log.error(f"TTS server returned {resp.status_code}")
            wait_q.put({'service': 'local', 'status': 'error',
                        'msg': f"Server error {resp.status_code}"})
            return
        temp_wav = "/tmp/speech.wav"
        with open(temp_wav, "wb") as f:
            f.write(resp.content)
        subprocess.run(["aplay", temp_wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(temp_wav)
        log.info("Session TTS via server succeeded")
        wait_q.put({'service': 'local', 'status': 'success'})
    except requests.exceptions.ConnectionError:
        log.error("Session TTS: Piper server not running – start piper.service")
        wait_q.put({'service': 'local', 'status': 'error',
                    'msg': 'Server not running'})
    except Exception as e:
        log.error(f"Session TTS error: {e}")
        wait_q.put({'service': 'local', 'status': 'error', 'msg': str(e)})


# ------------------------------------------------------------------------
# Server interface - only runs when this file is executed by piper.service
# ------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config as HyperConfig

    app = Quart(__name__)

    _piper_proc = None
    _piper_lock = threading.Lock()

    def _start_piper():
        global _piper_proc
        log.info(f"Starting persistent piper: {PIPER_BIN}")
        _piper_proc = subprocess.Popen(
            [PIPER_BIN, "--model", MODEL_PATH, "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        # Warmup: forces model + espeak-ng init. Discard PCM.
        _piper_proc.stdin.write(b"a\n")
        _piper_proc.stdin.flush()
        _drain(15.0)
        log.info("Piper warmup complete")

    def _drain(timeout):
        deadline = time.time() + timeout
        last = time.time()
        while time.time() < deadline:
            r, _, _ = select.select([_piper_proc.stdout], [], [], 0.05)
            if r:
                chunk = _piper_proc.stdout.read1(8192)
                if chunk:
                    last = time.time()
            elif time.time() - last > SILENCE_GAP:
                return

    def _read_utterance():
        buf = bytearray()
        start = time.time()
        last = time.time()
        while time.time() - start < MAX_UTTERANCE_SEC:
            r, _, _ = select.select([_piper_proc.stdout], [], [], 0.05)
            if r:
                chunk = _piper_proc.stdout.read1(8192)
                if chunk:
                    buf.extend(chunk)
                    last = time.time()
            elif buf and (time.time() - last) > SILENCE_GAP:
                break
        return bytes(buf)

    _start_piper()

    @app.route("/tts", methods=["POST"])
    async def tts():
        data = await request.get_json()
        text = data.get("text", "")
        if not text:
            return {"error": "Missing 'text' field"}, 400
        log.info(f"Synthesizing: {text[:50]}...")
        with _piper_lock:
            if _piper_proc.poll() is not None:
                _start_piper()
            _piper_proc.stdin.write((text + "\n").encode("utf-8"))
            _piper_proc.stdin.flush()
            pcm = _read_utterance()
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)
        log.info("Synthesis complete")
        return Response(wav_io.getvalue(), mimetype="audio/wav")

    @app.route("/health", methods=["GET"])
    async def health():
        return {"status": "ok", "piper_alive": _piper_proc.poll() is None}

    config = HyperConfig()
    config.bind = ["0.0.0.0:5004"]
    config.use_reloader = False
    config.debug = False
    config.accesslog = None
    config.errorlog = None
    asyncio.run(serve(app, config))
