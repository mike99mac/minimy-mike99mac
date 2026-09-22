"""Log discovery and tailing for the minimy debug TUI client.

Primary discovery is via configured log paths. Falls back to a guessed
CANDIDATE_LOG_DIRS list only when that's unavailable.
"""
from pathlib import Path
from dataclasses import dataclass, field
import re

# Candidate log directories for minimy
CANDIDATE_LOG_DIRS = [
    "~/.local/state/minimy",
    "~/.cache/minimy/log",
    "/var/log/minimy",
    "./logs",
]

# Known minimy service log filenames (without .log suffix)
KNOWN_LOG_NAMES = [
    "minimy", "bus", "skills", "audio", "voice", "other",
]


@dataclass
class LogSource:
    """A single tailable log file with a toggleable INCLUDE-filter
    state. Checked by default."""
    name: str
    path: Path
    enabled: bool = True
    _offset: int = field(default=0, repr=False)

    def read_new_lines(self):
        """Returns any lines appended since the last call. Handles the
        file being truncated/rotated."""
        if not self.path.exists():
            return []
        size = self.path.stat().st_size
        if size < self._offset:
            self._offset = 0  # file was rotated/truncated
        try:
            with open(self.path, "r", errors="replace") as f:
                f.seek(self._offset)
                new_data = f.read()
                self._offset = f.tell()
            if not new_data:
                return []
            return [line for line in new_data.splitlines() if line.strip()]
        except Exception:
            return []


def find_log_dir(override=None, is_local=True):
    """Returns the first directory that actually contains at least one
    recognized *.log file, or None if none do."""
    if override:
        return Path(override).expanduser()

    for candidate in CANDIDATE_LOG_DIRS:
        path = Path(candidate).expanduser()
        if not path.is_dir():
            continue
        if any((path / f"{name}.log").exists() for name in KNOWN_LOG_NAMES):
            return path
    return None


def discover_log_sources(log_dir, names=None):
    """Builds a LogSource for every name whose <name>.log file actually
    exists in log_dir."""
    if log_dir is None:
        return []
    sources = []
    for name in (names if names is not None else KNOWN_LOG_NAMES):
        path = log_dir / f"{name}.log"
        if path.exists():
            sources.append(LogSource(name=name, path=path, _offset=path.stat().st_size))
    return sources


def line_matches_filter(line: str, filter_text: str) -> bool:
    """Case-insensitive free-text substring match."""
    if not filter_text:
        return True
    return filter_text.lower() in line.lower()


KNOWN_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Standard log prefix pattern
_LOG_PREFIX_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\s*-\s*[^-]+\s*-\s*"
)


def strip_log_prefix(line: str) -> str:
    """Removes the leading 'TIMESTAMP - COMPONENT - ' prefix if present."""
    return _LOG_PREFIX_RE.sub("", line, count=1)


_LOG_LEVEL_RE = re.compile(r"-\s*(" + "|".join(KNOWN_LOG_LEVELS) + r")\s*-")


def extract_log_level(line: str):
    """Returns the log level (e.g. 'ERROR') found in a line, or None."""
    match = _LOG_LEVEL_RE.search(line)
    return match.group(1) if match else None


_SKILL_ID_RE = re.compile(r"skill_id['\"]?\s*[:=]\s*['\"]?([\w.\-]+)['\"]?")


def extract_skill_id(line: str):
    """Returns a skill_id substring found in a line's text, or None."""
    match = _SKILL_ID_RE.search(line)
    return match.group(1) if match else None
