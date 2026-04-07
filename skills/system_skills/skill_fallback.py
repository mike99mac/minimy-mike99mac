import json
import os
import re
import uuid
from datetime import datetime
from threading import Event, Lock, Thread
from urllib import error as urlerror
from urllib import request as urlrequest

from framework.util.utils import Config
from skills.sva_base import SimpleVoiceAssistant
import re

try:
    import llama_cpp
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    from llama_cpp import llama_chat_format
    from llama_cpp.llama_cache import LlamaRAMCache
except ImportError:
    llama_cpp = None
    hf_hub_download = None
    Llama = None
    llama_chat_format = None
    LlamaRAMCache = None

try:
    from llama_cpp import _internals as llama_internals
except ImportError:
    llama_internals = None

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
        self.prompt_cache = None
        self.system_prompt_formatters = {}
        self._patch_llama_cleanup_bug()
        self.run_remote_server = False

        should_load_local_llm = (not self.use_remote_llm) or self.cfg.is_hub()
        if should_load_local_llm and Llama is not None and hf_hub_download is not None:
            llm_role = "hub" if self.cfg.is_hub() else "local"
            self.llm_repo = self.cfg.get_cfg_val("Basic.LLMRepo")
            self.llm_file = self.cfg.get_cfg_val("Basic.LLMFile")

            if not self.llm_repo or not self.llm_file:
                self.log.error(
                    "FallbackSkill: LLM configuration missing "
<<<<<<< HEAD
                    "(Basic.LLMRepo or Basic.LLMFile) in mmconfig.yml. Cannot load model."
=======
                    "(Basic.LLMRepo or Basic.LLMFile) in mmconfig.yml. Cannot load model."
>>>>>>> 892174f (continue to merge main -> llama-cpp-python)
                )
            else:
                self.log.info(
                    f"FallbackSkill: Downloading/Loading {llm_role} LLM model from "
                    f"{self.llm_repo} ({self.llm_file})"
                )
                try:
                    model_path = hf_hub_download(
                        repo_id=self.llm_repo, filename=self.llm_file
                    )
                    self.llm = self._create_llm(model_path)
                    self._warm_system_prompt_cache()
                except Exception as e:
                    self.log.error(f"FallbackSkill: Failed to load Llama model: {e}")
        elif should_load_local_llm:
            self.log.error("FallbackSkill: llama_cpp or huggingface_hub not installed")
        else:
            self.log.info(
                f"FallbackSkill: Using remote hub LLM at {self.hub_host}:{self.REMOTE_PORT}"
            )

        if self.use_remote_llm and self.cfg.is_hub():
            self._setup_remote_server()

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
            "n_ctx": 2048,
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

    def _get_chat_formatter(self, add_generation_prompt):
        if llama_chat_format is None or self.llm is None:
            return None

        formatter = self.system_prompt_formatters.get(add_generation_prompt)
        if formatter is not None:
            return formatter

        template = self.llm.metadata.get("tokenizer.chat_template")
        if not template:
            return None

        eos_token_id = self.llm.token_eos()
        bos_token_id = self.llm.token_bos()
        eos_token = (
            self.llm._model.token_get_text(eos_token_id) if eos_token_id != -1 else ""
        )
        bos_token = (
            self.llm._model.token_get_text(bos_token_id) if bos_token_id != -1 else ""
        )

        formatter = llama_chat_format.Jinja2ChatFormatter(
            template=template,
            eos_token=eos_token,
            bos_token=bos_token,
            add_generation_prompt=add_generation_prompt,
            stop_token_ids=[eos_token_id] if eos_token_id != -1 else None,
        )
        self.system_prompt_formatters[add_generation_prompt] = formatter
        return formatter

    def _tokenize_chat_messages(self, messages, add_generation_prompt):
        formatter = self._get_chat_formatter(add_generation_prompt)
        if formatter is None or self.llm is None:
            return None

        formatted = formatter(messages=messages)
        return self.llm.tokenize(
            formatted.prompt.encode("utf-8"),
            add_bos=not formatted.added_special,
            special=True,
        )

    def _warm_system_prompt_cache(self):
        if self.llm is None or LlamaRAMCache is None:
            return

        try:
            # Store prompt-prefix KV state so the first real request does not have to
            # re-evaluate the full system prompt from scratch.
            self.prompt_cache = LlamaRAMCache(capacity_bytes=256 << 20)
            self.llm.set_cache(self.prompt_cache)

            system_prompts = (
                ("controller", self.controller_prompt),
                ("answer", self.answer_prompt),
            )

            for label, system_prompt in system_prompts:
                prompt_tokens = self._tokenize_chat_messages(
                    [{"role": "system", "content": system_prompt}],
                    add_generation_prompt=False,
                )
                if not prompt_tokens:
                    self.log.warning(
                        f"FallbackSkill: Unable to build {label} system prompt cache prefix"
                    )
                    continue

                self.llm.reset()
                self.llm.eval(prompt_tokens)
                self.prompt_cache[prompt_tokens] = self.llm.save_state()
                self.log.info(
                    f"FallbackSkill: Warmed KV cache for {label} system prompt ({len(prompt_tokens)} tokens)"
                )

            self.llm.reset()
        except Exception as e:
            self.log.warning(
                f"FallbackSkill: Failed to warm system prompt KV cache: {e}"
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
            self.remote_app.run(
                host="0.0.0.0",
                port=self.REMOTE_PORT,
                debug=False,
                use_reloader=False,
            )
        except Exception as e:
            self.log.error(f"FallbackSkill: Remote LLM server failed: {e}")

    def _build_capability_manifest(self):
        return """Smart Boombox capability manifest

Identity and architecture
- You are the language reasoning layer for Minimy, a smart boombox.
- You are not the execution engine. The deterministic Minimy command system performs actions.
- If you are asked to control the device, your job is to classify the request, normalize it into a canonical command if possible, or explain why it cannot be executed.
- Never claim that music started, volume changed, alarms were set, or any other device action already happened unless deterministic execution has already succeeded outside this fallback stage.

Core boombox capabilities you may rely on
- Music and media:
  accepted intent families include play music by artist, album, song, genre, playlist, radio station, internet music, or news.
  common examples include: play coldplay, play jazz radio, play npr, pause, resume, next track, previous track, stop music.
  malformed user phrases like put on, listen to, start playing, queue up, throw on, or can you play may be normalized to play when the meaning is clear.
- Time and date:
  what time is it, what is the date, what day is it.
- Weather:
  what is the weather, what is the forecast, what is the temperature, optionally with a location.
- Alarms:
  set or create an alarm, list alarms, delete or remove an alarm, stop a ringing alarm, snooze a ringing alarm.
- Volume and microphone:
  set, change, increase, decrease, mute, or unmute volume.
  set or change microphone level.
- Help:
  general help topics about music, radio, weather, time, alarms, volume, and related boombox usage.
- General question answering:
  answer ordinary factual questions that are not boombox control requests.

Optional or uncertain capabilities
- Home Assistant control and email may exist in some deployments, but do not promise them unless the provided context explicitly says they are available.
- Do not invent internet browsing, app launching, messaging, purchasing, or arbitrary external integrations.

Command normalization rules
- Preserve the user's intent. Do not add new details.
- Do not drop negation.
- Do not convert a capability question into an execution command unless the user is clearly asking for action.
- Only rewrite into short canonical commands the deterministic system is likely to understand.
- Good rewrite examples:
  put on some coldplay -> play coldplay
  can you turn the music down -> decrease volume
  whats the forecast for boston massachusetts -> what is the forecast for boston massachusetts
- Bad rewrites:
  play something relaxing -> play norah jones
  can you play coldplay -> play coldplay if the user is obviously asking about capability rather than issuing a command
  dont play coldplay -> play coldplay

Behavior rules
- Prefer truthfulness over helpful-sounding roleplay.
- Never say now playing, done, I changed it, I set that, or similar action-confirmation language inside this fallback layer.
- For boombox capability questions, answer only from this manifest.
- For unsupported or underspecified device requests, explain the limitation or what information is missing.
- This fallback interaction is single-turn. You cannot ask the user a follow-up question and wait for a response.
- If more information would normally be needed, state the missing information in one answer instead of asking an interactive follow-up.
- If a rewritten command later fails deterministic execution, the follow-up answer must discuss the original user request, not the rewritten command only."""

    def _build_controller_prompt(self):
        return f"""{self.capability_manifest}

Your task is to act as a hidden controller for the smart boombox fallback layer.

Follow this decision process exactly:
1. Decide whether the user input is primarily:
   - a general question,
   - a boombox capability question,
   - a boombox command request,
   - or unknown.
2. If it is a boombox command request, determine whether:
   - it is likely supported by the boombox,
   - it contains enough information to execute,
   - and it can be safely normalized into a concise canonical command.
3. Output JSON only. Do not output Markdown. Do not output prose outside the JSON object.

Return exactly one JSON object with these keys:
- route: one of "rewrite_command", "answer", "cannot_execute"
- confidence: number from 0.0 to 1.0
- canonical_utterance: string, empty unless route is "rewrite_command"
- answer: string, empty unless route is "answer" or "cannot_execute"
- reason: short string explaining the decision

Additional hard rules:
- If route is "rewrite_command", the command must be something the deterministic command system could plausibly parse.
- If route is "rewrite_command", never include a wake word, explanations, or multiple commands.
- If route is "answer", answer concisely and truthfully, and the answer field must not be empty.
- If route is "cannot_execute", explain what is missing, unsupported, or uncertain without pretending anything happened, and the answer field must not be empty.
- Do not ask the user a follow-up question. This is a single-turn decision.
- Never claim you performed an action.
- When in doubt, choose "cannot_execute" rather than inventing a command."""

    def _build_answer_prompt(self):
        return f"""{self.capability_manifest}

You are now producing the user-facing fallback answer for the smart boombox.

Rules:
- Speak plainly in complete sentences with no Markdown.
- If the user asked a general knowledge question, answer it directly and concisely.
- If the user asked about smart boombox capabilities, answer only from the provided capability manifest.
- If the user asked for device control and execution did not happen, say that clearly and do not pretend the action occurred.
- This is single-turn only. Do not ask the user a follow-up question.
- If information is missing, explain exactly what is missing in one answer instead of asking interactively.
- Never invent capabilities.
- Never say you already completed a boombox action unless that success was explicitly provided to you.
- Prefer short, concrete answers over broad assistant-style explanations."""

    def handle_message(self, msg):
        self.log.info(
            "FallbackSkill.handle_message() NOT EXPECTING THIS IS EVER CALLED!!!"
        )

    def _log_llm(self, label, prompt_text, answer_text):
        log_path = os.path.expanduser("~/minimy/logs/llm.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"Q: {ques}\nA: {ans}\n{'-'*40}\n")
        except Exception as log_err:
            self.log.error(f"FallbackSkill: Failed to write to {log_path}: {log_err}")
            
      except Exception as e:
        self.log.error(f"FallbackSkill: Error querying local LLM: {e}")
        ans = "I encountered an error trying to process your request."

    def _chat(self, system_prompt, user_prompt, max_tokens=220):
        if not self.llm:
            return None
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            try:
                output = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
                    chat_template_kwargs={"enable_thinking": False},
                )
            except TypeError:
                output = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
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
        answer = self._chat(self.answer_prompt, user_prompt, max_tokens=170)
        if answer:
            return answer
        if failed_rewrite:
            return self._default_command_failure_answer(original_utterance)
        return "I am sorry, my local language model is not available right now due to a configuration error."

    def _run_controller(self, sentence):
        controller_output = self._chat(self.controller_prompt, sentence, max_tokens=220)
        payload = self._extract_json_object(controller_output)
        if payload is None:
            self.log.warning(
                f"FallbackSkill._run_controller() failed to parse JSON from: {controller_output}"
            )
            return {
                "route": "answer",
                "confidence": 0.0,
                "canonical_utterance": "",
                "answer": self._default_answer_failure_answer(),
                "reason": "controller_parse_failure",
            }
        payload.setdefault("route", "answer")
        payload.setdefault("confidence", 0.0)
        payload.setdefault("canonical_utterance", "")
        payload.setdefault("answer", "")
        payload.setdefault("reason", "")
        return payload

    def _process_request_local(
        self,
        sentence,
        failed_rewrite=False,
        original_utterance="",
        rewritten_utterance="",
    ):
        with self.processing_lock:
            if not self.llm:
                return {
                    "action": "answer",
                    "answer": (
                        "I am sorry, my language model is not available right now due "
                        "to a configuration error."
                    ),
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
            route = str(decision.get("route", "answer")).strip()
            confidence = float(decision.get("confidence", 0.0) or 0.0)
            canonical_utterance = self._normalize_rewrite(
                decision.get("canonical_utterance", "")
            )
            answer = str(decision.get("answer", "") or "").strip()

            if route == "rewrite_command":
                if confidence >= 0.55 and canonical_utterance:
                    if canonical_utterance.lower() != sentence.lower():
                        return {
                            "action": "rewrite",
                            "canonical_utterance": canonical_utterance,
                        }
                answer = answer or self._default_command_failure_answer(sentence)

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
        return {
            "action": "answer",
            "answer": "I am sorry, the hub language model is not available right now.",
        }

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

        decision = self._run_controller(sentence)
        route = str(decision.get("route", "answer")).strip()
        confidence = float(decision.get("confidence", 0.0) or 0.0)
        canonical_utterance = self._normalize_rewrite(
            decision.get("canonical_utterance", "")
        )
        answer = str(decision.get("answer", "") or "").strip()

        if route == "rewrite_command":
            if confidence < 0.55:
                answer = answer or self._default_command_failure_answer(sentence)
            elif not canonical_utterance:
                answer = answer or self._default_command_failure_answer(sentence)
            elif canonical_utterance.lower() == sentence.lower():
                answer = answer or self._default_command_failure_answer(sentence)
            else:
                self._enqueue_rewrite(canonical_utterance, sentence)
                return

        answer = str(result.get("answer", "") or "").strip()
        if not answer:
            answer = "I am sorry, the language model is not available right now."
        self.log.debug(f"FallbackSkill:handle_fallback(): ans: {answer}")
        self.speak(answer)


# main()
if __name__ == "__main__":
    fs = FallbackSkill()
    if fs.run_remote_server:
        fs._run_remote_server()
    else:
        Event().wait()
