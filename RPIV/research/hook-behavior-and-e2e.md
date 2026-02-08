# PreToolUse Hook Behavior & E2E Testing Research

## Official Claude Code PreToolUse Hook Documentation

Based on research from [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) and related documentation:

### Hook Capabilities

**PreToolUse hooks:**
- Run **before** every tool call
- Can block destructive operations
- Can modify tool inputs before execution (v2.0.10+)
- Intercept tool calls and modify JSON input instead of forcing retries

### Hook Input (stdin JSON)

PreToolUse hooks receive these fields via stdin:
```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "permission_mode": "...",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status",
    ...
  }
}
```

**Confirmed fields used by safety-judge:**
- ✅ `tool_name` - Tool being called (e.g., "Bash", "Read", "WebFetch")
- ✅ `tool_input` - Tool-specific parameters (dict)

**Additional fields (not currently used):**
- `session_id` - Current session identifier
- `transcript_path` - Path to session transcript
- `cwd` - Current working directory
- `permission_mode` - Current permission mode setting

### Hook Output & Exit Codes

**Exit codes:**
- Exit 0 = success (Claude Code parses stdout for JSON output)
- Non-zero = hook error (behavior varies by hook type)

**stdout JSON output:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "explanation"
  }
}
```

**Special case for "allow":**
- Can return no output (empty/None) for silent pass-through
- Reduces noise in logs

**stderr:**
- Used for logging and diagnostics
- Not parsed by Claude Code
- safety-judge logs: `print(f"Safety hook: {decision} - {reason}", file=sys.stderr)`

### Matcher Syntax

**Pattern matching for tool names:**
- Case-sensitive for PreToolUse events
- Empty string `""` matches all tools
- Specific tool names: "Bash", "Read", "Edit"

**From safety-judge implementation:**
- Matcher in hooks.json is empty `""` (applies to all tools)
- Actual tool filtering done inside the Python script via PermissionMatcher

### Hook Execution Model

1. User/agent makes a tool call
2. Claude Code captures tool_name and tool_input
3. PreToolUse hook triggered (if registered)
4. Hook reads JSON from stdin
5. Hook evaluates and writes decision to stdout
6. Claude Code:
   - "allow" → Execute tool
   - "deny" → Block tool, show reason to user
   - "ask" → Prompt user for approval
7. Tool executes or is blocked based on decision

### Hook Registration

**Plugin-level auto-registration:**
- Hooks auto-register when plugin is installed
- No per-project setup required
- `${CLAUDE_PLUGIN_ROOT}` resolves to plugin installation directory

**From safety-judge hooks.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/safety_judge.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Timeout:**
- safety-judge uses 30s timeout
- Reasonable for LLM judge API calls (~500ms-2s typical)
- Prevents hanging on slow API responses

## E2E Testing Patterns from auto-learn Plugin

### Test Infrastructure

**From `/plugins/auto-learn/tests/test_e2e.py`:**

```python
def run_claude(prompt, cwd, timeout=120, extra_flags=None, debug_file=None):
    cmd = [
        "claude",
        "--plugin-dir", str(REPO_ROOT),  # Points to plugin source
        "--dangerously-skip-permissions",  # For testing
        "--output-format", "stream-json",  # Parseable output
        "--verbose",                       # Debug info
        "--model", "haiku",                # Fast, cheap
        "--debug-file", str(debug_file),   # Hook execution logs
        "-p", prompt
    ]
    subprocess.run(cmd, cwd=str(cwd), timeout=timeout)
```

**Key flags:**
- `--plugin-dir` - Load plugins from local source (not installed plugins)
- `--dangerously-skip-permissions` - Skip permission prompts (hooks still run)
- `--output-format stream-json` - Machine-readable output
- `--debug-file` - Captures hook execution details

### Sandbox Configuration

**Test project setup:**
```python
(tmp_path / ".claude" / "settings.json").write_text(json.dumps({
    "sandbox": {
        "enabled": True,
        "autoAllowBashIfSandboxed": True,
    }
}))
```

**Sandbox isolation:**
- Uses OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux)
- Restricts file writes to test project directory
- Claude runs on host with full auth
- Provides filesystem boundary without permission prompts

### Test Pattern: Two-Phase Validation

**Phase 1: Learn/Create**
1. Run claude with a prompt that should trigger behavior
2. Verify artifacts are created (config files, hooks, skills)
3. Check artifact contents match expectations

**Phase 2: Use/Verify**
1. Run fresh claude session in same project
2. Verify Claude's behavior reflects the learned config
3. Confirm config was actually loaded and used

### Output Parsing

**Extracting assistant response from stream-json:**
```python
def get_assistant_text(stdout):
    text = ""
    for line in stdout.strip().splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "assistant":
            for block in msg.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
    return text
```

### Debug Log Analysis

**Hook execution verification:**
```python
debug_file = test_project / "debug.log"
code, stdout, stderr = run_claude(
    prompt,
    cwd=test_project,
    debug_file=debug_file,
)

debug_log = debug_file.read_text()
assert '"continue": true' in debug_log, "Stop hook did not detect correction"
```

**Debug log contains:**
- Hook execution events
- Hook stdout/stderr output
- Hook decisions and reasons
- Timing information

### Gating E2E Tests

**Run only when explicitly requested:**
```python
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E"),
    reason="E2E tests require RUN_E2E=1 (makes API calls)",
)
```

**Why:**
- E2E tests make real API calls (costs money, uses quota)
- Slower than unit tests (full CLI startup + API latency)
- Requires working Claude Code installation
- May fail due to external factors (API downtime, network issues)

## E2E Test Scenarios for safety-judge

Based on auto-learn patterns, safety-judge E2E tests should verify:

### 1. Hook Registration & Activation
- Install plugin via `claude plugin install safety-judge`
- Verify hook is registered without manual setup
- Confirm hook runs on tool calls

### 2. Layered Security Evaluation
**Test: Regex denylist blocks catastrophic commands**
```python
# Prompt that should trigger rm -rf /
# Verify: Tool blocked, reason mentions "denylist"
```

**Test: Allow rules permit safe commands**
```python
# Prompt that triggers git status (with allow rule configured)
# Verify: Tool executes, no user prompt
```

**Test: LLM judge escalates suspicious commands**
```python
# Prompt that triggers allowed command with credential exfiltration
# Verify: Escalated to "ask", reason mentions "LLM Judge"
```

**Test: Unknown commands prompt user**
```python
# Prompt that triggers unknown command (no rule)
# Verify: User prompted, reason mentions "no matching permission rule"
```

### 3. Subagent Behavior
**Test: Task tool spawns agent with safety hook**
```python
# Prompt that triggers Task tool spawning subagent
# Subagent attempts destructive command
# Verify: Hook blocks subagent's destructive command
```

### 4. Performance & Reliability
**Test: LLM judge timeout handling**
```python
# Mock slow Haiku API response (>30s)
# Verify: Hook times out gracefully, fails to "ask"
```

**Test: Rapid-fire tool calls**
```python
# Prompt that triggers many consecutive tool calls
# Verify: All calls evaluated, no race conditions
```

### 5. Error Recovery
**Test: Hook crash fails closed**
```python
# Inject error into safety_judge.py (bad import, etc.)
# Verify: Tool blocked, reason mentions "hook error"
```

### 6. Edge Case Tools
**Test: NotebookEdit safety**
```python
# Prompt that triggers NotebookEdit with code injection
# Verify: Hook evaluates NotebookEdit tool calls
```

**Test: Write tool safety**
```python
# Prompt that triggers Write to .env file
# Verify: Hook blocks or prompts based on rules
```

## Critical Unknowns for E2E Testing

1. **Subagent inheritance:** Do Task-spawned agents inherit PreToolUse hooks?
   - Auto-learn tests don't use Task tool
   - Need dedicated test: spawn agent → agent attempts dangerous op → verify blocked

2. **Hook persistence:** Does hook survive session restarts?
   - Test: Phase 1 install plugin → Phase 2 new session → verify hook active

3. **Performance impact:** What's real-world latency with LLM judge?
   - Need instrumentation: measure time from tool call to execution
   - Compare: hook disabled vs enabled vs LLM judge active

4. **Concurrent tool calls:** How does hook handle parallel calls?
   - Test: Trigger multiple independent tasks in parallel
   - Verify: All evaluated correctly, no race conditions

5. **Debug observability:** Can we see hook decisions in debug logs?
   - Test: Run with --debug-file, verify all decisions logged
   - Confirm: allow/deny/ask reasons visible for debugging

## References

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Claude Code Hooks: A Practical Guide](https://www.datacamp.com/tutorial/claude-code-hooks)
- [Understanding Claude Code hooks documentation](https://blog.promptlayer.com/understanding-claude-code-hooks-documentation/)
- [How to configure hooks](https://claude.com/blog/how-to-configure-hooks)
