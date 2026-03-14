#!/usr/bin/env python3
"""PreToolUse hook: blocks Edit/Write/Bash until working summary is written.

Part of claude-working-memory plugin.
Exit 0 = allow, Exit 2 = block.
"""

import json
import os
import sys

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SUMMARY_PATH = os.path.join(
    os.path.expanduser("~"), ".claude", "rules", "working-summary.md"
)
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

    # Only activate after threshold fires
    if not state.get("threshold_fired"):
        sys.exit(0)

    # Always allow read-only, skill, and MCP tools
    if tool in ALWAYS_ALLOWED or tool.startswith("mcp__"):
        sys.exit(0)

    # Not a gated tool — allow
    if tool not in GATED_TOOLS:
        sys.exit(0)

    # Allow writes to working-summary.md itself
    file_path = tool_input.get("file_path", "")
    if file_path and os.path.basename(file_path) == "working-summary.md":
        sys.exit(0)

    # Check if summary has been written (>2000 chars)
    try:
        size = os.path.getsize(SUMMARY_PATH)
    except OSError:
        size = 0

    if size >= MIN_CHARS:
        sys.exit(0)

    # Block — summary not yet written
    # Use stdout JSON systemMessage so Claude sees the reason (stderr not visible in non-verbose mode)
    msg = (
        "[WORKING SUMMARY] Context threshold reached. "
        "Run /working-summary to save context before continuing."
    )
    print(json.dumps({"decision": "block", "reason": msg}))
    sys.exit(2)

except Exception:
    sys.exit(0)  # Fail-open: never crash the hook
