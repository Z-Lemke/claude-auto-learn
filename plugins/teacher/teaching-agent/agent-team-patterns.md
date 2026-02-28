# Agent Team Patterns for Adaptive Teaching

**Date**: 2026-02-22
**Purpose**: Research how multi-agent architectures can improve the teaching agent plugin -- concrete patterns, trade-offs, and recommendations for how agent teams slot into this specific codebase.

---

## Table of Contents

1. [Current Architecture Baseline](#1-current-architecture-baseline)
2. [State of the Art: Multi-Agent Tutoring Systems](#2-state-of-the-art-multi-agent-tutoring-systems)
3. [Claude Code Agent Capabilities](#3-claude-code-agent-capabilities)
4. [Concrete Team Patterns for the Teaching Plugin](#4-concrete-team-patterns-for-the-teaching-plugin)
5. [Trade-off Analysis](#5-trade-off-analysis)
6. [ROI-Ranked Recommendations](#6-roi-ranked-recommendations)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Current Architecture Baseline

### What exists today

The teaching plugin at `/plugins/teacher/` is a single-agent system with four slash commands:

| Command | Skill | What it does |
|---------|-------|-------------|
| `/build-course` | build-course | Intake, knowledge graph generation, diagnostic assessment, course initialization |
| `/study` | study | Adaptive tutoring session: teach new concepts + review old ones via Socratic method |
| `/quiz` | quiz | Pure assessment mode: test mastery, no teaching, no hints |
| `/progress` | progress | Read-only dashboard: mastery levels, recommendations |

**Classical algorithms** (in Python scripts):
- `fsrs.py` -- FSRS v4/v5 spaced repetition scheduler (19-parameter DSR model)
- `planner.py` -- Session planning, knowledge graph traversal (frontier/ZPD selection), mastery checks, Bloom progression, struggle detection, review scheduling
- `state.py` -- JSON-based state management at `~/.claude/teaching/` with atomic writes

**State structure**:
```
~/.claude/teaching/
  courses/<name>/
    knowledge-graph.json    # DAG of concepts, prerequisites, metadata
    curriculum.json         # Unit groupings, progression
    config.json            # Domain type, exercise prompts, rubrics, error taxonomy
  learner/
    profile.json           # Preferences, active courses
    <course>/
      progress.json        # Per-concept FSRS state, Bloom level, mastery score, error history
      sessions/            # Timestamped session logs
```

**Hook**: A lightweight Stop hook (`session-tracker.sh`) detects teaching sessions and logs activity.

### Where the single-agent design breaks down

1. **The tutor grades its own work.** The same agent that teaches a concept generates the exercise, evaluates the response, and updates mastery. This creates systematic bias -- the agent "knows" what it intended to teach and reads comprehension into partial responses. Research confirms this: separate assessment agents catch misunderstandings that tutor agents miss (IntelliCode showed 89.1% hint-assisted success vs 52.4% baseline precisely because assessment was decoupled).

2. **Course building is monolithic.** `/build-course` requires the agent to research pedagogy, generate a knowledge graph, create a curriculum, design exercise prompts, run a diagnostic, and initialize state -- all in sequence, in one context window. This means later steps (diagnostic, curriculum design) happen with a degraded context as the window fills with knowledge graph JSON.

3. **No quality gate on generated content.** Exercises and explanations go directly to the learner. There is no review step checking whether a generated exercise actually tests the intended concept at the intended Bloom level, or whether an explanation is accurate for low-resource domains like Malay.

4. **Session adaptation is reactive only.** The planner decides what to teach based on static progress data at session start. There is no background agent periodically reviewing progress patterns to restructure the curriculum, detect plateaus, or identify concepts that should be resequenced.

---

## 2. State of the Art: Multi-Agent Tutoring Systems

### GenMentor (WWW 2025)

Five-agent framework for goal-oriented learning:

| Agent | Role |
|-------|------|
| **Skill Identifier** | Maps learning goals to required skills using fine-tuned LLM + CoT |
| **Learner Profiler** | Tracks cognitive status, learning preferences, behavioral patterns |
| **Path Scheduler** | Generates learning paths with simulated learner feedback |
| **Content Creator** | RAG-augmented content generation (exploration -> drafting -> integration) |
| **Learner Simulator** | Role-plays the learner to pre-test content effectiveness |

**Key insight**: The Learner Simulator agent tests content *before* presenting it to the real learner. This is a quality gate that catches bad exercises and confusing explanations without wasting the learner's time.

**Results**: 4.6/5.0 skill identification accuracy, 4.71/5.0 path engagement, 80% human preference over baselines.

### IntelliCode (Dec 2025)

Six agents with a centralized StateGraph Orchestrator:

| Agent | Role |
|-------|------|
| **Skill Assessment** | Hybrid evaluation: test execution + semantic review |
| **Learner Profiler** | Mastery deltas, misconception detection, fatigue/velocity patterns |
| **Pedagogical Feedback** | 5-level graduated hinting, calibrated to proficiency |
| **Content Curator** | 40/50/10 policy: due reviews / growth-zone / challenge problems |
| **Progress Synthesizer** | Enhanced SM-2 scheduling with hint-usage and solve-time adjustments |
| **Engagement Orchestrator** | Motivational nudges, rate-limited to prevent spam |

**Key architectural decision**: The StateGraph Orchestrator is the *exclusive writer* to learner state. All agents operate as pure transforms over a shared, versioned state representation. This prevents conflicting writes and enables audit trails.

**Event-driven triggers**:
- `on_submission` -> Skill Assessment -> Learner Profiler -> Pedagogical Feedback
- `on_hint_request` -> Pedagogical Feedback (with proficiency context)
- `on_session_check` -> Content Curator + Engagement Orchestrator
- `on_daily_generation` -> Content Curator generates personalized problem sets
- `on_review_due` -> Progress Synthesizer + Content Curator

**Results**: 5.04% mean mastery gain, 89.1% success with graduated hinting, 90%+ topic coverage diversity.

### EduPlanner (2025)

Three-agent system focused on instructional design:

| Agent | Role |
|-------|------|
| **Question Analyst** | Analyzes educational questions for quality and alignment |
| **Optimizer** | Improves instructional materials iteratively |
| **Evaluator** | Quality-checks generated content against learning objectives |

**Key insight**: A single LLM cannot effectively manage the entire instructional design process. Decomposition into specialized roles with critique loops produces better results than a monolithic approach.

### Common patterns across all systems

1. **Separation of teaching from assessment.** Every production multi-agent tutoring system separates the agent that teaches from the agent that evaluates. The tutor optimizes for explanation quality; the assessor optimizes for honest evaluation. These are conflicting objectives that degrade when combined.

2. **Centralized state, decentralized reasoning.** Shared learner state that all agents read but only one coordinator writes. Agents produce recommendations; the coordinator merges them.

3. **Quality gates before the learner sees content.** A reviewer or simulator agent validates generated exercises and explanations before they reach the learner. This catches hallucinations, difficulty miscalibration, and domain errors.

4. **Event-driven orchestration.** Agents fire in response to events (submission, hint request, session boundary), not continuously. This keeps token costs bounded.

---

## 3. Claude Code Agent Capabilities

### Subagents (Task tool)

The existing codebase avoided subagents due to hook inheritance bug #21460. Current Claude Code documentation shows this has evolved significantly:

**Subagent definition**: Markdown files with YAML frontmatter, stored at:
- `.claude/agents/` (project-level, priority 2)
- `~/.claude/agents/` (user-level, priority 3)
- Plugin's `agents/` directory (priority 4)

**Key capabilities for the teaching plugin**:
- `tools` field restricts what a subagent can do (e.g., read-only for assessment)
- `model` field allows routing to cheaper models (Haiku for simple evaluation)
- `skills` field preloads skill content into the subagent's context
- `hooks` field defines lifecycle hooks scoped to the subagent (solving #21460)
- `memory` field enables persistent memory (`user`, `project`, or `local` scope)
- `permissionMode` controls permission handling
- `maxTurns` caps execution length

**Subagent limitations**:
- Subagents cannot spawn other subagents (no nesting)
- Each invocation creates a fresh context (but can be resumed via agent ID)
- MCP tools unavailable in background subagents
- Background subagents auto-deny unpre-approved permissions

### Agent Teams (Experimental)

Agent teams are a higher-level coordination mechanism:
- One team lead coordinates multiple teammates
- Each teammate has its own independent context window
- Communication via `SendMessage` tool (messages written to JSON inboxes at `~/.claude/teams/`)
- Shared task list with pending/in_progress/completed states and dependency tracking
- Teammates can message each other directly (not just through the lead)

**Key differences from subagents**:

| Aspect | Subagents | Agent Teams |
|--------|-----------|-------------|
| Context | Shares parent session | Independent contexts |
| Communication | Return result only | Bidirectional messaging |
| Coordination | Parent orchestrates | Self-organizing with tasks |
| Persistence | Session-scoped | Team-scoped |
| Parallelism | Yes (background) | Yes (independent sessions) |
| File coordination | Must manage carefully | Must manage carefully |

**Agent teams are experimental** and require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. They are heavy-weight (each teammate is a full Claude session).

### What this means for the teaching plugin

**Subagents are the right tool** for most teaching multi-agent patterns because:
1. Teaching is session-interactive -- the learner is present and waiting for responses
2. Subagent latency is lower than spinning up agent team members
3. Subagent hooks now work (defined in frontmatter, not inherited)
4. Subagent `memory` enables persistent specialized knowledge
5. Subagent `skills` preloading gives domain-specific context

**Agent teams could be useful for course building only**, where the learner is willing to wait while multiple agents research and build in parallel.

---

## 4. Concrete Team Patterns for the Teaching Plugin

### Pattern 1: Tutor + Assessor Separation

**The highest-ROI change.** The teaching agent should never grade its own work.

**Architecture**:
```
Main Agent (Tutor)                    Assessor Subagent
─────────────────                     ──────────────────
Teaches concept
Generates exercise  ─── exercise ──>  Reviews exercise quality
                    <── approved ────  (checks Bloom alignment,
                                       difficulty calibration,
                                       domain accuracy)

Presents exercise to learner
Receives learner response
                    ─── response ──>  Evaluates response
                    <── rating ──────  (FSRS rating, mastery
                                       signal, misconception
                                       detection, error category)
Updates state with
assessor's evaluation
```

**Subagent definition** (`plugins/teacher/agents/assessor.md`):
```yaml
---
name: teaching-assessor
description: Evaluates learner responses for the teaching plugin. Used when a learner submits an answer during study or quiz sessions.
tools: Read, Bash
model: sonnet
maxTurns: 3
skills:
  - study
---
```

**Why this works**:
- The assessor has no "investment" in the learner understanding -- it evaluates honestly
- The assessor can be prompted with structured rubrics from `config.json` without the tutor's conversational context diluting them
- The assessor can detect answer-leaking: "Did the tutor's explanation accidentally reveal the answer?"
- IntelliCode's data shows this pattern yields 89.1% vs 52.4% success rates

**Cost**: One additional subagent invocation per exercise evaluation. ~500-1000 tokens per evaluation with Sonnet. At ~8 exercises per 25-minute session, this adds ~4K-8K tokens of subagent cost per session.

### Pattern 2: Quality Reviewer for Generated Content

**Second-highest ROI.** Every exercise, explanation, and hint should pass through a quality gate before the learner sees it.

**Architecture**:
```
Main Agent (Tutor)                    Reviewer Subagent
─────────────────                     ──────────────────
Generates explanation
for concept X       ─── content ──>   Checks:
                                      - Factual accuracy
                                      - Domain-appropriate language
                                      - Difficulty matches target
                                      - No answer revealed in hints
                                      - Culturally appropriate
                    <── pass/fail ──  If fail: returns specific
                                      issues to fix
Presents to learner
(or regenerates)
```

**When to invoke**:
- New concept explanations (always review)
- Exercise generation (always review for Bloom alignment)
- Hint sequences (spot-check for answer leakage)
- Low-resource language content like Malay (always review for accuracy)

**Subagent definition** (`plugins/teacher/agents/content-reviewer.md`):
```yaml
---
name: content-reviewer
description: Reviews teaching content quality. Checks exercises for Bloom alignment, explanations for accuracy, and hints for answer leakage.
tools: Read, Grep
model: sonnet
maxTurns: 2
memory: user
---
```

**The `memory: user` flag is key**: The reviewer builds persistent knowledge about recurring quality issues across sessions. Over time, it learns what the tutor agent gets wrong (e.g., "for Malay courses, this tutor consistently confuses Indonesian and Malaysian conventions") and focuses its reviews accordingly.

**Cost**: ~300-500 tokens per review. Can be batched (review the full explanation + exercise together). Adds ~3-4 seconds latency per content generation.

### Pattern 3: Parallel Course Building

**Significant ROI for course creation UX.** Currently, `/build-course` takes many minutes because it is sequential. With subagents, independent tasks can run in parallel.

**Architecture**:
```
Main Agent (Orchestrator)
├── Subagent 1: Domain Researcher
│   - WebSearch/WebFetch for domain pedagogy
│   - Identify key concepts, prerequisites
│   - Find common misconceptions
│   - Output: research-summary.md
│
├── Subagent 2: Knowledge Graph Builder (waits for research)
│   - Takes research summary
│   - Generates concept nodes with prerequisites
│   - Validates DAG (no cycles, no orphans)
│   - Output: knowledge-graph.json
│
├── Subagent 3: Exercise Designer (waits for KG)
│   - For each concept, generates exercise prompts
│   - Per-Bloom-level templates
│   - Domain-specific error taxonomy
│   - Output: config.json (exercise_prompts, error_taxonomy)
│
└── Subagent 4: Curriculum Sequencer (waits for KG)
    - Groups concepts into units
    - Determines optimal teaching order
    - Estimates session counts
    - Output: curriculum.json
```

**Parallelism**: Subagents 3 and 4 can run concurrently once the KG is done. Research can partially overlap with the main agent's intake phase.

**Subagent definitions**: Each would be a focused agent with appropriate tools:
- Researcher: `tools: WebSearch, WebFetch, Read`
- KG Builder: `tools: Read, Bash(python3:*)`
- Exercise Designer: `tools: Read, Write`
- Curriculum Sequencer: `tools: Read, Write`

**Cost**: Higher than sequential (3-4 subagent contexts), but the wall-clock time drops significantly. The learner waits 2-3 minutes instead of 8-10.

### Pattern 4: Curriculum Adaptation Agent

**Medium ROI, high long-term value.** A background agent that periodically reviews progress data and suggests curriculum restructuring.

**Architecture**:
```
On session end (triggered by Stop hook):

  Adaptation Subagent
  ────────────────────
  Reads: progress.json, session logs, knowledge-graph.json
  Analyzes:
  - Concepts where mastery is plateauing
  - Prerequisites that should be reordered
  - Concepts that should be split (too many sub-skills lumped together)
  - Concepts that could be merged (artificially granular)
  - Emerging error patterns across concepts
  Writes: adaptation-recommendations.json

On next /study session:
  Main agent reads adaptation-recommendations.json
  Applies or presents recommendations to learner
```

**Subagent definition**:
```yaml
---
name: curriculum-adapter
description: Analyzes learning progress to suggest curriculum restructuring. Run after study sessions to identify plateaus and optimization opportunities.
tools: Read, Bash(python3:*)
model: sonnet
memory: project
maxTurns: 5
---
```

**The `memory: project` flag**: Keeps adaptation history per course/project. Can track multi-session trends.

**Cost**: Runs once per session end, not per interaction. ~2K-4K tokens per analysis. Could be run every 3-5 sessions instead of every session to reduce cost.

### Pattern 5: Domain Expert Subagents

**Variable ROI depending on domain.** Specialized agents with domain-specific knowledge preloaded.

**Example**: For a Malay language course, a "Malay Language Expert" subagent:
```yaml
---
name: malay-expert
description: Expert in Bahasa Melayu (Malaysian Malay). Validates Malay language content, distinguishes from Indonesian, provides cultural context.
tools: Read, WebSearch, WebFetch
model: opus
memory: user
skills:
  - study
---
```

With persistent `memory: user`, this agent builds up verified Malay language patterns, common tutor errors, and domain-specific knowledge across all sessions and courses.

**When to invoke**:
- During content review for language courses (Pattern 2)
- When the learner uses a word/construction the tutor is unsure about
- During course building for language-specific knowledge graph validation

**Cost**: Opus is expensive. Reserve for high-value checks (content generation for low-resource languages). For well-resourced languages (English, Spanish), Sonnet is sufficient.

---

## 5. Trade-off Analysis

### Token Cost

| Pattern | Added tokens/session | Latency impact | Frequency |
|---------|---------------------|----------------|-----------|
| Tutor + Assessor | ~4K-8K | +2-3s per exercise | Every exercise |
| Content Reviewer | ~2K-4K | +3-4s per content gen | Every new content |
| Parallel Course Build | ~20K-40K one-time | Saves 5-7 min wall-clock | Once per course |
| Curriculum Adaptation | ~2K-4K | None (async) | Every 3-5 sessions |
| Domain Expert | ~1K-3K per check | +2-4s per check | Selective |

**Total overhead for a 25-minute study session**: ~8K-16K additional tokens for Patterns 1+2, which is modest compared to the ~50K-100K tokens the main teaching conversation uses.

### Complexity

| Pattern | Complexity | State coordination | Risk |
|---------|-----------|-------------------|------|
| Tutor + Assessor | Low | None -- assessor reads, tutor writes | Low |
| Content Reviewer | Low | None -- reviewer returns pass/fail | Low |
| Parallel Course Build | Medium | File-based handoffs | Medium (merge conflicts) |
| Curriculum Adaptation | Medium | Writes recommendations file | Low (advisory only) |
| Domain Expert | Low | None -- returns validation result | Low |

### Quality Impact

| Pattern | Expected quality improvement | Evidence |
|---------|----------------------------|----------|
| Tutor + Assessor | HIGH -- eliminates self-grading bias | IntelliCode: 89.1% vs 52.4% |
| Content Reviewer | HIGH -- catches hallucinations + difficulty miscalibration | GenMentor Learner Simulator pattern |
| Parallel Course Build | MEDIUM -- better courses due to focused agents | EduPlanner decomposition results |
| Curriculum Adaptation | MEDIUM-HIGH over time -- compounding improvement | Duolingo's data-driven approach |
| Domain Expert | HIGH for low-resource domains, LOW for well-resourced | Malay-specific quality gaps |

---

## 6. ROI-Ranked Recommendations

### Tier 1: Implement immediately (highest ROI)

**1. Tutor + Assessor separation**
- Highest learning quality impact
- Lowest complexity
- Directly addresses the biggest flaw in the current design
- Implementation: Create `agents/assessor.md`, modify study and quiz skills to invoke assessor for response evaluation

**2. Content quality reviewer**
- Catches errors before they reach the learner
- Builds institutional knowledge via persistent memory
- Implementation: Create `agents/content-reviewer.md`, modify study skill to route generated content through reviewer

### Tier 2: Implement for course building

**3. Parallel course building**
- Big UX improvement (faster course creation)
- More complex to implement (file coordination)
- Implementation: Create researcher, KG builder, exercise designer, and curriculum sequencer subagents; modify build-course skill to orchestrate

### Tier 3: Implement after gathering data

**4. Curriculum adaptation agent**
- Requires accumulated session data to be useful
- Best added after 10+ sessions of learner data exist
- Implementation: Create `agents/curriculum-adapter.md`, add post-session trigger

**5. Domain expert subagents**
- Only valuable for specific domains (low-resource languages, niche technical areas)
- Template should exist; instances created per-course
- Implementation: Create template agent, populate per domain need

---

## 7. Implementation Roadmap

### Phase 1: Assessor + Reviewer (minimum viable multi-agent)

**Files to create**:
```
plugins/teacher/
  agents/
    assessor.md              # Response evaluation subagent
    content-reviewer.md      # Content quality gate subagent
```

**Skills to modify**:
- `skills/study/SKILL.md` -- After generating an exercise, invoke content-reviewer. After receiving a learner response, invoke assessor for evaluation. Use assessor's rating (not the tutor's self-assessment) for FSRS updates.
- `skills/quiz/SKILL.md` -- Invoke assessor for all quiz evaluation.

**State changes**: None. Assessor returns structured data (FSRS rating, mastery signal, error category) that the main agent writes to state via existing `state.py` functions. This preserves the single-writer pattern from IntelliCode.

**Hook changes**: None. The assessor is invoked inline during the study/quiz flow, not triggered by hooks.

### Phase 2: Parallel Course Building

**Files to create**:
```
plugins/teacher/
  agents/
    domain-researcher.md     # Research subagent for course building
    kg-builder.md            # Knowledge graph generation subagent
    exercise-designer.md     # Exercise prompt template generator
    curriculum-sequencer.md  # Unit grouping and ordering
```

**Skills to modify**:
- `skills/build-course/SKILL.md` -- Restructure from sequential monolith to orchestrated parallel flow. Main agent handles intake (Steps 1-2), then delegates Steps 3-4 to parallel subagents, then handles Steps 5-7 (diagnostic + initialization).

### Phase 3: Adaptation + Domain Experts

**Files to create**:
```
plugins/teacher/
  agents/
    curriculum-adapter.md    # Post-session curriculum analysis
    domain-expert-template.md  # Template for domain-specific experts
```

**Hook changes**: Modify `hooks/templates/session-tracker.sh` to optionally trigger curriculum adapter after sessions where significant new data was generated (e.g., 5+ exercises completed).

**State additions**: New file `~/.claude/teaching/courses/<name>/adaptation-recommendations.json` for the adapter's output.

### Critical implementation constraints

1. **Single-writer for learner state**: Only the main agent writes to `progress.json`. Subagents return recommendations/evaluations; the main agent applies them. This prevents race conditions and maintains audit trails.

2. **Subagent context must include course config**: The assessor needs `config.json` (rubrics, error taxonomy) and `knowledge-graph.json` (concept metadata) to evaluate correctly. Pass relevant slices via the Task tool prompt, or have the subagent `Read` the files.

3. **Graceful degradation**: If a subagent fails (timeout, error), the main agent should fall back to self-assessment rather than blocking the session. The learner's experience should never stall waiting for a subagent.

4. **Latency budget**: The learner is waiting during study sessions. Subagent round-trips must stay under 5 seconds. Use `model: sonnet` (not opus) for inline evaluations. Use `maxTurns: 2-3` to prevent runaway subagent conversations.

5. **No subagent nesting**: Subagents cannot spawn other subagents. The main agent is the only orchestrator. This is a Claude Code platform constraint.

---

## Sources

### Academic papers
- GenMentor: [LLM-powered Multi-agent Framework for Goal-oriented Learning in ITS](https://arxiv.org/html/2501.15749v1) (WWW 2025)
- IntelliCode: [Multi-Agent LLM Tutoring System with Centralized Learner Modeling](https://arxiv.org/html/2512.18669v1) (Dec 2025)
- EduPlanner: [LLM-Based Multi-Agent Systems for Customized Instructional Design](https://arxiv.org/html/2504.05370v1) (2025)
- [LLM Agents for Education: Advances and Applications](https://arxiv.org/html/2503.11733v1) (EMNLP 2025 Findings)

### Claude Code documentation
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents) -- Full subagent configuration reference
- [Agent Teams](https://code.claude.com/docs/en/agent-teams) -- Team coordination patterns

### Existing project research
- `/RPIV/research/teaching-agent/SUMMARY.md` -- Architecture decisions (hybrid LLM + classical)
- `/RPIV/research/teaching-agent/plugin-architecture-constraints.md` -- Plugin capabilities/limitations
- `/RPIV/research/teaching-agent/llm-teaching-approaches.md` -- Socratic prompting, assessment patterns
- `/RPIV/research/teaching-agent/adaptive-learning-systems.md` -- FSRS, BKT, knowledge graphs, adaptation mechanisms
