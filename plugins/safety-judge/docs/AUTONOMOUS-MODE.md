# Autonomous Mode Configuration Guide

## ⚠️ CRITICAL: NOT SAFE FOR PRODUCTION USE

**The safety-judge plugin CANNOT be used in autonomous or production mode until Claude Code fixes a critical security bug.**

**Issue:** Plugin-level PreToolUse hooks do NOT fire for Task tool subagents
**Tracking:** https://github.com/anthropics/claude-code/issues/21460
**Impact:** Subagents can bypass ALL safety restrictions
**Status:** Open, awaiting upstream fix from Anthropic

**This document is for REFERENCE ONLY** - documenting how autonomous operation WOULD work once the upstream bug is fixed.

---

## Prerequisites

Before considering autonomous operation:

1. **✅ REQUIRED: Claude Code fixes issue #21460**
   - Until fixed, Task tool MUST be disabled: `"deny": ["Task"]`
   - Without this fix, autonomous mode is completely unsafe

2. **✅ Test with supervision first**
   - Run multiple supervised sessions with your permission rules
   - Review `.claude/safety-audit.log` to check decisions
   - Verify no unexpected denials or approvals

3. **✅ Understand failure modes**
   - Read `/plugins/safety-judge/docs/KNOWN-LIMITATIONS.md`
   - LLM judge depends on Haiku API quality
   - Regex denylist can be bypassed by obfuscation

4. **✅ Enable audit logging**
   - Plugin automatically logs to `.claude/safety-audit.log`
   - Review after each autonomous run
   - Set up alerts for "deny" decisions

---

## Recommended Permission Rules

### Conservative Configuration (Safest)

Use this for initial autonomous runs or high-risk environments:

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(npm test)",
      "Bash(python3 -m pytest)",
      "Read",
      "Glob",
      "Grep",
      "WebSearch",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:docs.anthropic.com)"
    ],
    "deny": [
      "Task",                    // CRITICAL: Block subagents until upstream fix
      "Bash(git push:*)",        // Prevent auto-push
      "Bash(rm *)",              // Prevent file deletion
      "Bash(docker:*)",          // Prevent container operations
      "Bash(curl *)",            // Prevent network requests
      "Bash(wget *)",
      "Write(*.sh)",             // Prevent script creation
      "Write(*.bash)",
      "NotebookEdit"             // Prevent notebook modifications
    ],
    "ask": [
      "Edit",                    // File edits need approval
      "Write",                   // File writes need approval
      "Bash"                     // All other Bash commands ask
    ]
  }
}
```

**Rationale:**
- Allow only read operations + test execution
- Deny destructive/network operations explicitly
- Everything else requires approval

**Limitation:** Very restrictive, limits agent capabilities significantly

### Moderate Configuration (Balanced)

After validating conservative mode works well:

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git diff:*)",
      "Bash(npm *)",
      "Bash(python3 *)",
      "Bash(pytest *)",
      "Read",
      "Edit(src/**/*)",          // Allow edits in src/ only
      "Edit(tests/**/*)",
      "Glob",
      "Grep",
      "WebSearch",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:docs.anthropic.com)",
      "WebFetch(domain:pypi.org)"
    ],
    "deny": [
      "Task",                    // CRITICAL: Block until upstream fix
      "Bash(git push:*)",
      "Bash(rm -rf *)",
      "Bash(docker:*)",
      "Edit(.env)",              // Protect secrets
      "Edit(.git/**/*)",         // Protect git internals
      "Write(*.sh)",             // Shell scripts need review
      "NotebookEdit"
    ],
    "ask": [
      "Write",                   // New files need approval
      "Bash(curl *)",            // Network requests ask
      "Bash(wget *)",
      "Bash(pip install:*)",
      "Bash(npm install:*)"
    ]
  }
}
```

**Rationale:**
- Allows code edits in specific directories
- Allows git commits but not push
- Package installs require approval
- Network requests require approval

---

## Risk Assessment

### Security Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Subagent bypass | **CERTAIN** | **CRITICAL** | Disable Task tool until upstream fix |
| Obfuscated rm -rf | Medium | Critical | LLM judge escalates (depends on quality) |
| Credential exfil | Medium | Critical | LLM judge escalates + deny curl/wget |
| Script creation | Low | High | Deny .sh/.bash writes, evaluate .py |
| Unintended push | Low | Medium | Deny git push in allow rules |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False deny (blocks valid op) | Medium | Low | Review audit log, adjust rules |
| False allow (misses threat) | Low | High | Multi-layer defense, LLM judge backup |
| Hook timeout | Low | Medium | 30s timeout, fail to "ask" |
| API rate limits | Medium | Low | LLM judge optional, falls back to allow |

---

## Audit Log Review Procedures

After each autonomous run:

### 1. Check for Denials

```bash
grep '"decision": "deny"' .claude/safety-audit.log
```

**Questions to ask:**
- Was the denial correct? (Good catch)
- Was it a false positive? (Need to adjust rules)
- How did Claude respond? (Check transcript)

### 2. Check for Escalations

```bash
grep '"decision": "ask"' .claude/safety-audit.log
```

**Questions to ask:**
- Why did it escalate? (Reason field)
- Was LLM judge involved? (Look for "LLM Judge flagged")
- Should this be in allow or deny rules?

### 3. Review All Decisions

```bash
cat .claude/safety-audit.log | jq -r '[.timestamp, .tool_name, .decision, .reason] | @tsv'
```

**Look for:**
- Unexpected tool usage patterns
- Commands you don't recognize
- High frequency of "ask" (rules too restrictive)

### 4. Validate Session Behavior

- Did Claude accomplish the requested task?
- Were there unexpected errors due to denied commands?
- Did audit log reveal any attempted bypasses?

---

## Known Limitations

See `/plugins/safety-judge/docs/KNOWN-LIMITATIONS.md` for full details.

**Critical limitations:**

1. **Subagent bypass (BLOCKER for autonomous mode)**
   - Task tool spawns subagents that bypass ALL safety hooks
   - MUST disable Task tool or await upstream fix
   - See: https://github.com/anthropics/claude-code/issues/21460

2. **LLM judge quality dependency**
   - Bypass detection depends on Haiku's analysis
   - Not empirically validated with real API yet (only mocked tests)
   - Advanced adversarial prompts not tested

3. **Regex bypass via obfuscation**
   - Environment variables: `DIR="/" && rm -rf $DIR`
   - Command substitution: `$(echo rm -rf /)`
   - Encoding: `echo "..." | base64 -d | bash`
   - LLM judge provides second layer but not guaranteed

4. **Performance impact**
   - LLM judge adds ~500ms-2s latency per tool call
   - May impact user experience for high-frequency commands

---

## Emergency Procedures

### If Malicious Activity Detected

1. **Immediately interrupt the session** (Ctrl+C)
2. **Review audit log:** `.claude/safety-audit.log`
3. **Check what commands executed:** Look for "allow" decisions
4. **Assess damage:** What files were modified? What network requests made?
5. **Update deny rules** to prevent recurrence
6. **Report findings** if it's a bypass technique

### If Hook Fails

The hook is designed to **fail closed**:
- Hook errors → tool call blocked with "ask" decision
- LLM judge errors → escalate to "ask"
- Audit log errors → hook still runs (just logging fails)

If you see repeated hook errors:
1. Check `.claude/hooks/safety_judge.py` exists and is executable
2. Check Python dependencies installed (`anthropic` package)
3. Check `ANTHROPIC_API_KEY` set (if using LLM judge)
4. Review stderr output for error details

---

## Gradual Rollout Recommendation

### Phase 1: Supervised with Logging (Current)
- Run plugin in supervised mode
- Review all "ask" prompts manually
- Check audit log after each session
- Build confidence in rule set

### Phase 2: Semi-Autonomous (After upstream fix)
- **REQUIRES: Claude Code fixes issue #21460**
- Use conservative permission rules
- Limit to low-risk tasks (documentation, tests)
- Monitor audit log closely
- Expand allow rules gradually

### Phase 3: Full Autonomous (Future)
- **REQUIRES: Phase 2 validation + E2E testing with real LLM API**
- Use moderate permission rules
- Automated audit log alerts
- Regular security reviews
- Red team testing

---

## Configuration Examples

### Example 1: Documentation-Only Bot

Autonomous agent that can only read code and update documentation:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Edit(docs/**/*.md)",
      "Edit(README.md)",
      "WebSearch",
      "WebFetch(domain:github.com)"
    ],
    "deny": ["Task"],
    "ask": ["Write", "Bash", "NotebookEdit"]
  }
}
```

### Example 2: Test-Only Bot

Autonomous agent that runs and fixes tests:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Edit(tests/**/*)",
      "Edit(src/**/*)",
      "Bash(pytest *)",
      "Bash(npm test *)"
    ],
    "deny": ["Task", "Bash(git push:*)"],
    "ask": ["Write", "Bash", "NotebookEdit"]
  }
}
```

---

## Summary

**Current Status:** NOT READY for autonomous mode due to upstream bug

**Blocker:** https://github.com/anthropics/claude-code/issues/21460

**Once fixed:**
1. Start with conservative rules
2. Monitor audit logs closely
3. Expand permissions gradually
4. Maintain defense-in-depth approach

**Key Principle:** Fail closed, escalate to human approval when uncertain.
