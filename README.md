# llm-toolkit

A collection of Claude Code plugins for automated learning, safety, and development workflows.

## Plugins

### auto-learn

Automatically improves repository-level `.claude` configuration based on learned experiences. When Claude encounters errors, developer corrections, or missing project context, this plugin detects those learning opportunities and updates the project's `.claude` configuration.

**Detection patterns:**
- Error-Correction: Claude made a mistake, the developer corrected it
- Multi-Attempt: Claude struggled, trying the same thing multiple times
- Missing Context: The developer shared project-specific knowledge
- Enforcement Gap: Something that should have been automatically prevented

### safety-judge

PreToolUse safety hook with a layered security model:
1. Regex denylist for catastrophic commands (hard deny)
2. Permission rules from settings.json (allow/deny/ask)
3. LLM-as-judge via Haiku for ambiguous cases (escalates to ask, never hard-denies)

Gives you the convenience of `--dangerously-skip-permissions` with programmatic safety checks instead of manual approval fatigue.

## Installation

```bash
# Add the marketplace
claude plugin marketplace add Z-Lemke/llm-toolkit

# Install individual plugins
claude plugin install auto-learn
claude plugin install safety-judge
```

Hooks auto-register when each plugin is enabled -- no per-project setup needed.

## Usage

### auto-learn

Once installed, it works autonomously:
1. You work with Claude normally
2. At the end of each response, the stop hook checks for learning opportunities
3. If detected, Claude analyzes what happened and updates `.claude` config
4. Changes show up in your next `git diff` and go through normal PR review

Manual trigger: `/auto-learn:learn` or just say "learn" / "remember this".

### safety-judge

Once installed, the PreToolUse hook intercepts every tool call:
- Commands matching your allow rules pass through (after LLM safety check)
- Commands matching deny rules are blocked
- Everything else prompts for approval
- Catastrophic commands (rm -rf /, DROP DATABASE, fork bombs) are always blocked

## Repository Structure

```
llm-toolkit/
  .claude-plugin/
    marketplace.json       Marketplace manifest (lists all plugins)
  plugins/
    auto-learn/            Session learning and config improvement
    safety-judge/          PreToolUse safety hook with LLM judge
  tests/
    fixtures/              Shared test fixtures
    conftest.py            Shared test configuration
```

## Testing

```bash
# Run all tests
pytest

# Run tests for a specific plugin
pytest plugins/auto-learn
pytest plugins/safety-judge
```

## License

MIT
