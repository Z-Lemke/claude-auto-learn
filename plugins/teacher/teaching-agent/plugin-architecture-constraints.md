# Research: Claude Code Plugin Architecture & Constraints for a Teaching Agent

**Date:** 2026-02-20
**Purpose:** Understand the capabilities, constraints, and architecture of Claude Code plugins to determine what is feasible for a teaching agent plugin.

---

## 1. Plugin Architecture

### 1.1 Plugin Directory Structure

A Claude Code plugin is a directory containing a `.claude-plugin/plugin.json` manifest and optional hooks, skills, and commands. The structure observed in this repo:

```
plugins/<plugin-name>/
  .claude-plugin/
    plugin.json              # Required: name, version, description, author, license
  hooks/
    hooks.json               # Hook registration (auto-registered when plugin enabled)
    <script>.py or <script>.sh  # Hook implementation
  skills/
    <skill-name>/
      SKILL.md               # Skill definition (YAML frontmatter + markdown body)
      scripts/               # Supporting scripts
      references/            # Reference documents, templates
  commands/
    <command>.md             # Slash commands (YAML frontmatter + markdown body)
  tests/                     # Plugin-specific tests
```

**Marketplace wrapper** (repo-level):
```
.claude-plugin/
  marketplace.json           # Lists all plugins in the repo with name, description, source path
```

### 1.2 plugin.json Schema

Minimal required fields (from both `auto-learn` and `safety-judge`):

```json
{
  "name": "plugin-name",
  "version": "0.1.0",
  "description": "What it does",
  "author": { "name": "Author" },
  "repository": "https://github.com/...",
  "license": "MIT"
}
```

### 1.3 Installation and Activation

- Plugins install via `claude plugin install <name>` or `--plugin-dir <path>` for development
- When installed/enabled, hooks auto-register from `hooks/hooks.json`
- Skills become available for activation when their trigger phrases match user intent
- Slash commands become available as `/<command-name>`

---

## 2. Skills

### 2.1 SKILL.md Format

Skills are defined in `skills/<skill-name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: skill-name          # Required, kebab-case, lowercase
description: >            # Required, max 1024 chars
  What it does. Use when <trigger conditions>.
---

# Skill Name

## Instructions
[Markdown body with step-by-step instructions for Claude to follow]
```

**Frontmatter constraints (from test_plugin_structure.py):**
- `name` is required, must be kebab-case, lowercase, no spaces
- `description` is required, max 1024 characters
- Description MUST include trigger phrases for reliable activation (the LLM uses the description to decide when to activate a skill)
- Total SKILL.md should be under 5000 words

### 2.2 What Skills Can Do

A skill is essentially a set of instructions injected into Claude's context when activated. Skills do NOT have their own tool access by default -- they rely on the tools available to the current Claude session.

**Tools available during skill execution:**
- Read, Write, Edit -- file operations
- Bash -- shell commands (subject to permissions/sandbox)
- Glob, Grep -- search operations
- WebSearch, WebFetch -- web research (if permitted)
- NotebookEdit -- Jupyter notebook editing
- Task -- subagent spawning (subject to the known inheritance bug)

Skills can also have `references/` subdirectory with template files that the skill instructions reference for consistent output formatting.

### 2.3 Skill Activation

Skills activate in two ways:
1. **Automatic**: Claude matches user intent against skill descriptions and activates relevant skills
2. **Via slash command**: A command can explicitly instruct Claude to activate a skill (e.g., `/learn` activates the `auto-learn` skill)

**Key insight for teaching agent:** The description field is critical. It must contain the trigger phrases that will cause Claude to recognize when to activate the skill. For example, auto-learn's description includes: "use when the user says 'learn', 'remember this', 'update claude config'..."

### 2.4 Skills Cannot Invoke Other Skills Directly

There is no mechanism for one skill to programmatically invoke another skill. Skills are instruction sets, not callable functions. However:
- A skill's instructions can tell Claude to "activate the X skill" and Claude may do so
- A slash command can chain: it can instruct Claude to activate a skill after doing some work
- This is soft coupling through natural language, not hard coupling through APIs

**Implication for teaching agent:** Course building and tutoring would need to be separate skills. They cannot directly call each other, but they can reference shared state files on disk.

---

## 3. Slash Commands

### 3.1 Command Format

Commands live in `commands/<name>.md` with YAML frontmatter:

```yaml
---
description: What this command does
allowed-tools: Bash(mkdir:*) Bash(chmod:*) Read Write Edit Glob Grep
---

# /command-name - Title

Instructions for Claude when the user invokes this command.
```

**Key fields:**
- `description`: Shown to the user in command listings
- `allowed-tools`: Restricts which tools Claude can use when executing this command. Uses the same permission pattern syntax as settings.json

### 3.2 Commands vs Skills

| Aspect | Command | Skill |
|--------|---------|-------|
| Trigger | Explicit `/name` invocation | Automatic matching or explicit activation |
| Tool restriction | Yes, via `allowed-tools` frontmatter | No (inherits session tools) |
| Length | Short (entry point) | Long (detailed workflow) |
| Purpose | User-facing entry point | Detailed execution instructions |
| Best for | Quick actions, starting workflows | Complex multi-step procedures |

**Pattern observed:** Commands act as entry points that activate skills. The `/learn` command is just a thin wrapper that says "activate the auto-learn skill."

**Implication for teaching agent:** Use commands as user entry points (`/study`, `/quiz`, `/review`, `/progress`), each activating the appropriate skill with the right context.

---

## 4. Hooks

### 4.1 Hook Types

Hooks are shell scripts or Python scripts that run at specific lifecycle events:

| Hook Type | When It Fires | Can Block? | Use Case |
|-----------|---------------|------------|----------|
| PreToolUse | Before any tool call | Yes (deny/ask) | Safety gates, input validation |
| PostToolUse | After tool execution | No | Logging, format checks |
| Stop | After Claude's response | No (but can continue) | Session analysis, auto-learn |
| SubagentStart | When subagent spawns | No (can inject context) | Context injection |

### 4.2 hooks.json Format

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/templates/stop-and-learn.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

- `matcher`: Empty string matches all events. For PreToolUse, can match specific tool names.
- `${CLAUDE_PLUGIN_ROOT}`: Resolves to the plugin installation directory at runtime.
- `timeout`: Maximum execution time in seconds. Hook is killed if exceeded.

### 4.3 Hook Input/Output

**Input (stdin JSON):**
```json
{
  "session_id": "...",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "permission_mode": "...",
  "hook_event_name": "PreToolUse|PostToolUse|Stop|SubagentStart",
  "tool_name": "Bash",
  "tool_input": { "command": "..." }
}
```

**Output (stdout JSON):**

For PreToolUse:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "permissionDecisionReason": "explanation"
  }
}
```

For Stop:
```json
{ "continue": true }  // Signal Claude to continue the session
```

For SubagentStart:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": "Injected context string for the subagent"
  }
}
```

**Exit codes:**
- 0 = success (Claude parses stdout)
- Non-zero = error (behavior varies: PreToolUse blocks, Stop ignores)

### 4.4 Hook Capabilities Relevant to Teaching Agent

**Stop hook** is the most relevant for a teaching agent:
- Fires after every Claude response
- Receives `transcript_path` -- can analyze the full session history
- Can signal `{"continue": true}` to keep the session going
- Could detect learning patterns, track progress, trigger reviews

**SubagentStart hook:**
- Can inject context into spawned subagents
- Could inject curriculum state, learner profile, progress data
- Cannot block subagent creation

**PreToolUse hook:**
- Could gate certain operations based on learner level
- Could track which tools the learner is using
- Could enforce teaching boundaries (e.g., no answers before attempt)

### 4.5 Critical Bug: Hook Inheritance for Subagents

**CONFIRMED BUG:** Plugin-level hooks do NOT fire for Task tool subagents.

**Evidence:** Empirically validated in this repo's E2E tests. Safety-judge hooks loaded but did not execute for subagent tool calls. Filed as https://github.com/anthropics/claude-code/issues/21460.

**Impact on teaching agent:**
- If teaching uses subagents (e.g., a "quiz grader" subagent), hooks from the teaching plugin will NOT apply to those subagents
- Subagents spawned via Task tool operate in isolated contexts
- Workaround: Define hooks in subagent frontmatter, or avoid Task tool

---

## 5. State Persistence

### 5.1 File-Based Persistence

Claude Code plugins can persist state by writing to the local filesystem. There is no built-in key-value store or database -- file I/O is the persistence mechanism.

**Observed patterns:**
- `auto-learn` writes to `.claude/CLAUDE.md`, `.claude/learnings.md`, `.claude/settings.json`, `.claude/hooks/`, `.claude/skills/`
- All state stored under the project's `.claude/` directory
- State persists across sessions because it is on disk

### 5.2 Appropriate Directories for State

| Directory | Scope | Use |
|-----------|-------|-----|
| `<project>/.claude/` | Per-project | Project-specific config, learnings |
| `~/.claude/` | Per-user, global | User preferences, global settings |
| `<project>/.claude/skills/<name>/data/` | Per-skill, per-project | Skill-specific persistent data |

**Convention from this repo:** All learnings go to project `.claude/` directory, not user-level config. This is a deliberate design decision documented in CLAUDE.md.

### 5.3 State Persistence Strategy for Teaching Agent

The teaching agent needs to persist:
1. **Learner profile** -- knowledge level, learning style, preferences
2. **Course/curriculum state** -- what topics are planned, completed, in progress
3. **Progress data** -- quiz scores, concept mastery ratings, session history
4. **Curriculum content** -- lesson plans, reference materials, exercises

**Recommended structure:**
```
<project>/.claude/teaching/
  learner-profile.json       # Knowledge level, preferences, goals
  curriculum/
    <course-name>/
      plan.json              # Course plan, topic sequence, dependencies
      progress.json          # Completed topics, scores, timestamps
      resources/             # Downloaded/generated reference materials
      sessions/
        <session-id>.json    # Per-session detailed progress
```

**Alternative -- user-level storage:**
```
~/.claude/teaching/          # If learning is not project-specific
```

The choice depends on whether the teaching agent is project-scoped (learning a specific codebase's patterns) or user-scoped (learning general CS/programming topics).

### 5.4 File Format Considerations

- **JSON** for structured data (profiles, progress, plans) -- machine-readable, easy to parse
- **Markdown** for human-readable content (lesson plans, notes, summaries) -- Claude reads/writes markdown natively
- **JSONL** for append-only logs (session history) -- easy to append without reading whole file

### 5.5 Concurrency Considerations

Multiple Claude sessions could potentially run simultaneously. The existing plugins do not address this (they assume single-session access to state files). For a teaching agent:
- Reading state is safe (concurrent reads are fine)
- Writing state needs care -- last-write-wins could lose data
- Simple mitigation: Use atomic writes (write to temp file, then rename)
- For append-only logs, file append is generally safe on modern filesystems

---

## 6. Interaction Model Constraints

### 6.1 Text-Only CLI Interface

Claude Code operates as a CLI tool. The teaching agent's UX is constrained to:
- **Input:** Text typed by the user in the terminal
- **Output:** Text (with markdown formatting) displayed in the terminal
- No images, audio, or rich interactive elements
- No buttons, forms, or GUI widgets
- No color or formatting beyond what the terminal supports

**Implications for teaching:**
- Lessons must be text-based (explanations, code examples, ASCII diagrams)
- Quizzes are text-based (Q&A, fill-in-the-blank, code completion)
- Progress visualization is limited (text-based progress bars, tables, summaries)
- Code exercises can leverage actual file creation and execution via Bash

**Advantage:** The CLI environment IS the natural habitat for coding education. Learners can:
- Write and execute real code
- Interact with real tools (git, compilers, test runners)
- See real output, real errors
- This is better than a web-based tutorial for hands-on learning

### 6.2 Session-Based Interaction

Claude Code sessions are started and stopped by the user:
- User starts a session: `claude` or `claude -p "prompt"`
- Session runs until user stops it or Claude completes
- No background processes between sessions
- No push notifications or scheduled sessions
- No proactive outreach ("time for your daily lesson!")

**Implications for teaching:**
- The learner must initiate every interaction
- The agent cannot remind the learner to study
- Session continuity depends on state persistence to disk
- Each session must re-load context from persisted state

### 6.3 Session Length Constraints

Claude Code sessions are bounded by:
- **Context window:** Claude's context window limits how much conversation history fits in one session. With Opus/Sonnet, this is ~200k tokens.
- **Practical limits:** Very long sessions become expensive (API costs) and may hit rate limits
- **User fatigue:** Terminal-based interaction is intense; 30-60 minute sessions are likely the practical maximum for focused learning

**Reasonable session design:**
- Short focused sessions (15-30 min) for lessons and exercises
- Quiz sessions can be shorter (10-15 min)
- Review sessions checking progress can be very short (5 min)
- Long sessions for project-based learning (30-60 min) where the learner is coding

### 6.4 Stop Hook for Session Intelligence

The Stop hook fires after every Claude response. This gives the teaching agent the ability to:
- Analyze the conversation so far
- Track what concepts were discussed
- Detect when the learner is struggling (repeated errors, confusion signals)
- Signal Claude to continue the session (for follow-up exercises, hints, etc.)
- Update progress state after each response

This is the most powerful UX mechanism available -- it gives the agent awareness of the conversation without the learner explicitly triggering it.

---

## 7. Web Research Capabilities

### 7.1 WebSearch Tool

- Performs web searches and returns results
- Available to Claude if not restricted by permissions
- Practical for researching topics, finding documentation, checking current best practices
- Results include search snippets and URLs

**Constraints observed in this session:** WebSearch may be restricted by permissions or sandbox settings. The tool can be denied at the permission level.

### 7.2 WebFetch Tool

- Fetches content from a URL and processes it with an AI model
- Can retrieve documentation, tutorials, blog posts, API references
- Has a 15-minute self-cleaning cache for repeated access
- Cannot access authenticated resources (Google Docs, private GitHub repos, etc.)
- HTTP auto-upgraded to HTTPS
- Content may be summarized if very large

**Constraints observed in this session:** WebFetch may also be restricted by permissions.

### 7.3 Practical Constraints for Curriculum Research

**What the agent CAN do with web tools:**
- Search for tutorial content on a topic
- Fetch and summarize documentation pages
- Pull down code examples from public repositories
- Access public educational resources (MDN, Python docs, Wikipedia, etc.)
- Research current best practices and conventions

**What the agent CANNOT do:**
- Access paywalled or authenticated content (Coursera, O'Reilly, etc.)
- Download large files (e.g., full textbooks)
- Access private GitHub repos without authentication
- Reliably access any specific URL (may be blocked, redirected, or down)
- Guarantee consistent results across sessions (web content changes)

**Rate limits:**
- No explicit documented rate limits for WebSearch/WebFetch
- Practical limit: each call takes time (~1-5 seconds)
- LLM processing of fetched content adds latency
- Excessive fetching slows sessions noticeably

### 7.4 Curriculum Building Strategy

Given these constraints, the teaching agent should:
1. **Pre-research and cache:** When building a curriculum, research topics and store summaries locally in `resources/` files
2. **Use web during course building, not during tutoring:** Avoid web calls during interactive teaching sessions (too slow, may fail)
3. **Rely on Claude's training data first:** Claude already knows a vast amount about programming, CS, and software engineering. Web research supplements, not replaces, this knowledge
4. **Store persistent resources:** Fetched content should be saved as markdown files for reuse across sessions

---

## 8. Subagent Capabilities

### 8.1 Task Tool

The Task tool spawns subagents that can run in parallel or handle specialized subtasks. However, as documented in this repo's research:

**Known limitations:**
- Plugin-level hooks do NOT fire for subagent tool calls (confirmed bug)
- Subagents do NOT automatically inherit parent agent permissions
- Subagents operate in isolated contexts

### 8.2 Subagent Architecture for Teaching

**Course building vs tutoring as separate concerns:**

| Concern | Agent Type | When It Runs |
|---------|-----------|--------------|
| Curriculum design | Could be a subagent | During course building (offline) |
| Content research | Could be a subagent | During course building (offline) |
| Tutoring/teaching | Main agent | During interactive sessions |
| Quiz generation | Main agent or subagent | During session or pre-generated |
| Progress evaluation | Main agent | During session (after responses) |

**Option A: Single-agent architecture (recommended for Phase 1)**
- One skill handles everything
- State managed via files
- Simpler, more reliable
- No hook inheritance issues
- Switches modes based on commands (/build-course, /study, /quiz)

**Option B: Multi-agent architecture (future, after hook fix)**
- Subagents for parallel curriculum research
- Subagent for quiz grading while main agent teaches
- Requires hook inheritance fix for safety
- More complex state synchronization

### 8.3 Can a Skill Invoke Other Skills?

No direct invocation mechanism exists. However:
- A skill can instruct Claude to "now activate skill X"
- Claude may or may not comply (it is a language model, not a deterministic runtime)
- Slash commands can serve as reliable entry points that activate specific skills

**Practical approach:** Design skills as independent modules that share state via files. Use slash commands to switch between modes explicitly.

---

## 9. Summary of Constraints and Capabilities

### What a Teaching Agent Plugin CAN Do

1. **Persist state** across sessions via file I/O to `.claude/teaching/` or `~/.claude/teaching/`
2. **Provide slash commands** (`/study`, `/quiz`, `/progress`, `/build-course`) as user entry points
3. **Define skills** with detailed teaching instructions that Claude follows
4. **Use hooks** (Stop hook) to analyze sessions, track progress, detect learning patterns
5. **Execute real code** -- learners can write, compile, and run actual programs
6. **Research topics** via WebSearch/WebFetch (when permitted) for curriculum building
7. **Read/write files** -- create exercises, lesson plans, reference materials
8. **Leverage Claude's knowledge** -- Claude already knows programming, CS, math, etc.
9. **Maintain conversation context** within a session (up to ~200k tokens)
10. **Use the transcript** (via Stop hook) to analyze learning patterns

### What a Teaching Agent Plugin CANNOT Do

1. **Push notifications** -- cannot remind learner to study
2. **Schedule sessions** -- cannot initiate contact
3. **Rich media** -- no images, audio, video, interactive widgets
4. **Authenticated web content** -- cannot access paywalled resources
5. **Cross-session context** -- each session starts fresh; must reload from persisted state
6. **Subagent safety** -- hooks don't inherit; must avoid or carefully manage Task tool
7. **Guaranteed tool availability** -- WebSearch/WebFetch may be permission-denied
8. **Deterministic skill activation** -- Claude chooses when to activate skills based on description matching; not 100% reliable
9. **Long-running background processes** -- everything happens within a user session
10. **Direct skill-to-skill invocation** -- skills are instruction sets, not callable functions

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| State corruption from concurrent sessions | Medium | Atomic writes, append-only logs |
| Skill not activating when expected | Medium | Clear trigger phrases in description, slash commands as reliable fallback |
| Web research failing during curriculum build | Low | Cache results locally, rely on Claude's training data |
| Session too long for complex lessons | Medium | Design short focused sessions, persist progress between sessions |
| Learner never returns (no reminders) | High (UX) | Design for self-motivated learners; provide clear "next steps" at end of each session |
| Subagent hook inheritance bug | High (if using subagents) | Single-agent architecture for Phase 1 |
| Permission restrictions blocking needed tools | Medium | Document required permissions, provide fallback behaviors |

### Architecture Recommendations

1. **Phase 1: Single-agent, file-based state, slash-command driven**
   - One skill per mode (study, quiz, build-course, review)
   - All state in `.claude/teaching/` as JSON + markdown
   - Slash commands as reliable entry points
   - Stop hook for session analysis and progress tracking
   - No subagents (avoid hook inheritance bug)

2. **Phase 2: Enhanced UX and curriculum intelligence**
   - Pre-built curriculum templates stored as reference files
   - Adaptive difficulty based on tracked performance
   - WebSearch/WebFetch for supplemental research (when available)
   - Multi-session curriculum tracking

3. **Phase 3: Multi-agent architecture (after upstream fix)**
   - Parallel curriculum research via subagents
   - Specialized grading/evaluation subagents
   - More sophisticated progress analytics

---

## 10. Open Questions for Further Research

1. **Skill frontmatter hooks:** Can skills define their own hooks in frontmatter? Documentation suggests yes. This would let the teaching skill register a Stop hook scoped to its lifecycle, avoiding conflicts with other plugins.

2. **allowed-tools in skills:** The command frontmatter supports `allowed-tools`. Do skills also support this? Could restrict teaching sessions to safe operations only.

3. **Session resume:** Can a Claude Code session be resumed? If so, the teaching agent could support "continue where I left off" natively. If not, it must fully reconstruct context from persisted state.

4. **Transcript format:** The Stop hook receives `transcript_path`. What is the exact JSONL format? Auto-learn's detect script handles both flat and nested formats. The teaching agent's session analysis needs to handle the same.

5. **Maximum file sizes for skill references:** Are there limits on how much content can be in `references/`? For curriculum storage, this matters.

6. **Plugin update mechanism:** When the teaching agent's curriculum evolves, how does the user get updates? Is there a `claude plugin update` mechanism?

---

## References

**Files analyzed in this research:**
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/.claude-plugin/plugin.json`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/commands/learn.md`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/hooks/hooks.json`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/hooks/templates/stop-and-learn.sh`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/skills/auto-learn/SKILL.md`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/skills/auto-learn/scripts/detect-learning-opportunity.py`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/skills/auto-learn/references/templates/*.md`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/tests/test_plugin_structure.py`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/auto-learn/tests/test_e2e.py`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/.claude-plugin/plugin.json`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/hooks/hooks.json`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/hooks/safety_judge.py`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/SECURITY.md`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/docs/AUTONOMOUS-MODE.md`
- `/Users/lukelemke/Repositories/llm-toolkit/plugins/safety-judge/docs/KNOWN-LIMITATIONS.md`
- `/Users/lukelemke/Repositories/llm-toolkit/.claude-plugin/marketplace.json`
- `/Users/lukelemke/Repositories/llm-toolkit/CLAUDE.md`
- `/Users/lukelemke/Repositories/llm-toolkit/RPIV/research/subagent-hook-inheritance.md`
- `/Users/lukelemke/Repositories/llm-toolkit/RPIV/research/hook-behavior-and-e2e.md`
- `/Users/lukelemke/Repositories/llm-toolkit/RPIV/findings/task3-subagent-safety.md`
