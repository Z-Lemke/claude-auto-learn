# Adaptive Learning Systems: State of the Art Research

**Date**: 2026-02-20
**Purpose**: Comprehensive survey of adaptive learning architectures, knowledge modeling, assessment strategies, adaptation mechanisms, and cross-domain patterns -- to inform the design of an adaptive teaching agent.
**Sources**: Academic literature, ed-tech engineering blogs, open-source projects, and industry practice through early 2025.

---

## Table of Contents

1. [Adaptive Learning Architectures](#1-adaptive-learning-architectures)
2. [Knowledge Modeling](#2-knowledge-modeling)
3. [Assessment Strategies](#3-assessment-strategies)
4. [Adaptation Mechanisms](#4-adaptation-mechanisms)
5. [Generalization Across Domains](#5-generalization-across-domains)
6. [Open-Source Projects and Tools](#6-open-source-projects-and-tools)
7. [Design Implications for an LLM-Based Teaching Agent](#7-design-implications-for-an-llm-based-teaching-agent)
8. [Key References](#8-key-references)

---

## 1. Adaptive Learning Architectures

### 1.1 Core Components of an Adaptive Learning System

Every adaptive learning system, regardless of domain, shares a common abstract architecture with these interacting components:

```
+-------------------+     +--------------------+     +-------------------+
|   LEARNER MODEL   |<--->|  ADAPTATION ENGINE  |<--->|   DOMAIN MODEL    |
| (what they know)  |     | (what to do next)   |     | (what exists to   |
|                   |     |                     |     |  learn)           |
+-------------------+     +--------------------+     +-------------------+
        ^                         |                          ^
        |                         v                          |
        |                 +--------------------+             |
        +---------------->|  CONTENT / TASK    |<------------+
                          |  SELECTION ENGINE  |
                          +--------------------+
                                  |
                                  v
                          +--------------------+
                          |  PRESENTATION /    |
                          |  INTERACTION LAYER |
                          +--------------------+
```

**Learner Model**: Maintains a probabilistic estimate of what the learner knows, their learning rate, common error patterns, and affective state. Updated continuously from assessment signals.

**Domain Model**: A structured representation of the subject matter -- concepts, skills, prerequisite relationships, difficulty levels, and associated content/exercises. Often a graph.

**Adaptation Engine**: The decision-making core. Given the learner model and domain model, it decides *what to teach next*, *at what difficulty*, *in what format*, and *when to review*.

**Content/Task Selection Engine**: Selects or generates specific exercises, explanations, or tasks. In classical systems, this selects from a pre-authored item bank. In LLM-based systems, this can generate content on the fly.

**Presentation/Interaction Layer**: The UI and interaction patterns -- how content is delivered and how learner responses are captured.

### 1.2 Duolingo's Architecture (Birdbrain)

Duolingo is perhaps the most sophisticated production adaptive learning system. Key architectural insights:

**Birdbrain (Session Generator)**:
- Uses a bandit-based optimization approach to select exercises within a lesson
- Models each learner-word pair with a half-life regression (HLR) model that predicts the probability of recall as a function of time since last practice
- Each exercise is selected to maximize learning while keeping engagement high
- The model was described in Settles & Meeder (2016) "A Trainable Spaced Repetition Model for Language Flashcards" and has been continuously evolved

**Half-Life Regression (HLR)**:
- Models memory as exponential decay: P(recall) = 2^(-delta/h), where delta is time elapsed and h is the half-life
- The half-life h is modeled as a function of features: number of previous exposures, number of correct/incorrect responses, time since last exposure, lexeme difficulty
- Trained on billions of learner interactions
- Advantages over SM-2: data-driven, per-item personalization, continuous rather than discrete intervals

**Multi-Armed Bandit for Exercise Selection**:
- Each exercise type (translate, listen, speak, match, etc.) is an arm
- Reward signal is a composite of correctness, engagement, and long-term retention
- Thompson Sampling or Upper Confidence Bound (UCB) algorithms for exploration/exploitation
- Allows Duolingo to A/B test exercise formats at the individual learner level

**Content Architecture**:
- Courses are organized as a tree/DAG of skills
- Each skill contains a set of lexemes (words) and grammar concepts
- Exercises are generated from sentence templates, not fully handcrafted
- The system can create novel exercises by combining templates with target vocabulary

**Key Takeaway**: Duolingo's power comes from *massive data* (hundreds of millions of users) feeding relatively simple but well-calibrated statistical models. The learning science is encoded in the objective function, not in complex rule systems.

### 1.3 Khan Academy's Architecture (Khanmigo / Mastery System)

Khan Academy takes a mastery-based approach:

**Mastery System**:
- Content organized into courses > units > lessons > exercises
- Each skill has a mastery level: Not Started, Familiar, Proficient, Mastered
- Advancement requires demonstrating mastery through consecutive correct answers
- Mastery can decay over time (spaced review)

**Knowledge Map**:
- Skills are connected in a prerequisite graph
- The system recommends skills based on prerequisite completion and mastery decay
- Originally visualized as a literal map; now embedded in course structure

**Khanmigo (LLM Integration, 2023-2024)**:
- GPT-4-powered tutoring layer on top of existing mastery system
- The LLM does NOT replace the adaptive engine -- it augments it
- Khanmigo provides Socratic tutoring: asks questions rather than giving answers
- Uses structured prompts that include the learner's current exercise, mastery level, and common misconceptions
- The mastery system provides *what to teach*; the LLM provides *how to teach it*

**Key Takeaway**: Khan Academy demonstrates that LLMs work best as a *tutoring interface* layered on top of a structured adaptive system, not as a replacement for curriculum structure.

### 1.4 Anki / Open Spaced Repetition

Anki represents the purest spaced repetition architecture:

**Architecture**:
- Flat card-based model (no prerequisite graph)
- Each card has its own scheduling state
- The scheduler is the entire adaptation engine
- No domain model beyond card content and tags
- User-generated content (or shared decks)

**SM-2 Algorithm (Original Anki)**:
- Each card has: interval, ease factor, repetition count
- After review, ease factor adjusted by quality of response (0-5 scale)
- New interval = old interval * ease factor
- Simple, intuitive, but has known problems (ease factor death spiral, no per-user calibration)

**FSRS (Free Spaced Repetition Scheduler, 2022-2024)**:
- Developed by Jarrett Ye (open-spaced-repetition project)
- Replaced SM-2 as Anki's default scheduler in 2024
- Based on the DSR (Difficulty, Stability, Retrievability) model of memory
- Significant improvement in prediction accuracy over SM-2

**Key Takeaway**: Anki/FSRS shows that even without complex domain modeling, a well-calibrated memory model alone provides enormous learning value. But it's limited to memorization -- it doesn't model understanding or skill transfer.

### 1.5 Intelligent Tutoring Systems (ITS) -- Classical Approach

The academic ITS tradition (Carnegie Learning, AutoTutor, ALEKS) provides the deepest theoretical foundation:

**Cognitive Tutors (Carnegie Learning)**:
- Based on ACT-R cognitive architecture (John Anderson, CMU)
- Explicit cognitive model of the skill being taught
- Model tracing: the system maintains a model of the student's problem-solving process
- Knowledge tracing: Bayesian estimation of which knowledge components the student has mastered
- Can provide targeted hints based on where the student is in their solution process

**ALEKS (Assessment and Learning in Knowledge Spaces)**:
- Based on Knowledge Space Theory (Doignon & Falmagne, 1999)
- Models the domain as a partially ordered set of knowledge states
- Uses adaptive assessment to place the learner in the knowledge space
- Identifies the "outer fringe" -- concepts the student is ready to learn next
- Mathematically rigorous but computationally expensive for large domains

**AutoTutor**:
- Dialogue-based tutoring system
- Uses latent semantic analysis (LSA) to evaluate student responses
- Follows a tutoring dialogue framework: question, student response, short feedback, pump for elaboration, hint, prompt, assertion
- Closest classical analog to what an LLM-based tutor would do

**Key Takeaway**: Classical ITS work provides the theoretical gold standard. The challenge has always been the authoring bottleneck -- building cognitive models and content for each domain is extremely expensive. LLMs may finally solve the authoring problem.

### 1.6 LLM-Native Adaptive Systems (2023-2025 Wave)

The newest generation uses LLMs as the core of the adaptation engine:

**Architectures emerging in 2024-2025**:

1. **LLM-as-Tutor with Structured Backend**: (Khanmigo pattern)
   - Traditional adaptive engine handles sequencing/scheduling
   - LLM handles dialogue, explanation, hint generation
   - Structured data (learner model, domain model) passed to LLM as context
   - Most production-proven approach

2. **LLM-as-Full-Adaptive-Engine**:
   - LLM makes all decisions: what to teach, how to assess, when to advance
   - Learner state maintained in LLM context or external memory
   - Risk: LLMs are poor at consistent state tracking and numerical reasoning
   - Benefit: Zero authoring cost, infinite domain flexibility

3. **LLM + Retrieval-Augmented Generation (RAG) for Content**:
   - Domain knowledge stored in vector databases
   - LLM generates exercises and explanations from retrieved content
   - Allows teaching from arbitrary source material (textbooks, docs, papers)

4. **Hybrid: LLM for Generation, Classical Models for Scheduling**:
   - FSRS or Bayesian Knowledge Tracing for *when* to review
   - LLM for *what* to present and *how* to teach
   - Structured knowledge graph for *sequencing*
   - Arguably the best of all worlds

**Key Takeaway**: The hybrid approach (pattern 4) is the most promising for a teaching agent. Use well-understood algorithms where they work (memory scheduling, knowledge tracing), and use the LLM where it excels (natural language explanation, exercise generation, Socratic dialogue).

---

## 2. Knowledge Modeling

### 2.1 Knowledge Graphs and Prerequisite Maps

**What they are**: A directed acyclic graph (DAG) where nodes are concepts/skills and edges represent prerequisite relationships ("you must understand X before Y").

**Representation**:
```
concept:
  id: "linear_equations"
  name: "Solving Linear Equations"
  prerequisites: ["algebraic_expressions", "equality_properties"]
  skills: ["isolate_variable", "combine_like_terms", "check_solution"]
  difficulty: 0.4  # normalized difficulty
  bloom_level: "apply"
  estimated_time_minutes: 45
```

**Graph properties that matter**:
- **Depth**: How many prerequisite layers exist. Deeper graphs allow more precise placement but are harder to author.
- **Width**: How many parallel concepts exist at each level. Wider graphs allow more learner choice.
- **Density**: How interconnected concepts are. Dense graphs model reality better but make sequencing harder.
- **Granularity**: Coarse-grained (whole topics) vs fine-grained (individual skills). Fine-grained enables better adaptation but requires more modeling effort.

**Approaches to building prerequisite graphs**:
1. **Expert-authored**: Domain experts manually specify prerequisites. High quality but expensive and doesn't scale.
2. **Data-mined**: Analyze learner performance data to infer prerequisites. If learners who master A first do better on B, A is likely a prerequisite for B. Used by ALEKS.
3. **LLM-generated**: Ask an LLM to generate prerequisite structures for a domain. Surprisingly effective for well-known domains. Quality degrades for niche topics.
4. **Hybrid**: LLM generates initial graph, expert refines, data validates over time.

**For an LLM-based teaching agent**: Option 4 (hybrid) is most practical. The LLM can generate an initial knowledge graph from a curriculum description or textbook, then refine it based on observed learner performance.

### 2.2 Spaced Repetition Algorithms

Spaced repetition schedules review of learned material at increasing intervals to combat forgetting. The core insight is that memories decay exponentially but each successful recall strengthens the memory trace.

#### SM-2 (SuperMemo Algorithm 2, 1987)

The original widely-used algorithm, still the basis of many systems.

**State per item**:
- `repetition_count`: Number of successful consecutive reviews
- `ease_factor`: Multiplier for interval calculation (default 2.5, min 1.3)
- `interval`: Days until next review

**Algorithm**:
```
After a review with quality q (0-5):
  if q < 3:  # Failed
    repetition_count = 0
    interval = 1
  else:  # Passed
    if repetition_count == 0: interval = 1
    elif repetition_count == 1: interval = 6
    else: interval = interval * ease_factor
    repetition_count += 1

  ease_factor = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
  ease_factor = max(ease_factor, 1.3)
```

**Known problems**:
- Ease factor hell: Cards that are slightly hard get progressively shorter intervals, creating a death spiral
- No per-user calibration: Same algorithm for fast and slow learners
- No account for actual elapsed time since last review (only scheduled time)
- Discrete quality ratings (0-5) lose nuance

#### FSRS (Free Spaced Repetition Scheduler, v4/v5, 2023-2024)

Developed by Jarrett Ye, based on the DSR memory model. Adopted as Anki's default scheduler.

**Memory Model (DSR)**:
Three variables describe the state of a memory:
- **D (Difficulty)**: Inherent difficulty of the item (0-10 scale). Stable-ish property.
- **S (Stability)**: How strong the memory is, measured in days. After a successful review, stability increases. This is the "half-life" of the memory.
- **R (Retrievability)**: Probability the item can be recalled right now. Decays exponentially: R = (1 + t/(9*S))^(-1), where t is days since last review.

**Key formulas**:

Initial stability (first review):
```
S_0 = w_0 * exp(w_1 * (rating - 1))  # where w_0, w_1 are learned parameters
```

Stability after successful recall:
```
S'_recall = S * (1 + exp(w_2) * (11 - D) * S^(-w_3) * (exp(w_4 * (1 - R)) - 1))
```

Stability after failed recall (lapse):
```
S'_lapse = w_5 * D^(-w_6) * (S^w_7 - 1) * exp(w_8 * (1 - R))
```

Difficulty update:
```
D' = D + w_9 * (rating - 3)  # Adjusted toward mean to prevent extreme values
```

**Parameters**: 19 weights (w_0 through w_18), trained on user review data via gradient descent.

**Key advantages over SM-2**:
- Continuous retrievability model (not discrete intervals)
- Per-user parameter optimization (personalizes to individual learning speed)
- Accounts for actual elapsed time, not just scheduled time
- Mathematically grounded in memory research
- Open source with active development

**FSRS v5 improvements (2024)**:
- Better handling of same-day reviews
- Short-term memory component for items reviewed within same session
- Improved parameter optimization convergence

**For a teaching agent**: FSRS is the clear choice for scheduling review. It's open source, well-validated, and can be personalized per learner. The 19-parameter model can be initialized from population defaults and tuned as individual data accumulates.

#### Comparison Table

| Feature | SM-2 | FSRS | HLR (Duolingo) |
|---------|------|------|-----------------|
| Memory model | Ease factor + interval | DSR (Difficulty, Stability, Retrievability) | Exponential decay with half-life |
| Personalization | None (same for all users) | Per-user parameter optimization | Per-user, per-item |
| Training data needed | None (rule-based) | ~100 reviews for personalization | Millions of reviews |
| Handles actual vs scheduled time | No | Yes | Yes |
| Open source | Yes | Yes | No (proprietary) |
| Best for | Simple implementations | Individual learners | Platforms with massive data |

### 2.3 Bayesian Knowledge Tracing (BKT)

BKT is the standard approach for modeling skill mastery (not just memory) in adaptive learning.

**Model**: Hidden Markov Model where the hidden state is whether the learner has "learned" a skill.

**Four parameters per skill**:
- **P(L_0)**: Prior probability the skill is already known
- **P(T)**: Probability of transitioning from unlearned to learned on each practice opportunity
- **P(G)**: Probability of guessing correctly when the skill is not known
- **P(S)**: Probability of slipping (incorrect answer when the skill IS known)

**Update rule** (after observing correct/incorrect):
```
P(L_t | correct) = P(L_t-1) * (1 - P(S)) / P(correct)
P(L_t | incorrect) = P(L_t-1) * P(S) / P(incorrect)
P(L_t+1) = P(L_t | observation) + (1 - P(L_t | observation)) * P(T)
```

**Mastery threshold**: Typically, a skill is considered "mastered" when P(L) > 0.95.

**Extensions**:
- **Individualized BKT**: Per-learner parameters (especially P(L_0) and P(T))
- **Contextual BKT**: Parameters depend on context (time of day, exercise type, etc.)
- **Deep Knowledge Tracing (DKT)**: Replace BKT's HMM with a recurrent neural network. Better accuracy on large datasets but less interpretable.

**For a teaching agent**: BKT is excellent for tracking *skill mastery* (vs. FSRS for *memory retention*). A teaching agent should use both: BKT to determine if a concept is understood, FSRS to schedule review of known concepts.

### 2.4 Bloom's Taxonomy and Mastery Levels

Bloom's Taxonomy provides a framework for categorizing the *depth* of understanding:

```
6. Create      - Can produce new work using the knowledge
5. Evaluate    - Can justify a decision or course of action
4. Analyze     - Can distinguish between parts, identify relationships
3. Apply       - Can use knowledge in new situations
2. Understand  - Can explain ideas or concepts
1. Remember    - Can recall facts and basic concepts
```

**Practical application in adaptive learning**:
- Map each concept to a target Bloom level (e.g., "Variable assignment" targets "Apply", "Algorithm design" targets "Create")
- Design assessments that probe specific Bloom levels
- Track learner progress through levels, not just binary mastery
- Adapt content difficulty by Bloom level: start with Remember/Understand, advance to Apply/Analyze

**Implementation as a state machine per concept**:
```
states: [not_introduced, remember, understand, apply, analyze, evaluate, create]
transitions:
  - from: remember, to: understand, trigger: passes_comprehension_check
  - from: understand, to: apply, trigger: solves_novel_problem
  - from: apply, to: analyze, trigger: identifies_components_and_relationships
  ...
```

**For a teaching agent**: Bloom levels provide a useful vocabulary for the LLM to reason about learning progression. The agent can be prompted: "The learner is at the 'Understand' level for recursion. Generate an 'Apply'-level exercise to test if they can advance."

### 2.5 Zone of Proximal Development (ZPD)

Vygotsky's ZPD is the range of tasks that a learner can accomplish with guidance but not independently. This is the *optimal learning zone*.

**Three zones**:
1. **Can do independently**: Already mastered -- review only
2. **ZPD**: Can do with scaffolding -- this is where learning happens
3. **Cannot do even with help**: Too advanced -- prerequisites not met

**Operationalizing ZPD in an adaptive system**:
- Concepts where mastery is 0.3-0.7 are likely in the ZPD
- Concepts with all prerequisites mastered but concept itself not mastered are prime ZPD candidates
- The "outer fringe" in Knowledge Space Theory is essentially the ZPD

**Difficulty calibration within ZPD**:
- Target success rate of ~80% (Ebbinghaus; also called the "85% rule" from Wilson et al., 2019)
- Too easy (>95% success) = boredom, no learning signal
- Too hard (<60% success) = frustration, disengagement
- The "desirable difficulty" sweet spot varies per learner but 80% is a robust default

**For a teaching agent**: The ZPD concept translates to a concrete heuristic: always teach from the "frontier" of the knowledge graph where prerequisites are met but mastery isn't established, and calibrate difficulty to ~80% success rate.

### 2.6 Composite Learner Model Schema

Combining all the above, a comprehensive learner model for a teaching agent might look like:

```json
{
  "learner_id": "uuid",
  "global_parameters": {
    "learning_rate": 0.7,
    "fsrs_weights": [0.4, 0.6, ...],
    "preferred_explanation_style": "examples_first",
    "session_duration_preference_minutes": 25,
    "frustration_threshold": 0.55,
    "engagement_decay_rate": 0.02
  },
  "concept_states": {
    "linear_equations": {
      "bloom_level": "apply",
      "bkt_mastery_probability": 0.87,
      "fsrs_state": {
        "difficulty": 3.2,
        "stability": 14.5,
        "last_review": "2025-01-15T10:30:00Z",
        "retrievability": 0.82
      },
      "error_patterns": ["sign_errors", "distribution_mistakes"],
      "total_practice_count": 23,
      "last_session": "2025-01-15T10:30:00Z"
    }
  },
  "session_history": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "duration_minutes": 22,
      "concepts_practiced": ["linear_equations", "inequalities"],
      "exercises_attempted": 12,
      "exercises_correct": 9,
      "engagement_signal": "high"
    }
  ]
}
```

---

## 3. Assessment Strategies

### 3.1 Diagnostic Placement Tests

**Purpose**: Determine what the learner already knows before instruction begins.

**Approaches**:

**Adaptive placement (ALEKS-style)**:
- Start with a medium-difficulty item
- If correct, increase difficulty; if incorrect, decrease
- Items are selected to maximally partition the knowledge space
- Typically 15-30 items to place a learner across an entire course
- Based on Knowledge Space Theory: each response eliminates incompatible knowledge states

**Prerequisite probing**:
- Test prerequisite skills before introducing new material
- If prerequisites aren't met, redirect to prerequisite content
- Cheaper than full placement: only tests what's needed for the next unit

**Self-report with calibration**:
- Ask the learner what they already know
- Verify with a few targeted questions per claimed skill
- Efficient when learners are honest and have reasonable self-assessment
- Research shows self-report is unreliable for novices but reasonable for intermediates

**For a teaching agent**: Combine self-report ("What do you already know about X?") with brief targeted probing. An LLM can generate calibration questions on the fly: "You said you understand recursion. Can you explain what happens when this function is called with n=3?" The LLM can evaluate the response for understanding signals.

### 3.2 Formative Assessment (During Learning)

**Purpose**: Continuously gauge understanding during instruction to adapt in real time.

**Techniques**:

**Interleaved practice problems**:
- Present problems between explanations
- Immediate feedback on each response
- Adjust explanation depth based on error patterns

**Think-aloud prompts**:
- "Explain your reasoning"
- "What would happen if we changed X to Y?"
- "Can you predict the output before running this?"
- LLMs excel at evaluating these open-ended responses

**Error analysis**:
- Don't just track right/wrong -- categorize *what kind* of error
- Systematic errors (consistent misconception) vs. careless errors (slip)
- Systematic errors require re-teaching; slips require practice
- An LLM can analyze free-text responses to identify specific misconceptions

**Confidence-weighted responses**:
- Ask the learner how confident they are in their answer
- High confidence + correct = strong mastery signal
- High confidence + incorrect = dangerous misconception (high priority to correct)
- Low confidence + correct = fragile knowledge (needs reinforcement)
- Low confidence + incorrect = expected (still learning)

**Socratic probing**:
- Instead of telling the answer, ask guiding questions
- "What's the first step?" "What pattern do you notice?" "Why does that happen?"
- If the learner can arrive at the answer with minimal hints, understanding is deeper
- Track hint count as a signal: fewer hints = better understanding

**For a teaching agent**: This is where LLMs shine. The agent can engage in natural dialogue, evaluate free-text responses, identify misconceptions from explanations, and use Socratic questioning -- all things that were impossible in pre-LLM systems. The key is to feed these assessment signals back into the learner model.

### 3.3 Summative Assessment (After Units)

**Purpose**: Determine whether a unit's learning objectives have been met.

**Approaches**:

**Mastery checks**:
- Require N consecutive correct answers (Khan Academy uses 3-5)
- Items drawn from the full unit's skill set
- Must be done without hints or scaffolding

**Transfer tasks**:
- Present problems that require applying the concept in a novel context
- Tests whether the learner truly understands or just pattern-matched
- Example: After learning sorting algorithms, ask to design a sorting approach for a novel constraint

**Synthesis tasks**:
- Combine multiple concepts from the unit
- "Write a function that uses both recursion and dynamic programming to solve X"
- Tests integration of knowledge, not just isolated skills

**Spaced summative assessment**:
- Re-test after a delay (1 week, 1 month)
- Tests long-term retention, not just session memory
- If performance degrades, schedule targeted review

**For a teaching agent**: LLM-generated summative assessments are powerful because they can create novel problems (preventing memorization of specific test items). The agent should generate problems that require the target Bloom level, evaluate responses for understanding depth, and use this to update mastery estimates.

### 3.4 Item Response Theory (IRT)

IRT provides a mathematical framework for calibrating assessment items and estimating learner ability.

#### Models

**1-Parameter (1PL / Rasch Model)**:
```
P(correct | theta, b) = 1 / (1 + exp(-(theta - b)))
```
- theta: learner ability
- b: item difficulty
- All items equally discriminating

**2-Parameter (2PL)**:
```
P(correct | theta, a, b) = 1 / (1 + exp(-a * (theta - b)))
```
- a: discrimination (how sharply the item separates high/low ability)
- High discrimination items are more informative

**3-Parameter (3PL)**:
```
P(correct | theta, a, b, c) = c + (1 - c) / (1 + exp(-a * (theta - b)))
```
- c: guessing parameter (lower asymptote)
- For multiple choice: c ~ 1/number_of_options

#### Application in Adaptive Testing (CAT)

**Computerized Adaptive Testing (CAT)** uses IRT to select maximally informative items:

1. Start with an initial ability estimate (theta_0 = 0)
2. Select the item that provides maximum information at current theta estimate
3. After response, update theta using maximum likelihood or Bayesian estimation
4. Repeat until stopping criterion is met (standard error < threshold, or max items reached)

**Item Information Function**:
```
I(theta) = a^2 * P(theta) * (1 - P(theta))
```
Items are most informative when P(correct) is near 0.5 for that learner -- i.e., the item is at the learner's ability level.

**For a teaching agent**: Pure IRT requires pre-calibrated item banks, which we won't have for LLM-generated content. However, the *principles* apply:
- Items are most informative at the learner's boundary
- Track item difficulty and discrimination over time
- Use Bayesian ability estimation to update the learner model after each response
- The LLM can be prompted to generate items at a target difficulty level

#### Practical IRT for Dynamic Content

Since an LLM-based system generates novel items rather than drawing from a fixed bank, we need a modified approach:

1. **Prompt-calibrated difficulty**: Ask the LLM to generate an item at difficulty level X (on a defined scale). Validate by checking learner success rates.
2. **Post-hoc calibration**: Track success rates for generated items and use this to calibrate the LLM's difficulty targeting.
3. **Simplified ability tracking**: Use a running Bayesian estimate of ability per skill, updated by each item response. Don't need full IRT parameter estimation.

---

## 4. Adaptation Mechanisms

### 4.1 When to Advance vs. Remediate

**Mastery-based gating**:
- Advance when BKT mastery probability > threshold (typically 0.95)
- Remediate when mastery probability decreases or stagnates
- Never advance past unmastered prerequisites

**Trend-based detection**:
```
recent_performance = weighted_mean(last_5_responses)
if recent_performance > 0.85 and mastery > 0.7:
    advance()
elif recent_performance < 0.5 or mastery_decreasing:
    remediate()
else:
    continue_practice()
```

**Time-aware advancement**:
- If a learner has been stuck on a concept for too long (X sessions), consider:
  - Breaking the concept into smaller pieces
  - Trying a different explanation approach
  - Backing up to a prerequisite
  - Temporarily switching topics (interleaving) to avoid frustration

**Advancement strategies**:
1. **Linear**: Complete concept A, then concept B (simple but rigid)
2. **Mastery-gated DAG traversal**: Unlock concepts whose prerequisites are mastered (flexible, recommended)
3. **Learner-choice within frontier**: Present all available concepts, let learner choose (motivation boost)
4. **Interleaved**: Mix practice of old and new concepts (better for transfer but harder to manage)

### 4.2 Detecting Struggle vs. Mastery

**Struggle signals**:
- Increasing error rate over recent items (not just a single miss)
- Response time increasing (thinking harder, or disengaging)
- Repeated same-type errors (persistent misconception)
- Requesting more hints
- Shorter sessions (disengagement)
- Explicit frustration signals ("I don't get this", "this is too hard")

**Mastery signals**:
- Consistent correct responses (3-5 in a row)
- Decreasing response time (automaticity developing)
- Correct responses on novel/transfer problems
- Can explain reasoning coherently
- Self-corrects errors without prompting

**Distinguishing types of struggle**:

| Signal | Likely Cause | Appropriate Response |
|--------|-------------|---------------------|
| Consistent errors on one sub-skill | Missing prerequisite | Back up to prerequisite |
| Random errors across skills | Carelessness or fatigue | Suggest break, slow down |
| Correct but slow | Developing fluency | Continue practice, increase time pressure gradually |
| Wrong approach, right direction | Partial understanding | Scaffolded hints, worked example |
| Completely lost | Major gap | Reteach from scratch with different approach |
| Correct but can't explain why | Surface-level memorization | Probe understanding, increase Bloom level |

**For a teaching agent**: An LLM can detect nuanced struggle signals from natural language that classical systems can't: tone, confusion in explanations, vague language, repeated asking of similar questions. This is a major advantage.

### 4.3 Topic Pivoting and Interleaving

**When to pivot to a different topic**:
- Learner has been struggling for >10 minutes on same concept
- Frustration detected (lowering engagement)
- Learner explicitly asks to switch
- Current concept depends on a prerequisite that isn't as strong as estimated

**Interleaving research** (Rohrer & Taylor, 2007; Dunlosky et al., 2013):
- Mixing practice of different concepts (interleaving) produces better long-term retention than blocked practice (one concept at a time)
- Especially effective for discrimination tasks (e.g., telling apart similar concepts)
- Harder for learners (feels less productive) but more effective
- Optimal mix: ~70% new concept, ~30% interleaved review of recent concepts

**Implementation for interleaving**:
```
session_plan:
  - 3 items: current_concept (new material)
  - 1 item: recently_mastered_concept (review)
  - 3 items: current_concept (practice)
  - 1 item: different_recent_concept (review)
  - 2 items: current_concept (assessment)
```

### 4.4 Scaffolding and Hint Sequences

**Progressive hint framework**:
1. **Metacognitive prompt**: "What's the first step you would take?"
2. **Strategic hint**: "Think about what operation would isolate the variable."
3. **Specific hint**: "Try subtracting 3 from both sides."
4. **Worked step**: "If we subtract 3 from both sides, we get: x + 3 - 3 = 7 - 3, so x = 4"
5. **Full worked example**: Complete solution with explanation

**Scaffolding fading**: As the learner demonstrates mastery, provide fewer hints earlier:
- Session 1: Hints at level 2-3
- Session 3: Hints at level 1-2
- Session 5: No hints, independent practice

**For a teaching agent**: The LLM can dynamically generate hint sequences at any level. Track which hint level was needed for each item to inform the learner model. If the learner consistently needs level 3+ hints, mastery probability should be lowered.

### 4.5 Adaptation Decision Framework

A complete adaptation cycle:

```
function adapt(learner_model, domain_model, session_state):
  # 1. Select concept
  frontier = get_zpd_frontier(learner_model, domain_model)
  if session_state.current_concept in frontier and not should_pivot():
    concept = session_state.current_concept
  else:
    concept = select_concept(frontier, learner_model)

  # 2. Select exercise type and difficulty
  bloom_target = learner_model.concepts[concept].bloom_level + 1
  target_difficulty = calibrate_for_80_percent_success(learner_model, concept)
  exercise = generate_exercise(concept, bloom_target, target_difficulty)

  # 3. Present and assess
  response = present_to_learner(exercise)
  assessment = evaluate_response(response, exercise)

  # 4. Update learner model
  update_bkt(learner_model, concept, assessment)
  update_fsrs(learner_model, concept, assessment)
  update_error_patterns(learner_model, concept, assessment)

  # 5. Decide next action
  if should_advance(learner_model, concept):
    advance_bloom_level(learner_model, concept)
  elif should_remediate(learner_model, concept):
    remediate(learner_model, concept)
  elif should_interleave(session_state):
    switch_to_review_item()
  else:
    continue_practice()
```

---

## 5. Generalization Across Domains

### 5.1 Domain Classification

Different learning domains have fundamentally different characteristics that affect how adaptation should work:

#### Factual / Declarative Knowledge
**Examples**: Vocabulary, historical dates, anatomy, legal codes
**Characteristics**:
- Discrete, atomic facts
- Can be tested with recall/recognition
- Primary challenge: memory retention
- **Best approach**: Spaced repetition (FSRS)
- **Bloom levels used**: Remember, Understand

#### Procedural / Skill-Based Knowledge
**Examples**: Math procedures, programming syntax, laboratory techniques, music scales
**Characteristics**:
- Sequences of steps
- Requires practice to automate
- Errors in specific steps are diagnostic
- **Best approach**: Cognitive tutoring / model tracing + spaced practice
- **Bloom levels used**: Apply, Analyze

#### Conceptual / Relational Knowledge
**Examples**: Physics principles, software architecture, economic theories, literary analysis
**Characteristics**:
- Deep understanding of relationships and principles
- Transfer to novel situations is the goal
- Can't be tested with simple recall
- **Best approach**: Socratic dialogue, case studies, transfer tasks
- **Bloom levels used**: Understand, Analyze, Evaluate

#### Creative / Generative Knowledge
**Examples**: Writing, design, research, strategy, innovation
**Characteristics**:
- No single correct answer
- Quality is contextual and subjective
- Requires integration of many skills
- **Best approach**: Project-based learning, feedback on artifacts, rubric-based assessment
- **Bloom levels used**: Evaluate, Create

### 5.2 Domain-Agnostic Components

These components work across all domains:

| Component | Domain-Agnostic? | Notes |
|-----------|------------------|-------|
| Prerequisite graph structure | Yes | The representation is universal; content is domain-specific |
| Spaced repetition scheduling | Yes | Memory works the same regardless of domain |
| Mastery estimation (BKT) | Yes | Binary mastery model applies to any skill |
| Bloom's level progression | Yes | Levels apply to any knowledge type |
| ZPD / frontier selection | Yes | Always want to teach at the boundary |
| 80% success rate target | Mostly | May need adjustment for creative domains |
| Hint scaffolding framework | Yes | Progressive disclosure works everywhere |
| Interleaving | Yes | Benefits transfer across domains |
| Session pacing / fatigue detection | Yes | Human attention limits are universal |

### 5.3 Domain-Specific Components

These must be customized per domain:

| Component | Why It's Domain-Specific |
|-----------|------------------------|
| Exercise generation templates | Math problems vs. vocabulary cards vs. code challenges |
| Error taxonomy | Domain-specific misconceptions and error categories |
| Response evaluation rubrics | What counts as "correct" varies enormously |
| Prerequisite graph content | The actual concepts and relationships |
| Target Bloom levels per concept | Some concepts need "Create" level; others need "Remember" |
| Optimal session structure | Language learning benefits from daily short sessions; programming benefits from longer focused sessions |

### 5.4 Language Learning vs. Technical Skills vs. Conceptual Learning

**Language Learning** (Duolingo model):
- Very high item count (thousands of vocabulary items + grammar rules)
- Strong role for spaced repetition (memorization is critical)
- Clear progression: word -> phrase -> sentence -> paragraph -> conversation
- Well-suited to gamification and short sessions
- Assessment is relatively straightforward (translate, transcribe, match)
- *Unique challenge*: Productive vs. receptive skills (speaking vs. listening)

**Technical Skills** (programming, math, engineering):
- Moderate item count but high complexity per item
- Procedural fluency requires practice, but understanding requires explanation
- Clear prerequisite structures (must understand variables before loops)
- Assessment ranges from simple (syntax) to complex (architecture)
- *Unique challenge*: Multiple valid solutions to the same problem

**Conceptual Learning** (science, philosophy, social sciences):
- Lower item count but very deep per concept
- Memorization is insufficient -- must build mental models
- Prerequisites are often fuzzy (not strict ordering)
- Assessment requires evaluating quality of reasoning, not just correctness
- *Unique challenge*: Misconceptions are often deeply held and resistant to correction

### 5.5 The Generalization Pattern

For a domain-agnostic teaching agent, the architecture should:

1. **Use a domain configuration layer** that specifies:
   - Knowledge graph (concepts, prerequisites, Bloom targets)
   - Exercise generation templates/prompts
   - Error taxonomy
   - Assessment rubrics
   - Session structure preferences

2. **Keep the adaptation engine domain-agnostic**:
   - FSRS for memory scheduling
   - BKT for mastery tracking
   - ZPD frontier selection
   - Bloom level progression
   - Struggle detection heuristics

3. **Use the LLM to bridge domains**:
   - Generate exercises from domain-agnostic prompts + domain-specific context
   - Evaluate responses using domain-specific rubrics but generic evaluation framework
   - Provide explanations adapted to the domain's conventions

---

## 6. Open-Source Projects and Tools

### 6.1 Spaced Repetition

- **open-spaced-repetition/fsrs4anki** (GitHub): The reference FSRS implementation. Python library with parameter optimization. Well-documented, actively maintained.
- **open-spaced-repetition/rs-fsrs**: Rust implementation of FSRS. Fast, suitable for server-side deployment.
- **open-spaced-repetition/fsrs-optimizer**: Tool for optimizing FSRS parameters from Anki review data. Useful for understanding how personalization works.
- **Anki**: The gold standard open-source flashcard app. Now uses FSRS by default. Massive community and deck ecosystem.
- **Mnemosyne**: Alternative open-source SRS with research focus.

### 6.2 Knowledge Tracing

- **pyBKT** (GitHub): Python implementation of Bayesian Knowledge Tracing. Well-maintained, used in research.
- **Deep Knowledge Tracing papers**: Piech et al. (2015) original DKT paper. Many extensions: DKVMN, SAKT, AKT, simpleKT.
- **EdNet dataset**: Large public dataset of student interactions from a Korean TOEIC prep platform. Good for training/evaluating knowledge tracing models.
- **Junyi Academy dataset**: Another public educational interaction dataset.

### 6.3 Adaptive Learning Platforms (Open Source)

- **OpenStax Tutor**: Open-source adaptive textbook platform from Rice University. Uses spaced practice and knowledge modeling.
- **Open edX**: MOOC platform with some adaptive features. Extensible plugin architecture.
- **H5P**: Interactive content framework. Can be combined with adaptive backends.

### 6.4 LLM-Based Education Tools (2024-2025)

- **Khanmigo** (Khan Academy): GPT-4-powered tutor. Not open source but well-documented approach.
- **Duolingo Max**: GPT-4-powered features (Explain My Answer, Roleplay). Augments existing adaptive system.
- **Various research projects**: Growing body of work on LLM tutors, with most following the "LLM as interface, structured backend for adaptation" pattern.

---

## 7. Design Implications for an LLM-Based Teaching Agent

### 7.1 Recommended Architecture

Based on this research, the recommended architecture for an adaptive teaching agent:

```
+-----------------------------------------+
|          LLM Teaching Agent             |
|  (Explanation, Socratic Dialogue,       |
|   Exercise Generation, Assessment)      |
+-----------------------------------------+
          |              ^
          v              |
+-----------------------------------------+
|       Adaptation Engine (Code)          |
|  - FSRS memory scheduler               |
|  - BKT mastery tracker                 |
|  - ZPD frontier selector               |
|  - Bloom level progression             |
|  - Struggle detector                   |
+-----------------------------------------+
          |              ^
          v              |
+-----------------------------------------+
|         Learner Model (State)           |
|  - Per-concept FSRS state              |
|  - Per-concept BKT probability         |
|  - Per-concept Bloom level             |
|  - Error pattern history               |
|  - Global learning parameters          |
+-----------------------------------------+
          |              ^
          v              |
+-----------------------------------------+
|         Domain Model (Config)           |
|  - Knowledge graph (DAG)               |
|  - Concept metadata                    |
|  - Exercise generation prompts         |
|  - Assessment rubrics                  |
+-----------------------------------------+
```

### 7.2 Key Design Decisions

1. **LLM as interface, algorithms for scheduling**: Don't ask the LLM to decide *when* to review or *what* to teach next. Use FSRS and BKT for that. Ask the LLM to *generate content* and *evaluate responses* at the difficulty/level specified by the algorithms.

2. **Structured learner model, not LLM memory**: Store the learner model as structured data (JSON), not as LLM conversation context. LLMs lose fidelity on numerical state over long conversations. Pass relevant slices of the learner model to the LLM as context for each interaction.

3. **Domain model as configuration**: Make the domain model a separate, structured artifact (YAML/JSON knowledge graph). This allows the same agent to teach any domain by swapping the domain model.

4. **Hybrid assessment**: Use the LLM to evaluate open-ended responses (explanations, code, essays), but use structured scoring for objective items (multiple choice, numerical answers). Feed both into the same learner model update.

5. **Graceful cold start**: With no learner data, use population defaults for FSRS parameters and BKT priors. Quickly personalize through initial diagnostic assessment. The system should be useful from the first interaction, not requiring hundreds of data points.

### 7.3 Critical Algorithms to Implement

In priority order:

1. **FSRS core** (stability, difficulty, retrievability calculations + scheduling)
2. **Knowledge graph traversal** (prerequisite checking, frontier identification)
3. **BKT updater** (mastery probability estimation per concept)
4. **Session planner** (mix of new material, practice, and review based on learner state)
5. **Struggle detection** (heuristic classifier based on recent performance signals)
6. **Bloom level progression** (state machine for depth-of-understanding tracking)

### 7.4 What Makes This Different from Existing Systems

The LLM provides capabilities no previous adaptive learning system had:

- **Zero authoring cost**: Generate exercises, explanations, and hints for any topic without manual content creation
- **Natural language assessment**: Evaluate "explain your reasoning" responses, not just multiple choice
- **Infinite content variety**: Never show the exact same problem twice
- **Personalized explanations**: Adapt explanation style to the individual (analogies, examples, level of formality)
- **Socratic dialogue**: True back-and-forth tutoring conversation
- **Cross-domain flexibility**: Same system, different domain config, works for any subject

The risk is *over-relying* on the LLM. Without the structured backend (FSRS, BKT, knowledge graph), an LLM tutor would:
- Forget what it taught you last session
- Not know when to review material
- Not track precise mastery levels
- Not maintain consistent difficulty calibration
- Not optimize for long-term retention

The structured backend is what turns a chatbot into a tutor.

### 7.5 Open Questions for Further Research

1. **How to evaluate LLM-generated exercise quality?** Need a way to validate that generated exercises actually target the intended concept and difficulty level.
2. **How to handle learner model persistence across sessions?** JSON state is simple but what about long-term learners with thousands of concept states?
3. **How to build domain models efficiently?** Can the LLM generate a good-enough knowledge graph from a textbook or course syllabus?
4. **How to calibrate BKT parameters without a large learner population?** Individual tutoring doesn't have the data advantage of platforms like Duolingo.
5. **How to detect and correct misconceptions vs. surface errors?** This is where LLM evaluation of explanations could be transformative, but it needs validation.
6. **How to handle motivation and engagement?** Algorithms optimize for learning, but learners also need to *want* to continue. Session pacing, topic variety, and perceived progress all matter.

---

## 8. Key References

### Foundational Papers and Books

- **Corbett, A. T., & Anderson, J. R. (1995)**. "Knowledge tracing: Modeling the acquisition of procedural knowledge." *User Modeling and User-Adapted Interaction*. -- The original BKT paper.
- **Doignon, J.-P., & Falmagne, J.-C. (1999)**. *Knowledge Spaces*. Springer. -- Mathematical foundation for ALEKS-style systems.
- **Embretson, S. E., & Reise, S. P. (2000)**. *Item Response Theory for Psychologists*. -- Comprehensive IRT reference.
- **Piech, C., et al. (2015)**. "Deep Knowledge Tracing." *NeurIPS*. -- Neural network approach to knowledge tracing.
- **Settles, B., & Meeder, B. (2016)**. "A Trainable Spaced Repetition Model for Language Flashcards." *ACL*. -- Duolingo's HLR model.
- **Wilson, R. C., et al. (2019)**. "The Eighty Five Percent Rule for Optimal Learning." *Nature Communications*. -- Evidence for the ~85% success rate sweet spot.
- **Dunlosky, J., et al. (2013)**. "Improving Students' Learning With Effective Learning Techniques." *Psychological Science in the Public Interest*. -- Meta-review of learning techniques including interleaving and spaced practice.
- **Wozniak, P. A. (1990)**. Optimization of repetition spacing in the practice of learning. -- SM-2 algorithm origin.

### FSRS-Specific

- **Ye, J. (2023-2024)**. FSRS algorithm documentation and papers. Available at: github.com/open-spaced-repetition
- **Ye, J., et al. (2024)**. "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling." *KDD*. -- Theoretical grounding for FSRS.

### LLM + Education (2023-2025)

- **Khan Academy Khanmigo documentation and blog posts** (2023-2024). Detailed descriptions of how GPT-4 is integrated with mastery-based learning.
- **Duolingo engineering blog** (2023-2024). Posts on integrating GPT-4 for Explain My Answer and Roleplay features.
- **Kasneci, E., et al. (2023)**. "ChatGPT for Good? On Opportunities and Challenges of Large Language Models for Education." *Learning and Individual Differences*. -- Survey of LLM education applications.
- **Various ArXiv preprints (2024-2025)** on LLM-based tutoring systems, adaptive assessment with LLMs, and knowledge graph generation from LLMs.

### Datasets for Development and Testing

- **EdNet** (Choi et al., 2020): 131M interactions from 784K students. Largest public educational dataset.
- **ASSISTments** (various years): Popular dataset for knowledge tracing research.
- **Junyi Academy**: Taiwanese educational platform dataset.
- **Duolingo SLAM dataset** (2018): Second Language Acquisition Modeling shared task data.

---

*Note: Web search was unavailable during research. This document is based on knowledge of the field through early 2025. Specific claims about 2025-2026 developments should be verified with current sources. The core algorithms (FSRS, BKT, IRT), architectural patterns, and learning science principles described here are well-established and unlikely to have changed significantly.*
