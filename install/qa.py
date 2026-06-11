#!/usr/bin/env python3
#
# File: qa.py - answer questions with Minimy's fallback LLM service
# Usage: qa.py <your question>
#
import json
import sys
from urllib import request as urlrequest
from framework.util.utils import Config

cfg = Config()                             # Get hub from config file
use_remote = str(cfg.get_cfg_val("Basic.LLM.UseRemote") or "n").strip().lower()
if use_remote == 'y':
  hub = cfg.get_cfg_val("Basic.Hub") or "localhost"
else:
  hub = "localhost"
FALLBACK_URL = f"http://{hub}:5003/fallback"
TIMEOUT = 30

def answer_question(question):
  req_body = json.dumps({"sentence": question, "raw_input": question}).encode("utf-8")
  req = urlrequest.Request(FALLBACK_URL, data=req_body, headers={"Content-Type": "application/json"}, method="POST")
  try:
    with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
      result = json.loads(resp.read().decode("utf-8"))
  except Exception as e:
    return f"I am sorry, I could not reach the fallback service: {e}"

  # Handle rewrite if needed
  if result.get("action") == "rewrite":
    canonical = str(result.get("canonical_utterance", "") or "").strip()
    if canonical and canonical.lower() != question.lower():
      # Second attempt: send the rewritten command as a new request
      return answer_question(canonical)
    else:
      # No meaningful rewrite, fallback to answer
      return "I do not understand, please ask another way."

  answer = str(result.get("answer", "") or "").strip()
  answer = answer.replace('"', "")
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
