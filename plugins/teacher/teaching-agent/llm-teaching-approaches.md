# LLM Teaching and Tutoring Approaches: Research Survey

**Date**: 2026-02-20
**Status**: Initial research (compiled from training knowledge through early 2025; web search/fetch tools were unavailable for this session -- flagged items should be verified with live sources)

---

## Table of Contents

1. [LLM Tutoring Systems](#1-llm-tutoring-systems)
2. [Prompt Engineering for Teaching](#2-prompt-engineering-for-teaching)
3. [LLM Limitations for Teaching](#3-llm-limitations-for-teaching)
4. [Language Teaching with LLMs](#4-language-teaching-with-llms)
5. [Agent Architectures for Education](#5-agent-architectures-for-education)
6. [Key Takeaways and Recommendations](#6-key-takeaways-and-recommendations)
7. [Open Questions and Further Research Needed](#7-open-questions-and-further-research-needed)
8. [References and Sources to Verify](#8-references-and-sources-to-verify)

---

## 1. LLM Tutoring Systems

### 1.1 Khanmigo (Khan Academy + OpenAI)

**What it is**: Khan Academy's AI tutoring assistant, launched in 2023 and expanded through 2024-2025. Built on GPT-4 (and later models), Khanmigo is integrated directly into Khan Academy's existing course platform.

**Architecture and approach**:
- Uses a carefully designed system prompt that instructs GPT-4 to act as a Socratic tutor
- The system prompt explicitly tells the model: "You are a tutor. Do NOT give students the answer. Instead, ask leading questions to help them figure it out themselves."
- Khanmigo has access to the specific problem/lesson context the student is working on, injected into the conversation as context
- The system maintains guardrails: it refuses to do homework for students, redirects off-topic conversations, and escalates to human teachers when appropriate
- Integrated with Khan Academy's exercise system so it can see what problem the student is on, what they've tried, and their history

**Key design decisions**:
- **Constrained domain**: Khanmigo is not a general chatbot. It operates within Khan Academy's curriculum, which gives it structured content to anchor responses to
- **Prompt-level Socratic enforcement**: The entire teaching methodology is encoded in system prompts rather than fine-tuning
- **Teacher dashboard**: Teachers can review AI-student conversations, providing oversight and a feedback loop
- **Safety layers**: Content moderation, topic restriction, conversation monitoring

**Reported results (as of early 2025)**:
- Khan Academy published case studies showing student engagement increased when Khanmigo was available
- Sal Khan (in public talks and his book "Brave New Words", 2024) described early results as promising but acknowledged the system was still iterating
- The system was made free for US educators in 2024, suggesting enough confidence to scale
- Specific quantitative learning outcome data was limited in public reports -- most evidence was anecdotal or engagement-based rather than controlled trials

**Limitations observed**:
- Sometimes breaks character and gives direct answers despite Socratic prompting
- Can struggle with multi-step math problems where it needs to track the student's work precisely
- Students sometimes find the Socratic approach frustrating ("just tell me the answer")
- Cost was initially $44/year, limiting access (later made free for teachers)

### 1.2 Duolingo Max (GPT-4 powered features)

**What it is**: Duolingo's premium tier, launched March 2023, adding two GPT-4-powered features to the existing language learning platform.

**Key features**:
- **Roleplay**: Open-ended conversation practice with AI characters in realistic scenarios (ordering at a cafe, asking for directions, job interviews). The AI plays a character and the student practices natural conversation
- **Explain My Answer**: After getting an exercise wrong, students can tap to get a natural-language explanation of why their answer was incorrect and what the correct answer means, with grammatical breakdowns

**Architecture**:
- GPT-4 calls are made from Duolingo's backend, with system prompts that define the character, scenario, difficulty level, and target language constructs
- The system has access to the student's current proficiency level in Duolingo's internal model, allowing it to calibrate difficulty
- Conversations are constrained to specific scenarios and topics to keep them pedagogically useful
- Duolingo's existing spaced repetition and curriculum systems remain the backbone; GPT-4 features augment rather than replace

**What works well**:
- Roleplay fills a genuine gap: conversation practice is the hardest part of language learning to get without a human partner
- "Explain My Answer" replaces what would require a human teacher to explain grammar exceptions and nuances
- The scenario-constrained approach prevents conversations from going completely off the rails

**Limitations**:
- Initially only available for Spanish and French (languages with abundant training data)
- Expansion to other languages was slow, presumably because quality was harder to guarantee for lower-resource languages
- Latency was a concern -- GPT-4 API calls add delay to what was previously a snappy mobile app experience
- Cost: only available in Duolingo Max tier ($30/month or $168/year as of 2024)
- The roleplay feature cannot truly assess pronunciation (text-only in initial versions, later added voice)

### 1.3 Open-Source LLM Tutoring Projects

**Notable projects (as of early 2025)**:

- **Open Tutor** (various GitHub projects): Several open-source attempts to build tutoring systems on top of open-weight models (Llama 2/3, Mistral). Most are proof-of-concept rather than production-ready. Common pattern: a prompting framework that wraps an LLM with Socratic tutoring instructions + a simple UI

- **MathGPT / math tutoring projects**: Multiple open-source projects focused on math tutoring, often combining LLMs with symbolic math engines (SymPy, Wolfram) to verify mathematical correctness. This hybrid approach addresses the hallucination problem for math

- **LangChain / LlamaIndex educational agents**: Several community projects use agent frameworks to build educational chatbots with RAG over textbook content. The pattern is: embed a textbook, retrieve relevant sections, then have the LLM tutor using that content as ground truth

- **OpenAI Assistants API educational examples**: OpenAI published cookbook examples showing how to build tutoring assistants using the Assistants API with code interpreter for math verification

- **Squirrel AI (China)**: An adaptive learning system that predates LLMs but has been integrating them. Uses knowledge graphs + LLMs to create personalized learning paths. Significant deployment in China (claimed millions of students)

- **Merlyn Mind**: Built an education-specific LLM, focused on classroom use. Emphasis on safety, accuracy, and pedagogical alignment rather than general capability

**Common patterns in open-source approaches**:
1. System prompt defines the tutor persona and methodology
2. RAG over curriculum content provides factual grounding
3. Some form of student model tracks what the learner knows
4. Guardrails prevent the LLM from going off-curriculum
5. Verification tools (code execution, symbolic math) check factual claims

### 1.4 Academic Research on LLM Tutoring Effectiveness

**Key findings from the literature**:

- **"GPT-4 as a Tutor" studies (2023-2024)**: Several papers compared GPT-4's tutoring against human tutors in controlled settings. Findings were mixed: GPT-4 could match human tutors for straightforward concept explanation but fell behind for complex problem-solving guidance and for detecting student misconceptions

- **Bloom's Two Sigma Problem**: Much of the LLM tutoring research is motivated by Benjamin Bloom's 1984 finding that 1-on-1 tutoring improves student performance by two standard deviations. The hypothesis is that LLMs could provide something approaching 1-on-1 tutoring at scale. Early evidence suggests LLMs can capture some but not all of this benefit

- **Carnegie Mellon University studies**: CMU's LearnLab and HCII groups have published work on integrating LLMs into intelligent tutoring systems (ITS). Key finding: LLMs work best when integrated into structured ITS frameworks rather than used as standalone chatbots. The structure provides the pedagogical scaffolding that LLMs alone lack

- **Harvard/MIT studies on ChatGPT in education**: Research published in 2024 found that students using ChatGPT as a tutor sometimes showed *worse* outcomes than a control group when the AI was unconstrained -- students would get the AI to do their work rather than learn. However, when the AI was constrained to Socratic methods, outcomes improved

- **"The Tutor CoPilot" (2024)**: A notable study where LLMs were used to assist human tutors rather than replace them. The LLM suggested responses and strategies to novice human tutors in real-time. This "AI-augmented human tutor" approach showed promising results -- better than either humans or AI alone

- **Wang et al. (2024)**: Research on using LLMs for automated assessment and feedback in writing. Found that LLM feedback was rated as useful by students but that feedback quality was inconsistent, particularly for higher-order writing concerns (argumentation, thesis development) vs. surface-level issues (grammar, spelling)

---

## 2. Prompt Engineering for Teaching

### 2.1 Socratic Questioning Techniques

**The core challenge**: LLMs are trained to be helpful by providing direct answers. Teaching requires the opposite -- guiding students to discover answers themselves.

**Effective prompting strategies**:

**Strategy 1: Explicit role and anti-answer instructions**
```
You are a Socratic tutor. Your goal is to help the student learn by asking
questions, not by giving answers.

CRITICAL RULES:
- NEVER give the student the direct answer
- NEVER solve the problem for them
- When a student asks "what is the answer?", respond with a question that
  helps them figure it out
- If the student is completely stuck, give a HINT (not the answer) and
  ask them what they think
```

This works but is fragile. Models will break character, especially on direct "just tell me" requests. Multiple reinforcement points help.

**Strategy 2: Think-aloud scaffolding**
```
Guide the student through these steps, ONE AT A TIME:
1. First, ask them what they already know about the topic
2. Identify what they're confused about
3. Ask them to explain their current thinking
4. Point out where their reasoning is correct
5. Ask a targeted question about where their reasoning breaks down
6. If they can't answer, give a small hint and repeat step 5
7. When they arrive at the answer, ask them to summarize what they learned
```

This step-by-step approach gives the LLM a concrete algorithm to follow rather than a vague instruction to "be Socratic."

**Strategy 3: Response templates with placeholders**
```
When the student gives an answer, respond using this format:
- Acknowledge what they got right: "[specific thing they got right]"
- Identify the gap: "I notice you [description of where reasoning breaks down]"
- Ask a guiding question: "What do you think would happen if [scenario that
  reveals the gap]?"
```

Structured response formats constrain the model's output and make it harder for it to slip into "just give the answer" mode.

**Strategy 4: Student misconception anticipation**
```
Common misconceptions students have about [topic]:
1. [Misconception A] - When you detect this, ask: "[Question that reveals why A is wrong]"
2. [Misconception B] - When you detect this, ask: "[Question that reveals why B is wrong]"

Do NOT simply tell the student their misconception is wrong. Use the targeted
question to help them discover the error themselves.
```

Providing anticipated misconceptions with pre-planned responses is one of the most effective strategies because it mimics what experienced human tutors do.

### 2.2 Scaffolding Approaches

**Zone of Proximal Development (ZPD) in prompts**:

The pedagogical concept of ZPD -- the space between what a learner can do alone and what they can do with help -- can be operationalized in prompts:

```
Assess the student's current understanding based on their responses.
- If they demonstrate STRONG understanding: increase difficulty, ask them to
  apply the concept to a novel situation
- If they demonstrate PARTIAL understanding: provide a hint or simpler
  sub-problem that builds toward the full concept
- If they demonstrate NO understanding: break the concept down to prerequisites
  and start from what they DO know
```

**Graduated hint systems**:
```
When a student is stuck, provide hints in this order:
1. METACOGNITIVE hint: "What strategy could you use to approach this problem?"
2. CONCEPTUAL hint: "Remember that [relevant concept]. How might that apply here?"
3. PROCEDURAL hint: "Try [specific first step]. What do you get?"
4. NEAR-ANSWER hint: "The key insight is [concept very close to the answer].
   Can you take it from here?"

Only move to the next level after the student has tried and is still stuck.
Never skip to level 4.
```

**Worked example fading**:
```
For this problem type, follow this progression:
- First problem: Solve it completely, showing each step with explanation
- Second problem: Solve the first half, then ask the student to complete it
- Third problem: Set up the problem, then ask the student to solve it
- Fourth problem: Ask the student to solve it independently

If the student struggles at any stage, go back one level.
```

### 2.3 Assessing Understanding Without Giving Answers

**Transfer questions**: After a student demonstrates understanding of concept X, ask them to apply it to a new situation. If they can transfer, they understand; if not, they may have just pattern-matched.

```
After the student answers correctly:
"Great! Now here's a different situation: [novel scenario using same concept].
How would you approach this?"
```

**Explain-back technique**:
```
When the student gives a correct answer, ask them: "Can you explain to me
WHY that's correct? Pretend I'm a younger student who doesn't understand."

If their explanation reveals understanding: move on
If their explanation is superficial or wrong: probe deeper with follow-up
questions about the specific gaps
```

**Confidence calibration**:
```
After the student gives their answer, ask: "How confident are you in that
answer, on a scale of 1-5? And what part are you least sure about?"

Use their confidence and identified uncertainty to guide your next question.
```

**Predict-before-reveal**:
```
Before explaining a concept, ask the student to predict what will happen:
"Before I explain [concept], what do you THINK happens when [scenario]?
Just give me your best guess."

This surfaces their mental model, which you can then address.
```

### 2.4 Adapting Language Level to the Learner

**Explicit proficiency detection**:
```
At the start of the conversation, assess the student's level:
- Ask their age/grade (if appropriate) or what they already know about the topic
- Observe the vocabulary and sentence complexity they use
- Adjust your language accordingly:
  - BEGINNER: Short sentences, simple vocabulary, lots of examples, analogies
    to everyday life
  - INTERMEDIATE: Standard academic vocabulary, moderate sentence complexity,
    some technical terms with brief definitions
  - ADVANCED: Technical vocabulary, complex sentence structures, references
    to related concepts, nuance and edge cases
```

**Dynamic adjustment**:
```
Monitor the student's responses throughout the conversation:
- If they use technical vocabulary correctly → they can handle higher-level language
- If they seem confused or ask for clarification → simplify
- If they use informal/simple language → match their register
- Mirror their vocabulary level while gradually introducing new terms
```

**Progressive terminology introduction**:
```
When introducing a new technical term:
1. First use the everyday/informal version: "the thing that [description]"
2. Then introduce the term: "This is called [technical term]"
3. Use both together once: "[technical term] -- the thing that [description]"
4. Then use just the technical term going forward
```

---

## 3. LLM Limitations for Teaching

### 3.1 Hallucination and Factual Errors

**The problem**: LLMs generate plausible-sounding but incorrect information. In a teaching context, this is particularly dangerous because students trust the tutor.

**Observed failure modes**:
- **Math errors**: LLMs frequently make arithmetic mistakes, especially in multi-step calculations. They may get the method right but the numbers wrong (or vice versa)
- **Fabricated citations**: When asked to cite sources, LLMs often generate fake paper titles, authors, and publication venues that sound real but don't exist
- **Confident incorrectness**: Unlike a human teacher who might say "I'm not sure about this," LLMs typically present incorrect information with the same confidence as correct information
- **Knowledge boundary blindness**: LLMs don't reliably know what they don't know. They may confidently teach outdated information or information from outside their training distribution

**Mitigation strategies**:
- **RAG grounding**: Retrieve relevant content from verified sources and instruct the model to only teach from that content
- **Verification tools**: For math/code, use execution environments to verify answers before presenting them
- **Uncertainty prompting**: Include instructions like "If you are not confident in your answer, say so explicitly. It's better to say 'I'm not sure about this, let me suggest you check [source]' than to guess"
- **Domain restriction**: Constrain the tutor to specific topics where you've verified accuracy
- **Fact-checking pipeline**: After the LLM generates a response, run it through a separate verification step before showing it to the student

### 3.2 Difficulty Level Inconsistency

**The problem**: LLMs struggle to maintain a consistent difficulty level across a tutoring session. They may explain something simply, then suddenly use graduate-level terminology.

**Why this happens**:
- LLMs don't have a persistent model of the student's level
- Each response is generated somewhat independently (context window helps but doesn't solve this)
- The model draws from its entire training distribution, which includes content at all levels
- Difficulty calibration requires understanding what the student knows, which LLMs assess imperfectly

**Mitigation strategies**:
- **Explicit level tracking in system prompt**: "The student is at [X] level. Every response must be appropriate for this level."
- **Maintain a running student model**: Keep a structured summary of what the student knows/doesn't know in the conversation context
- **Example-anchored levels**: Rather than saying "beginner level," provide an example of what appropriate complexity looks like
- **Post-generation filtering**: Check if the response matches the target difficulty before showing it

### 3.3 The "Too Helpful" Problem

**The problem**: This is arguably the most significant limitation for teaching applications. LLMs are optimized during RLHF to be maximally helpful, which in a teaching context means they constantly want to give the answer.

**Observed patterns**:
- Student asks a question, tutor gives a Socratic response, student pushes back ("just tell me"), and the model caves and gives the answer
- The model provides so many hints that the answer becomes obvious
- When explaining why an answer is wrong, the model accidentally reveals the correct answer
- The model "rewards" partially correct answers too generously, letting misunderstandings slide

**Why standard prompting often fails**:
- RLHF training creates a deep behavioral tendency toward helpfulness
- System prompts compete with this training, and the training often wins
- Users (students) actively try to get the answer, creating adversarial pressure
- The model can't truly understand when withholding information serves the student's learning

**More robust mitigation strategies**:
- **Multi-turn reinforcement**: Repeat the Socratic instruction at multiple points in the system prompt, not just once
- **Response validation layer**: After generating a response, check: "Does this response contain the answer? If so, regenerate."
- **Hard-coded refusal patterns**: For specific known answer-seeking patterns ("just tell me the answer", "what's the solution"), have pre-written responses that redirect
- **Fine-tuning**: For production systems, fine-tuning on examples of correct Socratic behavior is more reliable than prompting alone. This was reportedly part of Khanmigo's approach
- **Constitutional AI approach**: Add a critique step: "Before sending your response, check: Did I give away the answer? If yes, revise to ask a guiding question instead."

### 3.4 Assessment Accuracy Challenges

**The problem**: LLMs are unreliable at assessing whether a student truly understands a concept vs. has just memorized a pattern.

**Specific issues**:
- **Surface pattern matching**: If a student uses the right keywords, the LLM may rate understanding as high even if the student's mental model is wrong
- **Grading inconsistency**: The same response may be graded differently depending on context, phrasing of the evaluation prompt, or even position in the conversation
- **Rubric adherence**: LLMs struggle to consistently apply detailed rubrics, especially for subjective assessments (essay quality, reasoning depth)
- **Over-acceptance of partially correct answers**: LLMs tend to be "nice" and accept answers that are partially correct without probing the incorrect parts

**Mitigation strategies**:
- **Structured rubrics in prompts**: Provide explicit, detailed rubrics with examples of each score level
- **Multi-question assessment**: Don't rely on a single question; use multiple questions from different angles to triangulate understanding
- **Transfer tasks**: Ask students to apply knowledge to novel situations (harder to fake)
- **Separate assessment model**: Use a different LLM call (or a fine-tuned model) specifically for assessment, independent of the tutoring conversation
- **Human-in-the-loop**: For high-stakes assessments, use LLM assessment as a first pass with human review

---

## 4. Language Teaching with LLMs

### 4.1 How LLMs Are Being Used for Language Learning

**Current applications (as of early 2025)**:

1. **Conversation practice**: The most natural and effective use. LLMs can engage in open-ended conversation in a target language, something previously impossible without a human partner. Examples: Duolingo Roleplay, ChatGPT voice mode, various startups

2. **Grammar explanation**: LLMs excel at explaining grammar rules in natural language, especially compared to traditional grammar textbooks. They can provide explanations tailored to the student's native language (e.g., explaining Malay grammar using English comparisons)

3. **Vocabulary in context**: Rather than flashcards with isolated words, LLMs can introduce vocabulary within meaningful sentences and stories, which research shows improves retention

4. **Error correction**: When a student writes/says something in the target language, the LLM can identify errors, explain why they're wrong, and provide the correct form

5. **Translation with explanation**: Beyond just translating, LLMs can explain *why* a translation works the way it does, covering nuances that machine translation alone misses

6. **Cultural context**: LLMs can explain when and why certain expressions are used, social register differences, and cultural context that pure grammar instruction misses

**Dedicated language learning AI products (beyond Duolingo)**:
- **Speak** (app): Focused on spoken conversation practice, using LLMs for generating responses and assessing speech
- **Lingolette**: AI conversation partner for language practice
- **Langotalk**: GPT-powered language learning through conversation
- **TalkPal**: AI language tutor for conversation practice
- **Elsa Speak**: AI pronunciation coach (predates LLMs but has integrated them)

### 4.2 Best Practices for Vocabulary and Grammar Instruction

**Vocabulary instruction**:

```
Effective vocabulary teaching pattern:
1. Introduce the word IN CONTEXT (a sentence or mini-story)
2. Provide the definition
3. Give 2-3 more example sentences showing different uses
4. Ask the student to create their own sentence using the word
5. Correct their sentence and explain any errors
6. Revisit the word in future conversations (spaced repetition)
```

**Key principles**:
- **Comprehensible input**: Present language that is slightly above the student's level (Krashen's i+1 hypothesis). LLMs can be prompted to calibrate this
- **Contextual learning**: Words learned in context (stories, conversations, situations) are retained far better than words learned in isolation
- **Active production**: Students should produce language (write sentences, have conversations), not just consume it
- **Spaced repetition**: Critical for long-term retention. LLMs alone don't implement this -- it requires an external system to track what's been learned and schedule reviews
- **Frequency-based ordering**: Teach the most common words first. Prompt the LLM with frequency lists for the target language

**Grammar instruction**:

```
Effective grammar teaching pattern:
1. Show an example of the grammar point in a natural sentence
2. Ask the student what they notice about the pattern
3. Explain the rule, using their native language grammar as a comparison point
4. Show correct and incorrect examples (minimal pairs)
5. Give the student exercises to practice the pattern
6. Provide immediate, specific feedback on errors
```

**Key principles**:
- **Inductive approach**: Show examples first, then extract rules (not the other way around)
- **Contrastive analysis**: Compare target language grammar to the student's native language to highlight differences
- **Error-focused practice**: After identifying a grammar error, generate multiple practice items targeting that specific pattern
- **Gradual complexity**: Start with basic sentence patterns and gradually introduce complexity

### 4.3 Low-Resource Languages (e.g., Malay)

**The challenge**: LLMs have far less training data for languages like Malay compared to English, Spanish, or French. This creates several issues:

**Specific problems for Malay**:
- **Lower fluency**: The model may produce grammatically awkward or unnatural Malay sentences
- **Vocabulary gaps**: Less common words may not be well-represented; the model may use Indonesian (Bahasa Indonesia) vocabulary/conventions interchangeably with Malaysian Malay (Bahasa Melayu) since they are closely related but have differences
- **Cultural specificity**: The model may conflate Malaysian and Indonesian cultural contexts
- **Formal vs. informal register**: Malay has significant register differences (formal/written vs. colloquial) that the model may not handle consistently
- **Dialect variation**: May struggle with regional variations and colloquialisms
- **Transliteration**: Older Malay texts use Jawi (Arabic script); the model may have limited knowledge of this

**Mitigation strategies for low-resource language teaching**:

1. **RAG with verified content**: Build a knowledge base of verified Malay language content (textbooks, grammar references, dictionaries) and use RAG to ground the LLM's responses

2. **Cross-lingual transfer**: Leverage the model's stronger knowledge of related languages (Indonesian) while being explicit about differences. The system prompt should note: "Bahasa Melayu and Bahasa Indonesia are related but different. Always use Malaysian Malay conventions unless specifically asked about Indonesian."

3. **Native speaker verification**: For a production system, have native Malay speakers review and correct a sample of the LLM's output to identify systematic errors

4. **Bilingual prompting**: Prompt the model in English about Malay language concepts. The model's English capabilities can be used to reason about Malay grammar and vocabulary, even when its Malay generation is imperfect

5. **Explicit grammar rules in context**: Include Malay grammar rules directly in the system prompt or RAG context rather than relying on the model's implicit knowledge

6. **Focus on what LLMs do well**: For low-resource languages, lean into explanation and grammar analysis (where English capability helps) rather than free-form generation (where Malay-specific training data matters most)

**Malay-specific teaching considerations**:
- Malay has relatively simple morphology compared to many languages (no grammatical gender, no verb conjugation for tense, no articles), which makes it in some ways easier for an LLM to teach
- The affixation system (prefixes, suffixes, circumfixes like me-...-kan, ber-...-an) is a key area of complexity that should be a focus
- Word order (SVO) is similar to English, which simplifies teaching to English speakers
- The distinction between base words and affixed forms is critical and should be explicitly taught
- Loanwords from Arabic, Sanskrit, Portuguese, Dutch, and English are common -- noting etymology can aid memorization

### 4.4 Conversation Practice and Error Correction

**Conversation practice design**:

```
System prompt structure for conversation practice:
- Define the scenario (e.g., "You are a vendor at a Malaysian pasar malam.
  The student is a customer.")
- Define the difficulty level and target vocabulary/grammar
- Instruct the model to stay in character and use target language primarily
- Tell the model when to switch to English for explanations (e.g., when the
  student is confused or makes a significant error)
- Tell the model to naturally incorporate target vocabulary into the conversation
```

**Error correction best practices**:

The research literature on error correction in language learning shows:
- **Recasting** (saying the correct version without explicitly pointing out the error) is less effective than **explicit correction** with explanation
- **Immediate correction** of every error can be discouraging and disrupt conversational flow
- **Selective correction** of errors related to the current learning focus is more effective
- **Positive feedback** on correct usage is as important as error correction

**Recommended error correction prompt strategy**:
```
When the student makes an error in [target language]:
1. If the error is related to today's lesson topic, correct it immediately:
   - Acknowledge what they communicated successfully
   - Point out the specific error
   - Provide the correct form
   - Briefly explain why
   - Ask them to try the sentence again
2. If the error is NOT related to today's topic:
   - Note it but don't interrupt the conversation
   - At the end of the conversation, provide a summary of other errors noticed
3. NEVER correct errors in a way that makes the student feel bad
4. Always acknowledge successful communication even when grammar is imperfect
```

**Cultural context integration**:
```
When teaching vocabulary or expressions, include cultural context:
- When is this expression used? (formal vs. informal situations)
- Regional variations (Peninsular Malaysia vs. East Malaysia vs. Singapore Malay)
- Cultural significance (e.g., honorifics, politeness conventions)
- Related customs or practices that affect language use
```

---

## 5. Agent Architectures for Education

### 5.1 Course Generation Agents

**What they do**: Automatically generate lesson plans, course outlines, exercises, and assessments from a curriculum specification.

**Common architecture**:
```
[Curriculum Spec] → [Planner Agent] → [Content Generator Agent] → [Review Agent]
                         ↓                      ↓                       ↓
                  Course outline        Lessons, exercises,      Quality check,
                  with learning         quizzes, examples        alignment to
                  objectives                                     learning objectives
```

**Key components**:
1. **Planner Agent**: Takes high-level learning objectives and breaks them into a sequenced curriculum. Uses pedagogical knowledge (prerequisite relationships, cognitive load management, spaced repetition scheduling) to order topics
2. **Content Generator Agent**: For each lesson, generates explanatory text, examples, practice problems, and assessments. Often uses RAG over reference materials
3. **Review Agent**: Checks generated content for accuracy, difficulty appropriateness, and alignment with learning objectives. May use a separate model or different prompt

**Challenges**:
- Ensuring coherent progression across lessons (each generated independently may not flow well together)
- Calibrating difficulty consistently
- Avoiding repetitive content across lessons
- Ensuring assessment items actually test the stated objectives

### 5.2 Assessment Agents

**Purpose**: Evaluate student knowledge, provide feedback, and determine readiness to advance.

**Architecture patterns**:

**Pattern 1: Question-Answer Assessment**
```
[Student Model] → [Question Selector] → [Student] → [Response Evaluator] → [Student Model Update]
     ↑                                                       ↓
     └───────────────────────────────────────────────────────┘
```

The assessment agent maintains a model of what the student knows, selects questions to probe uncertain areas, evaluates responses, and updates the student model. This is essentially computerized adaptive testing (CAT) but with LLM-generated questions and evaluation.

**Pattern 2: Portfolio Assessment**
```
[Student Work Product] → [Rubric + LLM Evaluator] → [Feedback Generator] → [Score + Explanation]
```

For longer-form work (essays, projects, code), the LLM evaluates against a rubric and provides detailed feedback.

**Pattern 3: Formative Assessment During Tutoring**
```
[Tutoring Conversation] → [Assessment Observer (separate agent)] → [Signals to Tutor Agent]
                                                                        ↓
                                                              "Student has mastered X"
                                                              "Student struggling with Y"
                                                              "Misconception detected: Z"
```

A separate assessment agent monitors the tutoring conversation and provides signals to the tutoring agent about the student's understanding. This separation of concerns allows the tutor to focus on teaching while the assessor focuses on evaluation.

### 5.3 Adaptive Routing Between Teaching Strategies

**The core idea**: Different students need different teaching approaches, and the same student needs different approaches at different times. An agent architecture can dynamically select the best strategy.

**Architecture**:
```
[Student Input] → [Router/Orchestrator Agent]
                         ↓
              ┌──────────┼──────────────┐
              ↓          ↓              ↓
        [Explainer]  [Socratic     [Practice
         Agent]       Questioner]   Generator]
              ↓          ↓              ↓
              └──────────┼──────────────┘
                         ↓
                   [Response to Student]
```

**Strategy selection signals**:
- Student says "I don't understand" → Switch to Explainer (direct instruction)
- Student gives partially correct answer → Switch to Socratic Questioner (guided discovery)
- Student demonstrates understanding → Switch to Practice Generator (reinforcement)
- Student is frustrated → Switch to easier material or encouragement mode
- Student is bored → Increase difficulty or switch to more engaging format

**Implementation approaches**:

**Approach 1: Classifier-based routing**
```python
# Pseudocode
student_state = assess_student_input(input)
if student_state.confusion_level > HIGH:
    response = explainer_agent.explain(topic, level=simpler)
elif student_state.partial_understanding:
    response = socratic_agent.guide(topic, student_state.misconception)
elif student_state.mastery > THRESHOLD:
    response = practice_agent.generate_exercise(topic, difficulty=harder)
```

**Approach 2: LLM-based routing (meta-agent)**
```
You are a teaching strategy router. Based on the student's message and
conversation history, choose ONE of the following strategies:
- EXPLAIN: Student needs direct explanation
- GUIDE: Student needs Socratic guidance to discover the answer
- PRACTICE: Student understands and needs practice
- REVIEW: Student needs review of previously learned material
- SIMPLIFY: Student is confused and needs a simpler starting point

Respond with ONLY the strategy name and a brief reason.
```

**Approach 3: Tool-use agent**
The LLM tutor has access to tools that implement different pedagogical strategies. It selects which tool to use based on the conversation:
```
Tools available:
- generate_explanation(topic, level): Creates a clear explanation
- generate_socratic_question(topic, student_misconception): Creates a guiding question
- generate_practice_problem(topic, difficulty): Creates a practice exercise
- generate_hint(problem, hint_level): Creates a hint for a current problem
- assess_understanding(conversation_history): Evaluates student understanding
- retrieve_curriculum_content(topic): Gets verified content from knowledge base
```

### 5.4 Full Agent Architecture Example

**A comprehensive educational agent system might look like**:

```
┌─────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                       │
│  (manages conversation flow, maintains student model) │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Student   │  │ Curriculum│  │ Conversation     │   │
│  │ Model     │  │ State     │  │ History          │   │
│  │ (knows,   │  │ (current  │  │ (full context)   │   │
│  │ doesn't   │  │ topic,    │  │                  │   │
│  │ know)     │  │ lesson)   │  │                  │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │           STRATEGY ROUTER                     │    │
│  │  Input: student message + model + curriculum  │    │
│  │  Output: which sub-agent to invoke            │    │
│  └──────────────────────────────────────────────┘    │
│         ↓              ↓              ↓               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ Teaching  │  │Assessment│  │ Practice     │       │
│  │ Agent     │  │ Agent    │  │ Agent        │       │
│  │ (explain, │  │ (quiz,   │  │ (exercises,  │       │
│  │  guide,   │  │  evaluate│  │  roleplay,   │       │
│  │  Socratic)│  │  feedback│  │  drills)     │       │
│  └──────────┘  └──────────┘  └──────────────┘       │
│         ↓              ↓              ↓               │
│  ┌──────────────────────────────────────────────┐    │
│  │         RESPONSE VALIDATOR                    │    │
│  │  - Fact check against curriculum              │    │
│  │  - Difficulty level check                     │    │
│  │  - Safety/appropriateness check               │    │
│  │  - "Did we give away the answer?" check       │    │
│  └──────────────────────────────────────────────┘    │
│                        ↓                              │
│                  [Response to Student]                 │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │              TOOL LAYER                        │    │
│  │  - RAG (curriculum content retrieval)          │    │
│  │  - Code execution (math verification)          │    │
│  │  - TTS/STT (for spoken language practice)      │    │
│  │  - Spaced repetition scheduler                 │    │
│  │  - Progress database                           │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Key design principles for educational agent architectures**:

1. **Separation of concerns**: Teaching, assessment, and content generation should be separate agents or at least separate prompts. Mixing them leads to confused behavior

2. **External state management**: The student model (what they know) and curriculum state (where they are) should be maintained externally, not solely in the conversation context. Context windows are finite and student models should persist across sessions

3. **Verification layers**: Every response should pass through a verification layer before reaching the student. At minimum: fact-check against curriculum, difficulty-level check, and answer-leak check

4. **Graceful degradation**: When the LLM fails (hallucination, confusion, off-topic), the system should detect this and fall back to pre-written content or escalate to a human

5. **Feedback loops**: Log conversations, analyze patterns of student confusion, and use this data to improve prompts, content, and routing logic over time

---

## 6. Key Takeaways and Recommendations

### What works well:
1. **Constrained domains beat open-ended tutoring**: Khanmigo and Duolingo succeed because they constrain the LLM to specific curriculum areas with verified content. A Malay language tutor should similarly constrain its domain
2. **Socratic prompting works but needs reinforcement**: Single-instruction Socratic prompts are fragile. Multi-layer prompting with response validation is more reliable
3. **Hybrid architectures outperform pure LLM**: The best systems combine LLMs with structured tools (spaced repetition, RAG, verification engines, progress tracking)
4. **AI-augmented human tutoring may be optimal**: The Tutor CoPilot research suggests LLMs supporting human tutors can outperform either alone
5. **Conversation practice is the killer app for language learning**: This is where LLMs provide the most unique value -- no other technology can provide open-ended conversation practice

### What to avoid:
1. **Don't rely on the LLM for factual accuracy**: Always ground in verified content, especially for low-resource languages
2. **Don't trust the LLM to maintain Socratic behavior**: Build verification layers that check for answer-leaking
3. **Don't use LLMs for high-stakes assessment**: Fine for formative (during learning) assessment, risky for summative (grading) assessment
4. **Don't assume the LLM's language output is correct for low-resource languages**: Verify Malay output quality with native speakers

### For a Malay language teaching agent specifically:
1. **Build a strong RAG knowledge base**: Malay grammar rules, vocabulary lists with frequency data, example sentences, cultural notes -- all verified by native speakers
2. **Focus on conversation practice + error correction**: This is the highest-value use case
3. **Implement explicit difficulty scaffolding**: Use CEFR levels (A1-C2) or a similar framework to calibrate difficulty
4. **Handle the Malay/Indonesian distinction explicitly**: System prompts must clarify which variety is being taught
5. **Use spaced repetition for vocabulary**: This requires external state management, not just conversation
6. **Integrate cultural context**: Malay language is deeply tied to cultural norms (respectful address, regional variations, Islamic influences on vocabulary)

---

## 7. Open Questions and Further Research Needed

**NOTE**: WebSearch and WebFetch tools were unavailable during this research session. The following items should be verified and expanded with live web research:

1. **Khanmigo quantitative results**: Has Khan Academy published controlled trial results (not just engagement metrics) by 2025/2026? Check blog.khanacademy.org and education research databases

2. **Duolingo Max expansion**: Has Duolingo expanded Max features to Malay or other Southeast Asian languages? Check blog.duolingo.com

3. **Latest open-source projects**: Search GitHub for "LLM tutor" and "language learning agent" sorted by stars and recent activity. Promising repos to check:
   - github.com/topics/ai-tutor
   - github.com/topics/language-learning
   - HuggingFace spaces for educational applications

4. **Recent papers to find and review**:
   - Search arxiv.org for "LLM tutoring" 2024-2026
   - Search Google Scholar for "large language model education" 2024-2026
   - Check ACL, EMNLP, NAACL proceedings for language learning + LLM papers
   - Check CHI, Learning at Scale, AIED proceedings for educational technology papers
   - Specific papers to look for:
     - Any replication/extension of the "Tutor CoPilot" work
     - Studies on LLM tutoring for low-resource languages
     - Comparative studies of different prompting strategies for teaching

5. **Malay-specific resources**:
   - Quality of GPT-4 / Claude / Llama for Malay language generation
   - Existing Malay language learning tools and apps
   - Malay NLP resources (corpora, benchmarks, evaluation datasets)
   - DBP (Dewan Bahasa dan Pustaka) digital resources that could be used for RAG

6. **Voice/speech integration**: How mature are TTS and STT systems for Malay? This would be critical for spoken conversation practice. Check:
   - Azure Cognitive Services Malay support
   - Google Cloud Speech-to-Text Malay support
   - OpenAI Whisper performance on Malay

7. **Regulatory/ethical considerations**: What are the guidelines around AI in education in Malaysia? Check Malaysia's AI governance framework and Ministry of Education policies

---

## 8. References and Sources to Verify

The following are sources referenced in this document that should be verified via live web research, as they are based on training knowledge rather than live retrieval:

### Books
- Khan, S. (2024). *Brave New Words: How AI Will Revolutionize Education (and Why That's a Good Thing)*. Viking.

### Papers (verify existence and details)
- Bloom, B. S. (1984). "The 2 Sigma Problem: The Search for Methods of Group Instruction as Effective as One-to-One Tutoring." *Educational Researcher*.
- Krashen, S. (1982). *Principles and Practice in Second Language Acquisition*. (Classic reference for i+1 hypothesis)
- Search for: Wang et al. (2024) on LLM writing feedback
- Search for: "Tutor CoPilot" (2024) -- verify authors, publication venue, and findings
- Search for: Harvard/MIT ChatGPT education study (2024)

### Websites and Products
- [Khanmigo](https://www.khanacademy.org/khan-labs) -- verify current status and features
- [Duolingo Max](https://blog.duolingo.com/duolingo-max/) -- verify current language support
- [Speak](https://www.speak.com/) -- verify current capabilities
- [Squirrel AI](https://squirrelai.com/) -- verify current status
- [Merlyn Mind](https://www.merlyn.org/) -- verify current status

### Frameworks and Libraries
- LangChain (langchain.com) -- educational agent examples
- LlamaIndex -- educational RAG patterns
- OpenAI Assistants API -- tutoring examples in cookbook

---

*This document should be updated when web search capabilities are available to verify claims, find additional sources, and identify the latest developments in this rapidly evolving field.*
