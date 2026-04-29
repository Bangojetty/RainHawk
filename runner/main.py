"""Event loop. Reads instructions.md, drives the long-running Opus session, dispatches classifier/responder on each ResultMessage."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from runner.classifier import classify
from runner.notify import send_sms
from runner.responder import draft_reply
from runner.session import (
    REPO_ROOT,
    extract_assistant_text,
    extract_session_id,
    load_state,
    make_client,
    save_state,
)

ITERATION_CAP = 20
INSTRUCTIONS_PATH = REPO_ROOT / "instructions.md"
LOG_DIR = REPO_ROOT / "logs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_event(event: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"
    payload = {"ts": _now_iso(), **event}
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


async def run() -> None:
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set in environment or .env")

    instructions = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    state = load_state()
    iteration = state["iteration"]

    _log_event({"event": "start", "session_id": state["session_id"], "iteration": iteration})

    client = make_client(state["session_id"])
    async with client:
        next_prompt: str = instructions

        while True:
            if iteration >= ITERATION_CAP:
                msg = (
                    f"RainHawk iteration cap ({ITERATION_CAP}) reached without "
                    f"feature_complete. Session {state['session_id']}. "
                    f"Last classification: {state['last_classification']}."
                )
                _log_event({"event": "cap_trip", "message": msg})
                send_sms(msg)
                return

            await client.query(next_prompt)
            messages = [m async for m in client.receive_response()]

            session_id = extract_session_id(messages) or state["session_id"]
            worker_text = extract_assistant_text(messages)

            _log_event({
                "event": "turn",
                "iteration": iteration,
                "session_id": session_id,
                "worker_text_len": len(worker_text),
            })

            classification = classify(worker_text)
            _log_event({"event": "classify", "result": classification})

            iteration += 1
            state.update({
                "session_id": session_id,
                "iteration": iteration,
                "last_classification": classification["state"],
                "last_updated": _now_iso(),
            })
            save_state(state)

            if classification["state"] == "feature_complete":
                # Reset counter for the next feature. Re-feed instructions.
                iteration = 0
                state["iteration"] = 0
                save_state(state)
                next_prompt = instructions
                _log_event({"event": "feature_complete_reset"})
            elif classification["state"] == "needs_input":
                next_prompt = draft_reply(
                    classification.get("questions") or [],
                    instructions,
                )
                _log_event({"event": "respond", "reply_len": len(next_prompt)})
            else:  # in_progress
                next_prompt = "Continue with your work."


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
