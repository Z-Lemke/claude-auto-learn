# Teaching Agent Methodology Review

**Date**: 2026-02-22
**Reviewer**: Methodology Review Agent (fresh eyes, no implementation context)
**Scope**: All SKILL.md files, Python scripts (fsrs.py, planner.py, state.py), research docs, ADR

---

## Executive Summary

The teaching agent has a solid architectural foundation: the hybrid LLM + classical algorithm approach is the right call, FSRS is well-implemented, state management is clean and atomic, and the SKILL.md instructions are thorough. However, there are significant methodology gaps that will degrade learning outcomes in practice. The most critical issues are: (1) mastery_score is never computed by any algorithm -- it is a phantom field that the LLM must set ad hoc, (2) the system has no mechanism for distinguishing misconceptions from surface errors, (3) Bloom level advancement is described in the SKILL.md but never actually triggered or persisted, and (4) the session planner ignores time commitment preferences the learner provides during intake.

Below are findings organized by the eight evaluation dimensions requested.

---

## 1. Pedagogical Soundness

### 1.1 GOOD: Hybrid architecture is well-motivated

The ADR correctly identifies that pure-LLM tutoring fails at state persistence and scheduling, while pure-classical-ITS fails at content generation. The hybrid approach (FSRS for scheduling, knowledge graph for sequencing, LLM for dialogue/content) matches the pattern recommended by the research. This mirrors the Khanmigo architecture: structured backend for *what to teach*, LLM for *how to teach it*.

### 1.2 PROBLEM: Socratic method lacks graduated response to learner resistance

**Severity: Medium**

The study SKILL.md defines a 5-step hint sequence (metacognitive -> conceptual -> procedural -> near-answer -> full explanation). This is good and matches the research literature's progressive scaffolding framework. However, it doesn't address the well-documented "just tell me" resistance pattern.

The SKILL.md says: *"When they say 'just tell me' or 'what's the answer?', respond: 'Let me give you a hint instead...'"* This is a single canned response. The LLM teaching research (section 3.3 of llm-teaching-approaches.md) specifically warns that LLMs break Socratic character under sustained pressure from students. A single-line defense is insufficient.

**Proposed fix**: Add a multi-layer resistance handling protocol to study/SKILL.md:

```markdown
### Handling "Just Tell Me" Requests

When the learner pushes for the answer directly:

1. **First request**: "I know it's tempting! Let me give you a hint that should help..." (proceed with hint sequence)
2. **Second request**: "I hear you -- this is hard. Let's break it into a smaller piece. Can you tell me just [smallest sub-step]?"
3. **Third request**: "OK, let's try a different angle. [Rephrase the problem using a different analogy or context]"
4. **Fourth request (give in gracefully)**: "Alright, let's work through this one together. [Give the answer BUT require them to explain it back]. Now, can you explain to me in your own words why that's the answer?"

NEVER just hand over the answer without the explain-back step. The explain-back preserves learning value even when Socratic scaffolding fails.
```

### 1.3 PROBLEM: No worked-example fading strategy

**Severity: Medium**

The research (llm-teaching-approaches.md section 2.2) describes worked-example fading as a proven technique: first demonstrate fully, then partially, then let the learner do it independently. The current study skill jumps directly from "present the concept" to "check understanding" to "practice exercise" with no intermediate scaffolding for genuinely new material.

For a complete beginner encountering a concept for the first time, asking them to produce something immediately after a single explanation is likely to fail, leading to unnecessary hint sequences that could have been avoided by demonstrating first.

**Proposed fix**: Add a worked-example step for new concepts (not reviews):

```markdown
### For NEW concepts:

**1. Present the concept** (existing)

**2. Demonstrate with a worked example**
- Show one complete example with your reasoning visible
- For languages: "Here's how I would use this in a sentence: [sentence]. I chose [word] because [reason]."
- For technical: "Here's how I'd solve this: [step-by-step solution with reasoning]"

**3. Guided practice**
- Present a similar problem and walk through it WITH the learner
- "Now let's try one together. What would be the first step?"

**4. Independent practice** (current "practice exercise" step)
```

### 1.4 PROBLEM: No confidence calibration

**Severity: Low-Medium**

The research identifies confidence-weighted responses as a powerful assessment signal (adaptive-learning-systems.md section 3.2). A learner who is correct but unsure has fragile knowledge. A learner who is confident but wrong has a dangerous misconception. The current system captures neither signal.

**Proposed fix**: After exercises (not every one -- perhaps every 3rd), ask the learner to rate their confidence before revealing feedback:

```markdown
### Confidence Check (use periodically, not every exercise)
After the learner answers, BEFORE giving feedback, ask:
"How confident are you in that answer? (1=guessing, 2=unsure, 3=pretty sure, 4=certain)"

Use this to weight your assessment:
- High confidence + correct = strong mastery signal (rate EASY in FSRS)
- High confidence + incorrect = MISCONCEPTION FLAG (see error taxonomy)
- Low confidence + correct = fragile knowledge (rate HARD in FSRS, review sooner)
- Low confidence + incorrect = expected at this stage (rate AGAIN, proceed normally)
```

---

## 2. Exercise Quality

### 2.1 PROBLEM: Exercise prompts are specified as a config field but never given concrete examples

**Severity: High**

The build-course SKILL.md tells the LLM to create `exercise_prompts` per Bloom level as part of the course config. But there are no examples of what good exercise prompts look like. The LLM is left to figure this out, and the quality will be highly variable.

The study SKILL.md says "Generate an exercise at the appropriate Bloom level for this concept. Use the exercise prompts from the course config." But the config's `exercise_prompts` are just template strings like `"Recall exercise for {concept}"` (from the test fixture). This is not specific enough to produce consistent, high-quality exercises.

**Proposed fix**: Add a reference section to the build-course SKILL.md (or a companion references file) with concrete exercise prompt examples per Bloom level and domain type:

```markdown
### Exercise Prompt Reference

**For Language Courses:**
- Remember: "Translate this word/phrase from [L1] to [L2]: {target_vocabulary}"
- Understand: "Read this sentence and explain what it means in English: {example_sentence_in_L2}"
- Apply: "Create a sentence using {target_vocabulary} in the context of {scenario}"
- Analyze: "Here are two sentences. One uses {grammar_point} correctly, one doesn't. Identify which is wrong and explain why: {sentence_pair}"
- Evaluate: "Read this paragraph and identify any errors in register, grammar, or vocabulary: {paragraph}"

**For Technical Courses:**
- Remember: "Define {key_term} in your own words"
- Understand: "Explain why {concept} matters. When would you use it vs {alternative}?"
- Apply: "Given this scenario: {scenario}, apply {concept} to solve it"
- Analyze: "Here's a system design: {design}. Identify the bottleneck and explain why"
- Evaluate: "Compare these two approaches to {problem}: {approach_A} vs {approach_B}. Which is better for {context} and why?"

**For Interview Prep:**
- Remember: "What are the key components of {concept}?"
- Apply: "Walk me through how you would answer this interview question: {question}"
- Evaluate: "Here's a candidate's answer to {question}: {answer}. What's good about it? What's missing?"
```

### 2.2 PROBLEM: No exercise variety tracking

**Severity: Medium**

The system generates exercises on the fly but has no mechanism to ensure variety. If the LLM generates a "translate this word" exercise three times in a row for the same concept, the learner may be pattern-matching rather than learning. Duolingo uses a multi-armed bandit to select exercise types; we need at least a lightweight version.

The session log stores exercises but the planner never reads them to avoid repetition.

**Proposed fix**: Add an `exercise_types_used` list to concept progress and pass the last 3 exercise types to the LLM when generating new exercises:

```markdown
When generating an exercise, check the concept's recent exercise history:
- Load the last 3 exercise types for this concept from the session log
- Instruct the LLM: "Generate an exercise that is NOT a [type_1], [type_2], or [type_3]. Choose a different format."
- Exercise types to cycle through: translation, fill-in-blank, sentence-creation, error-correction, explanation, matching, scenario-application, comparison
```

### 2.3 PROBLEM: No difficulty calibration feedback loop

**Severity: Medium**

The ADR and research both emphasize targeting ~80% success rate (the "85% rule" from Wilson et al., 2019). The planner has `should_advance` (>80% accuracy) and `should_remediate` (<50% accuracy) but nothing that dynamically adjusts the difficulty of generated exercises.

The LLM is told to generate exercises "at the appropriate Bloom level" but has no signal about whether its exercises are consistently too easy or too hard. If the learner gets 95% of exercises right, the exercises are too easy but nothing triggers an adjustment until the planner decides to advance the Bloom level.

**Proposed fix**: Add a running difficulty calibration signal to the concept progress:

```python
# In planner.py, add:
def get_difficulty_adjustment(concept_progress: dict) -> str:
    """Return 'easier', 'harder', or 'maintain' based on recent success rate."""
    practice = concept_progress.get("practice_count", 0)
    correct = concept_progress.get("correct_count", 0)
    if practice < 3:
        return "maintain"
    accuracy = correct / practice
    if accuracy > 0.90:
        return "harder"
    elif accuracy < 0.65:
        return "easier"
    return "maintain"
```

Pass this to the LLM in the exercise generation prompt: "The learner's recent accuracy on this concept is X%. Generate an exercise that is [easier/harder/at the same level]."

---

## 3. Assessment Accuracy

### 3.1 PROBLEM (CRITICAL): mastery_score is a phantom field -- never algorithmically computed

**Severity: Critical**

This is the most serious issue in the entire system. The `mastery_score` field exists in the progress schema (initialized to 0.0 in `state.py:init_progress`). It's used in `planner.py:is_mastered()` (threshold >= 0.85) and `planner.py:should_remediate()` (threshold < 0.4). But **no code anywhere computes or updates mastery_score**.

The `update_concept_progress()` function in state.py is a generic merge -- it writes whatever the caller passes. The SKILL.md code snippets show updating `practice_count`, `correct_count`, and `fsrs`, but never `mastery_score`. The build-course SKILL.md sets it to 0.9 for diagnosed-mastered concepts and 0.4 for learning concepts, but after that it is never updated again.

This means:
- `is_mastered()` will almost never return True (mastery_score stays at 0.0 for concepts learned through study sessions)
- Concepts that should be mastered will never get promoted to "mastered" status
- The frontier calculation depends on "mastered" status, so learners will get stuck in early concepts forever
- `should_remediate()` for the high-practice-low-mastery path will always trigger (mastery stays 0.0)

**Proposed fix**: Add a `compute_mastery_score()` function to planner.py and call it from the study/quiz SKILL.md after every exercise:

```python
def compute_mastery_score(concept_progress: dict) -> float:
    """Compute a composite mastery score from multiple signals.

    Combines:
    - Accuracy (correct_count / practice_count), weighted 0.5
    - FSRS stability (normalized), weighted 0.3
    - Bloom level progress (normalized), weighted 0.2

    Returns a score in [0, 1].
    """
    practice = concept_progress.get("practice_count", 0)
    correct = concept_progress.get("correct_count", 0)

    # Accuracy component
    accuracy = correct / practice if practice > 0 else 0.0

    # Stability component (normalized: stability of 30+ days = 1.0)
    fsrs_data = concept_progress.get("fsrs", {})
    stability = fsrs_data.get("stability", 0.0)
    stability_normalized = min(stability / 30.0, 1.0)

    # Bloom component (normalized against target)
    bloom = concept_progress.get("bloom_level", "remember")
    bloom_val = bloom_level_value(bloom)
    bloom_normalized = bloom_val / 6.0  # 6 levels total

    return 0.5 * accuracy + 0.3 * stability_normalized + 0.2 * bloom_normalized
```

Then in the study SKILL.md state update snippet:

```python
from planner import compute_mastery_score
mastery = compute_mastery_score(progress['concepts']['CONCEPT_ID'])
result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'mastery_score': mastery,
    # ... other fields
})
```

### 3.2 PROBLEM: No mechanism to distinguish misconceptions from surface errors

**Severity: High**

The research (adaptive-learning-systems.md section 3.2, llm-teaching-approaches.md section 3.4) emphasizes that systematic errors (misconceptions) and careless errors (slips) require different responses. A misconception needs re-teaching; a slip just needs more practice. BKT models this explicitly with P(G) (guess) and P(S) (slip) parameters.

The current system tracks `error_history` (a list in progress) but the SKILL.md never instructs the LLM to populate it, and nothing reads it. The `error_taxonomy` field in course config is defined but never referenced in the study or quiz skills.

**Proposed fix**:

1. In the study SKILL.md feedback section, add error classification:

```markdown
### After EVERY incorrect answer, classify the error:

Before giving feedback, determine the error type:
- **SLIP**: The learner clearly knows the concept but made a careless mistake (typo, mental arithmetic error, said the wrong word but corrected themselves). Evidence: they can explain the concept correctly when asked.
- **MISCONCEPTION**: The learner has a wrong mental model. Evidence: their reasoning is internally consistent but based on a wrong premise.
- **GAP**: The learner is missing prerequisite knowledge. Evidence: they can't engage with the problem at all, or their error relates to a different concept.

Record the error type when updating state:
```

2. Add error type tracking to the state update code:

```python
result = update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
    'error_history': existing_errors + [{'type': 'misconception', 'description': 'confused X with Y', 'timestamp': 'ISO_NOW'}],
})
```

3. Use error history in the planner to inform adaptation:

```python
def has_persistent_misconception(concept_progress: dict) -> bool:
    """Return True if the same misconception appears 2+ times."""
    errors = concept_progress.get("error_history", [])
    misconceptions = [e for e in errors if e.get("type") == "misconception"]
    # Check for repeated descriptions (fuzzy match via LLM would be better,
    # but exact match is a reasonable start)
    descriptions = [m.get("description", "") for m in misconceptions]
    return len(descriptions) != len(set(descriptions))
```

### 3.3 PROBLEM: LLM assessment has no structured rubric enforcement

**Severity: Medium**

The quiz SKILL.md says "Evaluate -- be fair but honest" and "Be honest in grading -- a generous quiz defeats its purpose." But it provides no structured rubric for the LLM to follow when grading. The research (llm-teaching-approaches.md section 3.4) documents that LLMs are inconsistent graders without explicit rubrics.

The course config has an `assessment_rubric` field, but the quiz skill never tells the LLM to load or use it.

**Proposed fix**: Add explicit rubric usage to the quiz SKILL.md:

```markdown
### Evaluation Rubric

Load the course config's `assessment_rubric` and apply it to every answer. For each response, evaluate on these dimensions:

1. **Correctness** (binary): Is the core answer right or wrong?
2. **Completeness** (0-2): 0=major gaps, 1=partial, 2=complete
3. **Depth** (for Bloom levels >= Apply): Does the answer show understanding beyond surface recall?

Map to FSRS rating:
- Correct + Complete + Deep = EASY (4)
- Correct + Complete = GOOD (3)
- Correct but incomplete OR partially correct = HARD (2)
- Incorrect or fundamentally wrong = AGAIN (1)

DO NOT give GOOD or EASY for answers that are correct but show no understanding. If the learner got lucky or guessed, rate HARD.
```

---

## 4. Adaptation Quality

### 4.1 PROBLEM: Bloom level advancement is described but never mechanically triggered

**Severity: High**

The study SKILL.md says: "If should_advance: Move to next concept or increase Bloom level." The `should_advance()` function in planner.py returns True when accuracy > 80% and practice >= 3. But increasing the Bloom level requires:

1. Updating `bloom_level` in the concept's progress
2. Using `next_bloom_level()` from planner.py to determine the new level
3. Generating exercises at the new Bloom level

None of these steps are shown in the SKILL.md code snippets. The study SKILL.md's state update code only updates `status`, `practice_count`, `correct_count`, `last_practiced`, and `fsrs`. It never updates `bloom_level`.

This means concepts will stay at "remember" bloom level forever, even if the learner has mastered recall and is ready for application-level exercises.

**Proposed fix**: Add explicit Bloom level advancement logic to the study SKILL.md's adaptation section:

```markdown
### Bloom Level Advancement

After checking should_advance:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from planner import should_advance, next_bloom_level, is_mastered
from state import load_progress, update_concept_progress

progress = load_progress('COURSE_NAME')
cp = progress['concepts']['CONCEPT_ID']

if should_advance(cp):
    current_bloom = cp.get('bloom_level', 'remember')
    new_bloom = next_bloom_level(current_bloom)
    if new_bloom:
        update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
            'bloom_level': new_bloom,
        })
        print(f'Advanced from {current_bloom} to {new_bloom}')
    else:
        # Already at highest bloom level -- check for mastery
        kg_concept = KG['concepts']['CONCEPT_ID']
        bloom_target = kg_concept.get('bloom_target', 'apply')
        if is_mastered(cp, bloom_target=bloom_target):
            update_concept_progress('COURSE_NAME', 'CONCEPT_ID', {
                'status': 'mastered',
            })
            print('Concept mastered!')
"
```
```

### 4.2 PROBLEM: Session planner ignores learner's stated time preferences

**Severity: Medium**

The build-course SKILL.md asks the learner "How many minutes per session?" and stores this in `session_preferences.default_duration_minutes` in the course config. But `plan_session()` in planner.py has `duration_minutes=25` as a hardcoded default. The study SKILL.md calls `plan_session(kg, progress)` without passing the config's duration.

**Proposed fix**: The study SKILL.md should pass the duration from config:

```python
config_duration = config.get('session_preferences', {}).get('default_duration_minutes', 25)
plan = plan_session(kg, progress, duration_minutes=config_duration)
```

### 4.3 PROBLEM: The planner uses overall accuracy as a proxy for recent accuracy

**Severity: Medium**

`should_advance()` in planner.py has a comment acknowledging this limitation:

```python
# Approximate recent accuracy: use overall ratio
# (exact per-interaction tracking would need an array;
#  the state schema stores totals, so we use them.)
accuracy = correct / practice
```

This is problematic because a learner who got 0/5 wrong initially but then got 10/10 right has an overall accuracy of 10/15 = 67%, which won't trigger advancement. But they've clearly learned the material. Conversely, a learner who got 10/10 right initially but is now struggling at 0/5 has 10/15 = 67%, which also won't advance -- correct for the wrong reason.

**Proposed fix**: Add a `recent_results` list (last 5-10 results) to the concept progress schema:

```python
# In state.py init_progress, add to each concept:
"recent_results": [],  # list of booleans, most recent last, max 10

# In planner.py should_advance:
def should_advance(concept_progress: dict) -> bool:
    recent = concept_progress.get("recent_results", [])
    if len(recent) < 3:
        return False
    # Use last 5 results (or all if fewer than 5)
    window = recent[-5:]
    accuracy = sum(window) / len(window)
    return accuracy > 0.80
```

Update the SKILL.md state snippets to append to recent_results on each exercise.

### 4.4 MINOR: Review ratio is hardcoded at 60/40 new/review

The planner uses `new_ratio=0.6` as default. The research suggests ~70% new / 30% review for optimal interleaving (adaptive-learning-systems.md section 4.3). But more importantly, the ratio should shift based on how many items are due for review. If a learner has 15 items due for review and only 2 frontier concepts, forcing 60% new material doesn't make sense.

**Proposed fix**: Make the ratio adaptive in `plan_session()`:

```python
# Dynamic ratio based on review backlog
if len(review_candidates) > total_slots * 0.7:
    # Heavy review backlog -- prioritize review
    new_ratio = 0.3
elif not review_candidates:
    new_ratio = 1.0
elif not frontier:
    new_ratio = 0.0
# else use default
```

---

## 5. Knowledge Graph Quality

### 5.1 PROBLEM: No validation of LLM-generated knowledge graphs beyond DAG checks

**Severity: High**

`validate_graph()` in planner.py checks for cycles, missing references, and orphans. These are necessary structural validations but insufficient for pedagogical quality. An LLM could generate a structurally valid graph that has:

- Prerequisites that are too strict (requiring mastery of tangential concepts)
- Prerequisites that are too loose (allowing learners to attempt advanced concepts without real foundations)
- Concepts at the wrong granularity (some too broad, some too narrow)
- Missing key concepts that are standard in the domain
- Bloom level targets that don't match the concept type (e.g., "remember" for a skill that requires practice)

The build-course SKILL.md says "Validate your own DAG -- mentally check that no concept requires something that comes after it." This is a manual check by the LLM, which is unreliable.

**Proposed fix**: Add pedagogical validation to the graph validation or as a separate function:

```python
def validate_graph_pedagogy(knowledge_graph: dict) -> List[str]:
    """Check pedagogical properties of the knowledge graph."""
    warnings = []
    concepts = knowledge_graph.get("concepts", {})

    # Check for concepts with too many prerequisites (likely over-constrained)
    for cid, info in concepts.items():
        prereqs = info.get("prerequisites", [])
        if len(prereqs) > 5:
            warnings.append(
                f"Concept '{cid}' has {len(prereqs)} prerequisites -- "
                "consider if all are truly necessary"
            )

    # Check for very long prerequisite chains (learner will take forever to reach deep concepts)
    max_depth = _get_max_depth(concepts)
    if max_depth > 10:
        warnings.append(
            f"Deepest prerequisite chain is {max_depth} levels -- "
            "consider if intermediate concepts can be parallelized"
        )

    # Check bloom_target vs concept type heuristics
    for cid, info in concepts.items():
        bloom = info.get("bloom_target", "apply")
        difficulty = info.get("difficulty", 0.5)
        if bloom == "remember" and difficulty > 0.7:
            warnings.append(
                f"Concept '{cid}' is high difficulty but targets 'remember' -- "
                "should this target 'apply' or 'analyze'?"
            )

    return warnings
```

Also: have the build-course skill present validation warnings to the learner before finalizing and allow adjustment.

### 5.2 PROBLEM: Cold-start: no mechanism to refine the knowledge graph after initial creation

**Severity: Medium**

Once a course is built, the knowledge graph is static. If the diagnostic assessment reveals that prerequisites are wrong (learner masters concept C without having mastered stated prerequisite B), there's no mechanism to update the graph. The learner is stuck with whatever the LLM generated initially.

**Proposed fix**: Add a `/edit-course` command or add graph refinement suggestions to the progress dashboard:

```markdown
### Knowledge Graph Refinement (in /progress skill)
If the data suggests graph problems, note them:
- "You mastered [concept] without its prerequisite [prereq]. The prerequisite link may be unnecessary."
- "You've been stuck on [concept] for 5+ sessions. It may have a missing prerequisite."

Offer: "Would you like me to adjust the course structure based on your learning patterns?"
```

---

## 6. Domain Generalization

### 6.1 PROBLEM: Language-specific instructions are mixed into generic skills

**Severity: Medium**

The study SKILL.md has language-specific instructions scattered throughout:
- "For languages: introduce vocabulary in sentences, show the pattern before stating the rule"
- "For languages: ask them to produce something using what was just taught"
- "For language exercises specifically: Correct grammar/vocabulary errors explicitly"
- "For language courses, match the target register"

Similarly, technical-specific and interview-specific instructions appear. This makes the skill files long and cluttered. More importantly, if a new domain type is added (e.g., "music theory"), the generic skill files would need modification.

**Proposed fix**: Move domain-specific instructions into reference files that the LLM loads based on `domain_type`:

```
skills/study/references/
  language-teaching.md    # Language-specific pedagogy
  technical-teaching.md   # Technical-specific pedagogy
  interview-teaching.md   # Interview-prep-specific pedagogy
```

The study SKILL.md would say:
```markdown
Load the domain-specific teaching reference for this course's domain_type from:
${CLAUDE_PLUGIN_ROOT}/skills/study/references/{domain_type}-teaching.md
```

This makes adding new domains a matter of adding a new reference file rather than editing the core skill.

### 6.2 PROBLEM: Interview prep domain is under-specified

**Severity: Low-Medium**

The build-course SKILL.md mentions interview prep as a first-class domain but the guidance is thin compared to language learning and technical subjects. Interview prep has unique requirements:
- Meta-skills (structuring answers, thinking aloud, asking clarifying questions) are as important as content knowledge
- Time pressure is a key variable
- The learner needs to practice *performing* under simulated conditions, not just understanding concepts
- Mock interview sessions would be a distinct modality from concept-by-concept study

**Proposed fix**: Add interview-prep-specific guidance to the build-course SKILL.md and create a reference file with interview-specific exercise templates, rubrics, and session structures. Consider whether a `/mock-interview` command that runs a full simulated interview would be appropriate as a future addition.

---

## 7. Learner Experience

### 7.1 PROBLEM: No engagement or frustration detection

**Severity: Medium-High**

The research (adaptive-learning-systems.md sections 4.1-4.2) identifies multiple engagement and frustration signals. The current system has no mechanism to detect:
- Learner is giving very short answers (disengagement)
- Learner's response time is increasing (struggle or boredom)
- Learner explicitly expresses frustration
- Learner asks to stop multiple times

The study SKILL.md mentions offering to pivot after "3+ attempts" on one concept, but this is a crude heuristic. There's no per-session engagement tracking.

**Proposed fix**: Add engagement monitoring instructions to the study SKILL.md:

```markdown
### Monitor Engagement Throughout the Session

Watch for these signals and adapt:

**Frustration signals** (slow down, offer encouragement or pivot):
- Learner says anything like "I don't get this", "this is impossible", "I'm lost"
- Learner gives one-word answers or stops trying
- Learner makes the same error 3+ times on the same concept
- Learner asks to skip or stop

**Boredom signals** (speed up or increase challenge):
- Learner answers instantly and correctly multiple times in a row
- Learner asks "is that all?" or "can we do something harder?"
- Responses become perfunctory ("yes", "ok", "got it")

**When frustration is detected**:
1. Acknowledge it explicitly: "This is a tricky one. Let's take a different approach."
2. Offer options: "We can (a) try a simpler version, (b) switch to a different topic, or (c) take a break and come back to this."
3. NEVER push through frustration for more than 2 exchanges after detection.

**When boredom is detected**:
1. Skip to a harder exercise or advance the Bloom level
2. Introduce a challenge: "You're doing great -- let me try to stump you with a harder one."
```

### 7.2 PROBLEM: Session end is abrupt -- no spaced repetition preview

**Severity: Low**

The study SKILL.md says to "Preview next session: Next time, you'll work on [upcoming concepts] and review [items due soon]." This is good, but it doesn't tell the learner *when* to come back. Since FSRS calculates optimal review intervals, the system should tell the learner: "Your next review is optimally scheduled for [date]. Try to study again by then."

**Proposed fix**: Add to session end:

```markdown
4. **Optimal next session timing**: Calculate when the first FSRS review is due and tell the learner:
   "Based on your memory model, the ideal time for your next session is [date/timeframe].
   Try to study again before then for best retention."
```

Use `schedule_next_review()` from fsrs.py on the most urgent concept to determine this.

### 7.3 MINOR: No session warm-up or cool-down

Production learning systems (Duolingo, Khan Academy) use warm-up exercises (easy review items) at the start of sessions to build confidence and activate prior knowledge, and cool-down (summary + easy win) at the end to leave the learner feeling good.

The current planner interleaves new and review items but doesn't front-load easy reviews or ensure the session ends positively.

**Proposed fix**: Modify `plan_session()` to start with 1-2 easy review items and end with a concept the learner is strong on:

```python
# In plan_session(), after building the interleaved plan:
# Move one easy review to the front (warm-up)
if review_items:
    plan.insert(0, review_items[0])
# Ensure last item is something the learner is strong on
```

---

## 8. State Management

### 8.1 GOOD: Atomic writes prevent corruption

`save_json()` in state.py uses write-to-temp-then-rename, which is the correct approach for preventing corruption on crash. This is well-implemented.

### 8.2 GOOD: FSRS implementation is faithful to the paper

The FSRS implementation matches the published formulas. The default weights match the population-level priors. The retrievability, stability, and difficulty calculations are correct. The test suite covers edge cases well.

### 8.3 PROBLEM: `init_progress` returns a Path, but the SKILL.md code treats it as returning a dict

**Severity: High (will cause runtime errors)**

In state.py:

```python
def init_progress(course_name: str, knowledge_graph: dict) -> Path:
    """Create initial progress.json with all concepts set to "not_started".
    Returns the path to progress.json.
    """
```

But the build-course SKILL.md Step 6 code does:

```python
progress = init_progress('COURSE_NAME', KNOWLEDGE_GRAPH_DICT)
# Mark diagnosed concepts
concepts = progress['concepts']  # <-- This will fail! progress is a Path, not a dict
```

This will crash at runtime when the LLM executes the code.

**Proposed fix**: Either:
(a) Change `init_progress()` to return the progress dict (since the caller immediately needs to modify it), or
(b) Fix the SKILL.md code to load the progress after initialization:

```python
init_progress('COURSE_NAME', KNOWLEDGE_GRAPH_DICT)
progress = load_progress('COURSE_NAME')
concepts = progress['concepts']
# ... modify ...
save_progress('COURSE_NAME', progress)
```

Option (b) is cleaner because it separates initialization from mutation.

### 8.4 PROBLEM: `active_courses` in profile is never updated

**Severity: Medium**

The profile has an `active_courses` list, and the study SKILL.md loads it to show available courses. But neither `build-course` nor any other skill ever adds a course to `active_courses`. This means the list is always empty, and the study skill will always need to fall through to `list_courses()`.

**Proposed fix**: In the build-course SKILL.md, after initializing the course, add it to the profile:

```python
profile = load_profile()
if course_name not in profile.get('active_courses', []):
    profile.setdefault('active_courses', []).append(course_name)
    save_profile(profile)
```

### 8.5 PROBLEM: Session stats (total_sessions, total_practice_time_minutes) are never updated

**Severity: Low**

The progress schema has `stats.total_sessions` and `stats.total_practice_time_minutes`, both initialized to 0. The `update_stats()` function in state.py only recalculates mastered/learning/not_started counts. Session counts are never incremented.

**Proposed fix**: Either increment these counters in the session-end code in the SKILL.md, or add an `increment_session_stats()` helper to state.py that the SKILL.md calls at session end.

### 8.6 MINOR: No data migration strategy

The state schema will inevitably change as the system evolves (e.g., adding `recent_results`, adding error classification). There's no version field in progress.json and no migration mechanism.

**Proposed fix**: Add a `schema_version` field to progress.json. When loading progress, check the version and apply migrations if needed:

```python
CURRENT_SCHEMA_VERSION = 1

def load_progress(course_name: str) -> Optional[dict]:
    progress = load_json(get_progress_dir(course_name) / "progress.json")
    if progress and progress.get("schema_version", 0) < CURRENT_SCHEMA_VERSION:
        progress = migrate_progress(progress)
        save_progress(course_name, progress)
    return progress
```

---

## Summary of Findings by Priority

### Critical (will cause incorrect behavior or runtime failures)

| # | Issue | Location | Section |
|---|-------|----------|---------|
| 1 | `mastery_score` is never computed -- phantom field breaks mastery detection and frontier progression | planner.py, study/SKILL.md | 3.1 |
| 2 | `init_progress` returns Path but SKILL.md treats it as dict -- will crash at runtime | state.py, build-course/SKILL.md | 8.3 |
| 3 | Bloom level advancement is described but never triggered -- concepts stay at "remember" forever | study/SKILL.md | 4.1 |

### High (significant impact on learning outcomes)

| # | Issue | Location | Section |
|---|-------|----------|---------|
| 4 | Exercise prompts have no concrete examples -- LLM will generate inconsistent quality | build-course/SKILL.md | 2.1 |
| 5 | No misconception vs. surface error distinction -- wrong remediation for wrong problems | study/SKILL.md, planner.py | 3.2 |
| 6 | Knowledge graph has no pedagogical validation beyond structural checks | planner.py, build-course/SKILL.md | 5.1 |
| 7 | No engagement/frustration detection -- learner may disengage without system adapting | study/SKILL.md | 7.1 |

### Medium (noticeable quality degradation)

| # | Issue | Location | Section |
|---|-------|----------|---------|
| 8 | Socratic resistance handling is a single canned response | study/SKILL.md | 1.2 |
| 9 | No worked-example fading for new concepts | study/SKILL.md | 1.3 |
| 10 | No exercise variety tracking | study/SKILL.md, state.py | 2.2 |
| 11 | No difficulty calibration feedback loop | planner.py, study/SKILL.md | 2.3 |
| 12 | Assessment has no structured rubric enforcement | quiz/SKILL.md | 3.3 |
| 13 | Planner uses overall accuracy instead of recent accuracy | planner.py | 4.3 |
| 14 | Session planner ignores learner's stated time preferences | planner.py, study/SKILL.md | 4.2 |
| 15 | No mechanism to refine knowledge graph after creation | build-course/SKILL.md, progress/SKILL.md | 5.2 |
| 16 | Language-specific instructions mixed into generic skills | study/SKILL.md | 6.1 |
| 17 | `active_courses` in profile never updated | build-course/SKILL.md, state.py | 8.4 |

### Low (polish and optimization)

| # | Issue | Location | Section |
|---|-------|----------|---------|
| 18 | No confidence calibration | study/SKILL.md | 1.4 |
| 19 | Interview prep domain is under-specified | build-course/SKILL.md | 6.2 |
| 20 | No spaced repetition timing preview at session end | study/SKILL.md | 7.2 |
| 21 | No session warm-up/cool-down | planner.py | 7.3 |
| 22 | Session stats never updated | state.py, study/SKILL.md | 8.5 |
| 23 | No data migration strategy | state.py | 8.6 |
| 24 | Review ratio is hardcoded, not adaptive to backlog | planner.py | 4.4 |

---

## What's Working Well

To be clear, the foundation is strong:

1. **FSRS implementation** is correct and well-tested (test_fsrs.py has 26 tests covering all edge cases)
2. **State management** is clean -- atomic writes, clear directory structure, separation of course data from progress data
3. **Knowledge graph traversal** (frontier detection, prerequisite chains, pivot suggestions) is correct and well-tested
4. **The SKILL.md approach** is clever -- encoding teaching methodology as LLM instructions rather than code means it can be iterated on without code changes
5. **User-level state** (in ~/.claude/teaching/) is the right decision -- learning is about the person, not the project
6. **The hint sequence** is well-structured and matches the progressive scaffolding literature
7. **Session logging** provides good data for future analysis and personalization
8. **The Stop hook** for session tracking is lightweight and non-blocking, which is the right pattern

The critical fixes (mastery_score computation, init_progress return type, Bloom advancement) are implementation gaps that can be fixed with relatively small code changes. The methodology improvements are larger but can be phased in.
