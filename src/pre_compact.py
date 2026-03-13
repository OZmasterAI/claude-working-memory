#!/usr/bin/env python3
"""PreCompact hook: start countdown to clear working summary after compaction.

Part of claude-working-memory plugin.
Resets threshold flag and starts 5-turn countdown so the summary persists
long enough for Claude to re-orient after /clear, then auto-clears.
"""

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
    state["threshold_fired"] = False  # Reset for next cycle
    state["turns"] = 0  # Reset turn counter

    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

    print(
        "[Working Summary] Countdown started (5 turns post-compaction)",
        file=sys.stderr,
    )
except Exception:
    pass  # Fail-open

sys.exit(0)
