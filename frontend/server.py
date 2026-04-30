"""FastAPI server for the RainHawk control panel.

Supervises the daemon as a subprocess (start/stop), exposes daemon state
and a Server-Sent Events stream of log entries, and serves the static UI.

Run with: python -m frontend.server  (or via serve.bat / serve.sh)
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "rainhawk-state.json"
LOG_DIR = REPO_ROOT / "logs"
PID_FILE = REPO_ROOT / ".daemon.pid"
FEATURESUM_DIR = REPO_ROOT / "featuresum"
PROJECTS_DIR = REPO_ROOT / "projects"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="RainHawk Control Panel")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---- daemon supervision ------------------------------------------------------

_supervised_proc: subprocess.Popen | None = None


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            # signal 0 doesn't work on Windows; use OpenProcess via os.kill which
            # raises OSError(EINVAL) for live processes given signal 0... actually
            # the simplest reliable check on Windows is the tasklist call.
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def _daemon_status() -> dict:
    pid = _read_pid()
    running = bool(pid and _process_alive(pid))
    if pid and not running:
        # stale pid file — clean up
        PID_FILE.unlink(missing_ok=True)
        pid = None
    return {"running": running, "pid": pid}


# ---- helpers -----------------------------------------------------------------


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _current_project() -> str | None:
    """Most recently-modified directory under projects/. Best-effort guess for the active project."""
    if not PROJECTS_DIR.exists():
        return None
    candidates = [p for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def _today_log_path() -> Path:
    return LOG_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"


# ---- API ---------------------------------------------------------------------


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def api_status() -> dict:
    return {
        "daemon": _daemon_status(),
        "state": _load_state(),
        "current_project": _current_project(),
        "now": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/start")
def api_start() -> dict:
    global _supervised_proc
    status = _daemon_status()
    if status["running"]:
        raise HTTPException(status_code=409, detail=f"Daemon already running (pid {status['pid']})")

    venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python if venv_python.exists() else sys.executable)

    creationflags = 0
    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP so we can send Ctrl+Break for graceful shutdown.
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    _supervised_proc = subprocess.Popen(
        [python_exe, "-m", "runner.main"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return {"started": True, "pid": _supervised_proc.pid}


@app.post("/api/stop")
def api_stop() -> dict:
    global _supervised_proc
    pid = _read_pid()
    if not pid or not _process_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return {"stopped": False, "reason": "no running daemon"}

    try:
        if sys.platform == "win32":
            # Ask politely first, then escalate.
            try:
                os.kill(pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            except (OSError, AttributeError):
                pass
            # Give it a moment, then taskkill if still alive.
            import time
            for _ in range(10):
                if not _process_alive(pid):
                    break
                time.sleep(0.3)
            if _process_alive(pid):
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
    finally:
        PID_FILE.unlink(missing_ok=True)
        _supervised_proc = None
    return {"stopped": True, "pid": pid}


@app.get("/api/featuresums")
def api_featuresums() -> list[dict]:
    if not FEATURESUM_DIR.exists():
        return []
    files = sorted(
        (f for f in FEATURESUM_DIR.glob("*.md")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {"name": f.name, "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()}
        for f in files
    ]


@app.get("/api/featuresums/{name}")
def api_featuresum(name: str) -> dict:
    if "/" in name or ".." in name or "\\" in name:
        raise HTTPException(status_code=400, detail="invalid name")
    path = FEATURESUM_DIR / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return {"name": name, "content": path.read_text(encoding="utf-8")}


@app.get("/api/events")
async def api_events() -> StreamingResponse:
    """SSE stream of log events. Replays today's log on connect, then tails for new lines."""

    async def stream() -> AsyncIterator[bytes]:
        log_path = _today_log_path()
        # Replay existing lines first
        last_size = 0
        if log_path.exists():
            try:
                content = log_path.read_text(encoding="utf-8")
                last_size = len(content.encode("utf-8"))
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        yield f"data: {line}\n\n".encode("utf-8")
            except OSError:
                pass

        # Then tail the file
        while True:
            await asyncio.sleep(1.0)
            current_path = _today_log_path()
            if current_path != log_path:
                # Day rolled over to a new log file
                log_path = current_path
                last_size = 0
                if not log_path.exists():
                    continue

            if not log_path.exists():
                continue

            try:
                size = log_path.stat().st_size
            except OSError:
                continue

            if size <= last_size:
                # heartbeat to keep the connection open
                yield b": heartbeat\n\n"
                continue

            try:
                with log_path.open("rb") as f:
                    f.seek(last_size)
                    chunk = f.read()
                last_size = size
                text = chunk.decode("utf-8", errors="replace")
                for line in text.splitlines():
                    line = line.strip()
                    if line:
                        yield f"data: {line}\n\n".encode("utf-8")
            except OSError:
                continue

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    import uvicorn
    uvicorn.run(
        "frontend.server:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
