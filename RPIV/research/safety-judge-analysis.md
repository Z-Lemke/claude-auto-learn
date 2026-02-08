# Safety-Judge Plugin Research

## Goal
Ensure the safety-judge plugin works as intended to enable fully autonomous agent work safely.

## Current Implementation Analysis

### Architecture Overview
The safety-judge plugin implements a PreToolUse hook with a multi-layered security model:

1. **Regex Denylist** (Layer 1 - Hard Deny)
   - Catastrophic commands: `rm -rf /`, `rm -rf ~`, `rm -rf .`
   - Database operations: `DROP DATABASE`, `TRUNCATE TABLE`
   - System-level destructive ops: `dd of=/dev/`, `mkfs.*`, fork bombs
   - Cannot be overridden by user

2. **Settings-based Deny Rules** (Layer 2 - Hard Deny)
   - Loaded from `.claude/settings.json` and `settings.local.json`
   - Evaluated before allow rules
   - Cannot be overridden by user

3. **Settings-based Allow Rules** (Layer 3 - Auto-approve)
   - Rules like `Bash(git *)`, `WebFetch(domain:github.com)`
   - Still checked by LLM judge if available
   - LLM judge can escalate to "ask" (not hard-deny)

4. **Settings-based Ask Rules** (Layer 4 - Prompt)
   - Explicitly requires user approval

5. **LLM Judge** (Safety Net)
   - Uses Haiku to evaluate ambiguous cases
   - Checks for: credential exfiltration, destructive ops, privilege escalation, data exfiltration, obfuscated intent
   - NEVER hard-denies (only escalates to "ask")
   - Gracefully degrades if unavailable

6. **Default** (Fail-safe)
   - No matching rule → ask (never silently allow)

### Test Coverage
The plugin has **660 lines** of comprehensive tests covering:
- ✅ Permission rule parsing (tool patterns, Bash word boundaries, colon syntax)
- ✅ Regex denylist (catastrophic commands)
- ✅ Full evaluation order (regex → deny → allow+LLM → ask → default)
- ✅ LLM judge behavior (mocked API calls)
- ✅ Settings loading (priority order, malformed JSON handling)
- ✅ Hook response format (JSON output for Claude Code)
- ✅ Realistic scenarios (using actual permission rules)

### Current Files
```
plugins/safety-judge/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata
├── hooks/
│   ├── hooks.json            # PreToolUse hook registration
│   └── safety_judge.py       # Main implementation (390 lines)
└── tests/
    ├── conftest.py           # Test setup
    └── test_safety_judge.py  # Unit tests (660 lines)
```

## Known Strengths

1. **Comprehensive Permission Matching**
   - Supports all Claude Code permission syntax
   - Handles Bash patterns with word boundaries (`git *` vs `git*`)
   - WebFetch domain matching
   - File path globs for Read/Edit/Write

2. **Layered Defense**
   - Multiple layers of protection
   - Clear evaluation order
   - Fail-closed on errors

3. **Smart LLM Integration**
   - Uses Haiku (fast, cheap)
   - Never hard-denies (respects user agency)
   - Graceful degradation

4. **Developer Experience**
   - Clear error messages
   - Configurable via settings files
   - Local settings override project settings

## Potential Gaps for Autonomous Operation

### 1. Missing E2E Testing
- No tests with actual Claude Code CLI
- Unknown: Does the hook actually register correctly?
- Unknown: Does it handle real tool call JSON format?
- Unknown: Does it work with Task tool spawning subagents?

### 2. Performance & Latency
- LLM judge adds API call latency (~500ms-2s per tool call)
- Unknown: Impact on rapid-fire tool calls?
- Unknown: Does it cache judgments for identical commands?
- Unknown: What happens if Haiku API is slow/down?

### 3. Edge Cases & Tool Coverage
- ✅ Tested: Bash, WebFetch, WebSearch, Read, Edit, Glob, Grep
- ❓ Untested: NotebookEdit, Write, Task, AskUserQuestion, mcp tools
- ❓ What happens with Task tool creating subagents?
- ❓ Do subagents inherit the safety hook?

### 4. Configuration for Autonomous Mode
- Current settings.local.json has many specific allow rules
- Needs curated "autonomous mode" configuration
- Missing: Documentation for setting up fully autonomous operation

### 5. Error Handling & Recovery
- ✅ Fail-closed on errors
- ❓ What if hook crashes mid-session?
- ❓ Can user recover without restarting?
- ❓ Are errors logged anywhere?

### 6. Observability & Monitoring
- Currently logs to stderr: `print(f"Safety hook: {decision} - {reason}", file=sys.stderr)`
- ❓ Can we track allow/deny/ask statistics?
- ❓ Can we identify rules that are too permissive/restrictive?
- ❓ Can we audit what was allowed during autonomous runs?

### 7. Security Validation
- ✅ Regex patterns tested
- ❓ Are there command obfuscation techniques that bypass regex?
- ❓ Can LLM judge be prompt-injected via malicious tool inputs?
- ❓ What about commands with environment variable expansion?

### 8. Hook Registration
- Uses `hooks/hooks.json` with empty matcher (`""` matches all tools)
- Unknown: Does this actually work for ALL tools?
- Unknown: Is the timeout (30s) appropriate?

## Open Questions

1. **Integration**: Does the hook work correctly when the plugin is installed via `claude plugin install`?
2. **Performance**: What's the real-world latency impact of the LLM judge?
3. **Coverage**: Does the hook intercept ALL tool calls or just specific ones?
4. **Subagents**: Do Task-spawned agents inherit the safety hook?
5. **Cache**: Should we cache LLM judgments for identical commands?
6. **Monitoring**: How can we observe what's being allowed/blocked during autonomous runs?
7. **Obfuscation**: Can malicious tool inputs bypass the safety checks?

## Research Tasks

- [ ] Review Claude Code hook documentation for PreToolUse behavior
- [ ] Test hook registration with actual plugin installation
- [ ] Measure LLM judge latency in realistic scenarios
- [ ] Test edge cases: NotebookEdit, Write, Task tool
- [ ] Validate subagent behavior with safety hook
- [ ] Test command obfuscation techniques
- [ ] Design autonomous mode settings configuration
- [ ] Create E2E test harness
- [ ] Add observability/logging capabilities
- [ ] Test error recovery scenarios
