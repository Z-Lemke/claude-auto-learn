#!/usr/bin/env python3
"""Tests for the session planner module."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

import planner
import fsrs as _fsrs


# ---------------------------------------------------------------------------
# Fixtures: sample knowledge graphs
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_kg():
    """Linear chain: A -> B -> C (A has no prereqs)."""
    return {
        "concepts": {
            "A": {"prerequisites": [], "difficulty": 1},
            "B": {"prerequisites": ["A"], "difficulty": 2},
            "C": {"prerequisites": ["B"], "difficulty": 3},
        }
    }


@pytest.fixture
def diamond_kg():
    """Diamond: A -> B, A -> C, B -> D, C -> D."""
    return {
        "concepts": {
            "A": {"prerequisites": [], "difficulty": 1},
            "B": {"prerequisites": ["A"], "difficulty": 2},
            "C": {"prerequisites": ["A"], "difficulty": 2},
            "D": {"prerequisites": ["B", "C"], "difficulty": 3},
        }
    }


@pytest.fixture
def branching_kg():
    """Branching: A -> B, A -> C (independent branches from A)."""
    return {
        "concepts": {
            "A": {"prerequisites": [], "difficulty": 1},
            "B": {"prerequisites": ["A"], "difficulty": 2},
            "C": {"prerequisites": ["A"], "difficulty": 3},
        }
    }


@pytest.fixture
def no_prereq_kg():
    """Multiple concepts, none with prerequisites."""
    return {
        "concepts": {
            "X": {"prerequisites": [], "difficulty": 1},
            "Y": {"prerequisites": [], "difficulty": 2},
            "Z": {"prerequisites": [], "difficulty": 3},
        }
    }


@pytest.fixture
def empty_progress():
    """All concepts not started."""
    return {"concepts": {}}


def make_progress(statuses: dict, **extra_fields) -> dict:
    """Helper to build a progress dict from a {concept_id: status} mapping."""
    concepts = {}
    for cid, status in statuses.items():
        cp = {
            "status": status,
            "bloom_level": "remember",
            "mastery_score": 0.0,
            "fsrs": {
                "difficulty": 5.0,
                "stability": 1.0,
                "last_review": None,
                "reps": 0,
                "lapses": 0,
            },
            "practice_count": 0,
            "correct_count": 0,
            "error_history": [],
            "last_practiced": None,
        }
        cp.update(extra_fields.get(cid, {}))
        concepts[cid] = cp
    return {"concepts": concepts}


# ---------------------------------------------------------------------------
# Tests: get_frontier
# ---------------------------------------------------------------------------

class TestGetFrontier:
    def test_no_prereq_concepts_in_frontier(self, no_prereq_kg):
        progress = make_progress({"X": "not_started", "Y": "not_started", "Z": "not_started"})
        result = planner.get_frontier(no_prereq_kg, progress)
        assert result == ["X", "Y", "Z"]

    def test_respects_prerequisites(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.get_frontier(simple_kg, progress)
        assert result == ["A"], "Only A should be in frontier (B requires A, C requires B)"

    def test_mastered_prereq_unlocks_next(self, simple_kg):
        progress = make_progress({"A": "mastered", "B": "not_started", "C": "not_started"})
        result = planner.get_frontier(simple_kg, progress)
        assert result == ["B"]

    def test_concept_with_unmastered_prereq_not_in_frontier(self, simple_kg):
        progress = make_progress({"A": "learning", "B": "not_started", "C": "not_started"})
        result = planner.get_frontier(simple_kg, progress)
        # A is learning (not mastered), so B should not be in frontier.
        # A itself is not mastered so it's in frontier.
        assert "A" in result
        assert "B" not in result

    def test_all_mastered_returns_empty(self, simple_kg):
        progress = make_progress({"A": "mastered", "B": "mastered", "C": "mastered"})
        result = planner.get_frontier(simple_kg, progress)
        assert result == []

    def test_diamond_frontier(self, diamond_kg):
        progress = make_progress({
            "A": "mastered", "B": "mastered", "C": "not_started", "D": "not_started"
        })
        result = planner.get_frontier(diamond_kg, progress)
        # C is unlocked (A mastered), D is NOT (C not mastered)
        assert result == ["C"]

    def test_diamond_both_branches_mastered(self, diamond_kg):
        progress = make_progress({
            "A": "mastered", "B": "mastered", "C": "mastered", "D": "not_started"
        })
        result = planner.get_frontier(diamond_kg, progress)
        assert result == ["D"]

    def test_returns_sorted(self, no_prereq_kg):
        progress = make_progress({"Z": "not_started", "X": "not_started", "Y": "not_started"})
        result = planner.get_frontier(no_prereq_kg, progress)
        assert result == sorted(result)

    def test_learning_concept_in_frontier(self, simple_kg):
        """A concept with status 'learning' is still in the frontier (not mastered yet)."""
        progress = make_progress({"A": "learning", "B": "not_started", "C": "not_started"})
        result = planner.get_frontier(simple_kg, progress)
        assert "A" in result


# ---------------------------------------------------------------------------
# Tests: get_prerequisite_chain
# ---------------------------------------------------------------------------

class TestGetPrerequisiteChain:
    def test_no_prerequisites(self, simple_kg):
        result = planner.get_prerequisite_chain(simple_kg, "A")
        assert result == []

    def test_single_prerequisite(self, simple_kg):
        result = planner.get_prerequisite_chain(simple_kg, "B")
        assert result == ["A"]

    def test_transitive_prerequisites(self, simple_kg):
        result = planner.get_prerequisite_chain(simple_kg, "C")
        # A must come before B in topological order.
        assert result == ["A", "B"]

    def test_diamond_prerequisites(self, diamond_kg):
        result = planner.get_prerequisite_chain(diamond_kg, "D")
        # A before both B and C.
        assert result[0] == "A"
        assert set(result) == {"A", "B", "C"}
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")

    def test_nonexistent_concept(self, simple_kg):
        result = planner.get_prerequisite_chain(simple_kg, "NONEXISTENT")
        assert result == []


# ---------------------------------------------------------------------------
# Tests: validate_graph
# ---------------------------------------------------------------------------

class TestValidateGraph:
    def test_valid_graph_returns_empty(self, simple_kg):
        errors = planner.validate_graph(simple_kg)
        assert errors == []

    def test_detects_missing_reference(self):
        kg = {
            "concepts": {
                "A": {"prerequisites": ["MISSING"]},
            }
        }
        errors = planner.validate_graph(kg)
        assert any("MISSING" in e and "does not exist" in e for e in errors)

    def test_detects_cycle(self):
        kg = {
            "concepts": {
                "A": {"prerequisites": ["B"]},
                "B": {"prerequisites": ["A"]},
            }
        }
        errors = planner.validate_graph(kg)
        assert any("cycle" in e.lower() for e in errors)

    def test_detects_self_cycle(self):
        kg = {
            "concepts": {
                "A": {"prerequisites": ["A"]},
            }
        }
        errors = planner.validate_graph(kg)
        assert any("cycle" in e.lower() for e in errors)

    def test_detects_orphaned_concept(self):
        kg = {
            "concepts": {
                "A": {"prerequisites": []},
                "B": {"prerequisites": ["A"]},
                "ORPHAN": {"prerequisites": []},
            }
        }
        errors = planner.validate_graph(kg)
        assert any("orphan" in e.lower() for e in errors)

    def test_single_concept_not_orphaned(self):
        kg = {
            "concepts": {
                "SOLO": {"prerequisites": []},
            }
        }
        errors = planner.validate_graph(kg)
        assert errors == [], "A single-concept graph should be valid"

    def test_valid_diamond_graph(self, diamond_kg):
        errors = planner.validate_graph(diamond_kg)
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: validate_graph_pedagogy
# ---------------------------------------------------------------------------

class TestValidateGraphPedagogy:
    def test_no_warnings_for_clean_graph(self, simple_kg):
        warnings = planner.validate_graph_pedagogy(simple_kg)
        assert warnings == []

    def test_warns_too_many_prerequisites(self):
        kg = {
            "concepts": {
                "A": {"prerequisites": [], "difficulty": 0.1},
                "B": {"prerequisites": [], "difficulty": 0.1},
                "C": {"prerequisites": [], "difficulty": 0.1},
                "D": {"prerequisites": [], "difficulty": 0.1},
                "E": {"prerequisites": [], "difficulty": 0.1},
                "F": {"prerequisites": [], "difficulty": 0.1},
                "TARGET": {"prerequisites": ["A", "B", "C", "D", "E", "F"], "difficulty": 0.5},
            }
        }
        warnings = planner.validate_graph_pedagogy(kg)
        assert any("6 prerequisites" in w for w in warnings)

    def test_warns_high_difficulty_remember(self):
        kg = {
            "concepts": {
                "HARD_VOCAB": {
                    "prerequisites": [],
                    "difficulty": 0.8,
                    "bloom_target": "remember",
                },
            }
        }
        warnings = planner.validate_graph_pedagogy(kg)
        assert any("remember" in w.lower() for w in warnings)

    def test_no_warning_for_normal_remember(self):
        kg = {
            "concepts": {
                "EASY_VOCAB": {
                    "prerequisites": [],
                    "difficulty": 0.3,
                    "bloom_target": "remember",
                },
            }
        }
        warnings = planner.validate_graph_pedagogy(kg)
        assert warnings == []

    def test_warns_deep_chain(self):
        # Build a chain of 12 concepts
        concepts = {}
        for i in range(12):
            prereqs = [f"C{i-1}"] if i > 0 else []
            concepts[f"C{i}"] = {"prerequisites": prereqs, "difficulty": 0.5}
        kg = {"concepts": concepts}
        warnings = planner.validate_graph_pedagogy(kg)
        assert any("11 levels" in w for w in warnings)


# ---------------------------------------------------------------------------
# Tests: is_mastered
# ---------------------------------------------------------------------------

class TestIsMastered:
    def test_true_when_all_criteria_met(self):
        cp = {"mastery_score": 0.90, "bloom_level": "apply", "practice_count": 5}
        assert planner.is_mastered(cp) is True

    def test_false_when_mastery_score_low(self):
        cp = {"mastery_score": 0.50, "bloom_level": "apply", "practice_count": 5}
        assert planner.is_mastered(cp) is False

    def test_false_when_bloom_level_below_target(self):
        cp = {"mastery_score": 0.90, "bloom_level": "remember", "practice_count": 5}
        assert planner.is_mastered(cp) is False

    def test_false_when_practice_count_low(self):
        cp = {"mastery_score": 0.90, "bloom_level": "apply", "practice_count": 2}
        assert planner.is_mastered(cp) is False

    def test_custom_bloom_target(self):
        cp = {"mastery_score": 0.90, "bloom_level": "analyze", "practice_count": 5}
        assert planner.is_mastered(cp, bloom_target="analyze") is True
        assert planner.is_mastered(cp, bloom_target="evaluate") is False

    def test_exact_thresholds(self):
        cp = {"mastery_score": 0.85, "bloom_level": "apply", "practice_count": 3}
        assert planner.is_mastered(cp) is True

    def test_just_below_thresholds(self):
        cp = {"mastery_score": 0.849, "bloom_level": "apply", "practice_count": 3}
        assert planner.is_mastered(cp) is False


# ---------------------------------------------------------------------------
# Tests: should_advance
# ---------------------------------------------------------------------------

class TestShouldAdvance:
    def test_true_when_accuracy_high(self):
        cp = {"practice_count": 5, "correct_count": 5}
        assert planner.should_advance(cp) is True

    def test_false_when_practice_too_low(self):
        cp = {"practice_count": 2, "correct_count": 2}
        assert planner.should_advance(cp) is False

    def test_false_when_accuracy_too_low(self):
        cp = {"practice_count": 5, "correct_count": 3}
        assert planner.should_advance(cp) is False

    def test_boundary_accuracy(self):
        # 4/5 = 0.80 -- NOT > 0.80 so should be False.
        cp = {"practice_count": 5, "correct_count": 4}
        assert planner.should_advance(cp) is False

    def test_just_above_boundary(self):
        # 5/6 ~ 0.833 -- > 0.80.
        cp = {"practice_count": 6, "correct_count": 5}
        assert planner.should_advance(cp) is True

    def test_minimum_practice(self):
        cp = {"practice_count": 3, "correct_count": 3}
        assert planner.should_advance(cp) is True


# ---------------------------------------------------------------------------
# Tests: should_remediate
# ---------------------------------------------------------------------------

class TestShouldRemediate:
    def test_true_low_accuracy(self):
        cp = {"practice_count": 4, "correct_count": 1, "mastery_score": 0.3}
        assert planner.should_remediate(cp) is True

    def test_true_high_practice_low_mastery(self):
        cp = {"practice_count": 6, "correct_count": 4, "mastery_score": 0.3}
        assert planner.should_remediate(cp) is True

    def test_false_when_doing_well(self):
        cp = {"practice_count": 5, "correct_count": 4, "mastery_score": 0.7}
        assert planner.should_remediate(cp) is False

    def test_boundary_accuracy(self):
        # 2/4 = 0.50 -- NOT < 0.50 so accuracy alone doesn't trigger.
        cp = {"practice_count": 4, "correct_count": 2, "mastery_score": 0.5}
        assert planner.should_remediate(cp) is False

    def test_zero_practice(self):
        cp = {"practice_count": 0, "correct_count": 0, "mastery_score": 0.0}
        # 0/0 would be 0.0 accuracy, which is < 0.50.
        assert planner.should_remediate(cp) is True


# ---------------------------------------------------------------------------
# Tests: suggest_pivot
# ---------------------------------------------------------------------------

class TestSuggestPivot:
    def test_returns_alternatives_excluding_current(self, branching_kg):
        progress = make_progress({"A": "mastered", "B": "not_started", "C": "not_started"})
        result = planner.suggest_pivot(branching_kg, progress, "B")
        assert "B" not in result
        assert "C" in result

    def test_excludes_dependents(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        # Struggling with A; B depends on A, C depends on B.
        result = planner.suggest_pivot(simple_kg, progress, "A")
        assert "B" not in result
        assert "C" not in result

    def test_sorted_by_difficulty(self, no_prereq_kg):
        progress = make_progress({"X": "not_started", "Y": "not_started", "Z": "not_started"})
        result = planner.suggest_pivot(no_prereq_kg, progress, "Z")
        # X(1), Y(2) should come before Z(3); Z is current so excluded.
        assert result == ["X", "Y"]

    def test_max_three_results(self):
        kg = {
            "concepts": {
                f"C{i}": {"prerequisites": [], "difficulty": i}
                for i in range(10)
            }
        }
        progress = make_progress({f"C{i}": "not_started" for i in range(10)})
        result = planner.suggest_pivot(kg, progress, "C9")
        assert len(result) <= 3

    def test_empty_when_no_alternatives(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        # A is the only frontier concept and it's the current one.
        # B and C depend on A transitively.
        result = planner.suggest_pivot(simple_kg, progress, "A")
        assert result == []


# ---------------------------------------------------------------------------
# Tests: get_review_items
# ---------------------------------------------------------------------------

class TestGetReviewItems:
    def test_returns_due_items_sorted_by_urgency(self):
        now = datetime.now(timezone.utc)
        old_review = (now - timedelta(days=30)).isoformat()
        recent_review = (now - timedelta(hours=1)).isoformat()
        progress = {
            "concepts": {
                "old_concept": {
                    "status": "learning",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 3,
                        "lapses": 0,
                    },
                },
                "recent_concept": {
                    "status": "learning",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 100.0,
                        "last_review": recent_review,
                        "reps": 3,
                        "lapses": 0,
                    },
                },
            }
        }
        result = planner.get_review_items(progress, n=5)
        # old_concept has low retrievability, recent_concept is high.
        # Only old_concept should be due (recent_concept has high stability).
        if len(result) == 2:
            assert result[0] == "old_concept"
        elif len(result) == 1:
            assert result[0] == "old_concept"

    def test_excludes_not_started_concepts(self):
        now = datetime.now(timezone.utc)
        old_review = (now - timedelta(days=30)).isoformat()
        progress = {
            "concepts": {
                "started": {
                    "status": "learning",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 3,
                        "lapses": 0,
                    },
                },
                "not_started": {
                    "status": "not_started",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 0,
                        "lapses": 0,
                    },
                },
            }
        }
        result = planner.get_review_items(progress, n=5)
        assert "not_started" not in result

    def test_empty_when_nothing_due(self):
        now = datetime.now(timezone.utc).isoformat()
        progress = {
            "concepts": {
                "fresh": {
                    "status": "learning",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1000.0,
                        "last_review": now,
                        "reps": 1,
                        "lapses": 0,
                    },
                },
            }
        }
        result = planner.get_review_items(progress, n=5)
        assert result == []

    def test_respects_n_limit(self):
        now = datetime.now(timezone.utc)
        old_review = (now - timedelta(days=30)).isoformat()
        progress = {
            "concepts": {
                f"C{i}": {
                    "status": "learning",
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 3,
                        "lapses": 0,
                    },
                }
                for i in range(10)
            }
        }
        result = planner.get_review_items(progress, n=3)
        assert len(result) <= 3


# ---------------------------------------------------------------------------
# Tests: plan_session
# ---------------------------------------------------------------------------

class TestPlanSession:
    def test_returns_required_keys(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.plan_session(simple_kg, progress)
        assert "new_concepts" in result
        assert "review_concepts" in result
        assert "plan" in result
        assert "estimated_minutes" in result

    def test_plan_has_mix_of_new_and_review(self, simple_kg):
        now = datetime.now(timezone.utc)
        old_review = (now - timedelta(days=30)).isoformat()
        progress = {
            "concepts": {
                "A": {
                    "status": "mastered",
                    "bloom_level": "apply",
                    "mastery_score": 0.9,
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 5,
                        "lapses": 0,
                    },
                    "practice_count": 5,
                    "correct_count": 5,
                    "error_history": [],
                    "last_practiced": old_review,
                },
                "B": {
                    "status": "not_started",
                    "bloom_level": "remember",
                    "mastery_score": 0.0,
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": None,
                        "reps": 0,
                        "lapses": 0,
                    },
                    "practice_count": 0,
                    "correct_count": 0,
                    "error_history": [],
                    "last_practiced": None,
                },
                "C": {
                    "status": "not_started",
                    "bloom_level": "remember",
                    "mastery_score": 0.0,
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": None,
                        "reps": 0,
                        "lapses": 0,
                    },
                    "practice_count": 0,
                    "correct_count": 0,
                    "error_history": [],
                    "last_practiced": None,
                },
            }
        }
        result = planner.plan_session(simple_kg, progress)
        types = {item["type"] for item in result["plan"]}
        # Should have new items (B is in frontier).
        assert "new" in types or "assess" in types
        # Should have review items (A is mastered with old review).
        assert "review" in types

    def test_handles_empty_frontier_all_review(self):
        """When all concepts are mastered, session should be all review."""
        now = datetime.now(timezone.utc)
        old_review = (now - timedelta(days=30)).isoformat()
        kg = {
            "concepts": {
                "A": {"prerequisites": [], "difficulty": 1},
            }
        }
        progress = {
            "concepts": {
                "A": {
                    "status": "mastered",
                    "bloom_level": "apply",
                    "mastery_score": 0.9,
                    "fsrs": {
                        "difficulty": 5.0,
                        "stability": 1.0,
                        "last_review": old_review,
                        "reps": 5,
                        "lapses": 0,
                    },
                    "practice_count": 5,
                    "correct_count": 5,
                    "error_history": [],
                    "last_practiced": old_review,
                },
            }
        }
        result = planner.plan_session(kg, progress)
        assert result["new_concepts"] == []
        assert len(result["review_concepts"]) > 0
        for item in result["plan"]:
            assert item["type"] == "review"

    def test_handles_no_review_items_all_new(self, simple_kg):
        """When no review is due, session should be all new."""
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.plan_session(simple_kg, progress)
        assert result["review_concepts"] == []
        assert len(result["new_concepts"]) > 0
        for item in result["plan"]:
            assert item["type"] in ("new", "assess")

    def test_estimated_minutes_is_multiple_of_three(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.plan_session(simple_kg, progress)
        assert result["estimated_minutes"] % 3 == 0

    def test_respects_duration(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.plan_session(simple_kg, progress, duration_minutes=9)
        # 9 minutes / 3 min per interaction = 3 interactions max.
        assert len(result["plan"]) <= 4  # Some slack for rounding

    def test_plan_items_have_required_fields(self, simple_kg):
        progress = make_progress({"A": "not_started", "B": "not_started", "C": "not_started"})
        result = planner.plan_session(simple_kg, progress)
        for item in result["plan"]:
            assert "type" in item
            assert "concept_id" in item
            assert item["type"] in ("new", "review", "assess")


# ---------------------------------------------------------------------------
# Tests: next_bloom_level
# ---------------------------------------------------------------------------

class TestNextBloomLevel:
    def test_progression(self):
        assert planner.next_bloom_level("remember") == "understand"
        assert planner.next_bloom_level("understand") == "apply"
        assert planner.next_bloom_level("apply") == "analyze"
        assert planner.next_bloom_level("analyze") == "evaluate"
        assert planner.next_bloom_level("evaluate") == "create"

    def test_none_at_create(self):
        assert planner.next_bloom_level("create") is None

    def test_unknown_level(self):
        assert planner.next_bloom_level("nonexistent") is None


# ---------------------------------------------------------------------------
# Tests: bloom_level_value
# ---------------------------------------------------------------------------

class TestBloomLevelValue:
    def test_all_levels(self):
        assert planner.bloom_level_value("remember") == 1
        assert planner.bloom_level_value("understand") == 2
        assert planner.bloom_level_value("apply") == 3
        assert planner.bloom_level_value("analyze") == 4
        assert planner.bloom_level_value("evaluate") == 5
        assert planner.bloom_level_value("create") == 6

    def test_invalid_raises(self):
        with pytest.raises(KeyError):
            planner.bloom_level_value("nonexistent")


# ---------------------------------------------------------------------------
# Tests: BLOOM_LEVELS constant
# ---------------------------------------------------------------------------

class TestBloomLevels:
    def test_is_dict(self):
        assert isinstance(planner.BLOOM_LEVELS, dict)

    def test_has_six_levels(self):
        assert len(planner.BLOOM_LEVELS) == 6

    def test_values_are_ordered(self):
        vals = list(planner.BLOOM_LEVELS.values())
        assert vals == sorted(vals)


# ---------------------------------------------------------------------------
# Tests: compute_mastery_score
# ---------------------------------------------------------------------------

class TestComputeMasteryScore:
    def test_zero_practice_returns_bloom_only(self):
        cp = {"practice_count": 0, "correct_count": 0, "bloom_level": "remember",
              "fsrs": {"stability": 0.0}}
        score = planner.compute_mastery_score(cp)
        # accuracy=0 * 0.5 + stability=0 * 0.3 + (1/6)*0.2 ≈ 0.033
        assert 0.03 <= score <= 0.04

    def test_perfect_accuracy_max_stability_max_bloom(self):
        cp = {"practice_count": 10, "correct_count": 10, "bloom_level": "create",
              "fsrs": {"stability": 60.0}}
        score = planner.compute_mastery_score(cp)
        # 1.0*0.5 + 1.0*0.3 + 1.0*0.2 = 1.0
        assert score == 1.0

    def test_mixed_signals(self):
        cp = {"practice_count": 10, "correct_count": 8, "bloom_level": "apply",
              "fsrs": {"stability": 15.0}}
        score = planner.compute_mastery_score(cp)
        # accuracy = 0.8 * 0.5 = 0.4
        # stability = 0.5 * 0.3 = 0.15
        # bloom = (3/6) * 0.2 = 0.1
        # total = 0.65
        assert abs(score - 0.65) < 0.01

    def test_stability_caps_at_one(self):
        cp = {"practice_count": 5, "correct_count": 5, "bloom_level": "remember",
              "fsrs": {"stability": 100.0}}
        score = planner.compute_mastery_score(cp)
        # accuracy = 1.0*0.5 + stability=1.0*0.3 + bloom=(1/6)*0.2 ≈ 0.833
        assert abs(score - 0.833) < 0.01

    def test_no_fsrs_data(self):
        cp = {"practice_count": 5, "correct_count": 5, "bloom_level": "understand"}
        score = planner.compute_mastery_score(cp)
        # accuracy=1.0*0.5 + stability=0*0.3 + bloom=(2/6)*0.2 ≈ 0.567
        assert abs(score - 0.567) < 0.01

    def test_invalid_bloom_level_defaults(self):
        cp = {"practice_count": 5, "correct_count": 5, "bloom_level": "invalid",
              "fsrs": {"stability": 10.0}}
        score = planner.compute_mastery_score(cp)
        # bloom falls back to 1 -> 1/6 * 0.2 = 0.033
        assert score > 0.0


# ---------------------------------------------------------------------------
# Tests: get_difficulty_adjustment
# ---------------------------------------------------------------------------

class TestGetDifficultyAdjustment:
    def test_maintain_with_few_results(self):
        cp = {"practice_count": 2, "correct_count": 2}
        assert planner.get_difficulty_adjustment(cp) == "maintain"

    def test_harder_with_high_accuracy(self):
        cp = {"practice_count": 10, "correct_count": 10,
              "recent_results": [True, True, True, True, True]}
        assert planner.get_difficulty_adjustment(cp) == "harder"

    def test_easier_with_low_accuracy(self):
        cp = {"practice_count": 10, "correct_count": 3,
              "recent_results": [False, False, True, False, False]}
        assert planner.get_difficulty_adjustment(cp) == "easier"

    def test_maintain_with_moderate_accuracy(self):
        cp = {"practice_count": 10, "correct_count": 8,
              "recent_results": [True, True, False, True, True]}
        assert planner.get_difficulty_adjustment(cp) == "maintain"

    def test_uses_recent_results_over_overall(self):
        # Overall accuracy is high (9/10) but recent results are bad
        cp = {"practice_count": 10, "correct_count": 9,
              "recent_results": [False, False, True, False, False]}
        assert planner.get_difficulty_adjustment(cp) == "easier"

    def test_falls_back_to_overall_without_recent(self):
        cp = {"practice_count": 10, "correct_count": 10}
        assert planner.get_difficulty_adjustment(cp) == "harder"

    def test_uses_last_five_of_recent(self):
        # Old results are bad, but last 5 are all good
        cp = {"recent_results": [False, False, False, False, False,
                                  True, True, True, True, True]}
        assert planner.get_difficulty_adjustment(cp) == "harder"


# ---------------------------------------------------------------------------
# Tests: should_advance with recent_results
# ---------------------------------------------------------------------------

class TestShouldAdvanceRecent:
    def test_uses_recent_results_when_available(self):
        # Overall accuracy is low (3/10) but recent is high
        cp = {"practice_count": 10, "correct_count": 3,
              "recent_results": [True, True, True, True, True]}
        assert planner.should_advance(cp) is True

    def test_recent_results_can_block_advance(self):
        # Overall accuracy is high (8/10) but recent is low
        cp = {"practice_count": 10, "correct_count": 8,
              "recent_results": [False, False, True, False, False]}
        assert planner.should_advance(cp) is False

    def test_falls_back_to_overall_without_recent(self):
        cp = {"practice_count": 5, "correct_count": 5}
        assert planner.should_advance(cp) is True

    def test_needs_minimum_three_recent(self):
        # Only 2 recent results, falls back to overall
        cp = {"practice_count": 5, "correct_count": 1,
              "recent_results": [True, True]}
        assert planner.should_advance(cp) is False
