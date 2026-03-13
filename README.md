# claude-working-memory

*Made by [Torus Framework](https://github.com/OZmasterAI/torus-framework)*

**Never lose context in long Claude Code sessions again.**

A lightweight plugin for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that automatically detects when your conversation is approaching the context window limit, warns you, and ensures Claude writes a structured summary before compaction wipes your working state. After compaction or `/clear`, the summary persists just long enough for Claude to re-orient, then auto-clears for the next cycle.

Zero external dependencies. Four small Python scripts. Works with any Claude Code setup.

### Why you need this

Long Claude Code sessions have a hidden failure mode: **context amnesia**. You spend 30 minutes debugging, making decisions, building up shared understanding — then the context window fills up. Claude Code compacts or you `/clear`, and suddenly Claude doesn't know what you were doing, which files matter, what you already tried, or what's left. You waste time re-explaining, Claude re-reads files it already understood, and decisions get relitigated.

This plugin creates a **structured handoff document** — Goal, Approach, Progress, Key Files, Decisions, Next Steps — that survives context resets. Claude writes it when context gets high, reads it after clearing, and picks up exactly where it left off. The gate ensures Claude actually writes the summary before getting distracted by your next request. The countdown ensures the summary cleans itself up when it's no longer needed.

**The result:** seamless continuity across context boundaries. No more "what were we doing?" after `/clear`.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Installation Options](#installation-options)
- [What Gets Installed](#what-gets-installed)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Accurate Context Tracking](#accurate-context-tracking)
- [Architecture](#architecture)
- [Example Summary](#example-summary)
- [Troubleshooting](#troubleshooting)
- [Uninstalling](#uninstalling)
- [Requirements](#requirements)
- [License](#license)

---

## How It Works

The plugin operates on a simple cycle:

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                        SESSION LIFECYCLE                        │
  └─────────────────────────────────────────────────────────────────┘

  1. SESSION START
     You start working. Context is empty.
     working-summary.md contains: "(awaiting threshold)"

  2. WORKING...
     You chat, read files, edit code, run tests.
     Context window fills up gradually.

  3. THRESHOLD HIT (65% context or ~80 turns)
     ┌──────────────────────────────────────────────────────────────┐
     │  [WORKING SUMMARY] Context at ~65%.                          │
     │  Run /working-summary to save context,                       │
     │  then consider /clear.                                       │
     └──────────────────────────────────────────────────────────────┘
     → You see this warning
     → Edit/Write/Bash are BLOCKED until summary is written
     → Read/Grep/Glob/Skill still work (Claude needs them to gather context)

  4. CLAUDE WRITES SUMMARY
     You (or Claude automatically) run /working-summary.
     Claude reviews the conversation and writes a structured summary:
       Goal, Approach, Progress, Key Files, Decisions, Next Steps
     → File exceeds 2000 chars → gate UNBLOCKS → you resume working

  5. COMPACTION or /clear
     Context gets cleared. But working-summary.md survives on disk.
     Claude reads it on the next turn and knows exactly where you left off.

  6. POST-CLEAR (5 turns)
     The summary persists for 5 more turns so Claude stays oriented.
     On turn 6, it auto-clears to "(awaiting threshold)".

  7. NEXT CYCLE
     Context fills up again → threshold fires → new summary written.
     The cycle repeats for as long as you work.
```

---

## Quick Start

```bash
git clone https://github.com/YOUR_USER/claude-working-memory.git
cd claude-working-memory
bash install.sh
```

That's it. Start a Claude Code session and work normally. When context hits ~65%, you'll see the warning and `/working-summary` becomes available.

---

## Installation Options

Three ways to install — pick whichever fits your workflow:

### Option 1: Bash Script

Best for: most users.

```bash
git clone https://github.com/YOUR_USER/claude-working-memory.git
cd claude-working-memory
bash install.sh
```

The script creates directories, copies hooks, merges hook registrations into your existing `settings.json` (won't overwrite your other hooks), and appends a behavioral rule to `CLAUDE.md`.

### Option 2: Single-File Python Installer

Best for: users who don't want to clone a repo. All source code is embedded in one file.

```bash
# Download install.py (or copy it from the repo)
python3 install.py
```

### Option 3: Claude Code Custom Command

Best for: letting Claude do the installation for you.

```bash
mkdir -p ~/.claude/commands
cp commands/install-working-summary.md ~/.claude/commands/
```

Then in Claude Code, type `/install-working-summary`. Claude reads the command file and creates all the files itself.

---

## What Gets Installed

```
~/.claude/
├── hooks/working-summary/
│   ├── pre_tool_use.py           # PreToolUse — blocks gated tools until summary written
│   ├── user_prompt_submit.py     # UserPromptSubmit — threshold detection + countdown
│   ├── pre_compact.py            # PreCompact — starts post-compaction countdown
│   ├── statusline.py             # Optional — accurate context % capture
│   └── state.json                # Plugin state (auto-managed, don't edit)
├── skills/working-summary/
│   └── SKILL.md                  # /working-summary skill definition
├── rules/
│   └── working-summary.md        # The summary file (Claude writes this)
├── settings.json                 # 3 hook entries added (merged with existing)
└── CLAUDE.md                     # 1 behavioral rule appended
```

**Nothing outside `~/.claude/` is touched.** The plugin is fully contained in your Claude Code config directory.

---

## Usage Guide

### Normal workflow

You don't need to do anything different. Work normally. The plugin runs silently in the background until the threshold fires.

### When the warning appears

You'll see:
```
[WORKING SUMMARY] Context at ~65%. Run /working-summary to save context, then consider /clear.
```

At this point, Edit/Write/Bash are blocked. Claude sees the warning too (via a `<working-memory-warning>` XML tag in stdout) and will automatically run `/working-summary` if the behavioral rule is in your `CLAUDE.md`. Once the summary exceeds 2000 characters, all tools unblock and you continue working.

### After /clear or compaction

The summary persists for 5 turns. During these turns, Claude reads it automatically (it's in `rules/`, which Claude Code loads every turn). By turn 6, the file auto-clears — lean and ready for the next cycle.

### Manual use

You can run `/working-summary` at any time, not just at the threshold. Useful when:
- You're about to `/clear` and want to preserve context
- You're switching tasks and want a checkpoint
- You want to capture a complex decision before you forget the reasoning

---

## Configuration

All settings are constants at the top of each hook file. Edit them in `~/.claude/hooks/working-summary/`:

| Setting | Default | File | What it controls |
|---------|---------|------|-----------------|
| `THRESHOLD_PCT` | `65` | `user_prompt_submit.py` | Context % that triggers the warning. Lower = earlier warning. |
| `TURN_FALLBACK` | `80` | `user_prompt_submit.py` | Fallback turn count if context % isn't available. |
| `MIN_CHARS` | `2000` | `pre_tool_use.py` | Min summary size (chars) to unblock tools. 2000 chars ≈ 500 tokens. |
| Countdown | `5` | `pre_compact.py` | Turns the summary persists after compaction. |

### Tuning tips

- **Short sessions** (< 30 min): Raise `THRESHOLD_PCT` to 75 or `TURN_FALLBACK` to 100.
- **Long complex sessions**: Lower `THRESHOLD_PCT` to 55-60 for earlier warnings.
- **Frequent `/clear` users**: Lower countdown to 3.
- **Want longer summaries**: Raise `MIN_CHARS` to 3000-4000.

---

## Accurate Context Tracking

By default, the plugin counts turns as a proxy for context usage. This works but isn't precise — a turn with a long code review uses more context than a turn with "yes".

For exact tracking, add the included statusline script to your `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "command": "python3 ~/.claude/hooks/working-summary/statusline.py"
  }
}
```

You'll see `ctx:42%` in your status bar, and the threshold fires at exactly 65%.

**If you already have a statusline**, add this to your existing script to feed context % into the plugin:

```python
# Add to your statusline script
pct = data.get("context_window", {}).get("used_percentage", 0)
state_path = os.path.expanduser("~/.claude/hooks/working-summary/state.json")
try:
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    state["context_pct"] = round(pct)
    with open(state_path, "w") as f:
        json.dump(state, f)
except Exception:
    pass
```

---

## Architecture

### How the pieces connect

```
                    ┌─────────────────────┐
                    │   Claude Code CLI    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                     │
          ▼                    ▼                     ▼
 ┌─────────────────┐ ┌─────────────────┐  ┌─────────────────┐
 │ UserPromptSubmit │ │   PreToolUse    │  │   PreCompact    │
 │                  │ │                 │  │                 │
 │ Every turn:      │ │ Every tool call:│  │ On compaction:  │
 │ • Count turns    │ │ • Check fired   │  │ • countdown = 5 │
 │ • Check context %│ │ • Check summary │  │ • fired = false │
 │ • Fire threshold │ │   size < 2000?  │  │ • turns = 0     │
 │ • Run countdown  │ │   → BLOCK       │  │                 │
 └────────┬────────┘ └────────┬────────┘  └────────┬────────┘
          │                    │                     │
          └────────────────────┼─────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │     state.json      │
                    │                     │
                    │ threshold_fired: T/F│
                    │ countdown: -1 to 5  │
                    │ turns: 0+           │
                    │ context_pct: 0-100  │
                    └─────────────────────┘
```

### What gets blocked vs allowed

When the threshold fires and the summary hasn't been written:

| Blocked | Allowed | Why allowed |
|---------|---------|-------------|
| Edit | Read | Claude needs to read files to write the summary |
| Write | Grep, Glob | Same — search tools for gathering context |
| Bash | Skill | Needed to invoke `/working-summary` |
| NotebookEdit | WebSearch, WebFetch | May need to reference docs |
| Task | `mcp__*` | MCP tools shouldn't be blocked |

**Exception:** Write to `working-summary.md` itself is always allowed (Claude needs to write the summary to unblock).

### Fail-open design

Every hook is wrapped in `try/except` → `sys.exit(0)`. If anything goes wrong — corrupted state, permission error, missing file — the plugin silently allows everything through. It will **never** crash your session or block you permanently.

---

## Example Summary

When `/working-summary` fires, Claude writes something like this:

```markdown
# Working Summary (Claude-written at context threshold)

## Goal
Implementing OAuth2 PKCE flow for the mobile app, replacing the legacy
API key authentication being deprecated in Q2.

## Approach
Authorization Code flow with PKCE (SHA256 code challenge). Chose over
Implicit flow because PKCE is current best practice for public clients.

## Progress
### Completed
- Token endpoint (src/auth/oauth.py:23-89)
- PKCE challenge generation (src/auth/pkce.py:12-45)
- Encrypted token storage (src/auth/storage.py:8-34)
- 12 unit tests passing (tests/test_oauth.py)
### In Progress
- Refresh token rotation — endpoint works, wiring into HTTP client
### Remaining
- Login screen UI update
- Integration tests against staging
- Migration guide for existing users

## Key Files
- src/auth/oauth.py — Token exchange and refresh logic
- src/auth/pkce.py — Code verifier/challenge generation
- src/api/client.py — HTTP client (needs Bearer token update)

## Decisions & Rationale
- PKCE over Implicit: Implicit is deprecated in OAuth 2.1
- Keychain over encrypted file: OS-level security, no key management
- SHA256 over plain: Required by OAuth server, more secure

## Gotchas & Errors
- Staging server rejects code_verifier with trailing `=` padding
- Refresh endpoint requires client_id even for public clients (non-standard)

## Next Steps (post-compaction)
1. Wire refresh rotation into src/api/client.py
2. Add PKCE challenge to login screen authorization URL
3. Integration tests against staging
4. Write migration guide
```

---

## Troubleshooting

### "I never see the warning"
Check `~/.claude/hooks/working-summary/state.json`. If `turns` is low, you haven't hit the threshold. If `context_pct` is `0`, set up the [statusline](#accurate-context-tracking) or lower `TURN_FALLBACK`.

### "Claude is blocked and can't do anything"
Run `/working-summary`. If that doesn't work, reset manually:
```bash
echo '{"threshold_fired":false,"countdown":-1,"turns":0,"context_pct":0}' > ~/.claude/hooks/working-summary/state.json
```

### "The summary is too short"
Raise `MIN_CHARS` in `pre_tool_use.py` (default: 2000). Higher values force Claude to write more detail.

### "The installer broke my existing hooks"
The installer appends to hook arrays, never overwrites. Check `~/.claude/settings.json` for duplicates and remove them manually.

---

## Uninstalling

```bash
# Option A
bash uninstall.sh

# Option B
python3 install.py --uninstall
```

Both remove hooks, skill, rules file, and clean `settings.json`. The `CLAUDE.md` rule is left in place — remove it manually if desired.

---

## Requirements

- **Claude Code** with [hooks support](https://docs.anthropic.com/en/docs/claude-code/hooks)
- **Python 3.8+**
- **No external dependencies** — standard library only (`json`, `os`, `sys`)

---

## License

MIT
