#!/usr/bin/env python3
import argparse
import io
import os
import wave
from pathlib import Path

import numpy as np
from quart import Quart, request

from stt import Model

_DIR = Path(__file__).parent
_ENV = dict(os.environ)

# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--model-dir", required=True, help="Path to model directory")
args = parser.parse_args()

model_dir = Path(args.model_dir)
model_path = next(model_dir.glob("*.tflite"))
scorer_path = next(model_dir.glob("*.scorer"))

# -----------------------------------------------------------------------------

app = Quart(__name__)

model = Model(str(model_path))
model.enableExternalScorer(str(scorer_path))

# From MODEL_CARD file
model.setScorerAlphaBeta(0.49506138236732433, 0.11939819449850608)


# -----------------------------------------------------------------------------


@app.route("/stt", methods=["GET", "POST"])
async def api_stt():
    wav_bytes = await request.data
    with io.BytesIO(wav_bytes) as wav_io:
        with wave.open(wav_io, "rb") as wav_file:
            audio_bytes = wav_file.readframes(wav_file.getnframes())
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

    text = model.stt(audio_array)
    print(text)

    return text


@app.route("/stream", methods=["GET", "POST"])
async def api_stream():
    model_stream = model.createStream()

    async for chunk in request.body:
        chunk_array = np.frombuffer(chunk, dtype=np.int16)
        model_stream.feedAudioContent(chunk_array)

    text = model_stream.finishStream()
    return text


app.run(debug=True, host="0.0.0.0", port=5002)
