---
name: study
description: >
  Runs an adaptive tutoring session for an active course. Activates when the user wants
  to study, practice, learn, review, or continue learning. Trigger phrases: 'study',
  'let me study', 'practice', 'continue learning', 'teach me', 'review', 'start session',
  'lets learn', 'next lesson'. Teaches new concepts and reviews old ones using spaced
  repetition and Socratic method.
---

# Study Session

Run an adaptive teaching session that introduces new concepts and reviews old ones.

## On Session Start

1. Load available courses and identify which one to study:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import list_courses, load_profile
courses = list_courses()
profile = load_profile()
print('Available:', courses)
print('Active:', profile.get('active_courses', []))
"
```

2. If multiple courses exist, ask the learner which one. If only one, use it.

3. Load course state and generate a session plan:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import load_course, load_progress
from planner import plan_session, get_frontier, get_review_items
kg, curriculum, config = load_course('COURSE_NAME')
progress = load_progress('COURSE_NAME')
config_duration = config.get('session_preferences', {}).get('default_duration_minutes', 25)
plan = plan_session(kg, progress, duration_minutes=config_duration)
frontier = get_frontier(kg, progress)
reviews = get_review_items(progress)
import json
print(json.dumps({
    'plan': plan,
    'frontier': frontier,
    'reviews': reviews,
    'domain_type': config.get('domain_type', 'conceptual'),
    'modality_weights': config.get('exercise_config', {}).get('modality_weights', {}),
    'modality_overrides': config.get('exercise_config', {}).get('modality_overrides', {})
}, indent=2))
"
```

4. Briefly tell the learner what today's session covers: "Today we'll learn [new concepts] and review [review concepts]."

## Teaching Loop

For each item in the session plan, follow this cycle:

### For NEW concepts (Worked-Example Fading):

**1. Present the concept**
- Explain it clearly, adapted to the learner's level
- Use examples, analogies, and context
- For languages: introduce vocabulary in sentences, show the pattern before stating the rule
- For technical: start with the "why", then the "what", then the "how"
- Keep it concise -- do not lecture for paragraphs

**2. Demonstrate with a worked example**
- Show one complete example with your reasoning visible
- For languages: "Here's how I would use this in a sentence: [sentence]. I chose [word] because [reason]."
- For technical: "Here's how I'd solve this: [step-by-step solution with reasoning visible at each step]"
- For conceptual: "Let me walk through an example: [scenario] -- here is how I would apply [concept]..."
- The learner watches you think aloud. This is not a test -- it is a demonstration.

**3. Guided practice (walk through together)**
- Present a similar problem and solve it WITH the learner
- "Now let's try one together. What would be the first step?"
- Prompt the learner for each sub-step, filling in if they are stuck
- The goal is a successful completion with scaffolding, not independent performance yet

**4. Independent practice exercise**
- Select a modality using the Exercise Modality System (see below)
- Generate an exercise at the appropriate Bloom level for this concept
- Use the exercise prompts from the course config
- The exercise should require active production, not just recognition
- Before presenting the exercise, run it through the content reviewer (see Subagent Integration)

**5. Evaluate and give feedback** (see Feedback section below)

**6. Update state** after evaluating:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import update_concept_progress, load_progress
from planner import compute_mastery_score, should_advance, next_bloom_level, is_mastered
from fsrs import review as fsrs_review, FSRSState, Rating
# RATING: 1=again, 2=hard, 3=good, 4=easy
# CORRECT: True or False

# First update the core fields
result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'status': 'learning',
    'practice_count': CURRENT_PRACTICE + 1,
    'correct_count': CURRENT_CORRECT + (1 if CORRECT else 0),
    'last_practiced': 'ISO_DATETIME',
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
        print(f'Advanced from {current_bloom} to {new_bloom}')
    elif is_mastered(cp):
        result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
            'status': 'mastered'
        })
        print('Concept mastered!')
print(f'mastery_score: {mastery:.2f}')
"
```

### For REVIEW concepts:

**1. Brief recap** -- One sentence reminding them what this concept is
**2. Exercise** -- Select a modality (prefer conversation for reviews -- fastest turnaround). Can be slightly harder than when first learned.
**3. Evaluate and feedback**
**4. Update FSRS state** -- This is critical for scheduling future reviews. Use the same state update code above.

---

## Exercise Modality System

The system supports five exercise modalities. Each item in the session plan gets a modality selected based on domain type, Bloom level, and concept type.

### Modalities

| Modality | Delivery | Best For |
|----------|----------|----------|
| **Worksheet** | MD file written to disk; learner fills in blanks | Vocabulary drills, fill-in-blank grammar, translation sets, term definitions, matching |
| **Conversation** | Interactive Q&A in-session | Socratic dialogue, roleplay, explanation practice, verbal reasoning, quick reviews |
| **Code** | Real files with tests; learner implements | Programming concepts, algorithm practice, any domain where code expresses understanding |
| **Long-form** | Open-ended written response (in chat or file) | Higher Bloom levels (Analyze, Evaluate, Create), essays, case studies, compare-and-contrast |
| **Image review** | Learner uploads photo of handwritten work | Script/handwriting practice, math proofs, diagrams -- always opt-in, never required |

### Decision Matrix

Look up (domain_type, bloom_level, concept_type) to select the primary modality:

| Domain Type | Bloom Level | Concept Type | Primary | Secondary |
|-------------|-------------|--------------|---------|-----------|
| Language | Remember | Vocabulary | Worksheet | Conversation |
| Language | Remember | Grammar rules | Worksheet | Conversation |
| Language | Understand | Grammar patterns | Conversation | Worksheet |
| Language | Understand | Cultural context | Conversation | Long-Form |
| Language | Apply | Sentence construction | Conversation | Worksheet |
| Language | Apply | Translation | Worksheet | Conversation |
| Language | Analyze | Text analysis | Long-Form | Conversation |
| Language | Evaluate | Register/style | Long-Form | Conversation |
| Language | Create | Free composition | Long-Form | Conversation |
| Language | * | Script/handwriting | Image Review | Worksheet |
| Technical | Remember | Terminology | Worksheet | Conversation |
| Technical | Remember | Syntax/APIs | Worksheet | Code |
| Technical | Understand | Concepts | Conversation | Long-Form |
| Technical | Apply | Implementation | Code | Conversation |
| Technical | Apply | Problem-solving | Code | Worksheet |
| Technical | Analyze | Code review | Long-Form | Conversation |
| Technical | Analyze | Architecture | Long-Form | Conversation |
| Technical | Evaluate | Trade-offs | Conversation | Long-Form |
| Technical | Create | Design/build | Code | Long-Form |
| Conceptual | Remember | Facts/definitions | Worksheet | Conversation |
| Conceptual | Understand | Concepts/models | Conversation | Long-Form |
| Conceptual | Apply | Case application | Long-Form | Conversation |
| Conceptual | Analyze | Relationships | Long-Form | Conversation |
| Conceptual | Evaluate | Arguments/evidence | Conversation | Long-Form |
| Conceptual | Create | Synthesis/proposals | Long-Form | Conversation |
| Interview | Remember | Knowledge recall | Conversation | Worksheet |
| Interview | Understand | Concept explanation | Conversation | Long-Form |
| Interview | Apply | Problem-solving | Conversation | Code |
| Interview | Analyze | System design | Long-Form | Conversation |
| Interview | Evaluate | Trade-off analysis | Conversation | Long-Form |

### Modality Selection Algorithm

```
1. Look up (domain_type, bloom_level, concept_type) in the decision matrix
2. If a direct match exists, use the primary modality
3. If no direct match, use the closest bloom_level match for the domain_type
4. Check course config for modality_overrides -- course-level overrides take precedence
5. Apply learner preference override (if profile specifies modality preferences)
6. Apply variety rule: if the last 3 exercises used the same modality,
   switch to the secondary modality
7. Apply session context: if session is near end (< 5 min remaining),
   prefer Conversation (fastest turnaround)
```

### Modality Transition Rules

1. **Teaching always uses conversation.** New concepts are introduced through dialogue, never worksheets.
2. **Practice uses the decision matrix.** The modality for practice exercises is selected from the matrix above.
3. **Reviews prefer conversation.** Review exercises should be fast. Conversation is the fastest turnaround modality.
4. **File-based modalities (worksheet, code) create a pause.** When you assign a worksheet or code exercise, the session pauses while the learner works. Set expectations: "Take your time. Tell me when you're done."
5. **Never assign two file-based exercises back-to-back.** This kills session momentum. Always interleave with conversation.
6. **Image review is always opt-in.** Never require image submission. Always offer it as an option: "You can also practice writing these characters by hand and show me a photo."

---

## Generating Exercises by Modality

### Worksheet Generation

**File location**: `~/.claude/teaching/learner/COURSE_NAME/worksheets/<timestamp>-<concept-id>.md`

Generate worksheets using this markdown schema:

```markdown
<!-- WORKSHEET -->
<!-- course: COURSE_NAME -->
<!-- concept: CONCEPT_ID -->
<!-- bloom_level: LEVEL -->
<!-- status: pending -->

# Worksheet: TITLE

**Instructions**: Fill in the blanks. Replace each `___` with your answer.

## Section 1: SECTION_TITLE

1. Question text: ___
2. Question text: ___

## Section 2: SECTION_TITLE

1. Question text: ___

<!-- ANSWER_KEY -->
<!-- answers:
1.1: answer
1.2: answer / alternate_answer
2.1: answer
-->
```

Key schema rules:
- Use `<!-- WORKSHEET -->` marker and metadata in HTML comments (invisible when rendered, parseable by the agent)
- All answer placeholders use `___` (three underscores)
- Answer key is in an HTML comment block. Multiple acceptable answers separated by ` / `
- Status field: `pending` -> `submitted` -> `evaluated`
- Answers referenced as `section.question` (e.g., `1.3` = Section 1, Question 3)

Worksheet flow:
1. Generate worksheet content following the schema
2. Write the file using the Write tool
3. Tell the learner: "I've created a worksheet at [path]. Open it in your editor, fill in the blanks, save, and tell me when you're done."
4. Wait for the learner to say "done" / "finished" / "check my worksheet"
5. Read the file, compare answers against the answer key
6. Provide feedback: score X/Y, per-question feedback for incorrect/partial answers
7. Update concept progress and worksheet status

### Code Exercise Generation

**File location**: `~/.claude/teaching/learner/COURSE_NAME/exercises/<concept-id>/`

Create two files:

**exercise.py** (or appropriate extension from course config):
```python
#!/usr/bin/env python3
"""
Exercise: TITLE
Concept: CONCEPT_ID
Bloom Level: LEVEL

Instructions:
    Description of what the learner should implement.

Hints (read only if stuck):
    1. First hint
    2. Second hint
    3. Third hint
"""


def function_name(params) -> return_type:
    """Docstring describing expected behavior."""
    # YOUR CODE HERE
    pass
```

**test_exercise.py**:
```python
#!/usr/bin/env python3
"""Tests for CONCEPT_ID exercise."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from exercise import function_name


def test_normal_case():
    assert function_name(input) == expected

def test_edge_case():
    assert function_name(edge_input) == expected

# ... more test cases ...


if __name__ == "__main__":
    tests = [test_normal_case, test_edge_case]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS: {test.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
```

Code exercise flow:
1. Create exercise file and test file
2. Tell learner: "I've created a code exercise at [path]. Implement the function in exercise.py, then run: `python3 [path/to/test_exercise.py]`"
3. Wait for the learner to implement and run tests
4. When they report back (or you run tests via Bash), evaluate: how many tests passed, read the implementation for approach quality
5. Provide feedback and update state

### Conversation Exercises

Conversation exercises happen entirely in-session. Types:

- **Direct question**: "Explain what happens when..."
- **Socratic dialogue**: "Let's explore how X works. What do you think..."
- **Roleplay / scenario**: "Let's practice [scenario]. I'll be [role]..."
- **Error identification**: "Find and correct the error in..."
- **Prediction / application**: "Given what you know about X, what would happen if..."

Evaluate inline: correctness, reasoning quality, and (for language) grammar/vocabulary/register appropriateness.

### Long-Form Exercises

For Bloom levels Analyze, Evaluate, and Create. Pose an open-ended question requiring a multi-paragraph response. The learner can respond in chat (shorter responses) or you can create a response template file at `~/.claude/teaching/learner/COURSE_NAME/responses/<timestamp>-<concept-id>.md`.

Evaluate against a rubric with dimensions: Accuracy (weight 0.3), Completeness (0.25), Reasoning Depth (0.25), Communication (0.2). Map weighted score to FSRS: 3.5-4.0 = Easy, 2.5-3.4 = Good, 1.5-2.4 = Hard, < 1.5 = Again.

### Image Review Exercises

Always opt-in. Offer as: "You can also practice writing these by hand and show me a photo."

When the learner provides an image:
1. Read the image using the Read tool (Claude's vision capability)
2. Evaluate: character formation/legibility (scripts), structural correctness (diagrams), step correctness (math)
3. Express uncertainty when image quality is poor -- never claim handwriting is "wrong" when you simply cannot read it
4. Provide feedback and update state

---

## Subagent Integration

### Content Reviewer (Pre-Delivery Quality Gate)

Before presenting any new exercise or explanation to the learner, invoke the content reviewer subagent defined at `${CLAUDE_PLUGIN_ROOT}/agents/content-reviewer.md`.

Pass to the reviewer:
- The generated exercise or explanation text
- Concept metadata (concept ID, prerequisites, relationships)
- Target Bloom level
- Domain type
- Course config quality criteria

If the reviewer rejects the content (returns `"approved": false`):
- Read the reviewer's issues and suggestions
- Regenerate the content addressing the identified problems
- Re-submit to the reviewer
- After 2 rejections, proceed with your best version (do not loop indefinitely)

This is especially critical for:
- Low-resource language content (e.g., Malay) where LLM training data may be unreliable
- Technical content where APIs or patterns may have changed
- Any exercise where factual accuracy directly determines the learner's score

### Assessor (Post-Response Evaluation)

After the learner responds to an exercise, invoke the assessor subagent defined at `${CLAUDE_PLUGIN_ROOT}/agents/assessor.md`.

Pass to the assessor:
- Exercise prompt (the question or task given)
- Learner response (what they submitted)
- Concept metadata (concept ID, prerequisites, relationships)
- Course config rubrics (domain-specific grading criteria)
- Error taxonomy (known error patterns for this concept/domain)
- Current Bloom level

Use the assessor's output for state updates:
- Use the assessor's `fsrs_rating` (not your own self-assessment) for the FSRS state update
- Use the assessor's `correct` field to determine CORRECT in the state update code
- Record the assessor's `error_type` and `error_description` in the concept's `error_history`:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import update_concept_progress, load_progress
progress = load_progress('COURSE_NAME')
existing_errors = progress['concepts']['CONCEPT_ID'].get('error_history', [])
update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'error_history': existing_errors + [{
        'type': 'ERROR_TYPE',
        'description': 'ERROR_DESCRIPTION',
        'timestamp': 'ISO_DATETIME'
    }]
})
"
```

### Graceful Degradation

If subagent invocation fails (e.g., tool not available, timeout, error):
- Fall back to self-assessment -- evaluate the response yourself using the rubric dimensions and FSRS mapping from this document
- Log a note in the session summary that subagent evaluation was unavailable
- This ensures the session is never blocked by infrastructure issues

---

## Feedback Rules

### CRITICAL: Socratic Method

**You MUST follow these rules. They are non-negotiable.**

- **NEVER give the answer directly** unless the learner has gone through the full resistance protocol below
- **NEVER solve the problem for them** when they ask

### Socratic Resistance Protocol (4-Layer)

When the learner pushes for the answer directly ("just tell me", "what's the answer?"):

1. **First request**: "I know it's tempting! Let me give you a hint that should help..." (proceed with the hint sequence below)
2. **Second request**: "I hear you -- this is hard. Let's break it into a smaller piece. Can you tell me just [smallest sub-step]?"
3. **Third request**: "OK, let's try a different angle. [Rephrase the problem using a different analogy or context]"
4. **Fourth request (give in gracefully)**: "Alright, let's work through this one together." Give the answer BUT require explain-back: "Now, can you explain to me in your own words why that's the answer?"

NEVER hand over the answer without the explain-back step. The explain-back preserves learning value even when Socratic scaffolding fails.

### When the learner is CORRECT:
- Acknowledge specifically what they got right
- If appropriate, ask a brief follow-up to deepen understanding
- Move on -- do not belabor correct answers

### When the learner is PARTIALLY CORRECT:
- Acknowledge what is right: "You've got [X] right..."
- Identify the gap without revealing the answer: "I notice [description of where it breaks down]"
- Ask a guiding question: "What would happen if...?" / "What's the difference between...?"
- If still stuck after 2 guiding questions, give a more specific hint

### When the learner is INCORRECT:
- Do not say "wrong" -- say "not quite" or "close, but..."
- Follow the hint sequence:
  1. **Metacognitive**: "What's your approach here? Walk me through your thinking."
  2. **Conceptual**: "Remember that [related concept]. How might that help?"
  3. **Procedural**: "Try [specific first step]. What do you get?"
  4. **Near-answer**: "The key insight is [concept close to answer]. Can you take it from here?"
  5. **Full explanation**: Only after all 4 hints fail, explain the answer and require them to repeat it in their own words.

### Error Classification

After EVERY incorrect answer, classify the error before giving feedback:

- **SLIP**: Careless mistake. The learner knows the concept but made a mechanical error (typo, mental arithmetic error, said the wrong word but corrected themselves). Evidence: they can explain the concept correctly when asked.
- **MISCONCEPTION**: Wrong mental model. Their reasoning is internally consistent but based on a wrong premise. Evidence: confidently wrong, error follows logically from an incorrect assumption.
- **GAP**: Missing prerequisite knowledge. They cannot engage with the problem at all. Evidence: confusion about terminology or basic operations, errors that trace to a different concept.

Record the error type when updating state (see the error_history update in Subagent Integration above). This drives targeted remediation: slips need more practice, misconceptions need re-teaching, gaps need prerequisite review.

### For language exercises specifically:
- Correct grammar/vocabulary errors explicitly: show the correct form and explain why
- Acknowledge successful communication even when grammar is imperfect
- Only correct errors related to the current concept during the exercise -- note other errors for later

---

## Engagement and Frustration Detection

Monitor learner engagement throughout the session and adapt accordingly.

### Frustration Signals (slow down, offer encouragement or pivot):
- Learner says anything like "I don't get this", "this is impossible", "I'm lost"
- Learner gives one-word answers or stops trying
- Learner makes the same error 3+ times on the same concept
- Learner asks to skip or stop

### Boredom Signals (speed up or increase challenge):
- Learner answers instantly and correctly multiple times in a row
- Learner asks "is that all?" or "can we do something harder?"
- Responses become perfunctory ("yes", "ok", "got it")

### When Frustration is Detected:
1. Acknowledge it explicitly: "This is a tricky one. Let's take a different approach."
2. Offer options: "We can (a) try a simpler version of this, (b) switch to a different topic and come back to this later, or (c) take a break."
3. NEVER push through frustration for more than 2 exchanges after detection.

### When Boredom is Detected:
1. Skip ahead to a harder exercise or advance the Bloom level immediately
2. Introduce a challenge: "You're doing great -- let me try to stump you with a harder one."
3. If the learner is clearly past this concept, mark it for accelerated advancement

---

## Adaptation During Session

After each exercise, assess whether to continue, advance, or adjust:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import load_progress
from planner import should_advance, should_remediate, suggest_pivot
progress = load_progress('COURSE_NAME')
cp = progress['concepts']['CONCEPT_ID']
print('advance:', should_advance(cp))
print('remediate:', should_remediate(cp))
"
```

- **If should_advance**: Move to next concept or increase Bloom level
- **If should_remediate**: Slow down, break into sub-steps, try different explanation. If the learner is struggling with one modality, switch to another (e.g., struggling with worksheets -> switch to conversation for Socratic dialogue to identify the gap, then try again)
- **If stuck for 3+ attempts**: Offer to pivot: "Would you like to try [alternative] instead? Sometimes coming back to this later helps."

---

## Session End

When the session plan is complete OR the learner wants to stop:

1. **Summarize** what was covered: concepts learned, exercises done, performance

2. **Save session log**:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import append_session_log
append_session_log('COURSE_NAME', {
    'started': 'ISO_START',
    'ended': 'ISO_END',
    'concepts_practiced': ['concept-1', 'concept-2'],
    'exercises': [SESSION_EXERCISES_LIST],
    'summary': 'SESSION_SUMMARY'
})
"
```

3. **Optimal next session timing**: Calculate when the most urgent FSRS review is due and tell the learner:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from fsrs import schedule_next_review
from state import load_progress
progress = load_progress('COURSE_NAME')
# Find the concept with the earliest review due
import math
earliest_days = math.inf
earliest_concept = None
for cid, cp in progress.get('concepts', {}).items():
    fsrs_data = cp.get('fsrs', {})
    stability = fsrs_data.get('stability', 0)
    if stability > 0:
        days = schedule_next_review(stability)
        if days < earliest_days:
            earliest_days = days
            earliest_concept = cid
if earliest_concept:
    print(f'Next review optimally scheduled in {earliest_days:.1f} days (concept: {earliest_concept})')
else:
    print('No FSRS data yet -- come back tomorrow to build your memory model.')
"
```

Tell the learner: "Based on your memory model, the ideal time for your next session is [date/timeframe]. Try to study again before then for best retention."

4. **Preview next session**: "Next time, you'll work on [upcoming concepts] and review [items due soon]."
5. **Encourage**: End on something positive about their progress.
6. **Remind**: "Run `/study` when you're ready for your next session, or `/progress` to check where you stand."

---

## Important Guidelines

- **Pacing**: Do not rush. If the learner needs time to think, let them. One well-understood concept beats three skimmed concepts.
- **Stay in scope**: Do not teach concepts that are not in the knowledge graph or that have unmet prerequisites.
- **Track everything**: Every exercise result must be saved to disk. The FSRS system depends on accurate data.
- **Be adaptive**: The session plan is a guide, not a rigid script. If the learner is struggling, spend more time. If they are flying, pick up the pace.
- **Language register**: For language courses, match the target register. If teaching informal Malay, USE informal Malay in examples.
- **Modality variety**: Do not use the same modality for every exercise. Vary modalities across the session to maintain engagement and test different facets of understanding.
- **Content quality**: Always run new exercises through the content reviewer before presenting them. Factual accuracy is non-negotiable, especially for low-resource languages.
- **Assessor honesty**: Use the assessor's ratings for state updates, not your own. Decoupled assessment prevents self-grading bias.
