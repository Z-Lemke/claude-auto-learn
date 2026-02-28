---
description: Build an adaptive learning course for any text-based subject
allowed-tools: Read Write Edit Bash(python3:*) Bash(mkdir:*) Glob Grep WebSearch WebFetch
---

# /build-course — Create a New Learning Course

You have been asked to build a new adaptive learning course.

## Instructions

1. **Activate the build-course skill** to create a structured, adaptive course.

2. Follow the build-course skill's complete workflow:
   - Step 1: Intake — understand what the learner wants to learn
   - Step 2: Research the domain and teaching approaches
   - Step 3: Generate the knowledge graph (concepts, prerequisites, units)
   - Step 4: Generate course config (exercise prompts, rubrics, session preferences)
   - Step 5: Diagnostic assessment to calibrate starting point
   - Step 6: Initialize learner state with diagnostic results
   - Step 7: Present the course plan and next steps

3. All state must be saved to disk via the Python scripts. The course should be fully persistent and ready for `/study` sessions.

## Important

- Take time on the knowledge graph — it's the foundation for the entire course.
- Run the diagnostic honestly to calibrate the starting point.
- Keep scope manageable (30-50 concepts to start).
- Tell the learner to use `/study` when they're ready to begin.
