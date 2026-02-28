#!/usr/bin/env python3
"""
Pure Python implementation of the FSRS (Free Spaced Repetition Scheduler) v4/v5 algorithm.

Based on the DSR (Difficulty, Stability, Retrievability) memory model.
No external dependencies -- requires only Python 3.8+ stdlib.

References:
    https://github.com/open-spaced-repetition/fsrs4anki
    https://github.com/open-spaced-repetition/py-fsrs
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import IntEnum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Rating(IntEnum):
    """Quality of recall during a review session."""
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass
class FSRSState:
    """Minimal state tracked per card / concept.

    Attributes:
        difficulty: Current difficulty estimate, clamped to [1, 10].
        stability:  Memory stability in days (expected half-life at R=0.9).
        last_review: ISO-8601 datetime string of the most recent review.
        reps:       Total number of reviews completed.
        lapses:     Number of times the card was forgotten (rated AGAIN).
    """
    difficulty: float
    stability: float
    last_review: str
    reps: int = 0
    lapses: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FSRSState":
        return cls(**d)


# ---------------------------------------------------------------------------
# Default weights (population-level priors from FSRS research)
# ---------------------------------------------------------------------------

def default_weights() -> List[float]:
    """Return the 19 FSRS default weights.

    Indices 0-3  : initial stability per rating (AGAIN..EASY)
    Index   4    : initial difficulty intercept
    Index   5    : initial difficulty slope
    Index   6    : difficulty update delta
    Index   7    : difficulty mean-reversion weight
    Index   8    : stability recall exponent factor
    Index   9    : stability recall stability exponent
    Index  10    : stability recall retrievability factor
    Index  11    : stability lapse base multiplier
    Index  12    : stability lapse difficulty exponent
    Index  13    : stability lapse stability exponent
    Index  14    : stability lapse retrievability factor
    Index  15    : hard penalty multiplier
    Index  16    : easy bonus multiplier
    Indices 17-18: reserved / unused
    """
    return [
        0.4, 0.6, 2.4, 5.8,       # w[0]-w[3]  initial stabilities
        4.93, 0.94, 0.86, 0.01,    # w[4]-w[7]  difficulty params
        1.49, 0.14, 0.94,          # w[8]-w[10] stability recall params
        2.18, 0.05, 0.34, 1.26,    # w[11]-w[14] stability lapse params
        0.29, 2.61,                # w[15]-w[16] hard penalty / easy bonus
        0.0, 0.0,                  # w[17]-w[18] reserved
    ]


# ---------------------------------------------------------------------------
# Core formulas
# ---------------------------------------------------------------------------

def calculate_retrievability(stability: float, days_elapsed: float) -> float:
    """Return the probability of recall given stability and elapsed time.

    Formula: R = (1 + t / (9 * S)) ^ (-1)

    Args:
        stability: Memory stability in days (S).
        days_elapsed: Time since last review in days (t).

    Returns:
        Retrievability in the range [0, 1].
    """
    if stability <= 0:
        return 0.0
    if days_elapsed <= 0:
        return 1.0
    return (1.0 + days_elapsed / (9.0 * stability)) ** (-1)


def initial_stability(rating: int, weights: List[float]) -> float:
    """Return the initial stability for a first review.

    S_0 = w[rating - 1]
    """
    rating = int(rating)
    if rating < 1 or rating > 4:
        raise ValueError(f"Rating must be 1-4, got {rating}")
    return weights[rating - 1]


def initial_difficulty(rating: int, weights: List[float]) -> float:
    """Return the initial difficulty for a first review.

    D_0 = w[4] - exp(w[5] * (rating - 1)) + 1
    Clamped to [1, 10].
    """
    rating = int(rating)
    d = weights[4] - math.exp(weights[5] * (rating - 1)) + 1
    return _clamp(d, 1.0, 10.0)


def update_stability_success(
    d: float,
    s: float,
    r: float,
    rating: int,
    weights: List[float],
) -> float:
    """Compute new stability after a successful recall (rating >= 2).

    S'_recall = S * (1 + exp(w[8]) * (11 - D) * S^(-w[9])
                * (exp(w[10] * (1 - R)) - 1) * hard_penalty * easy_bonus)

    Returns:
        New stability in days (always >= previous stability).
    """
    hard_penalty = weights[15] if rating == Rating.HARD else 1.0
    easy_bonus = weights[16] if rating == Rating.EASY else 1.0

    new_s = s * (
        1.0
        + math.exp(weights[8])
        * (11.0 - d)
        * (s ** (-weights[9]))
        * (math.exp(weights[10] * (1.0 - r)) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return max(new_s, 0.01)


def update_stability_failure(
    d: float,
    s: float,
    r: float,
    weights: List[float],
) -> float:
    """Compute new stability after a lapse (rating == AGAIN).

    S'_lapse = w[11] * D^(-w[12]) * ((S+1)^w[13] - 1) * exp(w[14] * (1 - R))

    Returns:
        New stability in days (minimum 0.01).
    """
    new_s = (
        weights[11]
        * (d ** (-weights[12]))
        * ((s + 1.0) ** weights[13] - 1.0)
        * math.exp(weights[14] * (1.0 - r))
    )
    return max(new_s, 0.01)


def update_difficulty(d: float, rating: int, weights: List[float]) -> float:
    """Update difficulty using mean-reversion formula.

    D' = w[7] * D_0(4) + (1 - w[7]) * (D - w[6] * (rating - 3))
    Clamped to [1, 10].

    The subtraction ensures AGAIN (rating=1) increases difficulty
    while EASY (rating=4) decreases it.
    """
    d0_easy = initial_difficulty(Rating.EASY, weights)
    new_d = weights[7] * d0_easy + (1.0 - weights[7]) * (d - weights[6] * (rating - 3))
    return _clamp(new_d, 1.0, 10.0)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def review(
    state: Optional[FSRSState],
    rating: int,
    review_date: Optional[str] = None,
    weights: Optional[List[float]] = None,
) -> FSRSState:
    """Process a single review and return the updated state.

    Args:
        state: Current card state, or None for first review.
        rating: Quality of recall (1=AGAIN, 2=HARD, 3=GOOD, 4=EASY).
        review_date: ISO-8601 datetime string. Defaults to now (UTC).
        weights: FSRS weight vector (length 19). Defaults to population defaults.

    Returns:
        New FSRSState reflecting the review outcome.
    """
    if weights is None:
        weights = default_weights()

    if review_date is None:
        review_date = datetime.now(timezone.utc).isoformat()

    rating = int(rating)

    # --- First review (new card) -------------------------------------------
    if state is None:
        s = initial_stability(rating, weights)
        d = initial_difficulty(rating, weights)
        return FSRSState(
            difficulty=d,
            stability=s,
            last_review=review_date,
            reps=1,
            lapses=1 if rating == Rating.AGAIN else 0,
        )

    # --- Subsequent reviews ------------------------------------------------
    days_elapsed = _days_between(state.last_review, review_date)
    r = calculate_retrievability(state.stability, days_elapsed)

    new_d = update_difficulty(state.difficulty, rating, weights)

    if rating == Rating.AGAIN:
        new_s = update_stability_failure(state.difficulty, state.stability, r, weights)
        new_lapses = state.lapses + 1
    else:
        new_s = update_stability_success(state.difficulty, state.stability, r, rating, weights)
        new_lapses = state.lapses

    return FSRSState(
        difficulty=new_d,
        stability=new_s,
        last_review=review_date,
        reps=state.reps + 1,
        lapses=new_lapses,
    )


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------

def schedule_next_review(
    stability: float,
    desired_retention: float = 0.9,
) -> float:
    """Return the number of days until the next review should occur.

    Derived from R = (1 + t/(9*S))^(-1) solved for t:
        t = 9 * S * (1/R - 1)

    Args:
        stability: Current memory stability in days.
        desired_retention: Target recall probability (default 0.9).

    Returns:
        Days until next review (float, >= 0).
    """
    if desired_retention <= 0.0 or desired_retention >= 1.0:
        raise ValueError("desired_retention must be in (0, 1)")
    if stability <= 0:
        return 0.0
    interval = 9.0 * stability * (1.0 / desired_retention - 1.0)
    return max(interval, 0.0)


def get_due_items(
    items: Dict[str, dict],
    desired_retention: float = 0.9,
) -> List[str]:
    """Return concept IDs whose retrievability has fallen below the target.

    Args:
        items: Mapping of concept_id -> dict with at least ``fsrs_state``
               (an FSRSState-compatible dict) and ``last_review`` (ISO string).
               The ``last_review`` inside ``fsrs_state`` is used if the
               top-level key is absent.
        desired_retention: Target recall probability.

    Returns:
        List of concept_id strings, sorted by retrievability ascending
        (most urgent first).
    """
    now = datetime.now(timezone.utc)
    scored: List[tuple] = []

    for concept_id, info in items.items():
        fs = info.get("fsrs_state", info)
        if isinstance(fs, FSRSState):
            fs = fs.to_dict()

        stability = fs.get("stability", 0.0)
        last_review_str = fs.get("last_review") or info.get("last_review")
        if last_review_str is None:
            # No review recorded -- treat as maximally due
            scored.append((concept_id, 0.0))
            continue

        last_dt = _parse_iso(last_review_str)
        elapsed = (now - last_dt).total_seconds() / 86400.0
        r = calculate_retrievability(stability, elapsed)

        if r < desired_retention:
            scored.append((concept_id, r))

    # Sort by retrievability ascending (most urgent first)
    scored.sort(key=lambda x: x[1])
    return [cid for cid, _ in scored]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 datetime string, tolerating several common formats."""
    # Python 3.7+ datetime.fromisoformat doesn't handle the trailing 'Z'
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _days_between(iso_a: str, iso_b: str) -> float:
    """Return the number of days between two ISO datetime strings."""
    a = _parse_iso(iso_a)
    b = _parse_iso(iso_b)
    return max((b - a).total_seconds() / 86400.0, 0.0)
