"""The Textual App: a 4-pane layout for testing minimy without a
mic/speaker. Type utterances, see the conversation, watch toggleable
live logs.

    ┌──────────────────────────────────────────┐
    │ Sources/Levels checkboxes (compact, one   │
    │ line each) - directly visible, no modal   │
    ├───────────────────────────┬───────────────┤
    │ Conversation (2/3 width)  │ Activity (1/3) │
    │ (auto-scrolls to bottom)  │                │
    ├───────────────────────────┴───────────────┤
    │ Input (bottom) - Up/Down browses history   │
    └──────────────────────────────────────────┘
"""
import argparse
import sys
from collections import deque
from pathlib import Path
from functools import partial

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Label

from debug_tui.bus import MinimyBusConnection
from debug_tui.logs import (
    find_log_dir, discover_log_sources, line_matches_filter, strip_log_prefix,
    extract_log_level, KNOWN_LOG_LEVELS,
)

LOG_POLL_INTERVAL = 0.5  # seconds
LOG_BUFFER_SIZE = 5000  # lines kept in memory

LOG_SOURCE_COLORS = {
    "minimy": "cyan", "bus": "bright_black", "skills": "green",
    "audio": "yellow", "voice": "cyan", "other": "white",
}
DEFAULT_LOG_COLOR = "white"


def format_log_line(source_name: str, line: str) -> str:
    """Colors a log line by its source, bolding it if it contains 'ERROR'."""
    clean_line = strip_log_prefix(line)
    color = LOG_SOURCE_COLORS.get(source_name, DEFAULT_LOG_COLOR)
    text = f"[{color}][{source_name}][/{color}] {clean_line}"
    if "ERROR" in clean_line:
        text = f"[bold]{text}[/bold]"
    return text


class MinimyDebugApp(App):
    CSS = """
    #logs-container {
        height: 45%;
        border: solid $accent;
    }
    #log-filter {
        height: 1;
        border: none;
    }
    #middle-row {
        height: 1fr;
    }
    #conversation {
        width: 2fr;
        border: solid $accent;
    }
    #activity {
        width: 1fr;
        border: solid $accent;
    }
    #utterance-input {
        dock: bottom;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("f5", "focus_logs", "Logs"),
        ("f6", "focus_conversation", "Conversation"),
        ("f7", "focus_activity", "Activity"),
        ("f8", "focus_input", "Input"),
    ]

    def __init__(self, host="127.0.0.1", port=8181, lang="en-us", log_dir_override=None):
        super().__init__()
        self.host = host
        self.port = port
        self.is_local = host in ("127.0.0.1", "localhost", "::1")
        self.bus = MinimyBusConnection(host=host, port=port, lang=lang)
        self.log_dir = find_log_dir(override=log_dir_override, is_local=self.is_local)
        self.log_sources = discover_log_sources(self.log_dir)
        self.utterance_history = []
        self.history_index = None
        self.log_buffer = deque(maxlen=LOG_BUFFER_SIZE)
        self.log_filter_text = ""
        self.level_enabled = {level: True for level in KNOWN_LOG_LEVELS}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="logs-container"):
            log_filter = Input(placeholder="Filter logs (free text)...", id="log-filter")
            yield log_filter
            logs_view = RichLog(id="logs-view", wrap=False, markup=True, auto_scroll=True)
            yield logs_view
        with Horizontal(id="middle-row"):
            conversation = RichLog(id="conversation", wrap=True, markup=True, auto_scroll=True)
            yield conversation
            activity = RichLog(id="activity", wrap=True, markup=True, auto_scroll=True)
            yield activity
        utterance_input = Input(placeholder="Type what you'd say to minimy...", id="utterance-input", select_on_focus=False)
        yield utterance_input
        yield Footer()

    def on_mount(self) -> None:
        self._write_status("Minimy Debug TUI v0.1.0")
        
        if not self.log_sources:
            self._write_to_log(self.query_one("#logs-view", RichLog),
                f"[yellow]No log files found. Pass --log-dir to point to the right one.[/yellow]")
        else:
            names = ", ".join(src.name for src in self.log_sources)
            self._write_status(f"Logs found: {names}")

        self.bus.on_speak(self._handle_speak)
        self.bus.on_activity(self._handle_activity)
        self.bus.connect()

        self.set_interval(LOG_POLL_INTERVAL, self._poll_logs)
        self.query_one("#utterance-input", Input).focus()
        self._write_status("Ready.")

    def _write_to_log(self, widget: RichLog, content) -> None:
        widget.auto_scroll = widget.is_vertical_scroll_end
        widget.write(content)

    def _handle_speak(self, utterance: str) -> None:
        self.call_from_thread(self._write_conversation, f"[blue]Minimy: {utterance}[/blue]")

    def _handle_activity(self, line: str) -> None:
        self.call_from_thread(self._write_activity, line)

    def _write_conversation(self, line: str) -> None:
        try:
            widget = self.query_one("#conversation", RichLog)
            self._write_to_log(widget, line)
        except:
            pass

    def _write_activity(self, line: str) -> None:
        try:
            widget = self.query_one("#activity", RichLog)
            self._write_to_log(widget, line)
        except:
            pass

    def _write_status(self, text: str) -> None:
        self._write_conversation(f"[dim]{text}[/dim]")

    def _poll_logs(self) -> None:
        try:
            view = self.query_one("#logs-view", RichLog)
        except:
            return
        for src in self.log_sources:
            new_lines = src.read_new_lines()
            for line in new_lines:
                self.log_buffer.append((src.name, line))
                if line_matches_filter(line, self.log_filter_text):
                    self._write_to_log(view, format_log_line(src.name, line))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "log-filter":
            return
        self.log_filter_text = event.value
        self._rerender_logs()

    def _rerender_logs(self) -> None:
        try:
            view = self.query_one("#logs-view", RichLog)
        except:
            return
        view.auto_scroll = True
        view.clear()
        for source_name, line in self.log_buffer:
            if line_matches_filter(line, self.log_filter_text):
                view.write(format_log_line(source_name, line))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "utterance-input":
            return
        text = event.value.strip()
        if not text:
            return
        self._send_utterance(text)
        event.input.value = ""

    def _send_utterance(self, text: str) -> None:
        self._write_conversation(f"[green]You: {text}[/green]")
        self.bus.send_utterance(text)
        self.utterance_history.append(text)
        self.history_index = None
        self.query_one("#utterance-input", Input).focus()

    def action_focus_logs(self) -> None:
        self.query_one("#logs-view", RichLog).focus()

    def action_focus_conversation(self) -> None:
        self.query_one("#conversation", RichLog).focus()

    def action_focus_activity(self) -> None:
        self.query_one("#activity", RichLog).focus()

    def action_focus_input(self) -> None:
        self.query_one("#utterance-input", Input).focus()

    def on_key(self, event) -> None:
        input_widget = self.query_one("#utterance-input", Input)
        if self.focused is not input_widget:
            return
        if event.key == "up":
            self._navigate_history(-1)
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            self._navigate_history(1)
            event.prevent_default()
            event.stop()

    def _navigate_history(self, direction: int) -> None:
        if not self.utterance_history:
            return
        input_widget = self.query_one("#utterance-input", Input)
        if self.history_index is None:
            self.history_index = len(self.utterance_history)
        new_index = self.history_index + direction
        if new_index < 0:
            new_index = 0
        elif new_index >= len(self.utterance_history):
            self.history_index = None
            input_widget.value = ""
            input_widget.cursor_position = 0
            return
        self.history_index = new_index
        input_widget.value = self.utterance_history[new_index]
        input_widget.cursor_position = len(input_widget.value)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="A split-pane terminal UI for testing minimy")
    parser.add_argument("--host", default="127.0.0.1", help="messagebus host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8181, help="messagebus port (default: 8181)")
    parser.add_argument("--lang", default="en-us", help="BCP-47 language code (default: en-us)")
    parser.add_argument("--log-dir", default=None, help="override log directory auto-detection")
    return parser


def run():
    args = build_arg_parser().parse_args()
    app = MinimyDebugApp(host=args.host, port=args.port, lang=args.lang, log_dir_override=args.log_dir)
    app.run()


if __name__ == "__main__":
    run()
