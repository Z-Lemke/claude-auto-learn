# Research: Subagent Hook Inheritance

## Question
Do PreToolUse hooks apply to Task tool subagents? If not, can we make them apply?

## Test Results (Empirical Evidence)

**Test:** Spawned 2 subagents in parallel - one to run `find`, one to run `curl`

**Findings:**
- ✅ Task tool successfully created 2 subagents
- ✅ safety-judge plugin loaded: `Loading plugin safety-judge from source`
- ✅ Hooks loaded: `Loading hooks from plugin: safety-judge`
- ✅ curl command WAS executed by subagent
- ❌ NO "Safety hook:" evidence in debug log
- ⚠️ curl was blocked by **sandbox**, not by our deny rule

**Conclusion:** The hook loaded but did NOT execute for subagent tool calls.

## Documentation Analysis

### Hook Scoping - Official Claude Code Documentation

From [hooks reference](https://code.claude.com/docs/en/hooks):

**Hook Locations Table:**
```
| Location                     | Scope                         |
| Plugin hooks/hooks.json      | When plugin is enabled        |
| Skill/agent frontmatter      | While the component is active |
```

**Key Distinction:**
- **Plugin-level hooks**: Scope is "when plugin is enabled" (no mention of component lifecycle)
- **Component-level hooks** (frontmatter): Explicitly "scoped to the component's lifecycle and only run when that component is active"

### Hooks in Skills and Agents (Direct Quote)

> "In addition to settings files and plugins, hooks can be defined directly in skills and subagents using frontmatter. These hooks are **scoped to the component's lifecycle and only run when that component is active.**"

This tells us:
1. Hooks CAN be defined in subagent frontmatter
2. Those hooks are scoped to that specific component
3. Plugin hooks are described differently (not component-scoped)

### Critical Ambiguity

The documentation does NOT explicitly state whether:
- Plugin-level PreToolUse hooks apply to subagent tool calls
- Subagents are separate "sessions" with isolated hook contexts
- Plugin hooks need re-registration for subagent contexts

**What we know:**
- ✅ Plugin hooks register when plugin is enabled
- ✅ Empty matcher means "match all tool calls"
- ✅ SubagentStart hook fires when subagents spawn
- ❌ NO statement that plugin hooks inherit to subagents
- ❌ NO statement that plugin hooks are isolated from subagents

## Interpretation Analysis

### Theory A: Plugin Hooks Should Apply to Subagents

**Evidence FOR:**
1. Plugin hooks are NOT described as "component-scoped" (unlike frontmatter hooks)
2. Empty matcher (`""`) means "match all tool calls" with no scope restriction
3. Documentation says hooks are "scoped to when plugin is enabled" - subagents run while plugin is enabled
4. No explicit documentation saying plugin hooks are main-session-only

**Evidence AGAINST:**
1. Empirical test showed hook did NOT fire for subagent tool calls
2. Hook loaded globally but didn't execute in subagent context
3. Documentation explicitly calls out component-scoping for frontmatter hooks, suggesting other hooks might be differently scoped

### Theory B: Subagents Have Isolated Hook Contexts

**Evidence FOR:**
1. Empirical test: hook loaded but didn't fire for subagent
2. Documentation distinguishes "component lifecycle" for frontmatter hooks
3. SubagentStart exists as separate event, suggesting subagents are separate contexts
4. Permission documentation states: "Subagents do not automatically inherit parent agent permissions"

**Evidence AGAINST:**
1. Hooks ≠ permissions (different systems)
2. No explicit documentation that subagents have isolated hook contexts
3. Plugin hooks are "global" in scope (when plugin enabled)

### Most Likely Explanation

**Subagents are separate sessions with separate hook contexts.**

Supporting evidence:
- Permissions don't inherit → suggests isolated contexts
- Hook loaded (debug log shows plugin loaded) but didn't fire (no "Safety hook:" output)
- This means plugin is present but hooks don't execute for subagent tool calls
- Subagent likely spawns as new session, gets plugin loaded, but hook registration doesn't trigger PreToolUse for that session's tool calls

## Alternative Approaches

### Option 1: SubagentStart Hook to Inject Safety Context

**Idea:** Use SubagentStart hook to inject safety requirements into subagent context.

**From documentation:**
> "SubagentStart hooks cannot block subagent creation, but they can inject context into the subagent."

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": "SAFETY REQUIREMENTS: Do not execute curl, wget, rm -rf, or other dangerous commands."
  }
}
```

**Limitations:**
- ❌ Can't block subagent creation (runs after subagent spawned)
- ❌ Relies on LLM following instructions (not a hard safety boundary)
- ❌ Not a technical enforcement, just context injection
- ❌ LLM could ignore or misinterpret safety context

**Verdict:** NOT a viable safety mechanism. This is defense-in-depth at best.

### Option 2: Component-Level Hook in Task Tool Frontmatter

**Idea:** If Task tool is defined as a skill/agent, add PreToolUse hook to its frontmatter.

**Problem:** Task is a built-in tool, not a skill we control. We can't modify its frontmatter.

**Verdict:** NOT viable. We don't control Task tool's definition.

### Option 3: Disable Task Tool via Deny Rules

**Idea:** Add Task to permission deny rules to prevent subagent spawning entirely.

```json
{
  "permissions": {
    "deny": ["Task"]
  }
}
```

**Pros:**
- ✅ Guaranteed to prevent subagent spawning
- ✅ Technical enforcement (not LLM-dependent)
- ✅ Simple configuration
- ✅ Documented and supported

**Cons:**
- ❌ Disables ALL Task tool usage (no parallel task execution)
- ❌ Reduces autonomous agent capabilities
- ❌ May limit complex multi-step workflows

**Verdict:** VIABLE but reduces functionality. Conservative approach for Phase 1.

### Option 4: Create Custom Subagent with Embedded Hooks

**Idea:** Define custom subagents with PreToolUse hooks in their frontmatter.

**From documentation:**
```yaml
---
name: secure-bash-agent
description: Bash agent with safety checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/hooks/safety_judge.py"
---
```

**Limitations:**
- ❌ Only applies to our custom agents, not built-in Task tool agents
- ❌ LLM chooses which agent to use (can't force it to use ours)
- ❌ Doesn't solve the general Task tool problem

**Verdict:** Partial solution. Could work for specific use cases but doesn't address core issue.

### Option 5: File Issue with Claude Code Team

**Idea:** Report this as either a bug or documentation gap.

**Possible outcomes:**
1. They clarify plugin hooks SHOULD inherit → it's a bug, gets fixed
2. They clarify plugin hooks DON'T inherit → document mitigation strategies
3. They add a configuration option for hook inheritance
4. They suggest using SubagentStart differently

**Verdict:** Worth doing but doesn't unblock Phase 1.

## Recommendation for Phase 1

**Use Option 3: Disable Task Tool**

**Rationale:**
1. ✅ Guarantees safety (technical enforcement)
2. ✅ Simple, documented, supported
3. ✅ Doesn't require experimental features
4. ✅ Can be relaxed in Phase 2 after validation
5. ❌ Reduces functionality but doesn't block autonomous operation

**Implementation:**
```json
{
  "permissions": {
    "deny": ["Task"]
  }
}
```

**Documentation needed:**
- Add to `.claude/settings.json` template
- Document in AUTONOMOUS-MODE.md as known limitation
- Explain why Task is disabled (hook inheritance unvalidated)
- Note as temporary until hook inheritance confirmed

## Open Questions for Claude Code Team

1. **Do plugin-level PreToolUse hooks fire for subagent tool calls?**
   - If yes: Why didn't our E2E test observe hook execution?
   - If no: Is this intended behavior? Should it be documented?

2. **Are subagents separate sessions with isolated hook contexts?**
   - How do subagent sessions relate to parent session?
   - Do plugins need to re-register hooks for subagent sessions?

3. **What's the recommended approach for applying safety hooks to subagents?**
   - SubagentStart context injection?
   - Component-level hooks in custom agents?
   - Permission deny rules?
   - Something else?

4. **Is there a way to make plugin hooks apply to all subagent tool calls?**
   - Configuration option we're missing?
   - Different registration pattern?
   - Architectural limitation?

## Next Steps

1. ✅ Document findings in this file
2. ⬜ Update task3-subagent-safety.md with Option 3 recommendation
3. ⬜ Implement Task tool deny rule in settings template
4. ⬜ Update execution plan: Task 3 complete with mitigation
5. ⬜ Proceed to Task 4 (Security Bypass Testing)
6. ⬜ File issue with Claude Code team (post-Phase 1)
