"""Twilio SMS sender. Fired on iteration cap-trip with a diagnostic payload."""
from __future__ import annotations

import os
import sys

from twilio.rest import Client


def send_sms(body: str) -> None:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    to_number = os.environ.get("TWILIO_TO_NUMBER")

    if not all([sid, token, from_number, to_number]):
        # Twilio not configured — print so the daemon can still halt cleanly
        # during local development. Production deploy must set all four.
        print(f"[notify] Twilio not configured. Would have sent: {body}", file=sys.stderr, flush=True)
        return

    Client(sid, token).messages.create(
        body=body[:1500],
        from_=from_number,
        to=to_number,
    )
