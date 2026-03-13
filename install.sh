#!/usr/bin/env bash
# claude-working-memory installer
# Usage: bash install.sh
set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
HOOK_DIR="${CLAUDE_DIR}/hooks/working-summary"
SKILL_DIR="${CLAUDE_DIR}/skills/working-summary"
RULES_DIR="${CLAUDE_DIR}/rules"
SETTINGS="${CLAUDE_DIR}/settings.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${SCRIPT_DIR}/src"

echo "=== claude-working-memory installer ==="
echo ""

# 1. Create directories
echo "[1/5] Creating directories..."
mkdir -p "${HOOK_DIR}" "${SKILL_DIR}" "${RULES_DIR}"

# 2. Copy hook files
echo "[2/5] Installing hooks..."
cp "${SRC}/pre_tool_use.py" "${HOOK_DIR}/pre_tool_use.py"
cp "${SRC}/user_prompt_submit.py" "${HOOK_DIR}/user_prompt_submit.py"
cp "${SRC}/pre_compact.py" "${HOOK_DIR}/pre_compact.py"
cp "${SRC}/statusline.py" "${HOOK_DIR}/statusline.py"
# Initialize state
echo '{"threshold_fired": false, "countdown": -1, "turns": 0, "context_pct": 0}' > "${HOOK_DIR}/state.json"

# 3. Copy skill and stub
echo "[3/5] Installing skill and rules..."
cp "${SRC}/SKILL.md" "${SKILL_DIR}/SKILL.md"
cp "${SRC}/working-summary.md" "${RULES_DIR}/working-summary.md"

# 4. Update settings.json (merge hooks, don't overwrite)
echo "[4/5] Updating settings.json..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 required for settings.json merge."
    echo "Manually add these hooks to ${SETTINGS}:"
    echo '  PreToolUse:  python3 ~/.claude/hooks/working-summary/pre_tool_use.py'
    echo '  UserPromptSubmit: python3 ~/.claude/hooks/working-summary/user_prompt_submit.py'
    echo '  PreCompact:  python3 ~/.claude/hooks/working-summary/pre_compact.py'
    exit 1
fi

python3 - "${SETTINGS}" <<'PYEOF'
import json, sys, os

settings_path = sys.argv[1]

# Load or create settings
settings = {}
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)

hooks = settings.setdefault("hooks", {})

new_hooks = {
    "PreToolUse": [{
        "matcher": "",
        "command": "python3 ~/.claude/hooks/working-summary/pre_tool_use.py"
    }],
    "UserPromptSubmit": [{
        "matcher": "",
        "command": "python3 ~/.claude/hooks/working-summary/user_prompt_submit.py"
    }],
    "PreCompact": [{
        "matcher": "",
        "command": "python3 ~/.claude/hooks/working-summary/pre_compact.py"
    }],
}

for event, entries in new_hooks.items():
    existing = hooks.get(event, [])
    for entry in entries:
        # Skip if already registered
        if any(entry["command"] in e.get("command", "") for e in existing):
            continue
        existing.append(entry)
    hooks[event] = existing

settings["hooks"] = hooks

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)

print(f"  Updated {settings_path}")
PYEOF

# 5. Add CLAUDE.md rule
echo "[5/5] Adding CLAUDE.md rule..."

RULE='9. **Working summary** — When you see `<working-memory-warning>`, immediately run /working-summary before continuing other work. Do not dismiss or defer.'

if [ -f "${CLAUDE_DIR}/CLAUDE.md" ]; then
    if ! grep -q "working-memory-warning" "${CLAUDE_DIR}/CLAUDE.md"; then
        echo "" >> "${CLAUDE_DIR}/CLAUDE.md"
        echo "${RULE}" >> "${CLAUDE_DIR}/CLAUDE.md"
        echo "  Appended rule to CLAUDE.md"
    else
        echo "  Rule already exists in CLAUDE.md"
    fi
else
    echo "# Claude Code Instructions" > "${CLAUDE_DIR}/CLAUDE.md"
    echo "" >> "${CLAUDE_DIR}/CLAUDE.md"
    echo "## Behavioral Rules" >> "${CLAUDE_DIR}/CLAUDE.md"
    echo "${RULE}" >> "${CLAUDE_DIR}/CLAUDE.md"
    echo "  Created CLAUDE.md with rule"
fi

echo ""
echo "=== Installation complete ==="
echo ""
echo "Installed:"
echo "  Hooks:   ${HOOK_DIR}/ (3 hooks + optional statusline)"
echo "  Skill:   ${SKILL_DIR}/SKILL.md"
echo "  Rules:   ${RULES_DIR}/working-summary.md"
echo ""
echo "Optional: For accurate context % tracking, add to settings.json:"
echo '  "statusLine": {"command": "python3 ~/.claude/hooks/working-summary/statusline.py"}'
echo ""
echo "To uninstall: bash $(dirname "$0")/uninstall.sh"
