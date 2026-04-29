"""Haiku 4.5 classifier. Reads worker output, returns {state, questions}."""
from __future__ import annotations

import json

from anthropic import Anthropic

from runner.prompts import CLASSIFIER_SYSTEM_PROMPT

CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
SENTINEL = "[[RAINHAWK::FEATURE_COMPLETE]]"


def classify(worker_text: str) -> dict:
    if SENTINEL in worker_text:
        return {"state": "feature_complete", "questions": []}

    client = Anthropic()
    resp = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=512,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": worker_text or "(empty turn)"}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"state": "in_progress", "questions": [], "_parse_error": raw}
    parsed.setdefault("questions", [])
    if parsed.get("state") not in ("needs_input", "feature_complete", "in_progress"):
        parsed["state"] = "in_progress"
    return parsed
