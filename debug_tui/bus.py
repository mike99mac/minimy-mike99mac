"""Wraps minimy bus client for the TUI's needs: sending an utterance,
and a callback-based interface for incoming events - decoupled from
Textual itself so this module has no UI framework dependency and can
be tested without spinning up a real App."""
import threading
import uuid

try:
    from ovos_bus_client import MessageBusClient, Message
except ImportError:
    # Fallback for minimy's own bus implementation
    MessageBusClient = None
    Message = None

from debug_tui.activity import summarize_message


class MinimyBusConnection:
    def __init__(self, host="127.0.0.1", port=8181, lang="en-us", client=None):
        """Connect to minimy's message bus.
        `client` is injectable for testing - defaults to a real
        MessageBusClient against (host, port)."""
        self.lang = lang
        if client:
            self._client = client
        elif MessageBusClient:
            self._client = MessageBusClient(host=host, port=port)
        else:
            self._client = None
        self._speak_handlers = []
        self._activity_handlers = []

    def connect(self):
        if not self._client:
            return
        try:
            self._client.on("speak", self._on_speak)
            self._client.on("message", self._on_raw_message)
            self._client.run_in_thread()
        except Exception as e:
            print(f"Failed to connect to bus: {e}")

    def _on_speak(self, message):
        if hasattr(message, 'data'):
            utterance = message.data.get("utterance", "")
        else:
            utterance = message.get("utterance", "")
        for handler in self._speak_handlers:
            handler(utterance)

    def _on_raw_message(self, raw):
        """Handle raw message from bus."""
        try:
            if isinstance(raw, str) and Message:
                message = Message.deserialize(raw)
            else:
                message = raw
            self._on_any_message(message)
        except Exception:
            return

    def _on_any_message(self, message):
        """Routes every bus message through the activity summarizer."""
        if hasattr(message, 'msg_type'):
            msg_type = message.msg_type
            msg_data = message.data if hasattr(message, 'data') else {}
        else:
            msg_type = message.get("type", "")
            msg_data = message
        
        line = summarize_message(msg_type, msg_data)
        if line is None:
            return
        for handler in self._activity_handlers:
            handler(line)

    def on_speak(self, handler):
        """Registers a callback(utterance: str) called whenever minimy
        speaks. Multiple handlers can be registered."""
        self._speak_handlers.append(handler)

    def on_activity(self, handler):
        """Registers a callback(summary_line: str) called for every
        bus message the activity summarizer considers worth showing."""
        self._activity_handlers.append(handler)

    def send_utterance(self, text):
        """Sends an utterance to the minimy engine."""
        if not self._client or not Message:
            return
        try:
            self._client.emit(Message("recognizer_loop:utterance", {
                "utterances": [text],
                "lang": self.lang,
                "utterance_id": str(uuid.uuid4()),
            }))
        except Exception as e:
            print(f"Failed to send utterance: {e}")
