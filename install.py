#!/usr/bin/env python3
"""claude-working-memory — Single-file installer.

Downloads nothing. All source code is embedded below.
Usage: python3 install.py [--uninstall]
"""

import json
import os
import sys

CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
HOOK_DIR = os.path.join(CLAUDE_DIR, "hooks", "working-summary")
SKILL_DIR = os.path.join(CLAUDE_DIR, "skills", "working-summary")
RULES_DIR = os.path.join(CLAUDE_DIR, "rules")
SETTINGS = os.path.join(CLAUDE_DIR, "settings.json")

# ── Embedded source files ────────────────────────────────────────────────────

PRE_TOOL_USE_PY = r'''#!/usr/bin/env python3
"""PreToolUse hook: blocks Edit/Write/Bash until working summary is written."""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SUMMARY_PATH = os.path.join(os.path.expanduser("~"), ".claude", "rules", "working-summary.md")
MIN_CHARS = 2000

GATED_TOOLS = {"Edit", "Write", "NotebookEdit", "Bash", "Task"}
ALWAYS_ALLOWED = {"Read", "Grep", "Glob", "WebSearch", "WebFetch", "Skill"}


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    state = load_state()

    if not state.get("threshold_fired"):
        sys.exit(0)

    if tool in ALWAYS_ALLOWED or tool.startswith("mcp__"):
        sys.exit(0)

    if tool not in GATED_TOOLS:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if file_path and os.path.basename(file_path) == "working-summary.md":
        sys.exit(0)

    try:
        size = os.path.getsize(SUMMARY_PATH)
    except OSError:
        size = 0

    if size >= MIN_CHARS:
        sys.exit(0)

    msg = (
        "[WORKING SUMMARY] Context threshold reached. "
        "Run /working-summary to save context before continuing."
    )
    print(json.dumps({"decision": "block", "reason": msg}))
    sys.exit(2)

except Exception:
    sys.exit(0)
'''

USER_PROMPT_SUBMIT_PY = r'''#!/usr/bin/env python3
"""UserPromptSubmit hook: threshold detection + countdown timer."""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SUMMARY_PATH = os.path.join(
    os.path.expanduser("~"), ".claude", "rules", "working-summary.md"
)
THRESHOLD_PCT = 65
TURN_FALLBACK = 80

STUB = (
    "# Working Summary (Claude-written at context threshold)\n"
    "<!-- Auto-managed. Claude writes at ~65% context. -->\n"
    "(awaiting threshold)\n"
)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"threshold_fired": False, "countdown": -1, "turns": 0, "context_pct": 0}


def save_state(state):
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


try:
    data = json.load(sys.stdin)
    state = load_state()

    state["turns"] = state.get("turns", 0) + 1

    pct = state.get("context_pct", 0)
    fired = state.get("threshold_fired", False)

    if not fired:
        if pct > 0:
            should_fire = pct >= THRESHOLD_PCT
        else:
            should_fire = state["turns"] >= TURN_FALLBACK

        if should_fire:
            display = f"~{pct}%" if pct > 0 else f"~{state['turns']} turns"
            print(
                f"<working-memory-warning>[WORKING SUMMARY] Context at {display}. "
                f"Run /working-summary to save context, then consider /clear."
                f"</working-memory-warning>"
            )
            state["threshold_fired"] = True

    countdown = state.get("countdown", -1)
    if countdown > 0:
        state["countdown"] = countdown - 1
    elif countdown == 0:
        try:
            with open(SUMMARY_PATH, "w") as f:
                f.write(STUB)
        except Exception:
            pass
        state["countdown"] = -1

    save_state(state)

except Exception:
    pass

sys.exit(0)
'''

PRE_COMPACT_PY = r'''#!/usr/bin/env python3
"""PreCompact hook: start countdown to clear working summary after compaction."""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

try:
    state = {}
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except Exception:
        pass

    state["countdown"] = 5
    state["threshold_fired"] = False
    state["turns"] = 0

    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

    print("[Working Summary] Countdown started (5 turns post-compaction)", file=sys.stderr)
except Exception:
    pass

sys.exit(0)
'''

STATUSLINE_PY = r'''#!/usr/bin/env python3
"""Optional statusline: captures real context_pct from Claude Code."""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

try:
    data = json.load(sys.stdin)
    pct = data.get("context_window", {}).get("used_percentage", 0)

    state = {}
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except Exception:
        pass

    state["context_pct"] = round(pct)

    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

    print(f"ctx:{pct:.0f}%")
except Exception:
    pass
'''

SKILL_MD = r"""# /working-summary — Write Context Summary Before Compaction

## When to use
Triggered automatically when context reaches ~65% threshold, or manually
when the user says "working summary", "write summary", "save context".

## Steps
1. **GATHER CONTEXT** — Review the current conversation:
   - What was the original goal/task?
   - What approach was chosen and why?
   - What progress has been made? What's done vs in-progress?
   - What key files were read or modified?
   - What errors/gotchas were encountered?
   - What decisions were made and their rationale?
   - What code snippets would save re-reading files post-compaction?
   - Did the user correct any behaviors during this session?

2. **WRITE SUMMARY** — Write `~/.claude/rules/working-summary.md` with this structure:

   # Working Summary (Claude-written at context threshold)

   ## Goal
   [1-2 sentences: what the user asked for]

   ## Approach
   [2-3 sentences: chosen strategy and why]

   ## Progress
   ### Completed
   - [bullet list of completed items with file:line references]
   ### In Progress
   - [current task and its state]
   ### Remaining
   - [ordered list of what's left]

   ## Key Files
   - [file paths with 1-line description of role/changes]

   ## Decisions & Rationale
   - [decision]: [why, what alternatives were rejected]

   ## Gotchas & Errors
   - [things that went wrong, workarounds found]

   ## Key Code
   [2-3 snippets of code created/modified THIS session that save re-reading files]
   [Format: `file:line` — signature or constant, 1-line what it does]
   [Prefer: signatures, constants, data structures. Skip: full bodies, unchanged code]

   ## User Corrections
   [Behavioral corrections from the user during this session]
   [Things like: "don't implement before discussing", "ask before acting"]
   [Only include corrections — not preferences already in CLAUDE.md]

   ## Next Steps (post-compaction)
   - [ordered priority list of what to do next]

3. **VERIFY SIZE** — Check that the written file is 2000-10000 chars (500-2500 tokens).
   If under 2000 chars, add more detail. If over 10000 chars, trim to essentials.

4. **CONFIRM** — Print: "[WORKING SUMMARY] Written (N chars). Context preserved for compaction."
"""

SUMMARY_STUB = (
    "# Working Summary (Claude-written at context threshold)\n"
    "<!-- Auto-managed. Claude writes at ~65% context. -->\n"
    "(awaiting threshold)\n"
)

CLAUDE_MD_RULE = (
    "\n9. **Working summary** — When you see `<working-memory-warning>`, "
    "immediately run /working-summary before continuing other work. "
    "Do not dismiss or defer.\n"
)

DEFAULT_STATE = (
    '{"threshold_fired": false, "countdown": -1, "turns": 0, "context_pct": 0}'
)


# ── Installer ────────────────────────────────────────────────────────────────


def install():
    print("=== claude-working-memory installer ===\n")

    # 1. Directories
    print("[1/5] Creating directories...")
    os.makedirs(HOOK_DIR, exist_ok=True)
    os.makedirs(SKILL_DIR, exist_ok=True)
    os.makedirs(RULES_DIR, exist_ok=True)

    # 2. Hooks
    print("[2/5] Installing hooks...")
    files = {
        "pre_tool_use.py": PRE_TOOL_USE_PY,
        "user_prompt_submit.py": USER_PROMPT_SUBMIT_PY,
        "pre_compact.py": PRE_COMPACT_PY,
        "statusline.py": STATUSLINE_PY,
        "state.json": DEFAULT_STATE,
    }
    for name, content in files.items():
        path = os.path.join(HOOK_DIR, name)
        with open(path, "w") as f:
            f.write(content.lstrip("\n"))
        print(f"  {path}")

    # 3. Skill + stub
    print("[3/5] Installing skill and rules...")
    with open(os.path.join(SKILL_DIR, "SKILL.md"), "w") as f:
        f.write(SKILL_MD.lstrip("\n"))
    with open(os.path.join(RULES_DIR, "working-summary.md"), "w") as f:
        f.write(SUMMARY_STUB)

    # 4. Settings.json
    print("[4/5] Updating settings.json...")
    settings = {}
    if os.path.exists(SETTINGS):
        with open(SETTINGS) as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})
    new_hooks = {
        "PreToolUse": {
            "matcher": "",
            "command": "python3 ~/.claude/hooks/working-summary/pre_tool_use.py",
        },
        "UserPromptSubmit": {
            "matcher": "",
            "command": "python3 ~/.claude/hooks/working-summary/user_prompt_submit.py",
        },
        "PreCompact": {
            "matcher": "",
            "command": "python3 ~/.claude/hooks/working-summary/pre_compact.py",
        },
    }
    for event, entry in new_hooks.items():
        existing = hooks.get(event, [])
        if not any(entry["command"] in e.get("command", "") for e in existing):
            existing.append(entry)
        hooks[event] = existing

    settings["hooks"] = hooks
    with open(SETTINGS, "w") as f:
        json.dump(settings, f, indent=2)
    print(f"  Updated {SETTINGS}")

    # 5. CLAUDE.md rule
    print("[5/5] Adding CLAUDE.md rule...")
    claude_md = os.path.join(CLAUDE_DIR, "CLAUDE.md")
    if os.path.exists(claude_md):
        with open(claude_md) as f:
            content = f.read()
        if "working-memory-warning" not in content:
            with open(claude_md, "a") as f:
                f.write(CLAUDE_MD_RULE)
            print("  Appended rule")
        else:
            print("  Rule already exists")
    else:
        with open(claude_md, "w") as f:
            f.write("# Claude Code Instructions\n\n## Behavioral Rules\n")
            f.write(CLAUDE_MD_RULE)
        print("  Created CLAUDE.md")

    print("\n=== Installation complete ===")
    print(f"\n  Hooks:   {HOOK_DIR}/")
    print(f"  Skill:   {SKILL_DIR}/SKILL.md")
    print(f"  Rules:   {RULES_DIR}/working-summary.md")
    print("\nOptional: For accurate context % tracking, add to settings.json:")
    print(
        '  "statusLine": {"command": "python3 ~/.claude/hooks/working-summary/statusline.py"}'
    )


def uninstall():
    import shutil

    print("=== claude-working-memory uninstaller ===\n")

    for path in [HOOK_DIR, SKILL_DIR]:
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"Removed {path}")

    summary = os.path.join(RULES_DIR, "working-summary.md")
    if os.path.exists(summary):
        os.remove(summary)
        print(f"Removed {summary}")

    if os.path.exists(SETTINGS):
        with open(SETTINGS) as f:
            settings = json.load(f)
        hooks = settings.get("hooks", {})
        changed = False
        for event in ["PreToolUse", "UserPromptSubmit", "PreCompact"]:
            entries = hooks.get(event, [])
            filtered = [
                e for e in entries if "working-summary" not in e.get("command", "")
            ]
            if len(filtered) != len(entries):
                changed = True
                if filtered:
                    hooks[event] = filtered
                else:
                    del hooks[event]
        if changed:
            settings["hooks"] = hooks
            with open(SETTINGS, "w") as f:
                json.dump(settings, f, indent=2)
            print(f"Cleaned hooks from {SETTINGS}")

    print("\nUninstalled. CLAUDE.md rule left in place (remove manually if desired).")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
