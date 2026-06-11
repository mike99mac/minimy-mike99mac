import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from threading import Lock
from urllib import request as urlrequest
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from framework.util.utils import LOG, Config

try:
  from huggingface_hub import hf_hub_download, try_to_load_from_cache
  import llama_cpp
  from llama_cpp import Llama
except ImportError:
  hf_hub_download = try_to_load_from_cache = llama_cpp = Llama = None

try:
  from llama_cpp import _internals as llama_internals
except ImportError:
  llama_internals = None

try:
  from quart import Quart, request as quart_request
except ImportError:
  Quart = quart_request = None

# Log to fallback.log
base_dir = os.getenv('SVA_BASE_DIR')
if base_dir is None:
  base_dir = os.path.expanduser('~/minimy')
log_file = os.path.join(base_dir, 'logs', 'fallback.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)
log = LOG(log_file).log


class FallbackLLMService:
  REMOTE_PORT = 5003
  REMOTE_TIMEOUT = 15

  def __init__(self):
    self.cfg = Config()
    self.llm = None
    self.rewrite_origins = {}
    self.capability_manifest = self._build_capability_manifest()
    self.controller_prompt = self._build_controller_prompt()
    self.answer_prompt = self._build_answer_prompt()
    self.processing_lock = Lock()
    self._patch_llama_cleanup_bug()

    self.llm_repo = str(self.cfg.get_cfg_val("Basic.LLMRepo") or "").strip()
    self.llm_file = str(self.cfg.get_cfg_val("Basic.LLMFile") or "").strip()
    base_dir = self.cfg.get_cfg_val("Basic.BaseDir") or "."
    self.llm_fallback_log = os.path.join(base_dir, "logs", "llm_fallback.log")
    self.llm_fallback_lock = os.path.join(base_dir, "tmp", "fallback_llm.lock")

    use_remote = str(self.cfg.get_cfg_val("Basic.LLM.UseRemote") or "n").strip().lower()
    if use_remote == 'y':
      self.mode = "client"
      self.remote_host = self.cfg.get_cfg_val("Basic.Hub") or "localhost"
      self.remote_port = self.REMOTE_PORT
    else:
      self.mode = "server"
      self.remote_host = None
      self.remote_port = None
    self._loading_failed = False

    log.info(f"FallbackLLMService: mode={self.mode}, LLM repo={self.llm_repo}, file={self.llm_file}")
    self._ensure_llm_ready()
    self._setup_remote_server()

  @contextmanager
  def _timed(self, label):
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000
    log.info(f"TIMING {label}: {elapsed:.1f} ms")

  def _patch_llama_cleanup_bug(self):
    model_cls = getattr(llama_internals, "LlamaModel", None)
    if model_cls is None or getattr(model_cls, "_minimy_cleanup_patch", False):
      return
    original_close = getattr(model_cls, "close", None)
    if not callable(original_close):
      return

    def safe_close(instance):
      try:
        return original_close(instance)
      except AttributeError as e:
        if "sampler" not in str(e):
          raise
        for attr_name in ("sampler", "context", "batch", "model", "vocab"):
          resource = getattr(instance, attr_name, None)
          if resource is None:
            continue
          close_fn = getattr(resource, "close", None)
          if callable(close_fn):
            try:
              close_fn()
            except Exception:
              pass
          try:
            setattr(instance, attr_name, None)
          except Exception:
            pass

    model_cls.close = safe_close
    model_cls._minimy_cleanup_patch = True

  def _get_num_threads(self):
    # If GPU is available (n_gpu_layers > 0), use fewer CPU threads
    if getattr(self, '_gpu_enabled', False):
      return max(1, os.cpu_count() // 4)   # Lighter on CPU when GPU does the work
    else:
      return max(1, os.cpu_count() // 2)   # More threads for CPU‑only inference

  def _create_llm(self, model_path):
    llm_kwargs = {
      "model_path": model_path,
      "n_ctx": 2048,
      "n_batch": 512,
      "temperature": 0.0,                  # deterministic
      "do_sample": False,                  # no random sampling
      "verbose": False
    }

    # Default to CPU mode, then probe for GPU
    self._gpu_enabled = False
    gpu_probe = getattr(llama_cpp, "llama_supports_gpu_offload", None)
    if callable(gpu_probe):
      try:
        if gpu_probe():
          llm_kwargs["n_gpu_layers"] = -1
          self._gpu_enabled = True
          log.info("FallbackLLMService._create_llm(): GPU offload available, enabling llama.cpp CUDA with n_gpu_layers=-1")
        else:
          log.info("FallbackLLMService_create_llm(): llama.cpp GPU offload not available, using CPU")
      except Exception as e:
        log.warning(f"FallbackLLMService._create_llm(): GPU capability probe failed, using CPU fallback: {e}")
    else:
      log.info("FallbackLLMService._create_llm(): llama.cpp GPU capability probe unavailable, using CPU fallback")

    # Set number of CPU threads dynamically
    llm_kwargs["n_threads"] = self._get_num_threads()
    log.info(f"Using {llm_kwargs['n_threads']} CPU threads")

    return Llama(**llm_kwargs)

  def _resolve_cached_model_path(self):
    log.debug(f"Resolving cached LLM path repo: {self.llm_repo} file: {self.llm_file}")
    if not self.llm_repo or not self.llm_file or hf_hub_download is None:
      return None
    if try_to_load_from_cache is not None:
      cached_path = try_to_load_from_cache(repo_id=self.llm_repo, filename=self.llm_file)
      if isinstance(cached_path, str) and os.path.exists(cached_path):
        log.info(f"Found cached model at {cached_path}")
        return cached_path
    try:
      cached_path = hf_hub_download(repo_id=self.llm_repo, filename=self.llm_file, local_files_only=True)
      if isinstance(cached_path, str) and os.path.exists(cached_path):
        return cached_path
    except Exception:
      pass
    return None

  def _launch_model_prefetch(self):
    helper_path = os.path.join(self.cfg.get_cfg_val("Basic.BaseDir") or ".", "install", "cache_llm.py")
    if not os.path.exists(helper_path):
      log.error(f"Missing LLM cache helper at {helper_path}")
      return False
    os.makedirs(os.path.dirname(self.llm_fallback_log), exist_ok=True)
    env = os.environ.copy()
    env["SVA_BASE_DIR"] = self.cfg.get_cfg_val("Basic.BaseDir") or "."
    try:
      log.info("Launching background LLM cache worker")
      with open(self.llm_fallback_log, "a", encoding="utf-8") as log_handle:
        subprocess.Popen(
          [sys.executable, helper_path],
          stdout=log_handle,
          stderr=subprocess.STDOUT,
          cwd=self.cfg.get_cfg_val("Basic.BaseDir") or ".",
          env=env,
          start_new_session=True,
          close_fds=True,
        )
      return True
    except Exception as e:
      log.error(f"Failed to start LLM cache worker: {e}")
      return False

  def _read_fallback_lock(self):
    try:
      with open(self.llm_fallback_lock, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return None

  def _is_pid_alive(self, pid):
    if not pid:
      return False
    try:
      os.kill(int(pid), 0)
      return True
    except Exception:
      return False

  def _ensure_model_download_requested(self):
    if os.path.exists(self.llm_fallback_lock):
      lock_info = self._read_fallback_lock()
      if lock_info:
        pid = lock_info.get("pid")
        if self._is_pid_alive(pid):
          return True
      try:
        os.remove(self.llm_fallback_lock)
      except FileNotFoundError:
        pass
    return self._launch_model_prefetch()

  def _ensure_llm_ready(self):
    if self.llm is not None:
      return True
    if not self.llm_repo or not self.llm_file:
      log.error("LLM configuration missing")
      return False
    model_path = self._resolve_cached_model_path()
    if model_path:
      try:
        self.llm = self._create_llm(model_path)
        from llama_cpp.llama_cache import LlamaRAMCache
        cache = LlamaRAMCache(capacity_bytes=268435456) # 256 MB
        self.llm.set_cache(cache)
        self._loading_failed = False       # reset on success
        return True
      except Exception as e:
        log.error(f"Failed to load cached Llama model: {e}")
        self._loading_failed = True        # remember that loading failed
        return False
    if not self._loading_failed:           # Model file not found
      self._ensure_model_download_requested()
    return False

  def _llm_unavailable_answer(self):
    if not self.llm_repo or not self.llm_file:
      return "Local language model not available due to a configuration error."
    if self._loading_failed:
      return "Local language model could not be loaded. Check logs for details."
    if os.path.exists(self.llm_fallback_lock):
      lock_info = self._read_fallback_lock()
      if lock_info and self._is_pid_alive(lock_info.get("pid")):
        return "Local language model is still downloading."
      try:
        os.remove(self.llm_fallback_lock)
      except FileNotFoundError:
        pass
    self._ensure_model_download_requested()
    return "Local language model is not ready yet. started downloading."

  def _build_capability_manifest(self):
    return """You are the fallback LLM for a smart boombox. Never claim an action was performed. I can play music, pause, resume, skip to the next or previous song, stop playback, tell you the current time or date, give local weather forecasts, set alarms, control volume or mute the microphone, and provide help for each command. Rewrite commands concisely. Never add details or drop negation. For live info (time/date/weather), prefer rewrite. Single turn only. Do not ask follow-up questions."""

  def _build_controller_prompt(self):
    return f"""{self.capability_manifest}

Output ONLY a JSON object. No other text.
For general knowledge questions: {{"route": "answer", "answer": "your short factual answer"}}
For boombox actions or live info requests: {{"route": "rewrite_command", "canonical_utterance": "the rewritten command"}}
Examples:
User: "what is the capital of New York" -> {{"route": "answer", "answer": "Albany"}}
User: "play coldplay" -> {{"route": "rewrite_command", "canonical_utterance": "play coldplay"}}
User: "what time is it" -> {{"route": "rewrite_command", "canonical_utterance": "what time is it"}}
User: "what color are apples" -> {{"route": "answer", "answer": "Apples can be red, green, or yellow."}}
Now respond with only the JSON object for: """

  def _build_answer_prompt(self):
    return f"""{self.capability_manifest}

You are now answering the user directly. Provide a short, factual, helpful answer. No markdown. No extra explanations. Just the answer."""

  def _log_llm(self, label, prompt_text, answer_text):
    log_path = os.path.expanduser("~/minimy/logs/llm.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
      with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{label}] Q: {prompt_text}\n[{label}] A: {answer_text}\n{'-' * 40}\n")
    except Exception as log_err:
      log.error(f"Failed to write to {log_path}: {log_err}")

  def _chat(self, system_prompt, user_prompt, max_tokens=220):
    if not self.llm:
      return None
    try:
      messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
      ]
      with self._timed(f"LLM call ({len(user_prompt)} chars)"):
        output = self.llm.create_chat_completion(
          messages=messages,
          max_tokens=max_tokens,
          temperature=0.0,
        )
      ans = output["choices"][0]["message"]["content"].strip()
      self._log_llm("fallback", user_prompt, ans)
      return ans
    except Exception as e:
      log.error(f"Error querying local LLM: {e}")
      return None

  def _extract_json_object(self, text):
    if not text:
      return None
    try:
      return json.loads(text)
    except Exception:
      pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
      return None
    try:
      return json.loads(match.group(0))
    except Exception:
      return None

  def _normalize_rewrite(self, text):
    if not text:
      return ""
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\"']+|[\"']+$", "", text)
    return text

  def _deterministic_query_rewrite(self, sentence):
    normalized = sentence.lower().strip()
    normalized = normalized.replace("what's", "what is")
    normalized = normalized.replace("whats", "what is")
    normalized = normalized.replace("todays", "today")
    normalized = normalized.replace("today's", "today")
    normalized = re.sub(r"\s+", " ", normalized)

    if "time" in normalized and (normalized.startswith("what") or normalized.startswith("can you tell") or normalized.startswith("tell me") or "time is it" in normalized):
      return "what time is it"
    if "date" in normalized or normalized in ["what day is today", "what is today"]:
      return "what is the date"
    if "day" in normalized and ("today" in normalized or normalized.startswith("what") or "day is it" in normalized or "day today" in normalized):
      return "what day is it"
    if "forecast" in normalized:
      return "what is the forecast"
    if "weather" in normalized:
      return "what is the weather"
    if "temperature" in normalized:
      return "what is the temperature"
    return None

  def _get_rewrite_nonce(self, raw_input):
    if not raw_input.startswith(f"[{self.REWRITE_HEADER_PREFIX}|"):
      return None
    end_idx = raw_input.find("]")
    if end_idx == -1:
      return None
    header = raw_input[1:end_idx]
    parts = header.split("|", 1)
    if len(parts) != 2:
      return None
    return parts[1]

  def _enqueue_rewrite(self, canonical_utterance, original_utterance):
    nonce = uuid.uuid4().hex[:12]
    self.rewrite_origins[nonce] = original_utterance
    text_path = os.path.join(self.cfg.get_cfg_val("Basic.BaseDir") or ".", "tmp", "save_text")
    fname = os.path.join(text_path, f"savetxt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}_{nonce}.txt")
    entry = f"[{self.REWRITE_HEADER_PREFIX}|{nonce}]{canonical_utterance}"
    with open(fname, "w", encoding="utf-8") as fh:
      fh.write(entry)
    log.info(f"Queued canonical utterance: {canonical_utterance}")

  def _default_command_failure_answer(self, original_utterance):
    return "I do not understand, please ask another way."

  def _default_answer_failure_answer(self):
    return "I cannot answer that right now."

  def _answer_user(self, original_utterance, failed_rewrite=False, rewritten_utterance=""):
    user_prompt = f"Original user utterance: {original_utterance}\n"
    if failed_rewrite:
      user_prompt += f"A previous command rewrite was attempted and deterministic execution did not succeed.\nRewritten command that failed: {rewritten_utterance}\nRespond to the original user utterance. Do not pretend any action happened.\n"
    answer = self._chat(self.answer_prompt, user_prompt, max_tokens=100)
    if answer:
      return answer
    if failed_rewrite:
      return self._default_command_failure_answer(original_utterance)
    return self._default_answer_failure_answer()

  def _run_controller(self, sentence):
    with self._timed(f"controller LLM for '{sentence[:30]}...'"):
      controller_output = self._chat(self.controller_prompt, sentence, max_tokens=100)
    payload = self._extract_json_object(controller_output)
    if payload is None:
      log.warning(f"Failed to parse JSON from: {controller_output}")
      return {"route": "answer", "answer": self._default_answer_failure_answer()}
    route = payload.get("route", "answer")
    if route == "answer":
      answer = payload.get("answer", "")
      if not answer:
        answer = self._default_answer_failure_answer()
      return {"route": "answer", "answer": answer}
    elif route == "rewrite_command":
      canonical_utterance = payload.get("canonical_utterance", "")
      return {"route": "rewrite_command", "canonical_utterance": canonical_utterance}
    else:
      return {"route": "answer", "answer": self._default_answer_failure_answer()}

  def _process_request_local(self, sentence, failed_rewrite=False, original_utterance="", rewritten_utterance=""):
    log.debug(f"_process_request_local: sentence={sentence!r}, failed_rewrite={failed_rewrite}")
    with self.processing_lock:
      if not self._ensure_llm_ready():
        return {"action": "answer", "answer": self._llm_unavailable_answer()}
      if failed_rewrite:
        source_utterance = original_utterance or sentence
        return {"action": "answer", "answer": self._answer_user(source_utterance, failed_rewrite=True, rewritten_utterance=rewritten_utterance or sentence)}
      fast_rewrite = self._deterministic_query_rewrite(sentence)
      if fast_rewrite and fast_rewrite.lower() != sentence.lower():
        return {"action": "rewrite", "canonical_utterance": fast_rewrite}
      decision = self._run_controller(sentence)
      route = str(decision.get("route", "answer")).strip()
      confidence = float(decision.get("confidence", 0.0) or 0.0)
      canonical_utterance = self._normalize_rewrite(decision.get("canonical_utterance", ""))
      answer = str(decision.get("answer", "") or "").strip()
      if route == "rewrite_command":
        if confidence >= 0.55 and canonical_utterance:
          if canonical_utterance.lower() != sentence.lower():
            return {"action": "rewrite", "canonical_utterance": canonical_utterance}
        answer = answer or self._default_command_failure_answer(sentence)
      if not answer:
        answer = self._default_answer_failure_answer()
      return {"action": "answer", "answer": answer}

  def _process_request_remote(self, sentence, failed_rewrite=False, original_utterance="", rewritten_utterance=""):
    req_body = json.dumps({
      "sentence": sentence,
      "failed_rewrite": failed_rewrite,
      "original_utterance": original_utterance,
      "rewritten_utterance": rewritten_utterance,
    }).encode("utf-8")
    req = urlrequest.Request(
      f"http://{self.remote_host}:{self.remote_port}/fallback",
      data=req_body,
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    try:
      with urlrequest.urlopen(req, timeout=self.REMOTE_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
      if isinstance(payload, dict):
        return payload
    except Exception as e:
      log.error(f"_process_request_remote failed: {e}")
    return None

  def _process_request_parallel(self, sentence, failed_rewrite=False, original_utterance="", rewritten_utterance=""):
    with ThreadPoolExecutor(max_workers=2) as executor:
      remote_future = executor.submit(self._process_request_remote, sentence, failed_rewrite, original_utterance, rewritten_utterance)
      local_future = executor.submit(self._process_request_local, sentence, failed_rewrite, original_utterance, rewritten_utterance)
      for future in as_completed([remote_future, local_future]):
        result = future.result()
        if result is not None:
          return result
    return {"action": "answer", "answer": self._default_answer_failure_answer()}

  def _process_request(self, sentence, failed_rewrite=False, original_utterance="", rewritten_utterance=""):
    if self.mode == "server":
      return self._process_request_local(sentence, failed_rewrite, original_utterance, rewritten_utterance)
    else:
      return self._process_request_parallel(sentence, failed_rewrite, original_utterance, rewritten_utterance)

  def _setup_remote_server(self):
    if Quart is None:
      log.error("FallbackLLMService: quart not installed, cannot start server")
      return
    self.remote_app = Quart(__name__)

    @self.remote_app.route("/fallback", methods=["POST"])
    async def fallback_endpoint():
      payload = await quart_request.get_json(silent=True)
      if not payload:
        return {"error": "missing JSON payload"}, 400
      sentence = str(payload.get("sentence", "") or "").strip()
      if not sentence:
        return {"error": "missing sentence"}, 400
      result = self._process_request(
        sentence=sentence,
        failed_rewrite=bool(payload.get("failed_rewrite", False)),
        original_utterance=str(payload.get("original_utterance", "") or ""),
        rewritten_utterance=str(payload.get("rewritten_utterance", "") or ""),
      )
      return result

  def _run_remote_server(self):
    if self.remote_app is None:
      self._setup_remote_server()
    try:
      import asyncio
      from hypercorn.asyncio import serve
      from hypercorn.config import Config as HyperConfig
      config = HyperConfig()
      config.bind = [f"0.0.0.0:{self.REMOTE_PORT}"]
      config.use_reloader = False
      config.debug = False
      asyncio.run(serve(self.remote_app, config))
    except Exception as e:
      log.error(f"FallbackLLMService: server failed: {e}")


if __name__ == "__main__":
  svc = FallbackLLMService()
  svc._run_remote_server()
