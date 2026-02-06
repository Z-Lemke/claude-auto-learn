# auto-claude-builder

A Claude Code plugin that automatically improves repository-level `.claude` configuration based on learned experiences.

## How It Works

When Claude encounters problems during a coding session -- errors, developer corrections, missing project context -- this plugin detects those learning opportunities and automatically updates the project's `.claude` configuration. Over time, Claude gets smarter about each project without anyone needing to manually fine-tune prompts, skills, or hooks.

### What Gets Updated

The plugin can create or improve any `.claude` configuration:

- **CLAUDE.md** -- Project instructions, conventions, and context
- **Hooks** -- Automated enforcement scripts (formatting, linting, validation)
- **Skills** -- Complex workflow instructions
- **Agents** -- Subagent configurations
- **Settings** -- Permissions and tool approvals

### Detection Patterns

The auto-learn system detects four types of learning opportunities:

1. **Error-Correction**: Claude made a mistake, the developer corrected it
2. **Multi-Attempt**: Claude struggled, trying the same thing multiple times
3. **Missing Context**: The developer shared project-specific knowledge Claude should have had
4. **Enforcement Gap**: Something that should have been automatically prevented or handled

## Installation

Install as a Claude Code plugin:

```bash
claude plugin add Z-Lemke/auto-claude-builder
```

## Setup

After installing the plugin, set up automatic learning in your project:

```
/setup-auto-learn
```

This installs a Stop hook that analyzes each session for learning opportunities. When opportunities are detected, Claude automatically continues the session to analyze and update `.claude` configuration.

## Usage

### Automatic Mode

Once hooks are installed via `/setup-auto-learn`, the plugin works autonomously:

1. You work with Claude normally
2. At the end of each response, the stop hook checks for learning opportunities
3. If corrections, failures, or context-sharing are detected, Claude continues
4. Claude analyzes what happened and updates `.claude` config
5. Changes show up in your next `git diff` and go through normal PR review

### Manual Mode

You can also trigger learning analysis manually at any point:

```
/learn
```

This analyzes the current session and applies any learnings to `.claude` configuration.

## What Gets Created

All learnings are stored at the repo level in `.claude/`:

```
.claude/
  CLAUDE.md          # Updated with project instructions
  settings.json      # Updated with hooks and permissions
  learnings.md       # Log of what was learned and when
  hooks/             # Auto-generated hook scripts
  skills/            # Auto-generated skill files
```

Changes are committed to the repo and go through normal code review.

## Architecture

```
auto-claude-builder/
  .claude-plugin/
    plugin.json          # Plugin manifest
    marketplace.json     # Marketplace registration
  skills/
    auto-learn/
      SKILL.md           # Core skill: analyze sessions, update config
      scripts/
        detect-learning-opportunity.py  # Transcript analysis
  commands/
    learn.md             # /learn - manual trigger
    setup-auto-learn.md  # /setup-auto-learn - install hooks
  hooks/
    templates/
      stop-and-learn.sh  # Stop hook template
```

### Components

- **auto-learn skill**: The brain of the plugin. Contains instructions for analyzing sessions, categorizing learnings, and generating the right type of `.claude` configuration update.

- **detect-learning-opportunity.py**: Python script that analyzes JSONL transcripts for patterns indicating learning opportunities (corrections, repeated failures, context sharing).

- **stop-and-learn.sh**: Stop hook that fires at the end of each Claude response. Runs the detection script and returns `{"continue": true}` when a learning opportunity is found.

- **/learn command**: Manual trigger for learning analysis.

- **/setup-auto-learn command**: One-time setup that installs the stop hook in a project.

## License

MIT
