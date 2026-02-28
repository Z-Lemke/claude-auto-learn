---
description: Run an adaptive study session for an active course
allowed-tools: Read Write Edit Bash(python3:*) Glob Grep
---

# /study — Start a Study Session

You have been asked to run a study session.

## Instructions

1. **Activate the study skill** to run an adaptive tutoring session.

2. Follow the study skill's complete workflow:
   - Load course state and generate a session plan
   - For each concept: present, practice, evaluate, give feedback, update state
   - Follow the Socratic method — NEVER give answers directly
   - Adapt to learner performance in real time
   - Save all progress and session logs to disk

3. If no courses exist, tell the learner to run `/build-course` first.

## Important

- Never give answers directly — use the hint sequence.
- Update state after every exercise.
- Be adaptive — slow down when struggling, speed up when succeeding.
- End with a summary and preview of next session.
