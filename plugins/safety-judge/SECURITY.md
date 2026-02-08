# ⚠️ CRITICAL SECURITY WARNING

## DO NOT USE IN AUTONOMOUS MODE

This plugin is **NOT safe for autonomous or production use** due to a critical security bug in Claude Code.

## The Issue

**Plugin-level PreToolUse hooks do not fire for Task tool subagents.**

- Subagents spawned via Task tool can bypass ALL safety restrictions
- This includes:
  - Catastrophic command denylist (rm -rf, etc.)
  - Permission deny rules
  - Permission allow rules
  - LLM judge evaluation
  - All safety layers

## Proof

We have empirically confirmed this via E2E testing:
- Spawned subagent via Task tool
- Subagent attempted `curl` command (in deny rules)
- **NO hook execution** - safety hook did not fire
- Command was blocked by sandbox network restriction, NOT by our deny rule

## Upstream Issue

**Claude Code Bug:** https://github.com/anthropics/claude-code/issues/21460

Status: OPEN, awaiting fix from Anthropic team

## Safe Usage

Until the upstream bug is fixed, you have two options:

### Option 1: Disable Task Tool (Recommended)
```json
{
  "permissions": {
    "deny": ["Task"]
  }
}
```

This prevents subagent spawning entirely, eliminating the bypass hole.

**Trade-off:** No parallel task execution, reduced agent capabilities

### Option 2: Await Upstream Fix

Monitor issue #21460 for updates. Once Claude Code implements hook inheritance for subagents, this plugin will be safe for autonomous use.

## Current Status

This plugin provides effective safety for:
- ✅ Main agent tool calls
- ✅ Direct user-initiated commands
- ✅ All non-Task tool operations

This plugin CANNOT protect against:
- ❌ Task tool subagent operations
- ❌ Any tool call made by a spawned subagent
- ❌ Multi-level agent hierarchies

## Development Status

We are continuing development to prove out the RPIV workflow and plugin architecture. Once Claude Code fixes hook inheritance, this plugin will provide comprehensive safety for autonomous operation.

**Last Updated:** 2026-02-08
**Tracking Issue:** https://github.com/anthropics/claude-code/issues/21460
