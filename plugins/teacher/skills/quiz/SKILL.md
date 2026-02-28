---
name: quiz
description: >
  Runs a quiz or assessment for an active course. Pure assessment mode — no teaching,
  no hints. Tests mastery and updates progress. Trigger phrases: 'quiz', 'test me',
  'assessment', 'check my knowledge', 'exam', 'how well do I know', 'quiz me'.
---

# Quiz / Assessment

Run a focused assessment to test the learner's knowledge without teaching.

## On Start

1. Load course state:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import list_courses, load_course, load_progress
from planner import get_review_items
courses = list_courses()
import json
print(json.dumps(courses))
"
```

2. Ask what kind of quiz:
   - **Unit quiz**: Test a specific unit ("Quiz me on Unit 2")
   - **Comprehensive**: Test all active/learning concepts
   - **Review quiz**: Test items due for FSRS review
   - **Custom**: Learner specifies which concepts

3. Select concepts based on quiz type. Aim for 5-15 questions depending on scope.

## Modality Selection for Quiz

Quizzes can use different modalities depending on the domain and concept type:

- **Conversation** (default): Direct Q&A, fastest turnaround. Use for most quiz questions.
- **Worksheet**: For vocabulary/terminology quizzes with many items. Write a worksheet file at `~/.claude/teaching/learner/COURSE/worksheets/` following the worksheet schema (HTML comment metadata, `___` placeholders, hidden answer key).
- **Code exercise**: For implementation quizzes. Write `exercise.py` + `test_exercise.py` at `~/.claude/teaching/learner/COURSE/exercises/CONCEPT_ID/`.
- **Long-form**: For comprehensive assessments at Bloom levels Analyze/Evaluate/Create. Pose an open-ended question requiring multi-paragraph response.

**Selection rules**:
- Quick quizzes (5-8 questions): use conversation exclusively
- Unit/comprehensive quizzes: mix modalities — start with conversation, include 1-2 worksheet or code exercises for depth
- Never more than 1 file-based exercise per quiz (keeps it focused)

## Quiz Loop

For each concept being quizzed:

1. **Generate a question** at the concept's current Bloom level
   - Questions should require active recall or production, not just recognition
   - Vary question types: open-ended, fill-in, translate, explain, apply, compare
   - For languages: translate sentences, complete phrases, correct errors, produce sentences
   - For technical: explain concepts, solve problems, analyze scenarios, evaluate trade-offs

2. **Present the question** — clearly, with no hints embedded

3. **Collect the answer** — let the learner respond fully before evaluating

4. **Evaluate using the assessor subagent**

   Invoke the `teaching-assessor` subagent (defined at `${CLAUDE_PLUGIN_ROOT}/agents/assessor.md`) to evaluate the response:
   - Pass: the exercise prompt, learner response, concept metadata from knowledge graph, assessment rubric from course config, error taxonomy, current bloom level
   - Use the assessor's FSRS rating for state updates
   - Record the assessor's error classification (slip/misconception/gap) in error_history

   **If the assessor subagent is unavailable**: Fall back to self-evaluation using this rubric:
   - **Correctness** (binary): Is the core answer right or wrong?
   - **Completeness** (0-2): 0=major gaps, 1=partial, 2=complete
   - **Depth** (for Bloom >= Apply): Does the answer show understanding beyond recall?

   FSRS rating mapping:
   - Correct + Complete + Deep = EASY (4)
   - Correct + Complete = GOOD (3)
   - Correct but incomplete OR partially correct = HARD (2)
   - Incorrect or fundamentally wrong = AGAIN (1)

   DO NOT give GOOD or EASY for answers that are correct but show no understanding. If the learner likely guessed, rate HARD.

5. **Provide brief feedback**
   - Correct: clear pass
   - Partially correct: note what was right and what was wrong
   - Incorrect: note the correct answer with a brief explanation
   - DO give the correct answer in quiz mode (unlike study mode, the point here is assessment)

6. **Rate and update state**:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import update_concept_progress
from planner import compute_mastery_score, should_advance, next_bloom_level, is_mastered
from fsrs import review as fsrs_review, FSRSState, Rating
# RATING: 1=again(wrong), 2=hard(struggled), 3=good(correct), 4=easy(instant)
# CORRECT: True or False

result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'practice_count': NEW_COUNT,
    'correct_count': NEW_CORRECT,
    'last_practiced': 'ISO_NOW',
    'fsrs': UPDATED_FSRS_DICT,
    'recent_results': (EXISTING_RECENT + [CORRECT])[-10:]
})

# Compute and update mastery score
cp = result['concepts']['CONCEPT_ID']
mastery = compute_mastery_score(cp)
result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'mastery_score': mastery
})

# Check for Bloom level advancement
cp = result['concepts']['CONCEPT_ID']
if should_advance(cp):
    current_bloom = cp.get('bloom_level', 'remember')
    new_bloom = next_bloom_level(current_bloom)
    if new_bloom:
        result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
            'bloom_level': new_bloom
        })
    elif is_mastered(cp):
        result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
            'status': 'mastered'
        })
"
```

## Results

After all questions:

1. **Score**: X/Y correct (percentage)
2. **Per-concept breakdown**: which concepts were strong, which need work
3. **Mastery changes**: any concepts newly mastered or dropped from mastery
4. **Recommendations**: "Focus your next study session on [weak areas]" or "You're ready to move to [next unit]"

Save session log:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import append_session_log
append_session_log('COURSE_NAME', {
    'started': 'ISO_START',
    'ended': 'ISO_END',
    'type': 'quiz',
    'concepts_practiced': CONCEPT_LIST,
    'exercises': EXERCISE_LIST,
    'score': {'correct': X, 'total': Y, 'percentage': Z},
    'summary': 'Quiz summary'
})
"
```

## Important Guidelines

- **No teaching during quiz** — save explanations for after the question is graded
- **Brief feedback only** — correct/incorrect + the right answer. Don't go into long explanations.
- **Be honest in grading** — a generous quiz defeats its purpose
- **Update FSRS after every question** — this data drives future review scheduling
- **Use the assessor** — let the assessor subagent evaluate responses when available. Self-assessment is the fallback, not the default.
- **Track error types** — record slip/misconception/gap classification in error_history for each incorrect answer
