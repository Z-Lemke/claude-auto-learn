---
description: Analyze the current session for learning opportunities and update .claude configuration
allowed-tools: Bash(mkdir:*) Bash(chmod:*) Read Write Edit Glob Grep
---

# /learn - Analyze Session and Update Configuration

You have been asked to analyze the current session for learning opportunities.

## Instructions

1. **Activate the auto-learn skill** to perform a full analysis of this session.

2. Follow the auto-learn skill's complete workflow:
   - Step 1: Analyze the session for learning opportunities
   - Step 2: Categorize each learning (improve existing config vs create new)
   - Step 3: Apply the updates to `.claude` configuration
   - Step 4: Log the learning to `.claude/learnings.md`
   - Step 5: Summarize what was learned

3. If no learning opportunities are found, say so and suggest what kinds of issues the auto-learn system can capture.

## Important

- Be conservative. Only log genuine, project-specific learnings.
- Check existing `.claude` configuration before creating duplicates.
- Prefer improving existing config over creating new config.
- Keep all changes minimal and focused.
