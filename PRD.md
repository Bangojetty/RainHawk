# RainHawk — PRD

Index: [[index]]

## Purpose

Test instruction strategies for **fully autonomous** AI software development. RainHawk is the meta-experiment; the codebases Claude builds are sub-projects that serve as experimental data points on which strategies (instruction prompts, brainstorming methods) work and which don't.

README descriptor: *To determine optimal/effective instructions for high-level feature implementation generated using arbitrary/unique brainstorming methods.*

No human in the loop during a run. The instructions file itself is the safety mechanism — it's authored to prevent hallucination by design, so the responder can answer Claude's questions autonomously without escalating.

## Architecture (event-driven daemon, not cron)

One long-running Python process. Internally an infinite event loop driven by Claude Agent SDK message events.

```
              ┌─────────────────────────────────────┐
              │   Long-running Claude session       │
              │   (Agent SDK, Opus 4.7,             │
              │    resumed via session_id)          │
              └────────────────┬────────────────────┘
                               │ ResultMessage = turn done
                               ▼
                       ┌──────────────┐
                       │  Classifier  │  Haiku 4.5, JSON output:
                       │              │  { state, questions }
                       └──────┬───────┘
                              │
            ┌─────────────────┼──────────────────┐
            │                 │                  │
       needs_input      feature_complete     in_progress*
            │                 │                  │
            ▼                 ▼                  ▼
       ┌─────────┐     ┌────────────┐      (treat as needs_input
       │Responder│     │Re-feed     │       w/ "what's next?")
       │Sonnet4.6│     │instructions│
       │drafts   │     │.md as next │
       │answer   │     │user turn   │
       └────┬────┘     └─────┬──────┘
            │                │
            └────────┬───────┘
                     ▼
            send as next user turn ─► back to top
```

`ResultMessage` is the unambiguous "Claude is done with this turn" signal — no heuristics, no parsing.

The long-running session has a **system prompt** instructing Claude to emit a structured "feature complete and tested" marker when it finishes a feature implementation. The classifier looks for that marker (and for question-asking patterns) to decide which branch to take.

## Components

| Component | Model | Job |
|---|---|---|
| Long-running session | claude-opus-4-7 | Builds the sub-project — designs PRD, roadmaps, implements features, tests |
| Classifier | claude-haiku-4-5 | Reads last assistant turn → returns `{state: needs_input \| feature_complete \| in_progress, questions: [...]}` |
| Responder | claude-sonnet-4-6 | Given questions + `instructions.md`, drafts answers as the next user turn |

## File layout

```
RainHawk/
├── PRD.md                        ← this file
├── README.md
├── instructions.md               ← user-authored; the "method"
├── runner/
│   ├── main.py                   ← daemon entry
│   ├── session.py                ← Agent SDK wrapper, resume logic
│   ├── classifier.py
│   ├── responder.py
│   └── prompts.py                ← system prompts, classifier prompts
├── vault/                        ← Obsidian vault for RainHawk meta-experiment
│   ├── .obsidian/
│   ├── strategies/               ← variants of instruction prompts
│   └── observations/             ← analysis: what worked, what didn't
├── projects/                     ← Claude-built sub-projects
│   └── <sub-project-name>/
│       ├── vault/                ← per-project Obsidian vault (Claude's notes)
│       └── ...                   ← actual source code Claude writes
├── logs/                         ← gitignored, NEVER read back into Claude context
│   └── <session-id>/
│       ├── transcript.jsonl
│       ├── classifier.jsonl
│       └── responder.jsonl
├── rainhawk-state.json           ← committed; current session_id, sub-project, counters
├── rainhawk-state.md             ← committed; appended human-readable session summaries
├── requirements.txt
└── .gitignore
```

### Why two vaults

- **`vault/`** at the root is *your* lab notebook — meta-analysis across runs: which instructions yielded better results, theories, comparisons.
- **`projects/<name>/vault/`** is Claude's working notebook for that specific sub-project — design notes, decisions, scratchpad.

Different purposes → different vaults. Keeps the meta-experiment vault from being polluted by per-project working notes.

## State & logs

- **`rainhawk-state.json`** (committed): machine state — current `session_id`, current sub-project name, iteration counts, classifier-verdict tally. Required for daemon restart / server migration.
- **`rainhawk-state.md`** (committed): append-only human-readable summary at the end of each session. Per user request.
- **`logs/`** (gitignored): full transcripts, classifier outputs, responder outputs. Saved for **post-hoc analysis only** — must never be read back into Claude's context (would pollute the experiment with prior runs' framing).

## Auth & setup (one-time)

- `ANTHROPIC_API_KEY` env var (from console.anthropic.com)
- `gh` CLI installed + `gh auth login`
- `git config --global user.name` / `user.email`
- **Twilio** (or equivalent SMS provider) credentials for cap-trip alerts: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_TO_NUMBER`

Starts on Windows, eventually moves to a Linux server with 100% uptime. Script must stay OS-agnostic — pure Python, no shell-isms.

## Caveats learned during design

- **Claude Code stores sessions per-directory** under `.claude/projects/<encoded-path>/...`. Renaming the project root breaks session continuity (this PRD exists partly because that happened during design). Once the daemon is running, **do not rename or move the project directory** — the session_id maps to the cwd through Anthropic's session store.
- The Agent SDK's session is independent of Claude Code's interactive session, but the same "don't move it mid-run" discipline applies to our state file.

## Resolved decisions

1. **Local directory.** User will create a new `RainHawk/` folder and move the PRD into it. The current `boxslime/` directory is the design-phase scratch space; the project lives in `RainHawk/` going forward.
2. **GitHub repo.** Renaming `Bangojetty/boxslime` → `Bangojetty/RainHawk` (auto-redirects).
3. **Instructions filename.** `instructions.md`.
4. **Inner-loop safety cap.** **20 iterations**. On cap-trip: send SMS via Twilio, write diagnostic to `rainhawk-state.md`, halt the daemon.

## Still to draft

- **System prompt** for the long-running session (with the structured "feature complete and tested" sentinel the classifier looks for) — to be co-authored alongside `instructions.md`.

## Design assumptions worth flagging

- Classifier emits one of `needs_input | feature_complete | in_progress`. `in_progress` shouldn't normally fire after a `ResultMessage` (the turn is over), but if it does, the daemon treats it as `needs_input` with a synthetic prompt of "what's next?". If this branch fires often in practice, revisit the classifier prompt.
- The responder is fully autonomous (no human escalation). This is safe **only** to the extent that `instructions.md` is authored to make the answers unambiguous. The instructions file is the experiment's load-bearing artifact — quality of the experiment depends on its quality.

## Roadmap

1. ~~Install `gh`~~ ✓ (installed at `C:\Program Files\GitHub CLI\gh.exe`).
2. Auth setup: run `gh auth login`, set `ANTHROPIC_API_KEY`, confirm git identity, (Twilio creds deferred).
3. Rename GitHub repo `Bangojetty/boxslime` → `Bangojetty/RainHawk`.
4. Init local git repo in `RainHawk/`, initial commit, push to renamed remote.
5. Scaffold file layout above (empty stubs).
6. Co-author `instructions.md` and the long-running session's system prompt.
7. Write the daemon (`runner/`).
8. Smoke test on a tiny instruction.
9. Migrate to remote Linux server.
