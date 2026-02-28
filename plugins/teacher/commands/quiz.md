---
description: Run a quiz to test your knowledge on an active course
allowed-tools: Read Write Edit Bash(python3:*) Glob Grep
---

# /quiz — Test Your Knowledge

You have been asked to run a quiz.

## Instructions

1. **Activate the quiz skill** to run an assessment session.

2. Follow the quiz skill's workflow:
   - Load course state and determine quiz scope
   - Generate and present questions
   - Evaluate answers honestly
   - Update FSRS state after each question
   - Present results with recommendations

3. If no courses exist, tell the learner to run `/build-course` first.

## Important

- This is assessment, not teaching. Give answers after grading, not hints.
- Be honest in evaluation — generous grading defeats the purpose.
- Update state after every question.
