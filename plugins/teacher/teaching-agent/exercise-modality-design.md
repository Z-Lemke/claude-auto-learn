# Exercise Modality System Design

**Date**: 2026-02-22
**Purpose**: Concrete design for the exercise modality system -- how different exercise types are selected, generated, delivered, evaluated, and tracked within the teaching agent plugin.

---

## Table of Contents

1. [Exercise Modalities Defined](#1-exercise-modalities-defined)
2. [Modality Selection: Decision Matrix](#2-modality-selection-decision-matrix)
3. [Worksheet System Design](#3-worksheet-system-design)
4. [Conversation / Roleplay Exercises](#4-conversation--roleplay-exercises)
5. [Code Exercises](#5-code-exercises)
6. [Long-Form Response Exercises](#6-long-form-response-exercises)
7. [Image Review Exercises](#7-image-review-exercises)
8. [Evaluation Pipelines Per Modality](#8-evaluation-pipelines-per-modality)
9. [Exercise Generation Quality](#9-exercise-generation-quality)
10. [Session Flow and Modality Mixing](#10-session-flow-and-modality-mixing)
11. [State Tracking and Modality Adaptation](#11-state-tracking-and-modality-adaptation)
12. [File Format Specifications](#12-file-format-specifications)
13. [Integration with Existing System](#13-integration-with-existing-system)
14. [Future Extensibility (v2+)](#14-future-extensibility-v2)

---

## 1. Exercise Modalities Defined

Five exercise modalities are supported in v1. Each is suited to different learning contexts.

### 1.1 Worksheet (Markdown File)

**What**: A structured markdown file written to disk containing exercises that the learner fills in. The agent generates the file, the learner edits it (in their editor of choice), and the agent evaluates the completed worksheet.

**Best for**: Vocabulary drills, fill-in-the-blank grammar, translation sets, math problem sets, definition matching, diagram labeling (ASCII).

**Why it matters**: Worksheets give the learner a tangible artifact they can work on at their own pace. They also provide a clear "before/after" for evaluation -- the agent can diff the template against the completed version.

### 1.2 Conversation (In-Session Dialogue)

**What**: Interactive back-and-forth dialogue within the Claude session. The agent poses questions, the learner responds in natural language, the agent evaluates and follows up.

**Best for**: Socratic questioning, explanation practice, roleplay/scenario-based learning, conversation practice for languages, verbal reasoning, interview prep.

**Why it matters**: This is the natural modality for an LLM tutor. It enables real-time adaptation, Socratic probing, and immediate feedback. It is also the only modality that supports multi-turn scaffolding (hint sequences).

### 1.3 Code Exercise (Real Files)

**What**: The agent creates a code file with a problem specification (in comments), starter code, and test cases. The learner implements the solution in their editor. The agent runs tests to evaluate.

**Best for**: Programming concepts, algorithm practice, technical skill building, any domain where code is the natural expression of understanding.

**Why it matters**: Code exercises leverage the CLI environment's greatest strength -- the learner is already in a terminal. Real files, real tests, real execution. This is strictly superior to "type your code in chat" because the learner gets editor support, syntax highlighting, and can iterate.

### 1.4 Long-Form Response (Essay / Explanation)

**What**: The agent poses an open-ended question requiring a multi-paragraph written response. The learner writes their response either in the chat or in a file. The agent evaluates against a rubric.

**Best for**: Higher Bloom levels (Analyze, Evaluate, Create), conceptual understanding checks, compare-and-contrast questions, case study analysis, research summaries.

**Why it matters**: Long-form responses are the gold standard for assessing deep understanding. A learner who can coherently explain a concept in writing demonstrably understands it better than one who can only fill in blanks.

### 1.5 Image Review (User Uploads Photo)

**What**: The learner does handwritten work (on paper, whiteboard, etc.) and uploads a photo. The agent evaluates the handwritten work using Claude's vision capabilities.

**Best for**: Handwriting practice (language scripts like Jawi, Chinese characters, etc.), mathematical proofs, circuit diagrams, free-form brainstorming, any domain where handwriting is pedagogically valuable.

**Why it matters**: Some learning activities are genuinely better done by hand. Writing characters by hand improves retention over typing (research-backed). Math proofs and diagrams often flow better on paper. This modality bridges physical and digital learning.

---

## 2. Modality Selection: Decision Matrix

The system selects exercise modalities based on three dimensions: **domain type**, **Bloom level**, and **concept type**. The agent uses this matrix to choose the primary modality and optionally a secondary modality for variety.

### 2.1 Primary Decision Matrix

| Domain Type | Bloom Level | Concept Type | Primary Modality | Secondary Modality |
|-------------|-------------|--------------|------------------|--------------------|
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

### 2.2 Selection Algorithm

The agent uses the following logic (implemented as instructions, not code) to select a modality:

```
1. Look up (domain_type, bloom_level, concept_type) in the decision matrix
2. If a direct match exists, use primary modality
3. If no direct match, use the closest bloom_level match for the domain_type
4. Apply learner preference override (if profile specifies modality preferences)
5. Apply variety rule: if the last 3 exercises used the same modality,
   switch to the secondary modality
6. Apply session context: if session is near end (< 5 min remaining),
   prefer Conversation (fastest turnaround) over Worksheet or Code
```

### 2.3 Course Config Integration

The decision matrix defaults can be overridden per-course in `config.json`:

```json
{
  "domain_type": "language",
  "modality_overrides": {
    "vocabulary": {
      "primary": "worksheet",
      "secondary": "conversation",
      "bloom_override": {
        "apply": { "primary": "conversation" }
      }
    },
    "grammar": {
      "primary": "conversation",
      "secondary": "worksheet"
    }
  },
  "modality_weights": {
    "worksheet": 0.3,
    "conversation": 0.4,
    "code": 0.0,
    "long_form": 0.2,
    "image_review": 0.1
  }
}
```

The `modality_weights` field controls the overall distribution across a session. A language course might never use `code` (weight 0.0). A programming course might heavily favor `code` (weight 0.5) and `conversation` (weight 0.3).

---

## 3. Worksheet System Design

### 3.1 File Location and Naming

Worksheets are stored in the learner's progress directory:

```
~/.claude/teaching/learner/<course-name>/worksheets/
  <session-timestamp>-<concept-id>.md     # The worksheet file
```

Example: `~/.claude/teaching/learner/bahasa-melayu/worksheets/20260222T143000Z-greetings.md`

### 3.2 Worksheet Markdown Schema

Every worksheet follows this structure:

```markdown
<!-- WORKSHEET -->
<!-- course: bahasa-melayu -->
<!-- concept: greetings -->
<!-- bloom_level: remember -->
<!-- generated: 2026-02-22T14:30:00Z -->
<!-- status: pending -->

# Worksheet: Greetings in Malay

**Concept**: Basic Greetings
**Instructions**: Fill in the blanks below. Replace each `___` with your answer.
**Time estimate**: 10 minutes

---

## Section 1: Translation (English to Malay)

1. Good morning: ___
2. Good afternoon: ___
3. Good evening: ___
4. How are you? (formal): ___
5. Thank you: ___

## Section 2: Fill in the Blank

Complete each sentence with the correct greeting.

1. When you meet your teacher at 9 AM, you say: "___, cikgu!"
2. You are leaving a friend's house at night, you say: "___"
3. Someone gives you a gift, you respond: "___"

## Section 3: Matching

Draw a line (or write the letter) matching each Malay greeting to its context.

| Malay | | Context |
|-------|---|---------|
| 1. Selamat pagi | ___ | A. Leaving at night |
| 2. Apa khabar | ___ | B. Morning greeting |
| 3. Selamat tinggal | ___ | C. Asking how someone is |

---

<!-- ANSWER_KEY (do not edit below this line) -->
<!-- This section is hidden from the learner and used by the evaluator -->
<!-- answers:
1.1: selamat pagi
1.2: selamat tengah hari / selamat petang
1.3: selamat malam / selamat petang
1.4: apa khabar
1.5: terima kasih
2.1: selamat pagi
2.2: selamat malam / selamat tinggal
2.3: terima kasih
3.1: B
3.2: C
3.3: A
-->
```

### 3.3 Key Schema Rules

1. **HTML comments for metadata**: The `<!-- WORKSHEET -->` marker and metadata fields are in HTML comments so they are invisible when rendered but parseable by the agent.
2. **Answer placeholders**: Always `___` (three underscores). This makes it easy for the agent to find unfilled answers.
3. **Answer key in comments**: The `<!-- ANSWER_KEY -->` section is in HTML comments. The agent reads this during evaluation. Multiple acceptable answers are separated by ` / `.
4. **Status tracking**: The `<!-- status: pending -->` comment is updated by the agent to `submitted` or `evaluated` after processing.
5. **Section numbering**: Answers are referenced as `section.question` (e.g., `1.3` = Section 1, Question 3).

### 3.4 Worksheet Generation Process

```
1. Agent determines concept, bloom level, and exercise count
2. Agent generates worksheet content following the schema above
3. Agent writes the file using the Write tool
4. Agent tells the learner: "I've created a worksheet at [path].
   Open it in your editor, fill in the blanks, save, and tell me
   when you're done."
5. Agent waits for the learner to respond
```

### 3.5 Worksheet Evaluation Process

```
1. Learner says "done" / "finished" / "check my worksheet"
2. Agent reads the worksheet file using the Read tool
3. Agent compares learner answers against the answer key
4. For each answer:
   a. Exact match or close match with any accepted answer -> correct
   b. Partial match (e.g., missing accent, minor typo) -> partially correct
   c. No match -> incorrect
5. Agent provides feedback:
   - Score: X/Y correct
   - Per-question feedback for incorrect/partial answers
   - Conceptual explanation for patterns of errors
6. Agent updates concept progress in state
7. Agent updates worksheet status to "evaluated"
```

### 3.6 Worksheet Types by Domain

| Domain | Worksheet Types |
|--------|----------------|
| Language | Vocabulary matching, translation, fill-in-blank sentences, error correction, sentence reordering |
| Technical | Term definitions, API usage fill-in, output prediction, matching concepts to descriptions |
| Conceptual | Definition matching, true/false with explanation, categorization, timeline ordering |
| Interview | STAR framework templates, behavioral question response outlines |

---

## 4. Conversation / Roleplay Exercises

### 4.1 Exercise Structure

Conversation exercises happen entirely within the Claude session. They follow this flow:

```
Agent presents exercise prompt
  -> Learner responds
    -> Agent evaluates inline
      -> Agent provides feedback
        -> (optional) Agent asks follow-up
          -> Learner responds again
            -> Agent concludes exercise
```

### 4.2 Conversation Exercise Types

**Type 1: Direct Question**
```
Agent: "Explain what happens when you call a recursive function
        without a base case."
Learner: [responds]
Agent: [evaluates, provides feedback]
```

**Type 2: Socratic Dialogue**
```
Agent: "Let's explore how Malay affixes work. What do you think
        the prefix 'ber-' does to a base word?"
Learner: [responds]
Agent: [guides with follow-up questions, scaffolds understanding]
```

**Type 3: Roleplay / Scenario**
```
Agent: "Let's practice ordering food. I'll be the server at a
        mamak restaurant. Saya pelayan di sini. Nak makan apa?"
Learner: [responds in Malay]
Agent: [stays in character, corrects errors gently, continues scenario]
```

**Type 4: Error Identification**
```
Agent: "Find and correct the error in this sentence:
        'Saya pergi ke sekolah semalam hari.'"
Learner: [identifies and corrects]
Agent: [evaluates correction]
```

**Type 5: Prediction / Application**
```
Agent: "Given what you know about binary search, what would happen
        if the input array wasn't sorted?"
Learner: [predicts]
Agent: [evaluates reasoning, not just answer]
```

### 4.3 Conversation Exercise Evaluation

The agent evaluates inline using these criteria:

```
For factual/procedural answers:
  - Is the answer correct? (binary or partial)
  - Does the reasoning show understanding? (not just memorized)
  - Are there misconceptions revealed?

For language production:
  - Is the grammar correct for the target structures?
  - Is the vocabulary appropriate?
  - Is the register appropriate for the context?
  - Is communication successful even if imperfect?

For open-ended responses:
  - Does the response address the prompt?
  - Is the reasoning coherent?
  - Are claims supported?
  - Is there evidence of the target Bloom level?
```

### 4.4 Rating Mapping

The agent maps its evaluation to an FSRS rating:

| Evaluation | FSRS Rating | Description |
|------------|-------------|-------------|
| Correct, immediate, confident | 4 (Easy) | Learner clearly knows this |
| Correct with some hesitation | 3 (Good) | Solid understanding |
| Partially correct or needed hints | 2 (Hard) | Getting there but not solid |
| Incorrect after hint sequence | 1 (Again) | Needs more practice |

---

## 5. Code Exercises

### 5.1 File Location and Structure

Code exercises are stored in the learner's progress directory:

```
~/.claude/teaching/learner/<course-name>/exercises/
  <concept-id>/
    exercise.py          # Problem specification + starter code
    test_exercise.py     # Test cases
    solution.py          # Reference solution (hidden, for evaluation)
```

The language/extension depends on the course. Python is the default; the course config can specify alternatives.

### 5.2 Exercise File Template

```python
#!/usr/bin/env python3
"""
Exercise: Implementing Binary Search
Concept: binary-search
Bloom Level: apply

Instructions:
    Implement the binary_search function below. It should return the index
    of the target value in a sorted list, or -1 if not found.

    Do NOT use Python's built-in bisect module.

Hints (read only if stuck):
    1. What are the boundaries of your search space?
    2. How do you calculate the midpoint?
    3. How do you decide which half to search next?
"""


def binary_search(arr: list, target: int) -> int:
    """Return the index of target in sorted list arr, or -1 if not found."""
    # YOUR CODE HERE
    pass
```

### 5.3 Test File Template

```python
#!/usr/bin/env python3
"""Tests for binary search exercise."""

import sys
import os

# Add exercise directory to path
sys.path.insert(0, os.path.dirname(__file__))

from exercise import binary_search


def test_found_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_found_first():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0

def test_found_last():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_not_found():
    assert binary_search([1, 3, 5, 7, 9], 4) == -1

def test_empty_list():
    assert binary_search([], 5) == -1

def test_single_element_found():
    assert binary_search([5], 5) == 0

def test_single_element_not_found():
    assert binary_search([5], 3) == -1


if __name__ == "__main__":
    tests = [
        test_found_middle, test_found_first, test_found_last,
        test_not_found, test_empty_list,
        test_single_element_found, test_single_element_not_found,
    ]
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

### 5.4 Code Exercise Flow

```
1. Agent creates exercise.py and test_exercise.py
2. Agent tells learner: "I've created a code exercise at [path].
   Implement the function in exercise.py, then run the tests:
   python3 [path/to/test_exercise.py]"
3. Learner implements and runs tests
4. Learner tells agent results (or agent runs tests via Bash)
5. Agent evaluates:
   a. How many tests passed?
   b. Read the implementation -- is it correct approach?
   c. Is there anything to improve (style, edge cases, efficiency)?
6. Agent provides feedback and updates state
```

### 5.5 Code Exercise Evaluation

```
Automated evaluation (via test runner):
  - All tests pass -> correct
  - Some tests pass -> partially correct
  - No tests pass -> incorrect

Qualitative evaluation (agent reads code):
  - Does the approach match the target concept?
  - Are there code quality issues to address?
  - Is the solution efficient?
  - Could the learner explain why it works? (ask in follow-up)
```

### 5.6 Rating Mapping for Code Exercises

| Tests Passed | Code Quality | FSRS Rating |
|-------------|-------------|-------------|
| All, clean implementation | Good | 4 (Easy) |
| All, minor style issues | Acceptable | 3 (Good) |
| Most, or needed hints | Needs improvement | 2 (Hard) |
| Few or none after attempt | Poor | 1 (Again) |

---

## 6. Long-Form Response Exercises

### 6.1 Delivery Options

Long-form responses can be delivered two ways:

**Option A: In-chat response**
The learner types their response directly in the Claude session. Best for shorter responses (1-3 paragraphs).

**Option B: File-based response**
The agent creates a response template file, the learner writes in their editor, then tells the agent to evaluate. Best for longer responses (essay-length).

### 6.2 Response Template (File-Based)

```
~/.claude/teaching/learner/<course-name>/responses/
  <session-timestamp>-<concept-id>.md
```

Template:

```markdown
<!-- RESPONSE -->
<!-- course: intro-to-algorithms -->
<!-- concept: sorting-tradeoffs -->
<!-- bloom_level: evaluate -->
<!-- generated: 2026-02-22T14:30:00Z -->

# Question: Sorting Algorithm Trade-offs

Compare and contrast merge sort and quicksort. Address the following:

1. Time complexity in best, average, and worst cases
2. Space complexity
3. Stability
4. When you would choose one over the other in practice

**Your response** (write below this line):

---


```

### 6.3 Evaluation Rubric Structure

Long-form responses are evaluated against a rubric embedded in the course config. Each rubric has dimensions scored on a 4-point scale:

```json
{
  "rubric_template": {
    "dimensions": [
      {
        "name": "Accuracy",
        "weight": 0.3,
        "levels": {
          "4": "All claims are factually correct with no errors",
          "3": "Minor errors that don't affect overall correctness",
          "2": "Some significant errors or misconceptions",
          "1": "Major errors or fundamental misconceptions"
        }
      },
      {
        "name": "Completeness",
        "weight": 0.25,
        "levels": {
          "4": "All required points addressed thoroughly",
          "3": "Most points addressed, minor gaps",
          "2": "Several points missing or superficial",
          "1": "Major gaps in coverage"
        }
      },
      {
        "name": "Reasoning Depth",
        "weight": 0.25,
        "levels": {
          "4": "Shows deep understanding with nuanced analysis",
          "3": "Shows good understanding with some analysis",
          "2": "Shows surface-level understanding",
          "1": "No evidence of understanding beyond recall"
        }
      },
      {
        "name": "Communication",
        "weight": 0.2,
        "levels": {
          "4": "Clear, well-organized, precise language",
          "3": "Generally clear with minor organizational issues",
          "2": "Unclear in places, disorganized",
          "1": "Difficult to follow, major clarity issues"
        }
      }
    ]
  }
}
```

### 6.4 Evaluation Process

```
1. Agent reads the learner's response
2. Agent evaluates against each rubric dimension
3. Agent calculates weighted score: sum(dimension_score * weight)
4. Agent provides:
   - Per-dimension score and brief explanation
   - Overall score (out of 4.0)
   - Specific strengths
   - Specific areas for improvement
   - One concrete suggestion for next time
5. Agent maps overall score to FSRS rating:
   - 3.5-4.0 -> Easy (4)
   - 2.5-3.4 -> Good (3)
   - 1.5-2.4 -> Hard (2)
   - < 1.5   -> Again (1)
```

---

## 7. Image Review Exercises

### 7.1 When to Use

Image review is triggered when:
- The concept involves handwriting or script practice (language courses with non-Latin scripts)
- The learner is asked to draw diagrams (circuits, architecture, data structures)
- The learner is doing math proofs or derivations by hand
- The course config explicitly includes `image_review` in the concept's modality list

### 7.2 Exercise Flow

```
1. Agent assigns the exercise: "Write the following 10 Jawi characters
   by hand. Take a photo and share it with me."

2. Agent provides the reference (what they should write/draw):
   - For scripts: the target characters/words
   - For diagrams: the specification of what to draw
   - For math: the problem to solve

3. Learner does the work by hand

4. Learner provides the image:
   - Pastes an image into the Claude session (if supported)
   - Or provides a file path: "Check my work at /path/to/photo.jpg"

5. Agent reads the image using the Read tool (Claude's vision capability)

6. Agent evaluates:
   - For scripts: character formation, stroke order (if visible), legibility
   - For diagrams: correctness of structure, labeling, completeness
   - For math: correctness of steps and final answer
```

### 7.3 Evaluation Criteria

**Script/Handwriting**:
- Character recognition: can the agent identify what was written?
- Correctness: does it match the target?
- Formation quality: are proportions and strokes reasonable?
- Consistency: is the writing consistent across examples?

**Diagrams**:
- Structural correctness: are components and relationships correct?
- Labeling: are all parts labeled correctly?
- Completeness: are all required elements present?

**Math/Proofs**:
- Step correctness: is each step valid?
- Final answer: is the conclusion correct?
- Presentation: is the work legible and organized?

### 7.4 Limitations and Caveats

- Image evaluation is inherently less precise than text evaluation
- The agent should express uncertainty when image quality is poor
- The agent should never claim handwriting is "wrong" when it simply cannot read it -- ask for clarification
- For high-stakes assessment, image review should be supplementary, not primary

---

## 8. Evaluation Pipelines Per Modality

### 8.1 Unified Evaluation Interface

All modalities produce the same output structure for the state system:

```json
{
  "exercise_id": "20260222T143000Z-greetings-ws",
  "concept_id": "greetings",
  "modality": "worksheet",
  "bloom_level": "remember",
  "timestamp": "2026-02-22T14:45:00Z",
  "score": {
    "correct": 8,
    "total": 10,
    "percentage": 0.80
  },
  "fsrs_rating": 3,
  "details": {
    "errors": [
      {
        "question": "1.3",
        "expected": "selamat petang",
        "actual": "selamat malam",
        "error_type": "confusion",
        "note": "Mixed up evening/night greetings"
      }
    ],
    "strengths": ["Basic greetings solid", "Good recall of terima kasih"],
    "improvements": ["Review time-of-day greetings"]
  },
  "hints_used": 0,
  "time_spent_seconds": null
}
```

### 8.2 Pipeline Per Modality

**Worksheet Pipeline**:
```
Read file -> Parse answers -> Compare to answer key -> Score ->
  Generate per-question feedback -> Calculate FSRS rating ->
    Update state -> Write evaluated status to file
```

**Conversation Pipeline**:
```
Receive response -> Evaluate inline (agent judgment) ->
  Provide immediate feedback -> Optionally ask follow-up ->
    Determine final rating -> Record exercise result ->
      Update state
```

**Code Pipeline**:
```
Run tests via Bash -> Parse test output -> Read implementation ->
  Evaluate approach quality -> Combine test score + quality ->
    Generate feedback -> Calculate FSRS rating -> Update state
```

**Long-Form Pipeline**:
```
Read response -> Evaluate against rubric dimensions ->
  Calculate weighted score -> Generate per-dimension feedback ->
    Calculate FSRS rating -> Update state
```

**Image Review Pipeline**:
```
Read image -> Identify written content -> Compare to reference ->
  Evaluate quality/correctness -> Generate feedback ->
    Calculate FSRS rating -> Update state
```

### 8.3 Error Taxonomy Integration

The evaluation pipeline feeds into the error taxonomy system. Each modality records error types:

| Domain | Error Types |
|--------|-------------|
| Language | `vocabulary_confusion`, `grammar_pattern`, `register_mismatch`, `spelling`, `word_order`, `affix_error`, `false_friend` |
| Technical | `syntax_error`, `logic_error`, `off_by_one`, `wrong_data_structure`, `missing_edge_case`, `misconception`, `complexity_error` |
| Conceptual | `definition_error`, `relationship_confusion`, `overgeneralization`, `undergeneralization`, `causal_error`, `correlation_causation` |

Errors are recorded in the concept progress `error_history` field and used to:
1. Generate targeted remediation exercises
2. Identify persistent misconceptions
3. Choose exercises that specifically address weak areas

---

## 9. Exercise Generation Quality

### 9.1 What Makes a Good Exercise

Per Bloom level, good exercises have these properties:

**Remember**:
- Tests recall of specific facts, terms, or procedures
- Has a single clear correct answer (or small set of acceptable answers)
- Does NOT allow guessing (avoid yes/no or binary choices)
- Good: "Translate 'good morning' to Malay"
- Bad: "Is 'selamat pagi' a greeting? (yes/no)"

**Understand**:
- Tests ability to explain, paraphrase, or interpret
- Requires the learner to demonstrate comprehension, not just recall
- Good: "In your own words, explain why we use 'ber-' prefix with some verbs"
- Bad: "What does the 'ber-' prefix mean?" (could be memorized)

**Apply**:
- Presents a novel situation requiring use of the concept
- The specific problem should not have been seen before
- Good: "Write a function that uses binary search to find the insertion point"
- Bad: "Implement binary search" (too similar to textbook example)

**Analyze**:
- Requires breaking down a complex situation into components
- Must involve identifying relationships, patterns, or structures
- Good: "Compare these two sorting algorithms. What are the trade-offs?"
- Bad: "List the properties of merge sort" (just recall)

**Evaluate**:
- Requires making and defending a judgment
- There should be multiple defensible positions
- Good: "Would you use SQL or NoSQL for this application? Justify your choice."
- Bad: "Which is better, SQL or NoSQL?" (no context for judgment)

**Create**:
- Requires producing something original using the concepts
- The output should demonstrate synthesis of multiple concepts
- Good: "Design a data model for a library system"
- Bad: "Write a class with a constructor and two methods" (too constrained)

### 9.2 Exercise Generation Prompts (Per Domain)

These prompt templates are stored in the course config and used by the agent when generating exercises.

**Language Domain - Vocabulary (Remember)**:
```
Generate a vocabulary exercise for the concept "{concept_name}".
Target vocabulary: {key_vocabulary}
Exercise type: {worksheet|conversation}

Requirements:
- Include {n} items
- Mix translation directions (L1->L2 and L2->L1)
- Use vocabulary in sentence context, not isolated words
- Include at least 2 distractors (similar words) to test discrimination
- Answers must be unambiguous
```

**Language Domain - Grammar (Apply)**:
```
Generate a grammar application exercise for "{concept_name}".
Grammar point: {grammar_points}
Learner level: {bloom_level}

Requirements:
- Present {n} sentences requiring active use of the grammar point
- Each sentence should be in a different context/topic
- Include at least one sentence where the grammar point is NOT needed (to test discrimination)
- Do not include any English translation in the exercise itself
```

**Technical Domain - Implementation (Apply)**:
```
Generate a code exercise for "{concept_name}".
Target skill: {description}
Language: {programming_language}

Requirements:
- Write a clear problem statement in docstring format
- Provide function signature and type hints
- Include {n} test cases covering normal, edge, and error cases
- The problem must be solvable using {concept_name} specifically
- Do not include problems solvable by brute force without the target concept
- Difficulty: appropriate for someone who just learned {concept_name}
```

**Conceptual Domain - Analysis (Analyze)**:
```
Generate an analysis question for "{concept_name}".
Related concepts: {prerequisites}

Requirements:
- Present a scenario or case study (3-5 sentences of context)
- Ask the learner to analyze using {concept_name}
- The analysis should require identifying 2-3 distinct factors
- There should be nuance -- not a simple right/wrong answer
- Provide a rubric for evaluation with 3-4 dimensions
```

### 9.3 Quality Checks

Before delivering an exercise, the agent should verify:

1. **Solvability**: Can the exercise be solved with the target concept?
2. **Unambiguity**: Is there a clear correct answer (or clear rubric for open-ended)?
3. **Difficulty match**: Is it at the right Bloom level? (not too easy, not too hard)
4. **Novelty**: Is it different from the last exercise on this concept?
5. **Scope**: Does it test the target concept without requiring unlearned prerequisites?

---

## 10. Session Flow and Modality Mixing

### 10.1 Session Flow Patterns

A typical 25-minute study session with modality mixing:

```
Session Start
  |
  v
[Load state, plan session]  (2 min)
  |
  v
[New Concept 1: Teach]  (3 min)
  |-- Agent explains concept (conversation)
  |-- Agent checks understanding (conversation)
  |
  v
[New Concept 1: Practice]  (5 min)
  |-- Primary modality exercise (e.g., worksheet)
  |-- Learner works on it
  |-- Agent evaluates
  |
  v
[Review Concept A: Quick check]  (3 min)
  |-- Conversation exercise (fastest turnaround for review)
  |
  v
[New Concept 2: Teach]  (3 min)
  |-- Agent explains concept (conversation)
  |
  v
[New Concept 2: Practice]  (5 min)
  |-- Different modality (e.g., code exercise) for variety
  |
  v
[Review Concept B: Quick check]  (3 min)
  |-- Conversation exercise
  |
  v
[Session Summary + Save]  (1 min)
```

### 10.2 Modality Transition Rules

1. **Teaching always uses conversation**: New concepts are introduced through dialogue, never worksheets.
2. **Practice uses the decision matrix**: The modality for practice exercises is selected from the decision matrix.
3. **Reviews prefer conversation**: Review exercises should be fast. Conversation is the fastest turnaround modality.
4. **File-based modalities (worksheet, code) create a pause**: When the agent assigns a worksheet or code exercise, the session pauses while the learner works. The agent should set expectations: "Take your time. Tell me when you're done."
5. **Never assign two file-based exercises back-to-back**: This kills session momentum. Always interleave with conversation.
6. **Image review is always opt-in**: Never require image submission. Always offer it as an option: "You can also practice writing these characters by hand and show me a photo."

### 10.3 Handling File-Based Exercise Pauses

When the agent assigns a worksheet or code exercise:

```
Agent: "I've created a worksheet at [path]. Take your time filling it in.
        When you're done, just say 'done' or 'check my worksheet'."

[Session pauses -- learner works in their editor]

Learner: "done"

Agent: [reads and evaluates the file]
Agent: "You got 8/10! Let me go through the ones you missed..."
```

The key design insight: the agent does NOT try to monitor the file in real-time. It waits for the learner to signal completion. This is simpler, more reliable, and respects the learner's workflow.

### 10.4 Adaptive Modality Switching Mid-Session

If the learner is struggling with a particular modality:

```
if learner struggles with worksheet exercises (< 50% on last 2):
  switch to conversation for the same concept
  use Socratic dialogue to identify the gap
  then offer worksheet again, or continue with conversation

if learner struggles with conversation exercises:
  switch to worksheet (more structured, less pressure)
  give them time to think before responding

if learner struggles with code exercises:
  switch to conversation to talk through the approach
  then return to code with more scaffolding (starter code, hints)
```

---

## 11. State Tracking and Modality Adaptation

### 11.1 Per-Concept Modality Performance

Extend the concept progress to track modality-specific performance:

```json
{
  "concept_id": "greetings",
  "status": "learning",
  "bloom_level": "apply",
  "mastery_score": 0.65,
  "modality_performance": {
    "worksheet": {
      "attempts": 3,
      "avg_score": 0.80,
      "last_used": "2026-02-20T10:00:00Z"
    },
    "conversation": {
      "attempts": 5,
      "avg_score": 0.70,
      "last_used": "2026-02-22T14:00:00Z"
    },
    "code": null,
    "long_form": null,
    "image_review": {
      "attempts": 1,
      "avg_score": 0.60,
      "last_used": "2026-02-19T15:00:00Z"
    }
  }
}
```

### 11.2 Learner Modality Preferences (Profile Level)

In the learner profile, track overall modality preferences:

```json
{
  "learning_preferences": {
    "session_duration_minutes": 25,
    "explanation_style": "examples_first",
    "modality_preferences": {
      "preferred": ["conversation", "code"],
      "avoided": ["image_review"],
      "auto_detected": {
        "highest_performance": "worksheet",
        "lowest_performance": "long_form",
        "most_engaged": "conversation"
      }
    }
  }
}
```

### 11.3 Adaptive Modality Selection

Over time, the system adapts which modalities it uses based on tracked performance:

```
Adaptation rules:
1. If a modality consistently produces high scores (avg > 0.85 over 5+ attempts),
   it may be too easy in that modality. Occasionally use a harder modality.

2. If a modality consistently produces low scores (avg < 0.50 over 3+ attempts),
   switch to a different modality. The learner may not be suited to this format.

3. If the learner explicitly says they prefer or dislike a modality, respect that
   and update profile preferences.

4. Mix modalities to prevent boredom. Even if conversation is highest performing,
   don't use it exclusively.

5. For concepts the learner is struggling with, try a modality they haven't used
   for that concept yet. A different format might unlock understanding.
```

### 11.4 v1 Simplification

In v1, modality adaptation is implemented purely through the agent's instructions (the decision matrix + variety rule + learner preferences). The `modality_performance` field is tracked in state but the adaptation rules are encoded in the SKILL.md instructions rather than in a Python script.

In v2+, a `select_modality()` function could be added to `planner.py` to make modality selection deterministic and data-driven.

---

## 12. File Format Specifications

### 12.1 Exercise Result Record

Every exercise, regardless of modality, produces a record stored in the session log:

```json
{
  "exercise_id": "20260222T143000Z-greetings-ws",
  "concept_id": "greetings",
  "modality": "worksheet",
  "bloom_level": "remember",
  "started": "2026-02-22T14:30:00Z",
  "completed": "2026-02-22T14:42:00Z",
  "score": {
    "correct": 8,
    "total": 10,
    "percentage": 0.80
  },
  "fsrs_rating": 3,
  "hints_used": 0,
  "errors": [
    {
      "question": "1.3",
      "error_type": "confusion",
      "detail": "Mixed up selamat petang / selamat malam"
    }
  ],
  "file_path": "~/.claude/teaching/learner/bahasa-melayu/worksheets/20260222T143000Z-greetings.md"
}
```

### 12.2 Worksheet File (Full Spec)

See Section 3.2 for the complete schema. Key points:
- Extension: `.md`
- Metadata in HTML comments
- Answer placeholders: `___`
- Answer key in `<!-- ANSWER_KEY -->` comment block
- Status field: `pending` -> `submitted` -> `evaluated`

### 12.3 Code Exercise Files (Full Spec)

See Section 5.2. Key points:
- Problem in docstring of main file
- Separate test file using assert statements
- Test runner works with `python3 test_exercise.py` (no pytest dependency)
- Reference solution in separate file (never shown to learner)

### 12.4 Long-Form Response Template (Full Spec)

See Section 6.2. Key points:
- Extension: `.md`
- Metadata in HTML comments
- Question/prompt in markdown
- Clear marker for where response goes: `**Your response** (write below this line):`
- Horizontal rule separator

### 12.5 Directory Structure Summary

```
~/.claude/teaching/
  learner/
    profile.json                          # Global learner profile
    <course-name>/
      progress.json                       # Per-concept state
      sessions/
        <timestamp>.json                  # Session logs (include exercise results)
      worksheets/
        <timestamp>-<concept-id>.md       # Worksheet files
      exercises/
        <concept-id>/
          exercise.<ext>                  # Code exercise
          test_exercise.<ext>             # Test file
          solution.<ext>                  # Hidden reference solution
      responses/
        <timestamp>-<concept-id>.md       # Long-form response templates
```

---

## 13. Integration with Existing System

### 13.1 Changes to state.py

No structural changes needed. The existing `update_concept_progress()` function accepts arbitrary `updates` dict, so `modality_performance` can be added to concept progress without code changes.

The `append_session_log()` function already stores per-session data as JSON, so exercise results (with modality information) fit naturally into the `exercises` list in each session log.

### 13.2 Changes to planner.py

Add a `select_modality()` function (v2) that encodes the decision matrix. For v1, the decision matrix lives in the SKILL.md instructions.

Add modality information to the session plan items:

```python
# Current plan item:
{"type": "new", "concept_id": "greetings"}

# Enhanced plan item (v1 - added by agent, not by planner):
{"type": "new", "concept_id": "greetings", "modality": "worksheet"}
```

### 13.3 Changes to SKILL.md (study)

The study skill needs a new section on modality selection and exercise delivery. The agent's instructions should include:

1. The decision matrix (from Section 2)
2. Instructions for generating each modality type (from Sections 3-7)
3. The evaluation pipeline for each modality (from Section 8)
4. Session flow rules for modality mixing (from Section 10)
5. Rating mapping tables (from Sections 4-7)

### 13.4 Changes to SKILL.md (quiz)

The quiz skill should also use modalities beyond conversation. For quiz mode:
- Worksheets are appropriate for vocabulary/terminology quizzes
- Code exercises are appropriate for implementation quizzes
- Conversation remains the default for quick-fire questions
- Long-form responses are appropriate for unit-level comprehensive assessments

### 13.5 Changes to config.json (per course)

Add the following fields:

```json
{
  "exercise_config": {
    "modality_weights": { ... },
    "modality_overrides": { ... },
    "code_language": "python",
    "worksheet_dir": "worksheets",
    "exercise_dir": "exercises",
    "response_dir": "responses"
  },
  "rubrics": {
    "long_form": { ... },
    "code_quality": { ... }
  }
}
```

---

## 14. Future Extensibility (v2+)

### 14.1 SRS Flashcards

**Architecture**: A `flashcards/` directory containing JSON files with card fronts/backs generated from the knowledge graph. Could integrate with Anki via AnkiConnect API or provide a built-in CLI review mode.

**Integration point**: The `select_modality()` function would add "flashcard" as a modality option for Remember-level concepts with the `vocabulary` concept type.

### 14.2 Audio/Pronunciation

**Architecture**: Use macOS `say` command for TTS, Google Cloud TTS API for higher quality, and OpenAI Whisper for speech-to-text assessment.

**Integration point**: Add "audio" modality for language courses at Apply level and above. The agent generates audio prompts and evaluates spoken responses.

### 14.3 Interactive Coding (REPL)

**Architecture**: Instead of file-based code exercises, use an interactive REPL session where the agent poses small coding challenges and the learner types responses.

**Integration point**: Add "repl" modality for Technical domain at Remember and Understand levels where the exercises are small enough for inline responses.

### 14.4 Collaborative Exercises

**Architecture**: Multi-agent exercises where a subagent plays a role (e.g., a conversation partner, a "student" the learner must teach, a "colleague" in a pair programming exercise).

**Integration point**: Requires the subagent hook inheritance fix (issue #21460). Would add "collaborative" modality for language roleplay and technical pair programming scenarios.

### 14.5 Spaced Exercise Variety

**Architecture**: Track which specific exercises (not just concepts) the learner has done. When reviewing a concept, generate a different exercise type than last time to prevent memorization of specific problems.

**Integration point**: Add `exercise_history` to concept progress tracking, storing exercise IDs and types. The generation prompt would include "Do NOT generate exercises similar to: [list of previous exercises]".

---

## Summary of Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Number of modalities in v1 | 5 (worksheet, conversation, code, long-form, image) | Covers all major learning activities without over-engineering |
| Modality selection | Decision matrix in SKILL.md instructions | Simpler than code-based selection for v1; agent can adapt contextually |
| Worksheet format | Markdown with HTML comment metadata | Human-readable, editor-agnostic, machine-parseable |
| Code exercise testing | Standalone test file with assert statements | No pytest dependency; works anywhere Python is installed |
| Evaluation output | Unified JSON structure for all modalities | Consistent state updates regardless of exercise type |
| Modality tracking | Per-concept `modality_performance` in progress.json | Enables data-driven modality adaptation in v2 |
| File-based exercise pause | Learner signals completion; agent does not poll | Simpler, more reliable, respects learner workflow |
| Modality mixing in sessions | Conversation-first, file-based exercises for variety | Conversation is fastest for reviews; file-based adds depth for practice |
| v1 implementation | Instructions in SKILL.md, not Python code | Avoids complexity; the agent interprets the decision matrix contextually |

---

## Interaction Flow Diagram (Full Session)

```
User: /study
  |
  v
[Load state] --> [Plan session]
  |
  v
[For each plan item:]
  |
  +-- type=new? --> [TEACH phase: conversation]
  |                    |
  |                    v
  |                 [CHECK UNDERSTANDING: conversation]
  |                    |
  |                    v
  |                 [SELECT MODALITY from decision matrix]
  |                    |
  |                    +-- worksheet? --> [Write file] --> [Wait] --> [Read & evaluate]
  |                    +-- conversation? --> [Ask question] --> [Evaluate response]
  |                    +-- code? --> [Write files] --> [Wait] --> [Run tests & evaluate]
  |                    +-- long_form? --> [Pose question] --> [Wait] --> [Evaluate]
  |                    +-- image? --> [Assign task] --> [Wait] --> [Read image & evaluate]
  |                    |
  |                    v
  |                 [MAP to FSRS rating]
  |                    |
  |                    v
  |                 [UPDATE state: concept progress, modality performance, errors]
  |
  +-- type=review? --> [SELECT MODALITY (prefer conversation for speed)]
  |                    |
  |                    v
  |                 [Exercise + Evaluate + Update state]
  |
  +-- type=assess? --> [HIGHER BLOOM exercise]
                       |
                       v
                    [Exercise + Evaluate + Update state]

  [After all items:]
  |
  v
[Session summary] --> [Save session log] --> [Preview next session]
```
