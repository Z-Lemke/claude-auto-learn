# llm-toolkit Development Guide

## Project Structure

This is a multi-plugin Claude Code marketplace. Each plugin lives under `plugins/` with its own `.claude-plugin/plugin.json`, hooks, skills, and commands.

```
.claude-plugin/            Root marketplace manifest
plugins/
  auto-learn/              Session learning plugin
    .claude-plugin/          Plugin manifest
    skills/auto-learn/       Core skill (SKILL.md + scripts)
    commands/                Slash commands (/learn)
    hooks/                   Stop hook (hooks.json + templates)
    tests/                   Plugin-specific tests
  safety-judge/            PreToolUse safety hook plugin
    .claude-plugin/          Plugin manifest
    hooks/                   PreToolUse hook (hooks.json + safety_judge.py)
    tests/                   Plugin-specific tests
tests/
  fixtures/                Shared test fixtures (transcripts)
  conftest.py              Shared test configuration
```

## Key Design Decisions

- **Monorepo marketplace**: Each plugin is independently installable via `claude plugin install <name>`
- **Per-plugin tests**: Each plugin has its own test suite, runnable independently or holistically
- **Shared fixtures**: Test data lives at `tests/fixtures/` and is available to all plugins
- **Autonomous operation**: Plugins update config without asking. Changes go through PR review.
- **Repo-level only**: All learnings go to project `.claude/` directory, not user-level config.
- **Zero setup**: Hooks auto-register via `hooks/hooks.json` when a plugin is enabled.

## Testing

```bash
# All tests
pytest

# Single plugin
pytest plugins/auto-learn
pytest plugins/safety-judge

# E2e tests (requires Claude CLI)
RUN_E2E=1 pytest plugins/auto-learn/tests/test_e2e.py
```

## Conventions

- Hook scripts use `#!/usr/bin/env bash` with `set -euo pipefail`
- Python scripts target Python 3.8+ (macOS and Linux compatible)
- YAML frontmatter in commands uses `allowed-tools` to restrict tool access
- Skill descriptions must include trigger phrases for reliable activation
- Each plugin must have `.claude-plugin/plugin.json` with name, version, description
