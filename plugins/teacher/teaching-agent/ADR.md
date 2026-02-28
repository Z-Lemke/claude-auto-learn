# ADR: Teaching Agent Plugin Architecture

**Date**: 2026-02-20
**Status**: Proposed
**Decision**: Build an adaptive teaching agent as a Claude Code plugin in the llm-toolkit marketplace

---

## Context

We want a Claude Code plugin that can teach any text-based subject adaptively. First use cases: informal Malay language learning, systems design with AI focus, and interview preparation. The agent must generalize across domains while providing domain-specific quality.

## Decision: Hybrid LLM + Classical Algorithm Architecture

### What we're building

A Claude Code plugin called `teacher` that provides:
1. **Course construction** — user describes what they want to learn, agent builds a structured curriculum
2. **Adaptive tutoring** — study sessions that teach, assess, and adapt in real time
3. **Assessment** — quizzes and mastery checks
4. **Progress tracking** — persistent tracking of what the learner knows and what to review next

### Why this approach over alternatives

**Alternative 1: Pure LLM tutor (just a good system prompt)**
- Rejected because: LLMs can't track numerical state (FSRS schedules, mastery probabilities) across sessions, can't maintain consistent difficulty, and have no memory between sessions without external state.

**Alternative 2: Full classical ITS (Intelligent Tutoring System)**
- Rejected because: Requires massive content authoring per domain. The whole point of using an LLM is zero-authoring-cost content generation.

**Alternative 3: Hybrid (chosen)**
- LLM for what it's good at: generating content, evaluating responses, natural dialogue, Socratic teaching
- Classical algorithms for what they're good at: scheduling reviews (FSRS), tracking mastery (simplified BKT), traversing knowledge graphs
- Structured state for what must persist: learner model, course data, session history

### Architecture

```
User ←→ Slash Commands (/study, /quiz, /build-course, /progress)
              ↓
         SKILL.md (teaching instructions for Claude)
              ↓
    ┌─────────────────────────────┐
    │     Claude (LLM Layer)      │
    │  - Content generation       │
    │  - Response evaluation      │
    │  - Socratic dialogue        │
    │  - Exercise generation      │
    └─────────┬───────────────────┘
              ↓ calls
    ┌─────────────────────────────┐
    │   Python Scripts (Engine)    │
    │  - fsrs.py (scheduling)     │
    │  - mastery.py (BKT)         │
    │  - planner.py (session)     │
    │  - graph.py (knowledge)     │
    └─────────┬───────────────────┘
              ↓ reads/writes
    ┌─────────────────────────────┐
    │   State Files (Persistence)  │
    │  ~/.claude/teaching/         │
    │    courses/<name>/           │
    │      knowledge-graph.json    │
    │      curriculum.json         │
    │    learner/                   │
    │      profile.json            │
    │      <course>/progress.json  │
    │      <course>/sessions/      │
    └─────────────────────────────┘
```

### Key Design Decisions

**1. User-level state, not project-level**

Teaching is about the person, not the project. Store everything under `~/.claude/teaching/`. A user learning Malay doesn't want their progress tied to whichever git repo they happen to be in.

**2. LLM generates the knowledge graph, Python scripts manage it**

When building a course, the LLM researches the domain and produces a structured knowledge graph (JSON). Python scripts then handle traversal, prerequisite checking, and frontier identification. The LLM never does graph math directly.

**3. FSRS for review scheduling, simplified mastery for advancement**

Full BKT requires parameter estimation that needs more data than a single learner provides. Instead: use FSRS (well-validated, works from first review) for scheduling when to review items, and a simplified mastery tracker (running accuracy + confidence) for deciding when to advance.

**4. Single-agent, multi-command design**

Due to the subagent hook inheritance bug, everything runs as the main agent. Different slash commands activate different "modes" of the same skill:
- `/build-course` — create a new course
- `/study` — run a learning session
- `/quiz` — assessment mode
- `/progress` — view progress and decide what to do next

**5. Domain-agnostic engine with domain-specific course configs**

The adaptation engine (Python scripts) is the same regardless of subject. Each course stores its own:
- Knowledge graph with concept-specific metadata
- Exercise generation prompts tailored to the domain
- Assessment rubrics
- Common misconceptions / error taxonomy

**6. Teaching methodology encoded in SKILL.md, not hardcoded**

The Socratic method, scaffolding approach, error correction strategy, etc. are all in the skill's markdown instructions. This makes them easy to iterate on without changing code.

## Trade-offs

| Trade-off | Upside | Downside |
|-----------|--------|----------|
| User-level state | Learning persists regardless of project | Can't teach project-specific things (e.g., "learn this codebase") |
| LLM-generated knowledge graphs | Zero authoring cost, works for any domain | Quality depends on LLM knowledge of the domain; may be wrong for niche topics |
| FSRS over full BKT | Works from first review, well-validated | Optimized for memory/recall, not deep understanding |
| Single-agent | Simple, reliable, no hook bugs | Can't parallelize course building with web research subagents |
| Python scripts for engine | Deterministic, testable, precise | Adds complexity; must shell out from Claude via Bash |

## Assumptions

1. Python 3.8+ is available on the user's machine (macOS and Linux)
2. Users will self-initiate study sessions (no push reminders)
3. Claude's training data is sufficient to generate reasonable knowledge graphs for the target domains
4. The SKILL.md instructions can be comprehensive enough to drive consistent teaching behavior
5. JSON files are sufficient for state management (no database needed)
6. The 80% success rate target is a reasonable default across domains

## Risks

1. **LLM quality for Malay**: Claude's Malay may be inconsistent. Mitigation: bilingual prompting, grammar rules in context
2. **Knowledge graph quality**: LLM-generated graphs may have wrong prerequisites. Mitigation: allow user to override/edit, validate with assessments
3. **Skill instruction length**: Complex teaching methodology may exceed SKILL.md's 5000-word limit. Mitigation: split into multiple skills, use reference files
4. **Session context limits**: Long study sessions may exhaust context. Mitigation: focused sessions with state checkpointing
