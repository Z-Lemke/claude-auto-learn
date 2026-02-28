# Teaching Agent Research Summary

**Date**: 2026-02-20

## Key Findings Across All Three Research Streams

### 1. Architecture: Hybrid is the way

The clear winner across all research is **Pattern 4: LLM for generation/dialogue, classical algorithms for scheduling/tracking**.

- **LLM handles**: natural language explanation, exercise generation, Socratic dialogue, response evaluation, conversation practice
- **Classical algorithms handle**: spaced repetition scheduling (FSRS), mastery tracking (BKT), knowledge graph traversal, difficulty calibration
- **Structured data handles**: learner state, course progression, session history

This is the Khanmigo pattern — the LLM doesn't replace the adaptive engine, it provides the teaching interface on top of one.

### 2. Plugin Architecture: Single-agent, slash-command driven

Due to the subagent hook inheritance bug (#21460), Phase 1 must be single-agent:

- Slash commands as entry points: `/build-course`, `/study`, `/quiz`, `/progress`
- Each command activates a skill with detailed instructions
- State persisted as JSON/markdown files in `.claude/teaching/` or `~/.claude/teaching/`
- Stop hook for session analysis and progress tracking
- No subagents needed for core functionality

### 3. Knowledge Modeling: Three-layer approach

1. **Domain Model** (knowledge graph): Concepts, prerequisites, Bloom targets, exercise templates — stored as JSON, varies per subject
2. **Learner Model** (per-concept state): FSRS scheduling state + BKT mastery probability + Bloom level + error patterns — stored as JSON
3. **Adaptation Engine** (decision logic): ZPD frontier selection, 80% success rate targeting, struggle detection, interleaving — implemented in the skill instructions + helper scripts

### 4. Generalization Strategy

**Domain-agnostic primitives** that work for any text-teachable subject:
- Concept/skill nodes with prerequisite edges
- Spaced repetition scheduling (FSRS)
- Mastery estimation (BKT or simplified)
- Bloom's taxonomy progression
- ZPD frontier selection
- Scaffolded hint sequences
- Interleaved practice

**Domain-specific configuration** per course:
- Knowledge graph content
- Exercise generation prompts/templates
- Error taxonomy and common misconceptions
- Assessment rubrics
- Session structure preferences (short/daily for languages, longer/focused for technical)

### 5. Critical Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Where does scheduling live? | FSRS in Python scripts | LLMs can't track numerical state reliably |
| Where does mastery tracking live? | Simplified BKT in Python scripts | Need probabilistic tracking across sessions |
| Where does the knowledge graph live? | JSON files per course | Must persist, must be machine-readable |
| How does course building work? | LLM generates initial graph + content, cached to disk | Can't rely on web research during tutoring |
| How does assessment work? | LLM evaluates responses against structured rubrics | Best of both: natural language understanding + consistency |
| How to prevent "too helpful"? | Multi-layer Socratic prompting + response validation in skill instructions | Deepest LLM teaching failure mode |
| User-level or project-level state? | User-level (~/.claude/teaching/) | Teaching isn't project-specific |

### 6. Scope for Phase 1

**In scope**:
- Course building slash command that generates a knowledge graph + curriculum from a topic description
- Study session slash command that teaches using the generated curriculum
- Quiz/assessment command for testing understanding
- Progress tracking command showing mastery levels
- FSRS-based review scheduling
- Simplified mastery tracking
- Adaptive difficulty (harder when succeeding, easier when struggling)

**Out of scope for Phase 1**:
- Voice/pronunciation (CLI is text-only)
- Multi-agent architecture (hook bug)
- Full BKT parameter estimation (not enough data per individual)
- RAG over external textbooks (permission issues with web tools)
- Fine-tuned models for assessment

### 7. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| LLM gives away answers | Multi-layer Socratic instructions, explicit anti-answer rules, response format constraints |
| Low-resource language quality (Malay) | Bilingual prompting (reason in English about Malay), explicit grammar rules in context, frequency lists |
| Difficulty inconsistency | FSRS + BKT drive difficulty, not LLM judgment; target 80% success rate |
| State loss between sessions | Atomic JSON writes, clear state schema, load-on-start pattern |
| Learner never returns | Clear "next steps" at session end, progress summary showing what's next |
| Assessment inaccuracy | Multi-question probing, transfer tasks, structured rubrics, confidence calibration |
