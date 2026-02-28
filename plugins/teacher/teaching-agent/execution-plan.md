# Execution Plan: Teaching Agent Plugin

**Date**: 2026-02-20
**ADR**: See `ADR.md` in this directory

---

## Task Overview

Build the `teacher` plugin in the llm-toolkit marketplace with these capabilities:
1. Course construction from a topic description
2. Adaptive study sessions
3. Assessment/quizzing
4. Progress tracking with FSRS scheduling

## Phase 1: Foundation (Plugin Structure + Engine Scripts)

### Task 1: Plugin Scaffold
**Context**: Create the plugin directory structure following the repo's conventions (matching auto-learn and safety-judge patterns).

**Implementation**:
- Create `plugins/teacher/.claude-plugin/plugin.json`
- Create directory structure: `skills/`, `commands/`, `hooks/`, `tests/`, `scripts/`
- Register in `.claude-plugin/marketplace.json`

**Requirements**: Follows exact conventions from existing plugins.

**Definition of Done**: Plugin structure passes the same structural tests as auto-learn (test_plugin_structure.py pattern).

**Validation**: `pytest plugins/teacher/tests/test_plugin_structure.py` passes.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 2: State Schema + Persistence Layer
**Context**: Define the JSON schemas for all persistent state and write Python helper scripts for reading/writing state atomically.

**Implementation**:
Create `plugins/teacher/scripts/state.py` with:
- **Course schema** (`~/.claude/teaching/courses/<name>/`):
  - `knowledge-graph.json` — nodes (concepts) with id, name, prerequisites, bloom_target, difficulty, metadata; edges are prerequisite relationships
  - `curriculum.json` — ordered learning path, unit groupings, session plans
  - `config.json` — domain-specific settings (exercise prompts, rubrics, error taxonomy, session preferences)
- **Learner schema** (`~/.claude/teaching/learner/`):
  - `profile.json` — name, learning preferences, goals, global FSRS parameters
  - `<course>/progress.json` — per-concept state: fsrs_state (difficulty, stability, retrievability, last_review), mastery_score, bloom_level, error_history, practice_count
  - `<course>/sessions/<timestamp>.json` — session log: concepts practiced, exercises attempted/correct, time spent, notes

Functions:
- `load_state(path)` — read JSON with error handling
- `save_state(path, data)` — atomic write (tmp + rename)
- `init_course(name)` — create directory structure with empty defaults
- `init_learner()` — create learner directory with default profile

**Requirements**: Atomic writes, Python 3.8+ compatible, no external dependencies.

**Definition of Done**: Schema files documented, helper functions working, test coverage for read/write/init.

**Validation**: `pytest plugins/teacher/tests/test_state.py` passes.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 3: FSRS Scheduling Engine
**Context**: Implement the core FSRS algorithm for scheduling when concepts should be reviewed. This is the memory model that prevents forgetting.

**Implementation**:
Create `plugins/teacher/scripts/fsrs.py`:
- DSR model: Difficulty, Stability, Retrievability
- `calculate_retrievability(stability, days_elapsed)` — R = (1 + t/(9*S))^(-1)
- `update_after_review(fsrs_state, rating)` — update D, S based on review outcome
  - rating: 1 (again), 2 (hard), 3 (good), 4 (easy)
  - Stability increase on success, decrease on failure
  - Difficulty adjustment
- `schedule_next_review(fsrs_state, desired_retention=0.9)` — days until next review
- `get_due_items(progress_data)` — return concepts where R < desired_retention
- Use population default weights (from FSRS research) as starting parameters

**Requirements**: Pure Python, no external deps, matches FSRS v4/v5 formulas from research.

**Definition of Done**: All FSRS calculations correct, tested against known examples.

**Validation**: `pytest plugins/teacher/tests/test_fsrs.py` with cases covering:
- New item scheduling
- Successful review → stability increase
- Failed review → stability decrease
- Retrievability decay over time
- Due items calculation

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 4: Knowledge Graph + Session Planner
**Context**: Scripts that manage the knowledge graph (prerequisite traversal, frontier identification) and plan what to teach in a session.

**Implementation**:
Create `plugins/teacher/scripts/planner.py`:
- `get_frontier(knowledge_graph, progress)` — concepts where all prerequisites are mastered but concept itself isn't. This is the ZPD.
- `get_review_items(progress, n=3)` — items due for FSRS review, prioritized by lowest retrievability
- `plan_session(knowledge_graph, progress, duration_minutes=25)` — returns a session plan:
  - Mix of new material (~60%) and review (~40%)
  - New items selected from frontier
  - Review items selected by FSRS schedule
  - Interleaving pattern: 3 new, 1 review, 3 new, 1 review, 2 assessment
- `is_mastered(concept_progress)` — mastery score > 0.85 AND bloom_level >= target
- `should_advance(concept_progress)` — recent accuracy > 0.85, 3+ practices
- `should_remediate(concept_progress)` — recent accuracy < 0.5 OR declining trend
- `suggest_pivot(knowledge_graph, progress, current_concept)` — when struggling, suggest alternative frontier concepts

**Requirements**: Pure Python, operates on the JSON state from Task 2.

**Definition of Done**: All planner functions working with test coverage.

**Validation**: `pytest plugins/teacher/tests/test_planner.py` with cases covering:
- Frontier selection respects prerequisites
- Review items sorted by urgency
- Session plan has correct mix
- Mastery/advance/remediate thresholds
- Pivot suggestions when stuck

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

## Phase 2: Skills + Commands (Teaching Logic)

### Task 5: Build Course Skill + Command
**Context**: The `/build-course` command that takes a topic description and generates a full course structure. This is the most complex skill — it needs to research the domain, generate a knowledge graph, create exercise templates, and set up the course state.

**Implementation**:
Create `plugins/teacher/skills/build-course/SKILL.md`:
- **Step 1: Intake** — Understand what the user wants to learn
  - What topic/subject?
  - What's their current level? (self-report + probing questions)
  - What's their goal? (conversational fluency, pass interview, understand concepts)
  - How much time per session? Per week?
  - Any specific areas of focus?
- **Step 2: Research** — If web tools available, research current teaching methodologies for this topic. Otherwise, use training knowledge.
- **Step 3: Generate Knowledge Graph** — Create a DAG of concepts with:
  - Clear prerequisite relationships
  - Bloom level targets per concept
  - Difficulty estimates
  - Grouped into logical units
  - Domain-specific metadata (for languages: vocab lists, grammar rules; for technical: concepts, patterns)
- **Step 4: Generate Course Config** — Exercise generation prompts, assessment rubrics, error taxonomy, session preferences
- **Step 5: Diagnostic Assessment** — Quick placement test to validate self-reported level
  - 5-10 targeted questions probing claimed knowledge
  - Adjust starting point based on results
- **Step 6: Initialize State** — Write knowledge graph, curriculum, config, and initial progress to disk
- **Step 7: Summary** — Show the user their course plan, starting point, and how to begin studying

Create `plugins/teacher/commands/build-course.md`:
- Slash command entry point
- `allowed-tools`: Read, Write, Edit, Glob, Grep, Bash(python3:*), Bash(mkdir:*), WebSearch, WebFetch

**Requirements**: Must work without web tools (fallback to training knowledge). Must produce valid JSON state files.

**Definition of Done**: User can run `/build-course`, describe a topic, complete intake, and get a course with valid knowledge graph and initial progress.

**Validation**: Manual QA — build courses for all three use cases (Malay, systems design, interview prep) and verify:
- Knowledge graph has reasonable concept count (20-100 concepts)
- Prerequisites form a valid DAG (no cycles)
- Bloom targets are assigned
- Config has exercise prompts
- Progress file initialized correctly

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 6: Study Session Skill + Command
**Context**: The `/study` command that runs an adaptive tutoring session. This is the core teaching experience.

**Implementation**:
Create `plugins/teacher/skills/study/SKILL.md`:
- **On start**: Load course state and learner progress. Run planner to get session plan.
- **Teaching loop** (per concept in session plan):
  1. **Present**: Explain the concept (adapted to learner level). For review items, briefly recap.
  2. **Practice**: Generate an exercise targeting the concept at the right Bloom level
  3. **Assess**: Evaluate the learner's response
     - For objective items: check correctness
     - For open-ended: evaluate understanding depth using rubric
  4. **Feedback**:
     - Correct: acknowledge, reinforce, move on
     - Partially correct: identify the gap, ask probing questions (Socratic)
     - Incorrect: scaffold hints (progressive: metacognitive → conceptual → procedural → worked example)
  5. **Update state**: Call Python scripts to update FSRS schedule and mastery scores
  6. **Adapt**: Check if should advance, continue, remediate, or pivot
- **Socratic method enforcement** (CRITICAL):
  - Never give answers directly unless learner has exhausted hint sequence
  - Multi-layer anti-answer instructions
  - Response format constraints that force questions before answers
  - Explicit instructions for handling "just tell me the answer" requests
- **Interleaving**: Mix new concepts with review of recently learned material
- **Session end**: Summarize what was learned, update progress, show what's coming next

Create `plugins/teacher/commands/study.md`:
- Slash command entry point
- `allowed-tools`: Read, Write, Edit, Bash(python3:*), Glob, Grep

**Requirements**: Must load state from disk, update state after each concept, handle learner struggling gracefully.

**Definition of Done**: User can run `/study`, get a teaching session with exercises, feedback adapts to their performance, state persists.

**Validation**: Manual QA — run study sessions for each course type and verify:
- Session plan follows planner output
- Exercises match concept and Bloom level
- Feedback is Socratic (doesn't give away answers)
- State updates correctly after each exercise
- Session adapts when learner struggles

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 7: Quiz/Assessment Skill + Command
**Context**: The `/quiz` command for testing understanding without teaching. Pure assessment mode.

**Implementation**:
Create `plugins/teacher/skills/quiz/SKILL.md`:
- **On start**: Load progress. Determine what to quiz:
  - Option A: Quiz on specific unit (user-selected)
  - Option B: Comprehensive quiz on all active concepts
  - Option C: Review quiz on items due for FSRS review
- **Quiz loop**:
  1. Generate question at target Bloom level for concept
  2. Present question (no hints, no teaching)
  3. Collect answer
  4. Evaluate (structured + LLM rubric-based)
  5. Brief feedback (correct/incorrect + short explanation)
  6. Update FSRS state and mastery
- **Results**: Score summary, per-concept breakdown, identify weak areas, suggest what to study next

Create `plugins/teacher/commands/quiz.md`

**Requirements**: No teaching during quiz. Clean assessment only. State updates from results.

**Definition of Done**: User can run `/quiz`, get assessed, see results, state reflects performance.

**Validation**: Manual QA — quiz on each course type, verify scoring and state updates.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 8: Progress Tracking Skill + Command
**Context**: The `/progress` command that shows the learner where they stand and helps them decide what to do next.

**Implementation**:
Create `plugins/teacher/skills/progress/SKILL.md`:
- **Overall progress**: % of knowledge graph mastered, current unit, time invested
- **Per-concept status**: mastered / learning / not started / due for review
- **Strength areas**: concepts with high mastery
- **Weak areas**: concepts with low mastery or declining
- **Due for review**: items that FSRS says need review (sorted by urgency)
- **Recommendations**: "You should study X next" / "Quiz on unit Y" / "Review these 5 items"
- **Session history**: recent sessions with summaries
- **Visual** (text-based): simple progress bars, tables, or ASCII charts

Create `plugins/teacher/commands/progress.md`

**Requirements**: Read-only (no state changes). Fast — just reads and displays.

**Definition of Done**: User can run `/progress` and see meaningful progress data.

**Validation**: Manual QA — verify progress display after several study/quiz sessions.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

## Phase 3: Integration + Polish

### Task 9: Stop Hook for Session Intelligence
**Context**: A stop hook that fires after each Claude response during study sessions. Analyzes the conversation for learning signals and updates progress.

**Implementation**:
Create `plugins/teacher/hooks/hooks.json` + `plugins/teacher/hooks/templates/session-tracker.sh`:
- Parse transcript from stdin
- Detect if this is a teaching session (check for active course state)
- If teaching session:
  - Extract exercise results from the conversation
  - Update FSRS state for concepts discussed
  - Detect struggle signals (repeated errors, confusion language)
  - Log session activity
- Output: `{}` (don't block stop) or `{"continue": true}` if mid-exercise

**Requirements**: Fast (<10s), won't interfere with non-teaching sessions.

**Definition of Done**: Hook fires during study sessions and correctly updates state.

**Validation**: `pytest plugins/teacher/tests/test_stop_hook.py` + manual QA.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

### Task 10: Tests + QA
**Context**: Comprehensive test suite and manual QA across all three target use cases.

**Implementation**:
- `test_plugin_structure.py` — validates plugin structure
- `test_state.py` — state read/write/init
- `test_fsrs.py` — FSRS calculations
- `test_planner.py` — session planning, frontier, mastery
- `test_stop_hook.py` — hook behavior
- `test_e2e.py` — end-to-end tests (requires Claude CLI, gated by RUN_E2E)

Manual QA:
- Build course for informal Malay → study → quiz → check progress
- Build course for systems design → study → quiz → check progress
- Build course for interview prep → study → quiz → check progress
- Test edge cases: empty course, all mastered, struggling learner, session resume

**Requirements**: All tests pass. All three use cases produce reasonable results.

**Definition of Done**: Full test suite green. All three courses QA'd.

**Validation**: `pytest plugins/teacher/` passes. Manual QA checklist completed.

**Checkboxes**: `[ ]` Code Complete `[ ]` Validated `[ ]` Reviewed

---

## Dependency Graph

```
Task 1 (scaffold)
  ↓
Task 2 (state schema) ──────────────→ Task 5 (build-course)
  ↓                                       ↓
Task 3 (FSRS) ──→ Task 4 (planner) → Task 6 (study)
                                      Task 7 (quiz)
                                      Task 8 (progress)
                                          ↓
                                      Task 9 (stop hook)
                                          ↓
                                      Task 10 (tests + QA)
```

**Parallelizable**: Tasks 3 and 2 can be worked in parallel. Tasks 5-8 can be partially parallelized (they depend on 2-4 but not on each other). Task 9 depends on having at least study working. Task 10 is last.

## Estimated Scope

- **Phase 1** (Tasks 1-4): Foundation — plugin structure, state management, FSRS, planner
- **Phase 2** (Tasks 5-8): Core features — build-course, study, quiz, progress
- **Phase 3** (Tasks 9-10): Integration — stop hook, comprehensive testing

Each phase builds on the previous. Phase 1 produces testable Python scripts. Phase 2 produces usable slash commands. Phase 3 ties it together.
