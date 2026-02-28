---
name: progress
description: >
  Shows learning progress, mastery levels, and recommendations for an active course.
  Trigger phrases: 'progress', 'how am I doing', 'show progress', 'my stats',
  'what should I study', 'where do I stand', 'status', 'dashboard', 'overview'.
---

# Progress Dashboard

Show the learner where they stand and help them decide what to do next.

## Load State

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
import json
from state import list_courses, load_course, load_progress, load_profile
from planner import get_frontier, get_review_items, compute_mastery_score, is_mastered
from fsrs import calculate_retrievability, schedule_next_review
from datetime import datetime, timezone

courses = list_courses()
for course in courses:
    data = load_course(course)
    if data is None:
        continue
    kg, curriculum, config = data
    progress = load_progress(course)
    if progress is None:
        continue
    frontier = get_frontier(kg, progress)
    reviews = get_review_items(progress)

    # Build per-concept mastery breakdown
    concept_details = []
    for cid, cp in progress.get('concepts', {}).items():
        mastery = compute_mastery_score(cp)
        concept_details.append({
            'id': cid,
            'status': cp.get('status', 'not_started'),
            'bloom_level': cp.get('bloom_level', 'remember'),
            'mastery_score': round(mastery, 2),
            'practice_count': cp.get('practice_count', 0),
            'recent_results': cp.get('recent_results', []),
        })

    # Sort by mastery score for strength/weakness display
    concept_details.sort(key=lambda x: x['mastery_score'], reverse=True)

    # Calculate next optimal session time
    next_review_date = None
    if reviews:
        first_review_cid = reviews[0]
        cp = progress['concepts'].get(first_review_cid, {})
        fsrs_data = cp.get('fsrs', {})
        stability = fsrs_data.get('stability', 1.0)
        next_days = schedule_next_review(stability)
        last_review = fsrs_data.get('last_review')
        if last_review:
            from datetime import timedelta
            lr = datetime.fromisoformat(last_review)
            next_review_date = (lr + timedelta(days=next_days)).isoformat()

    print(json.dumps({
        'course': course,
        'domain_type': config.get('domain_type', 'unknown'),
        'stats': progress.get('stats', {}),
        'frontier': frontier[:5],
        'reviews_due': reviews[:5],
        'total_concepts': len(kg.get('concepts', {})),
        'last_session': progress.get('last_session', 'never'),
        'top_concepts': concept_details[:5],
        'weak_concepts': [c for c in concept_details if c['mastery_score'] < 0.5 and c['status'] != 'not_started'][:5],
        'next_review_date': next_review_date,
    }, indent=2))
"
```

## Display

Present the following for each active course:

### Overall Progress
- **Course name** and description
- **Concepts mastered**: X / Y total (Z%)
- **Currently learning**: N concepts
- **Not yet started**: M concepts
- Progress bar: `[████████░░░░░░░░░░░░] 40%`

### Mastery Breakdown by Unit
For each unit in the curriculum:
- Unit name
- Concepts mastered / total in unit
- Status: Complete, In Progress, Not Started

### Strength Areas
- Concepts with highest mastery scores (top 5)
- Show mastery score as percentage: "Greetings: 92%, Numbers: 88%..."
- "You're solid on: [list]"

### Areas to Improve
- Concepts with low mastery or recent failures (mastery < 0.5)
- Show recent trend from `recent_results`: improving (more recent True), declining (more recent False), or flat
- "Focus on: [list]"

### Due for Review
- Items where FSRS says retrievability has dropped below threshold
- "These items need review soon: [list]"
- Show estimated retrievability percentage for each

### Optimal Next Session
- When the most urgent review is due: "Your next session is optimally scheduled for [date/timeframe]"
- If overdue: "You have overdue reviews — study soon for best retention!"

### Session History (Recent)
- Last 5 sessions: date, duration, concepts covered, performance
- Overall trend: improving, stable, or declining

### Knowledge Graph Observations
If the data suggests potential graph issues, note them:
- "You mastered [concept] without its prerequisite [prereq]. The prerequisite link may be unnecessary."
- "You've been stuck on [concept] for 5+ sessions. It may have a missing prerequisite."
- Offer: "Would you like me to adjust the course structure based on your learning patterns?"

### Recommendations
Based on the data, suggest ONE of:
- "Run `/study` to continue learning [next frontier concepts]"
- "Run `/quiz` to test your knowledge on [unit name]"
- "You have N items due for review — run `/study` to refresh them"
- "You've mastered everything! Consider expanding the course or starting a new one."

## Important Guidelines

- **Read-only** — this skill does NOT modify any state
- **Be encouraging but honest** — show real numbers, frame positively
- **Keep it scannable** — use tables, bullet points, and progress bars. Don't write paragraphs.
- **Actionable** — always end with a concrete next step
- **Show mastery scores** — use the computed mastery_score (0-100%) not just status labels
