"""Minimy skill for managing a local go-librespot receiver.

Reads its settings from Minimy's ``install/config.yml`` (read-only) and
launches go-librespot with command-line overrides. go-librespot manages its
own ``state.json`` (including Spotify credentials) inside ``StateDir``;
Minimy never reads or writes that file, and it never writes to
``install/config.yml``.
"""

import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Event

import yaml

from skills.sva_base import SimpleVoiceAssistant


DEFAULTS = {
    "Bin": "go-librespot",
    "Name": "Minimy",
    "ApiPort": 3678,
    "CacheDir": "~/.cache/go-librespot",
    "StateDir": "~/.config/go-librespot",
}


def _find_section(cfg, name):
    if isinstance(cfg, list):
        for item in cfg:
            if isinstance(item, dict) and name in item:
                return item[name]
        return None
    if isinstance(cfg, dict):
        return cfg.get(name)
    return None


class SpotifySkill(SimpleVoiceAssistant):
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
        self.base_dir = Path(
            os.environ.get("SVA_BASE_DIR", str(Path.home() / "minimy"))
        ).expanduser()
        self.config_path = Path(
            os.environ.get(
                "SVA_CONFIG", str(self.base_dir / "install" / "config.yml")
            )
        ).expanduser()
        self.log_path = self.base_dir / "logs" / "spotify.log"

        self._load_settings()

        self.register_intent("C", ["start", "launch", "open"], "spotify", self.start)
        self.register_intent("C", ["stop", "quit", "close"], "spotify", self.stop)
        self.register_intent("C", "pair", "spotify", self.pair)
        self.register_intent("Q", "what", "spotify", self.status)

        self.log.info(
            "SpotifySkill ready: bin=%s name=%s api_port=%s state_dir=%s paired=%s",
            self.golibrespot,
            self.device_name,
            self.api_port,
            self.state_dir,
            self._is_paired(),
        )

    def _load_settings(self):
        stored = {}
        if self.config_path.exists():
            try:
                cfg = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
                basic = _find_section(cfg, "Basic")
                if isinstance(basic, dict):
                    spotify = basic.get("Spotify")
                    if isinstance(spotify, dict):
                        stored = dict(spotify)
            except Exception as exc:
                self.log.error(
                    "Could not read %s: %s", self.config_path, exc, exc_info=True
                )

        merged = {**DEFAULTS, **stored}
        self.golibrespot = merged["Bin"]
        self.device_name = merged["Name"]
        self.api_port = int(merged["ApiPort"])
        self.cache_dir = Path(merged["CacheDir"]).expanduser()
        self.state_dir = Path(merged["StateDir"]).expanduser()

    def _is_paired(self):
        return (self.state_dir / "state.json").exists()

    def _running(self):
        return self.process is not None and self.process.poll() is None

    def _which(self, command):
        if os.path.dirname(command):
            return os.access(command, os.X_OK)
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(directory) / command
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return True
        return False

    def _start_process(self):
        if self._running():
            return True

        if not Path(self.golibrespot).exists() and not self._which(self.golibrespot):
            self.log.error("go-librespot executable not found: %s", self.golibrespot)
            return False

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.golibrespot,
            "-c", f"device_name={self.device_name}",
            "-c", f"server_port={self.api_port}",
            "-c", f"cache_dir={self.cache_dir}",
            "-config_dir", str(self.state_dir),
        ]

        log_file = self.log_path.open("a", encoding="utf-8")
        try:
            self.process = subprocess.Popen(
                cmd,
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

    def start(self, msg=None):
        try:
            if not self._start_process():
                self.speak("I could not find go-librespot.")
                return
            if self._is_paired():
                self.speak(f"Spotify Connect receiver {self.device_name} is running.")
            else:
                self.speak(
                    f"Spotify Connect receiver {self.device_name} is running, "
                    "but it is not paired yet. Say 'pair Spotify' to pair it."
                )
        except Exception as exc:
            self.log.error("Could not start go-librespot: %s", exc, exc_info=True)
            self.speak("I could not start Spotify.")

    def pair(self, msg=None):
        if self._running() and self._is_paired():
            self.speak("Spotify is already paired and running.")
            return

        try:
            self._start_process()
        except Exception as exc:
            self.log.error(
                "Could not start go-librespot for pairing: %s", exc, exc_info=True
            )
            self.speak("I could not start Spotify pairing.")
            return

        code_info = self._fetch_auth_code(timeout=20)
        if code_info:
            code = code_info.get("user_code") or code_info.get("code") or "unknown"
            url = (
                code_info.get("verification_uri")
                or code_info.get("verification_url")
                or "spotify.com/pair"
            )
            self.speak(
                f"To pair Spotify, open {url} in a browser and enter the code {code}."
            )
        else:
            self.speak(
                "Spotify pairing has started, but I could not read the pairing code. "
                "Check the Spotify log file."
            )

    def _fetch_auth_code(self, timeout=20):
        endpoint = f"http://localhost:{self.api_port}/auth/code"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(endpoint, timeout=2) as resp:
                    if resp.status == 200:
                        return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.URLError, json.JSONDecodeError, OSError):
                pass
            time.sleep(0.5)
        return None

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
            self.log.error("Could not stop go-librespot: %s", exc, exc_info=True)
            self.speak("I could not stop Spotify.")
        finally:
            self.process = None

    def status(self, msg=None):
        if not self._running():
            self.speak(f"Spotify Connect receiver {self.device_name} is stopped.")
        elif self._is_paired():
            self.speak(f"Spotify Connect receiver {self.device_name} is running.")
        else:
            self.speak(
                f"Spotify Connect receiver {self.device_name} is running but not paired."
            )

    def handle_message(self, msg):
        self.log.debug("SpotifySkill.handle_message(): %s", msg)


if __name__ == "__main__":
    SpotifySkill()
    Event().wait()
