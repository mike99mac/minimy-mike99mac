"""Minimy skill for starting and pairing a local librespot receiver.

librespot is the Spotify Connect receiver. Spotify playback selection is
performed by a Spotify controller; this skill manages the receiver process and
reports its state without storing Spotify credentials in Minimy.
"""

import os
import signal
import subprocess
from pathlib import Path
from threading import Event

from skills.sva_base import SimpleVoiceAssistant


class SpotifySkill(SimpleVoiceAssistant):
    """Manage a headless librespot receiver named ``Minimy``."""

    def __init__(self, bus=None, timeout=5):
        self.skill_id = "spotify_skill"
        super().__init__(
            msg_handler=self.handle_message,
            skill_id=self.skill_id,
            skill_category="user",
            bus=bus,
            timeout=timeout,
        )

        self.process = None
        self.librespot = os.environ.get("LIBRESPOT_BIN", "/home/pi/.cargo/bin/librespot")
        self.cache_dir = Path(
            os.environ.get(
                "LIBRESPOT_CACHE",
                str(Path.home() / ".cache" / "librespot"),
            )
        ).expanduser()
        self.device_name = os.environ.get("LIBRESPOT_NAME", "Minimy")
        self.log_path = Path(
            os.environ.get("SVA_BASE_DIR", str(Path.home() / "minimy"))
        ) / "logs" / "spotify.log"

        self.register_intent("C", ["start", "launch", "open"], "spotify", self.start)
        self.register_intent("C", ["stop", "quit", "close"], "spotify", self.stop)
        self.register_intent("C", "pair", "spotify", self.pair)
        self.register_intent("Q", "what", "spotify", self.status)

        self.log.info(
            "SpotifySkill ready: binary=%s cache=%s device=%s",
            self.librespot,
            self.cache_dir,
            self.device_name,
        )

    def _running(self):
        return self.process is not None and self.process.poll() is None

    def _command(self, device_auth=False):
        command = [
            self.librespot,
            "--name",
            self.device_name,
            "--cache",
            str(self.cache_dir),
        ]
        if device_auth:
            command.append("--enable-device-auth")
        return command

    def _start_process(self, device_auth=False):
        if self._running():
            return True

        if not Path(self.librespot).exists() and not self._which(self.librespot):
            self.log.error("librespot executable not found: %s", self.librespot)
            return False

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = self.log_path.open("a", encoding="utf-8")
        try:
            self.process = subprocess.Popen(
                self._command(device_auth),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError:
            log_file.close()
            self.process = None
            raise
        finally:
            log_file.close()
        return True

    def _which(self, command):
        if os.path.dirname(command):
            return os.access(command, os.X_OK)
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(directory) / command
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return True
        return False

    def start(self, msg=None):
        try:
            if self._start_process():
                self.speak(f"Spotify Connect receiver {self.device_name} is running.")
            else:
                self.speak("I could not find librespot.")
        except Exception as exc:
            self.log.error("Could not start librespot: %s", exc, exc_info=True)
            self.speak("I could not start Spotify.")

    def pair(self, msg=None):
        """Start device authorization for a headless Pi."""
        if self._running():
            self.speak("Spotify is already running. Stop it before pairing again.")
            return
        try:
            self._start_process(device_auth=True)
            self.speak(
                "Spotify pairing has started. Open the pairing URL shown in the Spotify log."
            )
        except Exception as exc:
            self.log.error("Could not start Spotify pairing: %s", exc, exc_info=True)
            self.speak("I could not start Spotify pairing.")

    def stop(self, msg=None):
        if not self._running():
            self.speak("Spotify is not running.")
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=5)
            self.speak("Spotify has stopped.")
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.speak("Spotify was stopped.")
        except Exception as exc:
            self.log.error("Could not stop librespot: %s", exc, exc_info=True)
            self.speak("I could not stop Spotify.")
        finally:
            self.process = None

    def status(self, msg=None):
        if self._running():
            self.speak(f"Spotify Connect receiver {self.device_name} is running.")
        else:
            self.speak(f"Spotify Connect receiver {self.device_name} is stopped.")

    def handle_message(self, msg):
        self.log.debug("SpotifySkill.handle_message(): %s", msg)


if __name__ == "__main__":
    SpotifySkill()
    Event().wait()
