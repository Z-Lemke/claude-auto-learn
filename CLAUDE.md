# auto-claude-builder Development Guide

## Project Structure

This is a Claude Code plugin with no traditional executable code. The implementation is prompt-driven: markdown files with YAML frontmatter that Claude Code interprets.

```
.claude-plugin/        Plugin manifests (plugin.json, marketplace.json)
skills/auto-learn/     Core skill that drives learning analysis and config updates
  SKILL.md             Main skill instructions
  scripts/             Python scripts for transcript analysis
commands/              Slash commands (/learn, /setup-auto-learn)
hooks/templates/       Hook script templates installed into target projects
```

## Key Design Decisions

- **Autonomous operation**: The plugin updates config without asking. Changes go through PR review.
- **Repo-level only**: All learnings go to project `.claude/` directory, not user-level config.
- **Improve before create**: Always check if existing config can be improved before creating new.
- **Conservative learnings**: Only capture genuinely project-specific knowledge, not one-off issues.
- **Progressive config types**: Prefer CLAUDE.md > hooks > skills. Use the simplest mechanism that works.

## Testing

To test the plugin locally, install it in a test project:
```bash
claude plugin add /path/to/auto-claude-builder
```

Then in the test project:
1. Run `/setup-auto-learn` to install hooks
2. Work with Claude and intentionally create correction scenarios
3. Verify that `.claude/` config gets updated appropriately
4. Check `.claude/learnings.md` for the learning log

## Conventions

- Hook scripts use `#!/usr/bin/env bash` with `set -euo pipefail`
- Python scripts target Python 3.8+ (macOS and Linux compatible)
- YAML frontmatter in commands uses `allowed-tools` to restrict tool access
- Skill descriptions must include trigger phrases for reliable activation
