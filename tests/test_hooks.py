#!/usr/bin/env python3
"""Tests for claude-working-memory plugin hooks."""

import json
import os
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0
SRC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
)


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS: {name}")
    else:
        FAILED += 1
        print(f"  FAIL: {name} {detail}")


def run_hook(script, stdin_data, env_overrides=None, state=None, state_file=None):
    """Run a hook script with given stdin JSON, return (exit_code, stdout, stderr)."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    # Write state file if provided
    if state is not None and state_file:
        with open(state_file, "w") as f:
            json.dump(state, f)

    proc = subprocess.run(
        [sys.executable, script],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ── pre_tool_use.py tests ─────────────────────────────────────────────────


def test_pre_tool_use():
    print("\n== pre_tool_use.py ==")
    script = os.path.join(SRC_DIR, "pre_tool_use.py")

    with tempfile.TemporaryDirectory() as tmp:
        state_file = os.path.join(tmp, "state.json")
        # Patch STATE_FILE by creating a wrapper
        wrapper = os.path.join(tmp, "pre_tool_use.py")
        with open(script) as f:
            src = f.read()
        src = src.replace(
            'os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")',
            f'"{state_file}"',
        )
        with open(wrapper, "w") as f:
            f.write(src)

        # Test 1: Allow when threshold not fired
        code, out, err = run_hook(
            wrapper,
            {"tool_name": "Edit", "tool_input": {"file_path": "/foo.py"}},
            state={"threshold_fired": False},
            state_file=state_file,
        )
        test("allows Edit when threshold not fired", code == 0)

        # Test 2: Block Edit when threshold fired and no summary
        summary_path = os.path.join(tmp, "working-summary.md")
        src2 = src.replace(
            'os.path.join(\n    os.path.expanduser("~"), ".claude", "rules", "working-summary.md"\n)',
            f'"{summary_path}"',
        )
        wrapper2 = os.path.join(tmp, "pre_tool_use2.py")
        with open(wrapper2, "w") as f:
            f.write(src2)

        code, out, err = run_hook(
            wrapper2,
            {"tool_name": "Edit", "tool_input": {"file_path": "/foo.py"}},
            state={"threshold_fired": True},
            state_file=state_file,
        )
        test("blocks Edit when threshold fired and no summary", code == 2)

        # Verify block message is JSON on stdout (not stderr)
        try:
            msg = json.loads(out)
            test(
                "block reason is JSON on stdout", "decision" in msg and "reason" in msg
            )
        except (json.JSONDecodeError, ValueError):
            test("block reason is JSON on stdout", False, f"got: {out!r}")

        # Test 3: Allow Read even when threshold fired
        code, out, err = run_hook(
            wrapper2,
            {"tool_name": "Read", "tool_input": {"file_path": "/foo.py"}},
            state={"threshold_fired": True},
            state_file=state_file,
        )
        test("allows Read even when threshold fired", code == 0)

        # Test 4: Allow MCP tools
        code, out, err = run_hook(
            wrapper2,
            {"tool_name": "mcp__memory__search_knowledge", "tool_input": {}},
            state={"threshold_fired": True},
            state_file=state_file,
        )
        test("allows MCP tools when threshold fired", code == 0)

        # Test 5: Allow writes to working-summary.md itself
        code, out, err = run_hook(
            wrapper2,
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/home/user/.claude/rules/working-summary.md"
                },
            },
            state={"threshold_fired": True},
            state_file=state_file,
        )
        test("allows Write to working-summary.md", code == 0)

        # Test 6: Allow Edit when summary is large enough
        with open(summary_path, "w") as f:
            f.write("x" * 2500)
        code, out, err = run_hook(
            wrapper2,
            {"tool_name": "Edit", "tool_input": {"file_path": "/foo.py"}},
            state={"threshold_fired": True},
            state_file=state_file,
        )
        test("allows Edit when summary >= 2000 chars", code == 0)


# ── pre_compact.py tests ──────────────────────────────────────────────────


def test_pre_compact():
    print("\n== pre_compact.py ==")
    script = os.path.join(SRC_DIR, "pre_compact.py")

    with tempfile.TemporaryDirectory() as tmp:
        state_file = os.path.join(tmp, "state.json")
        wrapper = os.path.join(tmp, "pre_compact.py")
        with open(script) as f:
            src = f.read()
        src = src.replace(
            'os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")',
            f'"{state_file}"',
        )
        with open(wrapper, "w") as f:
            f.write(src)

        # Set initial state
        with open(state_file, "w") as f:
            json.dump({"threshold_fired": True, "turns": 50, "countdown": -1}, f)

        code, out, err = run_hook(wrapper, {})
        test("exits 0", code == 0)

        with open(state_file) as f:
            state = json.load(f)
        test("sets countdown to 5", state.get("countdown") == 5)
        test("resets threshold_fired", state.get("threshold_fired") is False)
        test("resets turns to 0", state.get("turns") == 0)


# ── Run all ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_pre_tool_use()
    test_pre_compact()
    print(f"\n{'=' * 50}")
    print(f"claude-working-memory tests: {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 50}")
    sys.exit(1 if FAILED else 0)
