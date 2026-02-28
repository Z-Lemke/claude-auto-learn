#!/usr/bin/env python3
"""Tests for the FSRS (Free Spaced Repetition Scheduler) implementation."""

import math
from datetime import datetime, timezone, timedelta

import pytest

import fsrs
from fsrs import (
    FSRSState,
    Rating,
    calculate_retrievability,
    default_weights,
    get_due_items,
    initial_difficulty,
    initial_stability,
    review,
    schedule_next_review,
    update_difficulty,
    update_stability_failure,
    update_stability_success,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def weights():
    return default_weights()


@pytest.fixture
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _iso_days_ago(days: float) -> str:
    """Return an ISO datetime string for *days* days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# default_weights
# ---------------------------------------------------------------------------

class TestDefaultWeights:
    def test_returns_19_weights(self):
        w = default_weights()
        assert len(w) == 19

    def test_weight_values(self):
        w = default_weights()
        assert w[0] == 0.4
        assert w[3] == 5.8
        assert w[4] == 4.93


# ---------------------------------------------------------------------------
# initial_stability
# ---------------------------------------------------------------------------

class TestInitialStability:
    @pytest.mark.parametrize("rating,expected", [
        (Rating.AGAIN, 0.4),
        (Rating.HARD, 0.6),
        (Rating.GOOD, 2.4),
        (Rating.EASY, 5.8),
    ])
    def test_each_rating(self, rating, expected, weights):
        assert initial_stability(rating, weights) == expected


# ---------------------------------------------------------------------------
# initial_difficulty
# ---------------------------------------------------------------------------

class TestInitialDifficulty:
    @pytest.mark.parametrize("rating", [Rating.AGAIN, Rating.HARD, Rating.GOOD, Rating.EASY])
    def test_within_bounds(self, rating, weights):
        d = initial_difficulty(rating, weights)
        assert 1.0 <= d <= 10.0

    def test_again_harder_than_easy(self, weights):
        d_again = initial_difficulty(Rating.AGAIN, weights)
        d_easy = initial_difficulty(Rating.EASY, weights)
        assert d_again > d_easy

    def test_formula_good(self, weights):
        # D_0 = w[4] - exp(w[5] * (rating - 1)) + 1, rating=3
        expected = weights[4] - math.exp(weights[5] * 2) + 1
        expected = max(1.0, min(10.0, expected))
        assert math.isclose(initial_difficulty(Rating.GOOD, weights), expected, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# calculate_retrievability
# ---------------------------------------------------------------------------

class TestRetrievability:
    def test_zero_elapsed(self):
        assert calculate_retrievability(2.4, 0) == 1.0

    def test_decays_over_time(self):
        s = 2.4
        r0 = calculate_retrievability(s, 0)
        r1 = calculate_retrievability(s, 1)
        r10 = calculate_retrievability(s, 10)
        r30 = calculate_retrievability(s, 30)
        assert r0 > r1 > r10 > r30

    def test_at_one_day(self):
        s = 2.4
        expected = (1 + 1 / (9 * s)) ** (-1)
        assert math.isclose(calculate_retrievability(s, 1), expected, rel_tol=1e-9)

    def test_higher_stability_slower_decay(self):
        r_low = calculate_retrievability(1.0, 10)
        r_high = calculate_retrievability(10.0, 10)
        assert r_high > r_low

    def test_zero_stability(self):
        assert calculate_retrievability(0, 5) == 0.0


# ---------------------------------------------------------------------------
# update_stability_success
# ---------------------------------------------------------------------------

class TestUpdateStabilitySuccess:
    def test_stability_increases(self, weights):
        s = 2.4
        d = 5.0
        r = calculate_retrievability(s, 1)
        new_s = update_stability_success(d, s, r, Rating.GOOD, weights)
        assert new_s > s

    def test_easy_bonus(self, weights):
        s, d = 2.4, 5.0
        r = calculate_retrievability(s, 1)
        s_good = update_stability_success(d, s, r, Rating.GOOD, weights)
        s_easy = update_stability_success(d, s, r, Rating.EASY, weights)
        assert s_easy > s_good

    def test_hard_penalty(self, weights):
        s, d = 2.4, 5.0
        r = calculate_retrievability(s, 1)
        s_hard = update_stability_success(d, s, r, Rating.HARD, weights)
        s_good = update_stability_success(d, s, r, Rating.GOOD, weights)
        assert s_good > s_hard


# ---------------------------------------------------------------------------
# update_stability_failure
# ---------------------------------------------------------------------------

class TestUpdateStabilityFailure:
    def test_stability_decreases(self, weights):
        s = 10.0
        d = 5.0
        r = calculate_retrievability(s, 5)
        new_s = update_stability_failure(d, s, r, weights)
        assert new_s < s

    def test_minimum_stability(self, weights):
        new_s = update_stability_failure(10.0, 0.01, 0.01, weights)
        assert new_s >= 0.01


# ---------------------------------------------------------------------------
# update_difficulty
# ---------------------------------------------------------------------------

class TestUpdateDifficulty:
    def test_again_increases_difficulty(self, weights):
        d = 5.0
        new_d = update_difficulty(d, Rating.AGAIN, weights)
        assert new_d > d

    def test_easy_decreases_difficulty(self, weights):
        d = 5.0
        new_d = update_difficulty(d, Rating.EASY, weights)
        assert new_d < d

    def test_good_mean_reverts(self, weights):
        """Rating GOOD (3) means delta = 0, so only mean reversion acts."""
        d = 5.0
        new_d = update_difficulty(d, Rating.GOOD, weights)
        # Mean reversion pulls toward D_0(4) -- should stay near but not equal
        assert 1.0 <= new_d <= 10.0

    def test_clamped_low(self, weights):
        # Very low difficulty + EASY should not go below 1
        d = 1.0
        new_d = update_difficulty(d, Rating.EASY, weights)
        assert new_d >= 1.0

    def test_clamped_high(self, weights):
        # Very high difficulty + AGAIN should not exceed 10
        d = 10.0
        new_d = update_difficulty(d, Rating.AGAIN, weights)
        assert new_d <= 10.0


# ---------------------------------------------------------------------------
# review — new card (state=None)
# ---------------------------------------------------------------------------

class TestReviewNewCard:
    @pytest.mark.parametrize("rating", [Rating.AGAIN, Rating.HARD, Rating.GOOD, Rating.EASY])
    def test_creates_initial_state(self, rating, weights, now_iso):
        state = review(None, rating, review_date=now_iso, weights=weights)
        assert isinstance(state, FSRSState)
        assert state.reps == 1
        assert state.last_review == now_iso
        assert state.stability == initial_stability(rating, weights)
        assert math.isclose(state.difficulty, initial_difficulty(rating, weights), rel_tol=1e-9)

    def test_again_counts_lapse(self, weights, now_iso):
        state = review(None, Rating.AGAIN, review_date=now_iso, weights=weights)
        assert state.lapses == 1

    def test_good_no_lapse(self, weights, now_iso):
        state = review(None, Rating.GOOD, review_date=now_iso, weights=weights)
        assert state.lapses == 0


# ---------------------------------------------------------------------------
# review — subsequent reviews
# ---------------------------------------------------------------------------

class TestReviewExisting:
    def test_successful_review_increases_stability(self, weights):
        t0 = _iso_days_ago(1)
        t1 = datetime.now(timezone.utc).isoformat()
        state = review(None, Rating.GOOD, review_date=t0, weights=weights)
        old_s = state.stability
        state2 = review(state, Rating.GOOD, review_date=t1, weights=weights)
        assert state2.stability > old_s

    def test_failed_review_decreases_stability(self, weights):
        # Give the card a high stability first
        t0 = _iso_days_ago(10)
        t1 = _iso_days_ago(5)
        t2 = datetime.now(timezone.utc).isoformat()
        state = review(None, Rating.EASY, review_date=t0, weights=weights)
        state = review(state, Rating.EASY, review_date=t1, weights=weights)
        old_s = state.stability
        state = review(state, Rating.AGAIN, review_date=t2, weights=weights)
        assert state.stability < old_s

    def test_again_increments_lapses(self, weights):
        t0 = _iso_days_ago(1)
        t1 = datetime.now(timezone.utc).isoformat()
        state = review(None, Rating.GOOD, review_date=t0, weights=weights)
        assert state.lapses == 0
        state2 = review(state, Rating.AGAIN, review_date=t1, weights=weights)
        assert state2.lapses == 1

    def test_reps_increment(self, weights):
        t0 = _iso_days_ago(2)
        t1 = _iso_days_ago(1)
        t2 = datetime.now(timezone.utc).isoformat()
        s = review(None, Rating.GOOD, review_date=t0, weights=weights)
        assert s.reps == 1
        s = review(s, Rating.GOOD, review_date=t1, weights=weights)
        assert s.reps == 2
        s = review(s, Rating.EASY, review_date=t2, weights=weights)
        assert s.reps == 3


# ---------------------------------------------------------------------------
# schedule_next_review
# ---------------------------------------------------------------------------

class TestScheduleNextReview:
    def test_reasonable_interval_good(self, weights):
        s = initial_stability(Rating.GOOD, weights)  # 2.4
        days = schedule_next_review(s)
        # At 0.9 retention: t = 9 * 2.4 * (1/0.9 - 1) ≈ 2.4
        assert 0 < days < 30

    def test_higher_stability_longer_interval(self):
        d1 = schedule_next_review(1.0)
        d2 = schedule_next_review(10.0)
        assert d2 > d1

    def test_lower_retention_longer_interval(self):
        d_high = schedule_next_review(5.0, desired_retention=0.95)
        d_low = schedule_next_review(5.0, desired_retention=0.80)
        assert d_low > d_high

    def test_exact_value(self):
        # t = 9 * S * (1/R - 1)
        s = 5.0
        r = 0.9
        expected = 9.0 * s * (1.0 / r - 1.0)
        assert math.isclose(schedule_next_review(s, r), expected, rel_tol=1e-9)

    def test_invalid_retention(self):
        with pytest.raises(ValueError):
            schedule_next_review(5.0, desired_retention=0.0)
        with pytest.raises(ValueError):
            schedule_next_review(5.0, desired_retention=1.0)


# ---------------------------------------------------------------------------
# get_due_items
# ---------------------------------------------------------------------------

class TestGetDueItems:
    def test_returns_due_items(self):
        items = {
            "concept_a": {
                "fsrs_state": {
                    "stability": 1.0,
                    "last_review": _iso_days_ago(30),
                }
            },
            "concept_b": {
                "fsrs_state": {
                    "stability": 100.0,
                    "last_review": _iso_days_ago(1),
                }
            },
        }
        due = get_due_items(items, desired_retention=0.9)
        assert "concept_a" in due
        # concept_b has very high stability, should not be due after 1 day
        assert "concept_b" not in due

    def test_sorted_by_urgency(self):
        items = {
            "less_urgent": {
                "fsrs_state": {
                    "stability": 2.0,
                    "last_review": _iso_days_ago(5),
                }
            },
            "most_urgent": {
                "fsrs_state": {
                    "stability": 0.5,
                    "last_review": _iso_days_ago(30),
                }
            },
        }
        due = get_due_items(items, desired_retention=0.9)
        assert len(due) >= 1
        # most_urgent has lower retrievability -> should come first
        if len(due) == 2:
            assert due[0] == "most_urgent"

    def test_empty_items(self):
        assert get_due_items({}) == []

    def test_no_due_items(self):
        items = {
            "fresh": {
                "fsrs_state": {
                    "stability": 100.0,
                    "last_review": datetime.now(timezone.utc).isoformat(),
                }
            }
        }
        due = get_due_items(items, desired_retention=0.9)
        assert due == []

    def test_missing_last_review(self):
        items = {
            "no_review": {
                "fsrs_state": {
                    "stability": 5.0,
                }
            }
        }
        due = get_due_items(items, desired_retention=0.9)
        assert "no_review" in due


# ---------------------------------------------------------------------------
# FSRSState serialization
# ---------------------------------------------------------------------------

class TestFSRSStateSerialization:
    def test_round_trip(self, now_iso):
        state = FSRSState(difficulty=5.0, stability=2.4, last_review=now_iso, reps=3, lapses=1)
        d = state.to_dict()
        restored = FSRSState.from_dict(d)
        assert restored == state

    def test_to_dict_keys(self, now_iso):
        state = FSRSState(difficulty=5.0, stability=2.4, last_review=now_iso, reps=3, lapses=1)
        d = state.to_dict()
        assert set(d.keys()) == {"difficulty", "stability", "last_review", "reps", "lapses"}


# ---------------------------------------------------------------------------
# Rating enum
# ---------------------------------------------------------------------------

class TestRatingEnum:
    def test_values(self):
        assert Rating.AGAIN == 1
        assert Rating.HARD == 2
        assert Rating.GOOD == 3
        assert Rating.EASY == 4

    def test_ordering(self):
        assert Rating.AGAIN < Rating.HARD < Rating.GOOD < Rating.EASY
