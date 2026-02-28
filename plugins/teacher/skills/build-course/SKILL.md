---
name: build-course
description: >
  Builds an adaptive learning course for any text-based subject. Activates when the user
  wants to create a new course, start learning a topic, set up a study plan, or says
  'build course', 'teach me', 'I want to learn', 'create curriculum', 'new course',
  or 'set up learning plan'. Handles intake, knowledge graph generation, diagnostic
  assessment, and course initialization.
---

# Build Course

Create a structured, adaptive learning course for any text-based subject.

## Step 1: Intake — Understand What the Learner Wants

Ask the learner these questions (adapt phrasing naturally, don't read from a script):

1. **What do you want to learn?** Get the specific topic/subject.
2. **What's your goal?** Examples: conversational fluency, pass an interview, understand concepts deeply, build projects, pass a certification.
3. **What do you already know?** Get their self-assessed level (complete beginner, some exposure, intermediate, advanced wanting to fill gaps).
4. **Any specific focus areas?** Sub-topics they care about most, or areas they know they're weak in.
5. **Time commitment?** How many minutes per session, how many sessions per week.

Summarize their answers back to confirm before proceeding.

## Step 2: Research the Domain

Use your training knowledge (and WebSearch/WebFetch if available) to understand:

- How this subject is typically taught and structured
- What the standard progression looks like (beginner → intermediate → advanced)
- Key concepts, common prerequisites, and typical stumbling blocks
- Best pedagogical approaches for this domain type
- For languages: frequency lists, grammar progression, register/formality levels
- For technical subjects: concept dependencies, practical vs. theoretical balance
- For interview prep: common question types, evaluation frameworks, meta-skills

## Step 3: Generate the Knowledge Graph

Create a knowledge graph as a JSON structure. This is the backbone of the course.

**Requirements:**
- 20-80 concepts depending on scope (start smaller, can expand later)
- Each concept has: id (kebab-case), name, description, prerequisites (list of concept IDs), bloom_target, difficulty (0.0-1.0), unit grouping, and domain-specific metadata
- Prerequisites must form a valid DAG (no cycles)
- Group concepts into 4-8 units of logical progression
- Bloom targets: use "remember" for facts/vocabulary, "understand" for concepts, "apply" for skills, "analyze" for complex reasoning, "evaluate" for judgment calls

**For language courses specifically:**
- Include vocabulary concepts (grouped by topic: greetings, food, directions, etc.)
- Include grammar concepts (sentence structure, tense/aspect, affixation, etc.)
- Include pragmatic concepts (register, politeness, cultural context)
- In metadata, include: key_vocabulary (list of words), grammar_points (list), example_sentences
- Difficulty should follow frequency — common words/patterns are easier

**For technical courses:**
- Include concept nodes for each key idea
- Include skill nodes for practical application
- In metadata, include: key_terms, common_misconceptions, real_world_examples

**For interview prep courses:**
- Include knowledge concepts (what to know)
- Include skill concepts (how to communicate it)
- Include meta-skill concepts (how to handle pressure, structure answers, ask clarifying questions)
- In metadata, include: sample_questions, evaluation_criteria

**Validate** the knowledge graph before saving:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from planner import validate_graph, validate_graph_pedagogy
errors = validate_graph(KNOWLEDGE_GRAPH_DICT)
warnings = validate_graph_pedagogy(KNOWLEDGE_GRAPH_DICT)
if errors:
    print('ERRORS:', errors)
if warnings:
    print('WARNINGS:', warnings)
if not errors:
    print('Graph is valid')
"
```

If there are errors, fix them. If there are warnings (e.g., too many prerequisites, very deep chains), review them and adjust the graph if needed. Present any warnings to the learner and ask if the structure makes sense.

Save the knowledge graph by running:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import init_teaching, init_course
init_teaching()
init_course('COURSE_NAME', KNOWLEDGE_GRAPH_DICT, CURRICULUM_DICT, CONFIG_DICT)
print('Course initialized successfully')
"
```

Replace COURSE_NAME, KNOWLEDGE_GRAPH_DICT, CURRICULUM_DICT, and CONFIG_DICT with the actual values. Use proper Python dict literals.

## Step 4: Generate Course Config

Create the config with:
- `domain_type`: "language", "technical", "interview", or "conceptual"
- `exercise_prompts`: per-Bloom-level prompt templates (see reference below)
- `assessment_rubric`: how to evaluate responses for this domain
- `error_taxonomy`: common error types for this domain
- `session_preferences`: default duration, concepts per session, review ratio
- `modality_weights`: distribution of exercise modalities across sessions

### Exercise Prompt Reference

Include concrete exercise prompt templates per Bloom level adapted to the domain:

**For Language Courses:**
- Remember: "Translate this word/phrase from [L1] to [L2]: {target_vocabulary}"
- Understand: "Read this sentence and explain what it means in English: {example_sentence_in_L2}"
- Apply: "Create a sentence using {target_vocabulary} in the context of {scenario}"
- Analyze: "Here are two sentences. One uses {grammar_point} correctly, one doesn't. Identify which is wrong and explain why: {sentence_pair}"
- Evaluate: "Read this paragraph and identify any errors in register, grammar, or vocabulary: {paragraph}"
- Create: "Write a short dialogue between two people in a {scenario} using {grammar_points} and {vocabulary}"

**For Technical Courses:**
- Remember: "Define {key_term} in your own words"
- Understand: "Explain why {concept} matters. When would you use it vs {alternative}?"
- Apply: "Given this scenario: {scenario}, apply {concept} to solve it"
- Analyze: "Here's a system design: {design}. Identify the bottleneck and explain why"
- Evaluate: "Compare these two approaches to {problem}: {approach_A} vs {approach_B}. Which is better for {context} and why?"
- Create: "Design a {system/algorithm/data model} that handles {requirements}"

**For Interview Prep:**
- Remember: "What are the key components of {concept}?"
- Understand: "Explain {concept} as if to a non-technical stakeholder"
- Apply: "Walk me through how you would answer this interview question: {question}"
- Analyze: "Break down this system design question into sub-problems: {question}"
- Evaluate: "Here's a candidate's answer to {question}: {answer}. What's good? What's missing?"
- Create: "Design a solution for {problem} and explain your trade-offs"

### Modality Configuration

Set `modality_weights` to control exercise type distribution:

```json
{
  "modality_weights": {
    "worksheet": 0.3,
    "conversation": 0.4,
    "code": 0.0,
    "long_form": 0.2,
    "image_review": 0.1
  }
}
```

- Language courses: conversation 0.4, worksheet 0.3, long_form 0.2, image_review 0.1, code 0.0
- Technical courses: conversation 0.3, code 0.3, long_form 0.2, worksheet 0.2, image_review 0.0
- Interview courses: conversation 0.5, long_form 0.3, worksheet 0.1, code 0.1, image_review 0.0
- Conceptual courses: conversation 0.4, long_form 0.3, worksheet 0.2, code 0.0, image_review 0.1

### Error Taxonomy by Domain

Include domain-specific error types in `error_taxonomy`:

- **Language**: vocabulary_confusion, grammar_pattern, register_mismatch, spelling, word_order, affix_error, false_friend
- **Technical**: syntax_error, logic_error, off_by_one, wrong_data_structure, missing_edge_case, misconception, complexity_error
- **Conceptual**: definition_error, relationship_confusion, overgeneralization, undergeneralization, causal_error
- **Interview**: incomplete_answer, missed_tradeoff, poor_structure, over_engineering, missing_clarification

## Step 5: Diagnostic Assessment

Before finalizing the starting point, run a quick diagnostic. This validates the learner's self-reported level.

1. Select 5-8 concepts spanning the range from where they claim to be down to fundamentals
2. For each concept, ask ONE targeted question that tests genuine understanding (not just recognition)
3. Evaluate their responses — be honest about the assessment, not generous
4. Use results to determine the actual starting point:
   - If they nail concepts they claimed to know → trust their self-report
   - If they struggle with claimed knowledge → adjust starting point earlier
   - Mark concepts they demonstrated mastery of as "mastered" in initial progress

## Step 6: Initialize Learner State

Initialize the progress file by running:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from state import init_progress, init_profile, load_progress, save_progress, load_profile
init_profile()
init_progress('COURSE_NAME', KNOWLEDGE_GRAPH_DICT)
progress = load_progress('COURSE_NAME')
# Mark diagnosed concepts
concepts = progress['concepts']
for cid in MASTERED_IDS:
    concepts[cid]['status'] = 'mastered'
    concepts[cid]['mastery_score'] = 0.9
    concepts[cid]['bloom_level'] = 'apply'
for cid in LEARNING_IDS:
    concepts[cid]['status'] = 'learning'
    concepts[cid]['mastery_score'] = 0.4
# Add course to active courses list
profile = load_profile()
if 'COURSE_NAME' not in profile.get('active_courses', []):
    profile.setdefault('active_courses', []).append('COURSE_NAME')
    from state import save_profile
    save_profile(profile)
save_progress('COURSE_NAME', progress)
print('Progress initialized')
"
```

## Step 7: Present the Course Plan

Show the learner:
1. **Course overview**: name, total concepts, estimated completion time
2. **Your starting point**: based on diagnostic results
3. **Unit breakdown**: what each unit covers
4. **First session preview**: what they'll learn in their first `/study` session
5. **How to start**: tell them to run `/study` when ready

Keep it encouraging but honest. If the diagnostic revealed gaps, frame it positively: "You've got a solid foundation in X, and we'll strengthen Y before moving to Z."

## Important Guidelines

- **Be thorough in the knowledge graph** — it's the foundation for everything. Spend time getting the prerequisites right.
- **Don't over-scope** — 30-50 concepts is usually better to start than 100. The learner can always expand later.
- **Validate your own DAG** — mentally check that no concept requires something that comes after it.
- **Use the diagnostic honestly** — the point is to calibrate, not to make the learner feel good. Being placed too high wastes their time.
- **Save everything to disk** — all state must be persisted via the Python scripts. Nothing should exist only in conversation context.
