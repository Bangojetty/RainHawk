"""Sonnet 4.6 responder. Drafts a user-turn reply for the worker."""
from __future__ import annotations

from anthropic import Anthropic

from runner.prompts import RESPONDER_SYSTEM_PROMPT

RESPONDER_MODEL = "claude-sonnet-4-6"


def draft_reply(questions: list[str], instructions_text: str) -> str:
    if not questions:
        return "Continue with your work."

    bulleted = "\n".join(f"- {q}" for q in questions)
    user_msg = (
        "Active strategy (instructions.md):\n\n"
        f"```\n{instructions_text}\n```\n\n"
        "Worker's questions:\n"
        f"{bulleted}\n\n"
        "Draft the worker's next user-turn reply."
    )

    client = Anthropic()
    resp = client.messages.create(
        model=RESPONDER_MODEL,
        max_tokens=1024,
        system=RESPONDER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text.strip()
