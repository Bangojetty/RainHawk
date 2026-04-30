"""Wraps ClaudeSDKClient. Persists session_id to rainhawk-state.json and resumes on restart."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from runner.prompts import OPUS_SESSION_SYSTEM_PROMPT

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "rainhawk-state.json"
WORKER_MODEL = "claude-opus-4-7"


def load_state() -> dict:
    default = {
        "session_id": None,
        "iteration": 0,
        "features_completed": 0,
        "last_classification": None,
        "last_updated": None,
    }
    if STATE_FILE.exists():
        return {**default, **json.loads(STATE_FILE.read_text())}
    return default


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    state["last_updated"] = datetime.now(timezone.utc).isoformat()


def make_client(session_id: str | None) -> ClaudeSDKClient:
    options = ClaudeAgentOptions(
        system_prompt=OPUS_SESSION_SYSTEM_PROMPT,
        model=WORKER_MODEL,
        cwd=str(REPO_ROOT),
        permission_mode="bypassPermissions",
        resume=session_id,
    )
    return ClaudeSDKClient(options=options)


def extract_assistant_text(messages: list) -> str:
    out: list[str] = []
    for m in messages:
        if isinstance(m, AssistantMessage):
            for block in m.content:
                if isinstance(block, TextBlock):
                    out.append(block.text)
    return "\n".join(out)


def extract_session_id(messages: list) -> str | None:
    for m in messages:
        if isinstance(m, ResultMessage):
            return m.session_id
    return None
