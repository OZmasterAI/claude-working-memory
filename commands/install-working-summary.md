Install the claude-working-memory plugin. This gives you automatic context preservation before compaction.

## What to install

Create these files and directories:

### 1. Hook: `~/.claude/hooks/working-summary/pre_tool_use.py`
PreToolUse hook that blocks Edit/Write/Bash/Task when context threshold fires and working summary hasn't been written yet. Always allows Read/Grep/Glob/Skill/memory tools. Checks if `~/.claude/rules/working-summary.md` is >2000 chars to unblock. Reads `state.json` in the same directory for `threshold_fired` flag. Exit 2 to block, exit 0 to allow. Fail-open on any exception.

### 2. Hook: `~/.claude/hooks/working-summary/user_prompt_submit.py`
UserPromptSubmit hook that:
- Increments turn counter in `state.json`
- Reads `context_pct` from state (set by optional statusline) or uses turn count fallback (80 turns)
- At 65% context (or 80 turns): prints `<working-memory-warning>` tag and sets `threshold_fired: true`
- Handles countdown: decrements each turn, clears `working-summary.md` to stub when countdown hits 0
- Always exits 0

### 3. Hook: `~/.claude/hooks/working-summary/pre_compact.py`
PreCompact hook that sets `countdown: 5`, `threshold_fired: false`, `turns: 0` in state.json. This starts the 5-turn post-compaction countdown. Always exits 0.

### 4. State: `~/.claude/hooks/working-summary/state.json`
Initialize with: `{"threshold_fired": false, "countdown": -1, "turns": 0, "context_pct": 0}`

### 5. Skill: `~/.claude/skills/working-summary/SKILL.md`
The /working-summary skill that gathers conversation context and writes a structured summary to `~/.claude/rules/working-summary.md` with sections: Goal, Approach, Progress (Completed/In Progress/Remaining), Key Files, Decisions & Rationale, Gotchas & Errors, Next Steps. Target size: 2000-10000 chars.

### 6. Stub: `~/.claude/rules/working-summary.md`
```
# Working Summary (Claude-written at context threshold)
<!-- Auto-managed. Claude writes at ~65% context. -->
(awaiting threshold)
```

### 7. Settings: `~/.claude/settings.json`
Merge these hooks into the existing hooks section (don't overwrite existing hooks):
- PreToolUse: `python3 ~/.claude/hooks/working-summary/pre_tool_use.py`
- UserPromptSubmit: `python3 ~/.claude/hooks/working-summary/user_prompt_submit.py`
- PreCompact: `python3 ~/.claude/hooks/working-summary/pre_compact.py`

### 8. CLAUDE.md rule
Append this behavioral rule to `~/.claude/CLAUDE.md` if not already present:
```
9. **Working summary** — When you see `<working-memory-warning>`, immediately run /working-summary before continuing other work. Do not dismiss or defer.
```

## After installation
Write all files, update settings.json, and confirm with: "Working Summary plugin installed. You'll see a warning at ~65% context usage prompting you to run /working-summary."
