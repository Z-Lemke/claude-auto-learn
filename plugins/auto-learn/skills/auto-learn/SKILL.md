---
name: auto-learn
description: >
  Analyzes Claude Code sessions to identify learning opportunities and automatically
  creates or improves the project's .claude configuration (CLAUDE.md, hooks, skills,
  agents, settings) to prevent recurring issues. Activates when Claude encounters errors,
  receives developer corrections, struggles with project-specific conventions, or when
  the stop-and-learn hook detects a learning opportunity. Also use when the user says
  'learn', 'remember this', 'update claude config', 'add this to claude config',
  'improve setup', 'fix this hook', or 'update this skill'.
---

# Auto-Learn

Automatically analyze coding sessions and update `.claude` configuration so that Claude gets smarter about this project over time.

## When This Skill Activates

This skill activates in two ways:

1. **Automatically** via the stop-and-learn hook, which detects learning opportunities at the end of Claude responses and continues the session with a learning prompt.
2. **Manually** via the `/learn` command, which the developer can invoke at any point.

When activated, follow the full workflow below.

## Step 1: Analyze the Session

Review the current conversation to identify learning opportunities. Look for these patterns:

### Error-Correction Pattern
Claude made a mistake, the user corrected it. This indicates missing project-specific knowledge.
- Claude used the wrong command, convention, or approach
- User said something like "no, we use X instead" or "that's not how this project works"
- Claude had to be told about a project convention

### Multi-Attempt Pattern
Claude tried something multiple times before succeeding. This indicates missing context about how something works in this project.
- Same tool called 3+ times with different parameters
- Repeated failures before finding the right approach

### Missing Context Pattern
User provided project-specific knowledge that Claude should have had from the start.
- User explained a project convention, architecture decision, or workflow
- User shared information about dependencies, APIs, or patterns this project uses
- User described how the team works (branching strategy, review process, etc.)

### Enforcement Gap Pattern
Something happened that should have been automatically prevented or handled.
- Code was written without proper formatting/linting
- A common mistake was made that a hook could catch
- A permission was needed that could be pre-approved

If no learning opportunities are found, state "No learning opportunities detected in this session" and stop.

## Step 2: Categorize the Learning

For each learning opportunity identified, determine whether to **create new** configuration or **improve existing** configuration. Always check what already exists first.

### Improving Existing Configuration

Before creating anything new, check if existing `.claude` configuration could be improved to address the issue:

- **CLAUDE.md instructions that are too vague**: Make them more specific based on what was learned
- **Hooks that miss edge cases**: Update the hook script to handle the newly discovered scenario
- **Skills with incomplete instructions**: Add the missing step, troubleshooting entry, or example
- **Agents with wrong tool access or insufficient context**: Update their configuration
- **Settings with missing permissions**: Add the permission that was needed
- **Outdated instructions**: Update or remove instructions that are no longer accurate

When improving existing config, make surgical edits rather than rewriting. Preserve the original author's style and intent.

### Creating New Configuration

If no existing configuration covers the learning, determine the best type to create:

### CLAUDE.md Update
**Use when**: The learning is about instructions, conventions, patterns, or context that Claude should know. This is the most common type.
- Project-specific conventions (naming, file organization, architecture)
- Build/test/deploy commands and workflows
- Team preferences and standards
- Technology-specific patterns used in this project
- Common pitfalls and how to avoid them

### Hook Creation
**Use when**: The learning should be enforced automatically via a shell command.
- Code formatting (Prettier, Black, etc.) after file writes
- Linting validation before commits
- Test execution requirements
- File permission or security checks
- Auto-approval of frequently-used safe commands

### Skill Creation
**Use when**: The learning represents a complex, multi-step workflow that Claude performs repeatedly.
- Project-specific deployment procedures
- Complex testing workflows
- Code generation patterns with multiple steps
- Integration workflows

### Settings Update
**Use when**: The learning is about tool permissions or Claude Code configuration.
- Commands that should be auto-approved
- Tool restrictions for safety

## Step 3: Apply the Update

### For CLAUDE.md Updates

1. Read the existing `CLAUDE.md` file (create it if it doesn't exist)
2. Determine the right section for the new instruction:
   - If a relevant section exists, append to it
   - If no relevant section exists, create one with a clear heading
3. Write the instruction clearly and concisely
4. Do NOT duplicate existing instructions
5. Keep instructions actionable and specific
6. Follow the structure in `references/templates/claude-md-structure.md`. Only add sections that have content. Do not create empty sections.

### For Hook Creation

1. Create the hook script in `.claude/hooks/`
2. Base it on the template in `references/templates/hook-template.sh`
3. Make the script executable: `chmod +x .claude/hooks/<script-name>.sh`
4. Register the hook in `.claude/settings.json` following the structure in `references/templates/hook-settings.json`

When creating hooks, follow these rules:
- Use `set -euo pipefail` for safety
- Parse stdin JSON with `python3 -c` if `jq` is not available
- Use exit code 0 for success, 2 for blocking
- Keep hooks fast (under 10 seconds)
- Log errors to stderr, structured output to stdout

### For Skill Creation

1. Create a directory under `.claude/skills/<skill-name>/`
2. Base it on the template in `references/templates/skill-template.md`
3. Keep SKILL.md under 5000 words
4. Add scripts to `scripts/` subdirectory if needed
5. Add reference docs to `references/` if needed

### For Settings Updates

1. Read existing `.claude/settings.json`
2. Merge the new settings carefully (don't overwrite existing entries)
3. Write the updated settings back

## Step 4: Log the Learning

After applying any update, append an entry to `.claude/learnings.md` following the format in `references/templates/learning-entry.md`.

Create `.claude/learnings.md` if it doesn't exist, using the header from `references/templates/learnings-header.md`.

## Step 5: Summarize

After all updates are applied, provide a brief summary:
- What was learned
- What configuration was updated
- Why this will help in future sessions

## Important Guidelines

- **Be conservative**: Only create learnings that are clearly project-specific and would help in future sessions. Do not log one-off issues or user-specific preferences.
- **Be specific**: "Use pytest for testing" is too vague. "Run tests with `pytest tests/ -v --tb=short` from the project root" is specific and actionable.
- **Don't duplicate**: Always check existing configuration before adding. If an instruction already covers the learning, skip it.
- **Don't over-engineer**: Prefer CLAUDE.md updates over hooks. Prefer hooks over skills. Only create the minimum configuration needed.
- **Respect existing structure**: If the project already has a CLAUDE.md with a specific style, match that style. Don't reorganize existing content.
- **One learning at a time**: Apply each learning as a discrete, focused change. Don't bundle unrelated learnings into one update.
