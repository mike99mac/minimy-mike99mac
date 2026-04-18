#!/usr/bin/env python3
import json
import os
import socket
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from framework.util.utils import Config

try:
    from huggingface_hub import hf_hub_download
    from huggingface_hub import try_to_load_from_cache
except ImportError:
    hf_hub_download = None
    try_to_load_from_cache = None


def _log(message):
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"{timestamp} {message}", flush=True)


def _read_lockfile(lock_path):
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def _pid_is_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def acquire_lock(lock_path, repo_id, filename):
    existing = _read_lockfile(lock_path)
    if existing and _pid_is_alive(existing.get("pid")):
        _log(
            "LLM cache download already running "
            f"(pid={existing.get('pid')}, repo={existing.get('repo_id')}, file={existing.get('filename')})",
        )
        return False

    if existing:
        _log(
            "LLM cache lock existed but the recorded worker was no longer alive; "
            "removing stale lock"
        )
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

    payload = {
        "pid": os.getpid(),
        "repo_id": repo_id,
        "filename": filename,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)

    _log(
        f"Acquired LLM cache lock at {lock_path} "
        f"(pid={payload['pid']}, repo={repo_id}, file={filename})"
    )
    return True


def release_lock(lock_path):
    try:
        os.remove(lock_path)
        _log(f"Released LLM cache lock at {lock_path}")
    except FileNotFoundError:
        pass


def resolve_cached_path(repo_id, filename):
    if try_to_load_from_cache is not None:
        cached_path = try_to_load_from_cache(repo_id=repo_id, filename=filename)
        if isinstance(cached_path, str) and os.path.exists(cached_path):
            return cached_path

    if hf_hub_download is None:
        return None

    try:
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_files_only=True,
        )
        if isinstance(cached_path, str) and os.path.exists(cached_path):
            return cached_path
    except Exception:
        return None

    return None


def should_cache_local_llm(cfg):
    use_remote = cfg.get_cfg_val("Basic.LLM.UseRemote") == "y"
    return (not use_remote) or cfg.is_hub()


def main():
    cfg = Config()
    base_dir = cfg.get_cfg_val("Basic.BaseDir") or os.getcwd()
    tmp_dir = os.path.join(base_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    lock_path = os.path.join(tmp_dir, "llm_download.lock")

    if hf_hub_download is None:
        _log("huggingface_hub is not installed; cannot cache LLM model")
        return 1

    if not should_cache_local_llm(cfg):
        _log("LLM cache not required on this node; skipping")
        return 0

    repo_id = str(cfg.get_cfg_val("Basic.LLMRepo") or "").strip()
    filename = str(cfg.get_cfg_val("Basic.LLMFile") or "").strip()
    if not repo_id or not filename:
        _log("LLMRepo or LLMFile is missing in mmconfig.yml; skipping")
        return 1

    cached_path = resolve_cached_path(repo_id, filename)
    if isinstance(cached_path, str) and os.path.exists(cached_path):
        _log(f"LLM model already cached at {cached_path}")
        return 0

    if not acquire_lock(lock_path, repo_id, filename):
        return 0

    try:
        _log(
            f"Downloading LLM model {repo_id} ({filename}) on host {socket.gethostname()}"
        )
        cached_path = hf_hub_download(repo_id=repo_id, filename=filename)
        _log(f"LLM model cached at {cached_path}")
        return 0
    except Exception as exc:
        _log(f"LLM model download failed: {exc}")
        return 1
    finally:
        release_lock(lock_path)


if __name__ == "__main__":
    sys.exit(main())
