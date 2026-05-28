import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from threading import Event, Lock
from urllib import error as urlerror
from urllib import request as urlrequest
from contextlib import contextmanager
from framework.util.utils import Config
from skills.sva_base import SimpleVoiceAssistant

try:
  from huggingface_hub import hf_hub_download
  from huggingface_hub import try_to_load_from_cache
  import llama_cpp
  from llama_cpp import Llama
  from llama_cpp import llama_chat_format
  from llama_cpp.llama_cache import LlamaRAMCache
except ImportError:
  hf_hub_download = None
  try_to_load_from_cache = None
  llama_cpp = None
  Llama = None
  llama_chat_format = None
  LlamaRAMCache = None

try:
  from llama_cpp import _internals as llama_internals
except ImportError:
  llama_internals = None

try:
  from quart import Quart
  from quart import request as quart_request
except ImportError:
  Quart = None
  quart_request = None


class FallbackSkill(SimpleVoiceAssistant):
  REWRITE_HEADER_PREFIX = "LLM_REWRITE"
  REMOTE_PORT = 5003
  REMOTE_TIMEOUT = 15

  def __init__(self, bus=None, timeout=5):
    super().__init__(
      msg_handler=self.handle_message,
      skill_id="fallback_skill",
      skill_category="fallback",
    )
    self.cfg = Config()
    self.llm = None
    self.rewrite_origins = {}
    self.capability_manifest = self._build_capability_manifest()
    self.controller_prompt = self._build_controller_prompt()
    self.answer_prompt = self._build_answer_prompt()
    self.processing_lock = Lock()
    self.hub_host = self.cfg.get_cfg_val("Basic.Hub") or "localhost"
    self.use_remote_llm = self.cfg.get_cfg_val("Advanced.LLM.UseRemote") == "y"
    self.remote_app = None
    self._patch_llama_cleanup_bug()
    self.run_remote_server = False
    self.llm_repo = str(self.cfg.get_cfg_val("Basic.LLMRepo") or "").strip()
    self.llm_file = str(self.cfg.get_cfg_val("Basic.LLMFile") or "").strip()
    self.llm_download_log = os.path.join(self.base_dir, "logs", "llm_download.log")
    self.llm_download_lock = os.path.join(self.base_dir, "tmp", "llm_download.lock")

    can_manage_local_llm = (
      Llama is not None and hf_hub_download is not None and self.llm_repo and self.llm_file
    )
    should_load_local_llm = (not self.use_remote_llm) or self.cfg.is_hub()
    if can_manage_local_llm:
      if should_load_local_llm:
        self._ensure_llm_ready()
      else:
        self.log.info(
          "FallbackSkill: Remote LLM is enabled on a spoke; requesting local "
          "model cache so remote failures can fall back to local"
        )
        self._ensure_model_download_requested()
    elif should_load_local_llm:
      self.log.error(
        "FallbackSkill: llama_cpp or huggingface_hub not installed, cannot manage local LLM"
      )
    else:
      self.log.info(
        f"FallbackSkill: Using remote hub LLM at {self.hub_host}:{self.REMOTE_PORT}"
      )

    if self.use_remote_llm and self.cfg.is_hub():
      self._setup_remote_server()

  @contextmanager
  def _timed(self, label):
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000
    self.log.info(f"TIMING {label}: {elapsed:.1f} ms")

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

  def _create_llm(self, model_path):
    llm_kwargs = {
      "model_path": model_path,
      "n_ctx": 4096,
      "n_batch": 256,
      "verbose": False,
    }

    gpu_probe = getattr(llama_cpp, "llama_supports_gpu_offload", None)
    if callable(gpu_probe):
      try:
        if gpu_probe():
          llm_kwargs["n_gpu_layers"] = -1
          self.log.info(
            "FallbackSkill: GPU offload available, enabling llama.cpp CUDA with n_gpu_layers=-1"
          )
        else:
          self.log.info(
            "FallbackSkill: llama.cpp GPU offload not available, using CPU"
          )
      except Exception as e:
        self.log.warning(
          f"FallbackSkill: GPU capability probe failed, using CPU fallback: {e}"
        )
    else:
      self.log.info(
        "FallbackSkill: llama.cpp GPU capability probe unavailable, using CPU fallback"
      )

    return Llama(**llm_kwargs)

  def _resolve_cached_model_path(self):
    self.log.debug(
      "FallbackSkill: Resolving cached LLM path "
      f"(repo={self.llm_repo}, file={self.llm_file}, "
      f"hf_hub_download={hf_hub_download is not None}, "
      f"try_to_load_from_cache={try_to_load_from_cache is not None})"
    )
    if not self.llm_repo or not self.llm_file or hf_hub_download is None:
      self.log.warning(
        "FallbackSkill: Cannot resolve cached model path because LLM config "
        f"is incomplete or huggingface_hub is missing "
        f"(repo={self.llm_repo}, file={self.llm_file}, "
        f"hf_hub_download={hf_hub_download is not None})"
      )
      return None

    if try_to_load_from_cache is not None:
      cached_path = try_to_load_from_cache(
        repo_id=self.llm_repo,
        filename=self.llm_file,
      )
      if isinstance(cached_path, str) and os.path.exists(cached_path):
        self.log.info(
          f"FallbackSkill: Found cached model via huggingface cache at {cached_path}"
        )
        return cached_path

    try:
      cached_path = hf_hub_download(
        repo_id=self.llm_repo,
        filename=self.llm_file,
        local_files_only=True,
      )
      if isinstance(cached_path, str) and os.path.exists(cached_path):
        self.log.info(
          f"FallbackSkill: Found cached model via hf_hub_download local lookup at {cached_path}"
        )
        return cached_path
    except Exception:
      self.log.debug(
        "FallbackSkill: Local-only hf_hub_download lookup did not find the model"
      )
      return None

    self.log.debug(
      f"FallbackSkill: Cached model path not found for {self.llm_repo} ({self.llm_file})"
    )
    return None

  def _launch_model_prefetch(self):
    helper_path = os.path.join(self.base_dir, "install", "cache_llm.py")
    if not os.path.exists(helper_path):
      self.log.error(
        f"FallbackSkill: Missing LLM cache helper at {helper_path}"
      )
      return False

    os.makedirs(os.path.dirname(self.llm_download_log), exist_ok=True)
    env = os.environ.copy()
    env["SVA_BASE_DIR"] = self.base_dir

    try:
      self.log.info(
        "FallbackSkill: Launching background LLM cache worker "
        f"for {self.llm_repo} ({self.llm_file}); worker output will be "
        f"appended to {self.llm_download_log}"
      )
      with open(self.llm_download_log, "a", encoding="utf-8") as log_handle:
        proc = subprocess.Popen(
          [sys.executable, helper_path],
          stdout=log_handle,
          stderr=subprocess.STDOUT,
          cwd=self.base_dir,
          env=env,
          start_new_session=True,
          close_fds=True,
        )
      self.log.info(
        "FallbackSkill: Started background LLM cache worker "
        f"(pid={proc.pid}) for {self.llm_repo} ({self.llm_file})"
      )
      return True
    except Exception as e:
      self.log.error(f"FallbackSkill: Failed to start LLM cache worker: {e}")
      return False

  def _read_download_lock(self):
    try:
      with open(self.llm_download_lock, "r", encoding="utf-8") as lock_handle:
        return json.load(lock_handle)
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
    self.log.debug(
      "FallbackSkill: Checking whether background LLM download should be requested "
      f"(lock={self.llm_download_lock})"
    )
    if os.path.exists(self.llm_download_lock):
      lock_info = self._read_download_lock()
      if lock_info:
        pid = lock_info.get("pid")
        repo_id = lock_info.get("repo_id", self.llm_repo)
        filename = lock_info.get("filename", self.llm_file)
        if self._is_pid_alive(pid):
          self.log.info(
            "FallbackSkill: Background LLM cache worker already running "
            f"(pid={pid}, repo={repo_id}, file={filename})"
          )
          return True

        self.log.warning(
          "FallbackSkill: Found stale LLM cache lock; removing it and "
          f"restarting download (pid={pid}, repo={repo_id}, file={filename})"
        )
      else:
        self.log.warning(
          "FallbackSkill: Found unreadable LLM cache lock; removing it "
          "and restarting background download"
        )
      try:
        os.remove(self.llm_download_lock)
      except FileNotFoundError:
        pass

    self.log.info(
      f"FallbackSkill: Requesting background download for {self.llm_repo} ({self.llm_file})"
    )
    return self._launch_model_prefetch()

  def _ensure_llm_ready(self):
    self.log.debug(
      "FallbackSkill: Ensuring local LLM is ready "
      f"(llm_loaded={self.llm is not None}, repo={self.llm_repo}, "
      f"file={self.llm_file}, use_remote_llm={self.use_remote_llm}, "
      f"is_hub={self.cfg.is_hub()})"
    )
    if self.llm is not None:
      self.log.debug("FallbackSkill: Local LLM already loaded")
      return True

    if not self.llm_repo or not self.llm_file:
      self.log.error(
        "FallbackSkill: LLM configuration is missing; cannot load local model "
        f"(repo={self.llm_repo}, file={self.llm_file})"
      )
      return False

    model_path = self._resolve_cached_model_path()
    if model_path:
      llm_role = "hub" if self.cfg.is_hub() else "local"
      self.log.info(
        f"FallbackSkill: Loading cached {llm_role} LLM model from "
        f"{self.llm_repo} ({self.llm_file})"
      )
      try:
        self.llm = self._create_llm(model_path)
        return True
      except Exception as e:
        self.log.error(f"FallbackSkill: Failed to load cached Llama model: {e}")
        return False

    self.log.warning(
      f"FallbackSkill: LLM model {self.llm_repo} ({self.llm_file}) is not cached locally yet"
    )
    self._ensure_model_download_requested()
    return False

  def _llm_unavailable_answer(self):
    self.log.debug(
      "FallbackSkill: Building unavailable-answer response "
      f"(repo={self.llm_repo}, file={self.llm_file}, "
      f"lock_exists={os.path.exists(self.llm_download_lock)}, "
      f"llm_loaded={self.llm is not None})"
    )
    if not self.llm_repo or not self.llm_file:
      self.log.error(
        "FallbackSkill: Returning unavailable-answer because LLM config is missing"
      )
      return (
        "I am sorry, my local language model is not available right now due "
        "to a configuration error."
      )

    if os.path.exists(self.llm_download_lock):
      lock_info = self._read_download_lock()
      if lock_info and self._is_pid_alive(lock_info.get("pid")):
        self.log.info(
          "FallbackSkill: Local LLM is still downloading "
          f"(pid={lock_info.get('pid')}, repo={lock_info.get('repo_id', self.llm_repo)}, "
          f"file={lock_info.get('filename', self.llm_file)})"
        )
        return (
          "I am sorry, my local language model is still downloading. "
          "Please try again in a few minutes."
        )

      self.log.warning(
        "FallbackSkill: LLM download lock exists but no worker is alive; "
        "clearing stale lock and requesting a fresh download"
      )
      try:
        os.remove(self.llm_download_lock)
      except FileNotFoundError:
        pass

    download_started = self._ensure_model_download_requested()
    if not download_started:
      self.log.error(
        "FallbackSkill: Returning unavailable-answer because background download "
        "could not be started"
      )
      return (
        "I am sorry, my local language model is not ready yet, and I could not "
        "start the background download automatically."
      )
    self.log.info(
      "FallbackSkill: Returning unavailable-answer after starting background download"
    )
    return (
      "I am sorry, my local language model is not ready yet. "
      "I have started downloading it in the background, so please try again in a few minutes."
    )

  def _setup_remote_server(self):
    if Quart is None:
      self.log.error(
        "FallbackSkill: quart is not installed, cannot start remote LLM server on hub"
      )
      return
    self.remote_app = Quart(__name__)
    self.run_remote_server = True

    @self.remote_app.route("/fallback", methods=["POST"])
    async def fallback_endpoint():
      payload = await quart_request.get_json(silent=True)
      if not payload:
        return {"error": "missing JSON payload"}, 400

      sentence = str(payload.get("sentence", "") or "").strip()
      if not sentence:
        return {"error": "missing sentence"}, 400

      result = self._process_request_local(
        sentence=sentence,
        failed_rewrite=bool(payload.get("failed_rewrite", False)),
        original_utterance=str(payload.get("original_utterance", "") or ""),
        rewritten_utterance=str(payload.get("rewritten_utterance", "") or ""),
      )
      return result

  def _run_remote_server(self):
    try:
      self.log.info(
        f"FallbackSkill: Starting remote LLM server on 0.0.0.0:{self.REMOTE_PORT}"
      )
      import asyncio
      from hypercorn.asyncio import serve
      from hypercorn.config import Config as HyperConfig
      config = HyperConfig()
      config.bind = [f"0.0.0.0:{self.REMOTE_PORT}"]
      config.use_reloader = False
      config.debug = False
      assert self.remote_app is not None, "Remote app not initialized"
      asyncio.run(serve(self.remote_app, config))
    except Exception as e:
      self.log.error(f"FallbackSkill: Remote LLM server failed: {e}")

  def _build_capability_manifest(self):
    return """You are the fallback LLM for a smart boombox. Never claim an action was performed. Capabilities: play music, pause, resume, next/prev, stop, time/date, weather, alarms, volume/mic control, help. Rewrite commands concisely. Never add details or drop negation. For live info (time/date/weather), prefer rewrite. Single turn only. Do not ask follow-up questions."""

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

  def handle_message(self, msg):
    self.log.info(
      "FallbackSkill.handle_message() NOT EXPECTING THIS IS EVER CALLED!!!"
    )

  def _log_llm(self, label, prompt_text, answer_text):
    log_path = os.path.expanduser("~/minimy/logs/llm.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
      with open(log_path, "a", encoding="utf-8") as f:
        f.write(
          f"[{label}] Q: {prompt_text}\n[{label}] A: {answer_text}\n{'-' * 40}\n"
        )
    except Exception as log_err:
      self.log.error(f"FallbackSkill: Failed to write to {log_path}: {log_err}")

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
      self.log.error(f"FallbackSkill: Error querying local LLM: {e}")
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

    if "time" in normalized and (
      normalized.startswith("what")
      or normalized.startswith("can you tell")
      or normalized.startswith("tell me")
      or "time is it" in normalized
    ):
      return "what time is it"

    if "date" in normalized or normalized in ["what day is today", "what is today"]:
      return "what is the date"

    if "day" in normalized and (
      "today" in normalized
      or normalized.startswith("what")
      or "day is it" in normalized
      or "day today" in normalized
    ):
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
    text_path = os.path.join(self.base_dir, "tmp", "save_text")
    fname = os.path.join(
      text_path,
      f"savetxt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}_{nonce}.txt",
    )
    entry = f"[{self.REWRITE_HEADER_PREFIX}|{nonce}]{canonical_utterance}"
    with open(fname, "w", encoding="utf-8") as fh:
      fh.write(entry)
    self.log.info(
      f"FallbackSkill._enqueue_rewrite() queued canonical utterance: {canonical_utterance}"
    )

  def _default_command_failure_answer(self, original_utterance):
    return (
      "I understood that as a smart boombox request, but I could not turn it into a supported command. "
      "Please try saying it another way."
    )

  def _default_answer_failure_answer(self):
    return "I am sorry, I could not answer that right now."

  def _answer_user(
    self, original_utterance, failed_rewrite=False, rewritten_utterance=""
  ):
    user_prompt = f"Original user utterance: {original_utterance}\n"
    if failed_rewrite:
      user_prompt += (
        "A previous command rewrite was attempted and deterministic execution did not succeed.\n"
        f"Rewritten command that failed: {rewritten_utterance}\n"
        "Respond to the original user utterance. Do not pretend any action happened.\n"
      )
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
      self.log.warning(
        f"FallbackSkill._run_controller() failed to parse JSON from: {controller_output}"
      )
      return {
        "route": "answer",
        "answer": self._default_answer_failure_answer(),
      }
    route = payload.get("route", "answer")
    if route == "answer":
      answer = payload.get("answer", "")
      if not answer:
        answer = self._default_answer_failure_answer()
      return {
        "route": "answer",
        "answer": answer,
      }
    elif route == "rewrite_command":
      canonical_utterance = payload.get("canonical_utterance", "")
      return {
        "route": "rewrite_command",
        "canonical_utterance": canonical_utterance,
      }
    else:
      return {
        "route": "answer",
        "answer": self._default_answer_failure_answer(),
      }

  def _process_request_local(
    self,
    sentence,
    failed_rewrite=False,
    original_utterance="",
    rewritten_utterance="",
  ):
    self.log.debug(
      "FallbackSkill: Processing local fallback request "
      f"(sentence={sentence!r}, failed_rewrite={failed_rewrite}, "
      f"original_utterance={original_utterance!r}, rewritten_utterance={rewritten_utterance!r})"
    )
    with self.processing_lock:
      if not self._ensure_llm_ready():
        self.log.warning(
          "FallbackSkill: Local LLM is not ready; using unavailable-answer path"
        )
        return {
          "action": "answer",
          "answer": self._llm_unavailable_answer(),
        }

      if failed_rewrite:
        source_utterance = original_utterance or sentence
        return {
          "action": "answer",
          "answer": self._answer_user(
            source_utterance,
            failed_rewrite=True,
            rewritten_utterance=rewritten_utterance or sentence,
          ),
        }

      fast_rewrite = self._deterministic_query_rewrite(sentence)
      if fast_rewrite and fast_rewrite.lower() != sentence.lower():
        return {
          "action": "rewrite",
          "canonical_utterance": fast_rewrite,
        }

      decision = self._run_controller(sentence)
      route = decision.get("route", "answer")
      if route == "rewrite_command":
        canonical_utterance = decision.get("canonical_utterance", "")
        if canonical_utterance and canonical_utterance.lower() != sentence.lower():
          return {
            "action": "rewrite",
            "canonical_utterance": canonical_utterance,
          }
        answer = self._default_command_failure_answer(sentence)
      else:
        answer = decision.get("answer", self._default_answer_failure_answer())

      if not answer:
        answer = self._default_answer_failure_answer()

      return {
        "action": "answer",
        "answer": answer,
      }

  def _process_request_remote(
    self,
    sentence,
    failed_rewrite=False,
    original_utterance="",
    rewritten_utterance="",
  ):
    req_body = json.dumps(
      {
        "sentence": sentence,
        "failed_rewrite": failed_rewrite,
        "original_utterance": original_utterance,
        "rewritten_utterance": rewritten_utterance,
      }
    ).encode("utf-8")
    req = urlrequest.Request(
      f"http://{self.hub_host}:{self.REMOTE_PORT}/fallback",
      data=req_body,
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    try:
      with urlrequest.urlopen(req, timeout=self.REMOTE_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
      if isinstance(payload, dict):
        return payload
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as e:
      self.log.error(f"FallbackSkill: Remote LLM request failed: {e}")
    except Exception as e:
      self.log.error(f"FallbackSkill: Unexpected remote LLM failure: {e}")
    self.log.warning(
      "FallbackSkill: Falling back to local LLM path after remote request failure "
      f"(sentence={sentence!r}, failed_rewrite={failed_rewrite}, "
      f"original_utterance={original_utterance!r}, rewritten_utterance={rewritten_utterance!r})"
    )
    return self._process_request_local(
      sentence=sentence,
      failed_rewrite=failed_rewrite,
      original_utterance=original_utterance,
      rewritten_utterance=rewritten_utterance,
    )

  def _process_request(
    self,
    sentence,
    failed_rewrite=False,
    original_utterance="",
    rewritten_utterance="",
  ):
    if self.use_remote_llm and not self.cfg.is_hub():
      return self._process_request_remote(
        sentence=sentence,
        failed_rewrite=failed_rewrite,
        original_utterance=original_utterance,
        rewritten_utterance=rewritten_utterance,
      )
    return self._process_request_local(
      sentence=sentence,
      failed_rewrite=failed_rewrite,
      original_utterance=original_utterance,
      rewritten_utterance=rewritten_utterance,
    )

  def handle_fallback(self, msg):
    self.log.debug(
      f"FallbackSkill:handle_fallback(): msg: \n{json.dumps(msg, indent=2)}"
    )
    utt = msg["payload"]["utt"]
    sentence = utt["sentence"].strip()
    raw_input = utt.get("raw_input", "")

    # Guard against very short or meaningless utterances
    words = sentence.split()
    if len(words) < 2 and sentence.lower() not in ["computer", "help", "stop", "pause", "resume", "next", "previous"]:
      self.log.info(f"FallbackSkill: Ignoring too short sentence: '{sentence}'")
      return

    rewrite_nonce = self._get_rewrite_nonce(raw_input)
    if rewrite_nonce is not None:
      original_utterance = self.rewrite_origins.pop(rewrite_nonce, sentence)
      result = self._process_request(
        sentence=original_utterance,
        failed_rewrite=True,
        original_utterance=original_utterance,
        rewritten_utterance=sentence,
      )
      ans = str(result.get("answer", "") or "").strip()
      self.log.debug(
        f"FallbackSkill:handle_fallback(): rewrite failure ans: {ans}"
      )
      self.speak(ans)
      return

    result = self._process_request(sentence=sentence)
    if result.get("action") == "rewrite":
      canonical_utterance = self._normalize_rewrite(
        result.get("canonical_utterance", "")
      )
      if canonical_utterance:
        self._enqueue_rewrite(canonical_utterance, sentence)
        return

    answer = str(result.get("answer", "") or "").strip()
    if not answer:
      answer = self._default_answer_failure_answer()
    self.log.debug(f"FallbackSkill:handle_fallback(): ans: {answer}")
    self.speak(answer)


if __name__ == "__main__":
  fs = FallbackSkill()
  if fs.run_remote_server:
    fs._run_remote_server()
  else:
    Event().wait()
