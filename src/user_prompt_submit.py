#!/usr/bin/env python3
"""UserPromptSubmit hook: threshold detection + countdown timer.

Part of claude-working-memory plugin.
- Detects when context reaches ~65% (or ~80 turns as fallback)
- Prints warning for Claude to see
- Decrements post-compaction countdown
- Clears working-summary.md to stub after countdown reaches 0
"""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SUMMARY_PATH = os.path.join(
    os.path.expanduser("~"), ".claude", "rules", "working-summary.md"
)
THRESHOLD_PCT = 65
TURN_FALLBACK = 80  # Fire after this many turns if context_pct unavailable

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

    # Increment turn counter
    state["turns"] = state.get("turns", 0) + 1

    # --- Threshold detection ---
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

    # --- Countdown logic (post-compaction) ---
    countdown = state.get("countdown", -1)
    if countdown > 0:
        state["countdown"] = countdown - 1
    elif countdown == 0:
        # Clear working-summary.md to stub
        try:
            with open(SUMMARY_PATH, "w") as f:
                f.write(STUB)
        except Exception:
            pass
        state["countdown"] = -1

    save_state(state)

except Exception:
    pass  # Fail-open: never crash the hook

sys.exit(0)
