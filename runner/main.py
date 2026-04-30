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

ITERATION_CAP = 20  # per-feature: SMS + halt if the worker spins this long without feature_complete
FEATURE_CAP = 20    # per-run:     clean halt (no SMS) after this many features completed
INSTRUCTIONS_PATH = REPO_ROOT / "instructions.md"
LOG_DIR = REPO_ROOT / "logs"
PID_FILE = REPO_ROOT / ".daemon.pid"


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
    # Pop the API key out of the process env before the SDK spawns its CLI
    # subprocess. The CLI prefers ANTHROPIC_API_KEY over OAuth/keychain when
    # it sees one (per `claude --bare` docs), so to make the worker use the
    # Claude subscription we must hide the key from the subprocess.
    # Classifier and responder still need it; we pass it explicitly to them.
    api_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set in environment or .env")

    instructions = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    state = load_state()
    iteration = state["iteration"]
    features_completed = state.get("features_completed", 0)

    _log_event({
        "event": "start",
        "session_id": state["session_id"],
        "iteration": iteration,
        "features_completed": features_completed,
        "auth": "worker=subscription (via Claude CLI OAuth), classifier/responder=ANTHROPIC_API_KEY",
    })

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

            classification = classify(worker_text, api_key)
            _log_event({"event": "classify", "result": classification})

            iteration += 1
            state.update({
                "session_id": session_id,
                "iteration": iteration,
                "last_classification": classification["state"],
                "last_updated": _now_iso(),
                "features_completed": features_completed,
            })
            save_state(state)

            if classification["state"] == "feature_complete":
                features_completed += 1
                state["features_completed"] = features_completed
                save_state(state)
                _log_event({"event": "feature_complete", "features_completed": features_completed})

                if features_completed >= FEATURE_CAP:
                    _log_event({
                        "event": "feature_cap_reached",
                        "message": f"Run complete: {features_completed}/{FEATURE_CAP} features delivered. Halting cleanly.",
                    })
                    return

                # Reset per-feature iteration counter, re-feed instructions for the next feature.
                iteration = 0
                state["iteration"] = 0
                save_state(state)
                next_prompt = instructions
                _log_event({"event": "feature_complete_reset"})
            elif classification["state"] == "needs_input":
                next_prompt = draft_reply(
                    classification.get("questions") or [],
                    instructions,
                    api_key,
                )
                _log_event({"event": "respond", "reply_len": len(next_prompt)})
            else:  # in_progress
                next_prompt = "Continue with your work."


def main() -> None:
    PID_FILE.write_text(str(os.getpid()))
    try:
        asyncio.run(run())
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
