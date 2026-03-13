#!/usr/bin/env python3
"""Optional statusline script: captures real context_pct from Claude Code.

If you use this as your statusLine command, the plugin gets accurate
context percentage instead of the turn-count fallback.

Configure in ~/.claude/settings.json:
  "statusLine": {
    "command": "python3 ~/.claude/hooks/working-summary/statusline.py"
  }
"""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


try:
    data = json.load(sys.stdin)
    pct = data.get("context_window", {}).get("used_percentage", 0)

    # Update context_pct in state file
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

    # Output status line text
    print(f"ctx:{pct:.0f}%")

except Exception:
    pass
