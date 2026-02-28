#!/usr/bin/env python3
"""Session planning, knowledge-graph traversal, mastery checks, and adaptation.

Pure Python 3.8+ module with no external dependencies.
Imports from sibling modules ``fsrs`` and ``state``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import fsrs as _fsrs
import state as _state


# ---------------------------------------------------------------------------
# Bloom taxonomy constants
# ---------------------------------------------------------------------------

BLOOM_LEVELS: Dict[str, int] = {
    "remember": 1,
    "understand": 2,
    "apply": 3,
    "analyze": 4,
    "evaluate": 5,
    "create": 6,
}

_BLOOM_ORDER: List[str] = [
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
]


def bloom_level_value(level: str) -> int:
    """Return the integer value for a Bloom taxonomy level.

    Raises ``KeyError`` if *level* is not a recognised Bloom level name.
    """
    return BLOOM_LEVELS[level]


def next_bloom_level(current_level: str) -> Optional[str]:
    """Return the next Bloom level, or ``None`` if already at ``create``."""
    try:
        idx = _BLOOM_ORDER.index(current_level)
    except ValueError:
        return None
    if idx + 1 < len(_BLOOM_ORDER):
        return _BLOOM_ORDER[idx + 1]
    return None


# ---------------------------------------------------------------------------
# Knowledge-graph operations
# ---------------------------------------------------------------------------

def get_frontier(knowledge_graph: dict, progress: dict) -> List[str]:
    """Return concept IDs whose prerequisites are all mastered but which are
    themselves not yet mastered.

    A concept with no prerequisites and a status of ``"not_started"`` is
    considered part of the frontier.

    Returns a **sorted** list of concept IDs.
    """
    concepts = knowledge_graph.get("concepts", {})
    concept_progress = progress.get("concepts", {})
    frontier: List[str] = []

    for concept_id, concept_info in concepts.items():
        cp = concept_progress.get(concept_id, {})
        status = cp.get("status", "not_started")

        # Already mastered -- skip.
        if status == "mastered":
            continue

        prereqs = concept_info.get("prerequisites", [])
        all_prereqs_mastered = all(
            concept_progress.get(pid, {}).get("status") == "mastered"
            for pid in prereqs
        )

        if all_prereqs_mastered:
            frontier.append(concept_id)

    return sorted(frontier)


def get_prerequisite_chain(knowledge_graph: dict, concept_id: str) -> List[str]:
    """Return a topologically sorted list of **all** transitive prerequisites
    for *concept_id* (not including *concept_id* itself).
    """
    concepts = knowledge_graph.get("concepts", {})

    # Gather transitive prerequisites via DFS.
    visited: set = set()
    order: List[str] = []

    def _dfs(cid: str) -> None:
        if cid in visited:
            return
        visited.add(cid)
        info = concepts.get(cid, {})
        for prereq in info.get("prerequisites", []):
            _dfs(prereq)
        order.append(cid)

    # Start from the direct prerequisites of the target concept.
    target_info = concepts.get(concept_id, {})
    for prereq in target_info.get("prerequisites", []):
        _dfs(prereq)

    return order


def validate_graph(knowledge_graph: dict) -> List[str]:
    """Validate a knowledge graph and return a list of error strings.

    Checks performed:
    - Cycles in prerequisite relationships.
    - Prerequisites that reference non-existent concept IDs.
    - Orphaned concepts (no prerequisites AND no concept depends on them)
      **only** when there are 2+ concepts in the graph. A single-concept
      graph is valid on its own.

    Returns an empty list when the graph is valid.
    """
    concepts = knowledge_graph.get("concepts", {})
    errors: List[str] = []

    # --- Missing prerequisite references ---
    all_ids = set(concepts.keys())
    for cid, info in concepts.items():
        for prereq in info.get("prerequisites", []):
            if prereq not in all_ids:
                errors.append(
                    f"Concept '{cid}' has prerequisite '{prereq}' which does not exist"
                )

    # --- Cycle detection (Kahn's algorithm) ---
    in_degree: Dict[str, int] = {cid: 0 for cid in concepts}
    adj: Dict[str, List[str]] = {cid: [] for cid in concepts}
    for cid, info in concepts.items():
        for prereq in info.get("prerequisites", []):
            if prereq in all_ids:
                adj[prereq].append(cid)
                in_degree[cid] += 1

    queue: List[str] = [cid for cid, deg in in_degree.items() if deg == 0]
    topo_count = 0
    while queue:
        node = queue.pop(0)
        topo_count += 1
        for neighbour in adj.get(node, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if topo_count < len(concepts):
        errors.append("Knowledge graph contains a cycle")

    # --- Orphan detection (only meaningful for graphs with 2+ concepts) ---
    if len(concepts) >= 2:
        depended_on: set = set()
        has_prereqs: set = set()
        for cid, info in concepts.items():
            prereqs = info.get("prerequisites", [])
            if prereqs:
                has_prereqs.add(cid)
                for prereq in prereqs:
                    depended_on.add(prereq)

        for cid in concepts:
            if cid not in depended_on and cid not in has_prereqs:
                errors.append(f"Concept '{cid}' is orphaned (no connections)")

    return errors


def validate_graph_pedagogy(knowledge_graph: dict) -> List[str]:
    """Check pedagogical properties of a knowledge graph.

    Returns a list of warning strings (not errors — the graph is structurally
    valid but may have pedagogical issues).
    """
    concepts = knowledge_graph.get("concepts", {})
    warnings: List[str] = []

    # Check for concepts with too many prerequisites.
    for cid, info in concepts.items():
        prereqs = info.get("prerequisites", [])
        if len(prereqs) > 5:
            warnings.append(
                f"Concept '{cid}' has {len(prereqs)} prerequisites — "
                "consider if all are truly necessary"
            )

    # Check for very long prerequisite chains.
    max_depth = 0
    for cid in concepts:
        chain = get_prerequisite_chain(knowledge_graph, cid)
        if len(chain) > max_depth:
            max_depth = len(chain)
    if max_depth > 10:
        warnings.append(
            f"Deepest prerequisite chain is {max_depth} levels — "
            "consider if intermediate concepts can be parallelised"
        )

    # Check bloom_target vs difficulty heuristics.
    for cid, info in concepts.items():
        bloom = info.get("bloom_target", "apply")
        difficulty = info.get("difficulty", 0.5)
        if bloom == "remember" and difficulty > 0.7:
            warnings.append(
                f"Concept '{cid}' is high difficulty ({difficulty}) but targets "
                "'remember' — should this target 'apply' or 'analyze'?"
            )

    return warnings


# ---------------------------------------------------------------------------
# Mastery and adaptation
# ---------------------------------------------------------------------------

def compute_mastery_score(concept_progress: dict) -> float:
    """Compute a composite mastery score from multiple signals.

    Combines:
    - Accuracy (correct_count / practice_count), weighted 0.5
    - FSRS stability (normalised: stability of 30+ days = 1.0), weighted 0.3
    - Bloom level progress (normalised against 6 levels), weighted 0.2

    Returns a score in [0, 1].
    """
    practice = concept_progress.get("practice_count", 0)
    correct = concept_progress.get("correct_count", 0)

    # Accuracy component
    accuracy = correct / practice if practice > 0 else 0.0

    # Stability component (normalised: 30+ days of stability = 1.0)
    fsrs_data = concept_progress.get("fsrs", {})
    stability = fsrs_data.get("stability", 0.0)
    stability_normalised = min(stability / 30.0, 1.0)

    # Bloom component (normalised against 6 total levels)
    bloom = concept_progress.get("bloom_level", "remember")
    try:
        bloom_val = bloom_level_value(bloom)
    except KeyError:
        bloom_val = 1
    bloom_normalised = bloom_val / 6.0

    return 0.5 * accuracy + 0.3 * stability_normalised + 0.2 * bloom_normalised


def get_difficulty_adjustment(concept_progress: dict) -> str:
    """Return ``'easier'``, ``'harder'``, or ``'maintain'`` based on recent
    success rate.

    Uses ``recent_results`` (a list of booleans) when available, otherwise
    falls back to overall accuracy.
    """
    recent = concept_progress.get("recent_results", [])
    if recent and len(recent) >= 3:
        window = recent[-5:]
        accuracy = sum(window) / len(window)
    else:
        practice = concept_progress.get("practice_count", 0)
        correct = concept_progress.get("correct_count", 0)
        if practice < 3:
            return "maintain"
        accuracy = correct / practice

    if accuracy > 0.90:
        return "harder"
    elif accuracy < 0.65:
        return "easier"
    return "maintain"


def is_mastered(concept_progress: dict, bloom_target: str = "apply") -> bool:
    """Return ``True`` if the concept meets all mastery criteria.

    Criteria:
    - ``mastery_score`` >= 0.85
    - ``bloom_level`` value >= *bloom_target* value
    - ``practice_count`` >= 3
    """
    mastery = concept_progress.get("mastery_score", 0.0)
    bloom = concept_progress.get("bloom_level", "remember")
    practice = concept_progress.get("practice_count", 0)

    return (
        mastery >= 0.85
        and bloom_level_value(bloom) >= bloom_level_value(bloom_target)
        and practice >= 3
    )


def should_advance(concept_progress: dict) -> bool:
    """Return ``True`` if the learner should move to the next Bloom level.

    Criteria: recent accuracy > 0.80 AND practice_count >= 3.
    Uses ``recent_results`` (list of booleans) when available for a more
    accurate recency signal.  Falls back to overall accuracy otherwise.
    """
    practice = concept_progress.get("practice_count", 0)
    if practice < 3:
        return False

    # Prefer recent_results window when available.
    recent = concept_progress.get("recent_results", [])
    if recent and len(recent) >= 3:
        window = recent[-5:]
        accuracy = sum(window) / len(window)
    else:
        correct = concept_progress.get("correct_count", 0)
        accuracy = correct / practice if practice > 0 else 0.0

    return accuracy > 0.80


def should_remediate(concept_progress: dict) -> bool:
    """Return ``True`` if the learner is struggling and needs remediation.

    Criteria:
    - recent accuracy < 0.50, **OR**
    - practice_count >= 5 AND mastery_score < 0.4
    """
    practice = concept_progress.get("practice_count", 0)
    correct = concept_progress.get("correct_count", 0)
    mastery = concept_progress.get("mastery_score", 0.0)

    accuracy = correct / practice if practice > 0 else 0.0

    if accuracy < 0.50:
        return True
    if practice >= 5 and mastery < 0.4:
        return True
    return False


def suggest_pivot(
    knowledge_graph: dict,
    progress: dict,
    current_concept: str,
) -> List[str]:
    """Suggest up to 3 alternative frontier concepts when the learner is
    struggling with *current_concept*.

    Excludes *current_concept* and any concept that depends (transitively)
    on *current_concept*.  Results are sorted by difficulty (easiest first,
    using the concept's ``difficulty`` field, defaulting to 1).
    """
    concepts = knowledge_graph.get("concepts", {})

    # Build set of concepts that transitively depend on current_concept.
    dependents: set = set()

    def _collect_dependents(cid: str) -> None:
        for other_id, other_info in concepts.items():
            if cid in other_info.get("prerequisites", []) and other_id not in dependents:
                dependents.add(other_id)
                _collect_dependents(other_id)

    _collect_dependents(current_concept)

    # Get frontier and filter.
    frontier = get_frontier(knowledge_graph, progress)
    candidates = [
        cid for cid in frontier
        if cid != current_concept and cid not in dependents
    ]

    # Sort by difficulty (easiest first).
    def _difficulty(cid: str) -> float:
        return concepts.get(cid, {}).get("difficulty", 1)

    candidates.sort(key=_difficulty)
    return candidates[:3]


# ---------------------------------------------------------------------------
# Review helpers
# ---------------------------------------------------------------------------

def get_review_items(progress: dict, n: int = 5) -> List[str]:
    """Return up to *n* concept IDs due for FSRS review, sorted by urgency
    (lowest retrievability first).

    Only concepts with status ``"learning"`` or ``"mastered"`` are
    considered.
    """
    concept_progress = progress.get("concepts", {})
    eligible: Dict[str, dict] = {}

    for cid, cp in concept_progress.items():
        status = cp.get("status", "not_started")
        if status in ("learning", "mastered"):
            fsrs_data = cp.get("fsrs", {})
            # Only include if there has been at least one review.
            if fsrs_data.get("last_review") is not None:
                eligible[cid] = {"fsrs_state": fsrs_data}

    if not eligible:
        return []

    # get_due_items returns IDs sorted by retrievability ascending (most
    # urgent first).
    due = _fsrs.get_due_items(eligible)
    return due[:n]


# ---------------------------------------------------------------------------
# Session planning
# ---------------------------------------------------------------------------

def plan_session(
    knowledge_graph: dict,
    progress: dict,
    duration_minutes: int = 25,
    new_ratio: float = 0.6,
) -> dict:
    """Create a session plan mixing new concepts and reviews.

    Returns a dict with keys:
    - ``new_concepts``: list of new concept IDs to introduce.
    - ``review_concepts``: list of concept IDs due for review.
    - ``plan``: ordered list of ``{"type": ..., "concept_id": ...}`` dicts.
    - ``estimated_minutes``: estimated session length.

    Approximately *new_ratio* of interactions target new material and the
    remainder targets review.  Interactions are interleaved so that new and
    review items are mixed.
    """
    minutes_per_interaction = 3
    total_slots = max(duration_minutes // minutes_per_interaction, 1)

    # Determine new concepts from the frontier.
    frontier = get_frontier(knowledge_graph, progress)
    review_candidates = get_review_items(progress, n=total_slots)

    # Allocate slots.
    new_slots = round(total_slots * new_ratio)
    review_slots = total_slots - new_slots

    # If one pool is empty, give all slots to the other.
    if not frontier:
        new_slots = 0
        review_slots = total_slots
    if not review_candidates:
        review_slots = 0
        new_slots = total_slots

    # Select concepts for each pool.
    # For new concepts, pick as many distinct concepts as needed; each
    # concept may get multiple interactions (intro + practice + assess).
    # Heuristic: ~2-3 interactions per new concept.
    interactions_per_new_concept = 3
    num_new_concepts = max(new_slots // interactions_per_new_concept, 1) if new_slots > 0 else 0
    num_new_concepts = min(num_new_concepts, len(frontier))

    new_concepts = frontier[:num_new_concepts]
    review_concepts = review_candidates[:review_slots]

    # Build the plan list.
    plan: List[dict] = []

    # Distribute new-concept interactions.
    new_items: List[dict] = []
    if new_concepts:
        # First pass: one "new" per concept.
        for cid in new_concepts:
            new_items.append({"type": "new", "concept_id": cid})
        # Fill remaining new slots with practice/assess for new concepts.
        remaining_new = new_slots - len(new_items)
        types_cycle = ["new", "assess"]
        idx = 0
        while remaining_new > 0:
            cid = new_concepts[idx % len(new_concepts)]
            t = types_cycle[idx % len(types_cycle)]
            new_items.append({"type": t, "concept_id": cid})
            remaining_new -= 1
            idx += 1

    review_items: List[dict] = []
    for cid in review_concepts:
        review_items.append({"type": "review", "concept_id": cid})
    # If we have more review slots than concepts, cycle through.
    remaining_review = review_slots - len(review_items)
    r_idx = 0
    while remaining_review > 0 and review_concepts:
        cid = review_concepts[r_idx % len(review_concepts)]
        review_items.append({"type": "review", "concept_id": cid})
        remaining_review -= 1
        r_idx += 1

    # Interleave: alternate between new and review items.
    ni = 0
    ri = 0
    while ni < len(new_items) or ri < len(review_items):
        if ni < len(new_items):
            plan.append(new_items[ni])
            ni += 1
        if ri < len(review_items):
            plan.append(review_items[ri])
            ri += 1

    estimated = len(plan) * minutes_per_interaction

    return {
        "new_concepts": new_concepts,
        "review_concepts": review_concepts,
        "plan": plan,
        "estimated_minutes": estimated,
    }
