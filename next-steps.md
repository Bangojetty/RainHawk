# RainHawk — Next Steps (handoff)

If you're a fresh Claude session reading this: **start by reading `PRD.md` in this folder.** It has the full design. This file is just the to-do list and any state that wouldn't be obvious from the code.

---

## What's already done

- `PRD.md` written (full architecture + decisions).
- GitHub CLI (`gh`) installed at `C:\Program Files\GitHub CLI\gh.exe` (may not be on PATH in fresh shells until terminal restart — use full path or restart terminal).
- Task list created (Install gh ✓, Resolve PRD open items ✓, plus pending tasks for auth, repo init, scaffold, etc.).

## Decisions already locked in (don't re-litigate)

- Project name: **RainHawk** (this folder is `boxslime/` for legacy reasons; new folder will be `RainHawk/`).
- GitHub repo: rename `Bangojetty/boxslime` → `Bangojetty/RainHawk`.
- Instructions file: `instructions.md` (not `chron-job-instructions.md`).
- Architecture: event-driven Python daemon using Claude Agent SDK. **Not cron.** `ResultMessage` is the "Claude is done" signal.
- Models: Opus 4.7 (long-running session), Haiku 4.5 (classifier), Sonnet 4.6 (responder).
- Inner-loop cap: 20 iterations. On trip → SMS via Twilio + halt + diagnostic.
- Logs in `logs/` are gitignored AND **must never be read back into Claude's context** (would pollute the experiment).
- Two Obsidian vaults: `vault/` at root (meta-experiment lab notebook), `projects/<name>/vault/` (Claude's per-project notes).

## To-do (in order)

### 1. Move project to new folder
- User is creating a new `RainHawk/` folder and moving `PRD.md` + this `next-steps.md` into it.
- Once moved, run subsequent steps from inside `RainHawk/`.

### 2. Auth setup
- **`gh auth login`** — interactive, user must run. Choose: GitHub.com → HTTPS → Yes (auth Git too) → Login with web browser.
- **`ANTHROPIC_API_KEY`** — DEFERRED to scaffolding (Step 5). Will live in `.env` (gitignored), loaded via `python-dotenv`. Decision: skip Windows `setx` because deploy target is Linux; one `.env` pattern works in both places. Key is only needed when the daemon runs, so no urgency before scaffolding.
- **Git identity**: confirm `git config --global user.name` and `git config --global user.email` are set; if not, set them.
- **Twilio creds** (defer until daemon is ready): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_TO_NUMBER`. Skip for initial scaffolding; wire in before deploying to remote server.

### 3. Rename the GitHub repo
- `gh repo rename Bangojetty/boxslime RainHawk` (run from anywhere once authed). GitHub auto-redirects the old URL.

### 4. Init local git repo and push
- From inside `RainHawk/`: `git init`, add files, initial commit, `git remote add origin https://github.com/Bangojetty/RainHawk.git`, `git push -u origin main`.
- Initial commit contents: `PRD.md`, `next-steps.md`, `README.md`, `.gitignore`.

### 5. Scaffold project layout (per PRD)
Create empty stubs for:
```
RainHawk/
├── runner/
│   ├── main.py
│   ├── session.py
│   ├── classifier.py
│   ├── responder.py
│   ├── prompts.py
│   └── notify.py            # Twilio SMS on cap-trip
├── vault/                   # Obsidian vault (meta)
│   └── .obsidian/           # let Obsidian create on first open
├── projects/                # populated by Claude as it builds
├── logs/                    # gitignored
├── instructions.md          # to be co-authored
├── rainhawk-state.json      # committed; current session_id, counters
├── rainhawk-state.md        # committed; per-session summaries appended
├── requirements.txt         # claude-agent-sdk, anthropic, python-dotenv, twilio
└── .gitignore               # ignores logs/, .env, __pycache__, .venv, etc.
```

### 6. Co-author `instructions.md` and the system prompt
- `instructions.md` — the "method" prompt the user defines. This is the experimental variable.
- System prompt for the long-running Opus session — must require Claude to emit a structured "feature complete and tested" sentinel that the classifier can detect. Co-author with the user.

### 7. Implement the daemon (`runner/`)
- `session.py`: wraps `claude_agent_sdk.query()`, persists session_id to `rainhawk-state.json`, resumes on restart.
- `classifier.py`: Haiku 4.5 call, structured JSON output `{state: needs_input | feature_complete | in_progress, questions: [...]}`.
- `responder.py`: Sonnet 4.6, given questions + `instructions.md` + recent context, drafts answers as user-turn input.
- `notify.py`: Twilio SMS send.
- `main.py`: event loop. Read `instructions.md` → send to session → on `ResultMessage` → classifier → branch (needs_input → responder; feature_complete → re-feed instructions; cap-trip → SMS + halt).

### 8. Smoke test
- Run daemon against a tiny throwaway instruction (e.g., "create a hello-world Python script and write a test for it"). Verify: session resumes correctly, classifier fires, responder fires if needed, ResultMessage detected, logs land in `logs/`, state persists, no context pollution.

### 9. Migrate to remote Linux server (later)
- Ensure all paths are OS-agnostic. Set up systemd unit or similar to keep daemon alive. Copy `rainhawk-state.json` to maintain session continuity, or accept a fresh session on the remote.

---

## Things that would be easy to mess up

- **Don't rename the project root** mid-run — the SDK session_id is conceptually tied to the cwd via our state file. Once the daemon is running, the folder location is locked.
- **Don't read `logs/` into Claude context** — they exist purely for human post-hoc analysis.
- **Don't commit `.env`** or any file with `ANTHROPIC_API_KEY` / Twilio creds.
- **Don't lower the iteration cap below ~10** without thinking — legitimate clarification chains can run 5–8 deep.
- The "no cron" decision was made deliberately after considering cron — re-introducing cron means re-introducing lockfiles and overlap handling. Don't.

## Open authoring items (not yet started)

- `instructions.md` content — user defines.
- Long-running session system prompt — co-author with user.
- Twilio account setup — user creates account, provides creds.
