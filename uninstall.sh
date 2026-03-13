#!/usr/bin/env bash
# claude-working-memory uninstaller
set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
HOOK_DIR="${CLAUDE_DIR}/hooks/working-summary"
SKILL_DIR="${CLAUDE_DIR}/skills/working-summary"
SUMMARY="${CLAUDE_DIR}/rules/working-summary.md"
SETTINGS="${CLAUDE_DIR}/settings.json"

echo "=== claude-working-memory uninstaller ==="
echo ""

# Remove hooks
if [ -d "${HOOK_DIR}" ]; then
    rm -rf "${HOOK_DIR}"
    echo "Removed ${HOOK_DIR}"
fi

# Remove skill
if [ -d "${SKILL_DIR}" ]; then
    rm -rf "${SKILL_DIR}"
    echo "Removed ${SKILL_DIR}"
fi

# Remove rules file
if [ -f "${SUMMARY}" ]; then
    rm "${SUMMARY}"
    echo "Removed ${SUMMARY}"
fi

# Remove hooks from settings.json
if [ -f "${SETTINGS}" ] && command -v python3 &>/dev/null; then
    python3 - "${SETTINGS}" <<'PYEOF'
import json, sys, os

settings_path = sys.argv[1]
with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.get("hooks", {})
changed = False
for event in ["PreToolUse", "UserPromptSubmit", "PreCompact"]:
    entries = hooks.get(event, [])
    filtered = [e for e in entries if "working-summary" not in e.get("command", "")]
    if len(filtered) != len(entries):
        changed = True
        if filtered:
            hooks[event] = filtered
        else:
            del hooks[event]

if changed:
    settings["hooks"] = hooks
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    print(f"Cleaned hooks from {settings_path}")
PYEOF
fi

echo ""
echo "Uninstalled. CLAUDE.md rule left in place (remove manually if desired)."
