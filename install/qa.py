#!/usr/bin/env python3
#
# File: qa.py - answer questions with Minimy's fallback LLM
# Usage: qa.py <your question>
#
import os
import sys

def _get_base_dir():
  return os.environ.get("SVA_BASE_DIR") or os.path.join(
    os.path.expanduser("~"), "minimy"
  )

def _ensure_venv_python(base_dir):
  venv_python = os.path.join(base_dir, "minimy_venv", "bin", "python3")
  if not os.path.exists(venv_python):
    return
  current_python = os.path.realpath(sys.executable)
  target_python = os.path.realpath(venv_python)
  if current_python != target_python:
    os.execv(venv_python, [venv_python] + sys.argv)

class NoOpBus:
  def on(self, _msg_type, _callback):
    return None

  def send(self, _msg_type, _target_client_id, _payload):
    return None

  def close(self):
    return None

def answer_question(question):
  base_dir = _get_base_dir()
  os.environ.setdefault("SVA_BASE_DIR", base_dir)
  _ensure_venv_python(base_dir)
  if base_dir not in sys.path:
    sys.path.append(base_dir)

  from skills.system_skills.skill_fallback import FallbackSkill

  fallback = FallbackSkill(bus=NoOpBus())
  result = fallback._process_request(question)

  if result.get("action") == "rewrite":
    canonical = str(result.get("canonical_utterance", "") or "").strip()
    if canonical:
      result = fallback._process_request(
        sentence=question,
        failed_rewrite=True,
        original_utterance=question,
        rewritten_utterance=canonical
      )

  answer = str(result.get("answer", "") or "").strip()
  answer = answer.replace('"', "")         # remove quotes
  if not answer:
    answer = "I am sorry, I could not answer that right now."
  return answer

if __name__ == "__main__":
  question = " ".join(sys.argv[1:]).strip()
  if not question:
    print("Usage: qa.py <your question>", file=sys.stderr)
    sys.exit(1)
  try:
    print(answer_question(question))
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
