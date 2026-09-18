"""Connect the debug TUI to Minimy's input pipeline.

The main Minimy services in this repository do not consume an OVOS
``recognizer_loop:utterance`` websocket event. The STT service writes text
files to ``tmp/save_text`` and the intent service polls that directory. The
TUI therefore uses the same file-queue contract for locally running Minimy.
"""
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from debug_tui.activity import summarize_message


class MinimyBusConnection:
    def __init__(self, host="127.0.0.1", port=8181, lang="en-us", client=None,
                 input_dir=None):
        """Connect the TUI to Minimy's input pipeline.

        ``client`` is retained for compatibility and for tests. The current
        Minimy intent service consumes ``tmp/save_text/*.txt`` rather than an
        OVOS websocket event, so local utterances are queued there directly.
        """
        self.host = host
        self.port = port
        self.lang = lang
        self._client = client
        self.input_dir = Path(input_dir or self._default_input_dir())
        self._speak_handlers = []
        self._activity_handlers = []

    @staticmethod
    def _default_input_dir():
        base_dir = os.environ.get("SVA_BASE_DIR")
        if base_dir:
            return Path(base_dir) / "tmp" / "save_text"
        return Path.home() / "minimy" / "tmp" / "save_text"

    def connect(self):
        """Start the optional client used for receiving activity/speak events."""
        if not self._client:
            return
        try:
            self._client.on("speak", self._on_speak)
            self._client.on("message", self._on_raw_message)
            self._client.run_in_thread()
        except Exception as e:
            print(f"Failed to connect to bus: {e}")

    def _on_speak(self, message):
        if hasattr(message, "data"):
            utterance = message.data.get("utterance", "")
        else:
            utterance = message.get("utterance", "")
        for handler in self._speak_handlers:
            handler(utterance)

    def _on_raw_message(self, raw):
        """Handle raw message from an optional client."""
        try:
            if isinstance(raw, str):
                return
            self._on_any_message(raw)
        except Exception:
            return

    def _on_any_message(self, message):
        """Routes every bus message through the activity summarizer."""
        if hasattr(message, "msg_type"):
            msg_type = message.msg_type
            msg_data = message.data if hasattr(message, "data") else {}
        else:
            msg_type = message.get("type", "")
            msg_data = message

        line = summarize_message(msg_type, msg_data)
        if line is None:
            return
        for handler in self._activity_handlers:
            handler(line)

    def on_speak(self, handler):
        self._speak_handlers.append(handler)

    def on_activity(self, handler):
        self._activity_handlers.append(handler)

    def send_utterance(self, text):
        """Queue text exactly as STT does so ``Intent.run`` parses it.

        ``Intent.run`` polls ``SVA_BASE_DIR/tmp/save_text`` and expects a
        header followed by the utterance. ``[TUI]`` is deliberately a
        non-RAW header: RAW input is routed to the system skill and never
        enters question parsing.
        """
        text = text.strip()
        if not text:
            return

        self.input_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            f"savetxt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}_"
            f"{uuid.uuid4().hex}.txt"
        )
        # Write and rename atomically so Intent.run never reads a partial file.
        fd, temp_name = tempfile.mkstemp(prefix=".tui-", dir=self.input_dir,
                                         text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(f"[TUI]{text}")
            os.replace(temp_name, self.input_dir / filename)
        except Exception as e:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            print(f"Failed to queue utterance: {e}")
            return

        for handler in self._activity_handlers:
            handler(f'→ queued: "{text}"')
