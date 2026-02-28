"""Tests for the teaching agent state management module."""

import json
import os
from pathlib import Path

import pytest

import state


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fake_home(monkeypatch, tmp_path):
    """Redirect Path.home() so all tests use a temp directory."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


@pytest.fixture
def sample_knowledge_graph():
    return {
        "course_name": "test-course",
        "version": 1,
        "concepts": {
            "greetings": {
                "id": "greetings",
                "name": "Basic Greetings",
                "description": "Hello, goodbye, etc.",
                "prerequisites": [],
                "bloom_target": "apply",
                "difficulty": 0.3,
                "unit": "Basics",
                "metadata": {},
            },
            "numbers": {
                "id": "numbers",
                "name": "Numbers 1-10",
                "description": "Counting from 1 to 10",
                "prerequisites": ["greetings"],
                "bloom_target": "remember",
                "difficulty": 0.4,
                "unit": "Basics",
                "metadata": {},
            },
            "food": {
                "id": "food",
                "name": "Ordering Food",
                "description": "Restaurant vocabulary",
                "prerequisites": ["greetings", "numbers"],
                "bloom_target": "apply",
                "difficulty": 0.6,
                "unit": "Daily Life",
                "metadata": {},
            },
        },
    }


@pytest.fixture
def sample_curriculum():
    return {
        "course_name": "test-course",
        "units": [
            {
                "name": "Basics",
                "concepts": ["greetings", "numbers"],
                "description": "Foundational concepts",
            },
            {
                "name": "Daily Life",
                "concepts": ["food"],
                "description": "Everyday situations",
            },
        ],
        "total_concepts": 3,
    }


@pytest.fixture
def sample_config():
    return {
        "course_name": "test-course",
        "domain_type": "language",
        "exercise_prompts": {
            "remember": "Recall exercise for {concept}",
            "understand": "Comprehension exercise for {concept}",
            "apply": "Application exercise for {concept}",
        },
        "assessment_rubric": "Standard rubric",
        "error_taxonomy": ["pronunciation", "grammar"],
        "session_preferences": {
            "default_duration_minutes": 25,
            "new_concepts_per_session": 3,
            "review_ratio": 0.4,
        },
    }


# ---------------------------------------------------------------------------
# Path helper tests
# ---------------------------------------------------------------------------

class TestGetTeachingRoot:
    def test_creates_directory(self, fake_home):
        root = state.get_teaching_root()
        assert root.exists()
        assert root == fake_home / ".claude" / "teaching"

    def test_is_idempotent(self, fake_home):
        root1 = state.get_teaching_root()
        root2 = state.get_teaching_root()
        assert root1 == root2


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

class TestInitTeaching:
    def test_creates_structure(self, fake_home):
        root = state.init_teaching()
        assert (root / "courses").is_dir()
        assert (root / "learner").is_dir()


class TestInitCourse:
    def test_creates_files(
        self, fake_home, sample_knowledge_graph, sample_curriculum, sample_config
    ):
        course_dir = state.init_course(
            "test-course", sample_knowledge_graph, sample_curriculum, sample_config
        )
        assert (course_dir / "knowledge-graph.json").exists()
        assert (course_dir / "curriculum.json").exists()
        assert (course_dir / "config.json").exists()

        kg = json.loads((course_dir / "knowledge-graph.json").read_text())
        assert kg["course_name"] == "test-course"
        assert "greetings" in kg["concepts"]


class TestInitProgress:
    def test_creates_all_concepts(self, fake_home, sample_knowledge_graph):
        path = state.init_progress("test-course", sample_knowledge_graph)
        assert path.exists()

        progress = json.loads(path.read_text())
        assert set(progress["concepts"].keys()) == {"greetings", "numbers", "food"}

        for concept in progress["concepts"].values():
            assert concept["status"] == "not_started"
            assert concept["mastery_score"] == 0.0
            assert concept["practice_count"] == 0
            assert concept["fsrs"]["reps"] == 0

        assert progress["stats"]["concepts_not_started"] == 3
        assert progress["stats"]["concepts_mastered"] == 0
        assert progress["stats"]["concepts_learning"] == 0


class TestInitProfile:
    def test_creates_default(self, fake_home):
        path = state.init_profile()
        assert path.exists()

        profile = json.loads(path.read_text())
        assert "created" in profile
        assert profile["learning_preferences"]["session_duration_minutes"] == 25
        assert profile["active_courses"] == []

    def test_does_not_overwrite_existing(self, fake_home):
        path = state.init_profile()
        profile = json.loads(path.read_text())
        profile["active_courses"] = ["custom-course"]
        path.write_text(json.dumps(profile))

        # Calling init_profile again should NOT overwrite.
        path2 = state.init_profile()
        assert path == path2
        reloaded = json.loads(path2.read_text())
        assert reloaded["active_courses"] == ["custom-course"]


# ---------------------------------------------------------------------------
# IO helper tests
# ---------------------------------------------------------------------------

class TestSaveLoadJson:
    def test_roundtrip(self, fake_home):
        path = fake_home / "test.json"
        data = {"key": "value", "nested": {"a": 1}}
        state.save_json(path, data)
        loaded = state.load_json(path)
        assert loaded == data

    def test_load_missing_returns_none(self, fake_home):
        result = state.load_json(fake_home / "nonexistent.json")
        assert result is None

    def test_atomic_write(self, fake_home):
        """Verify that save_json uses a tmp file and rename approach.

        After a successful save there should be no leftover .tmp files
        and the target file should contain the correct data.
        """
        path = fake_home / "atomic_test.json"
        data = {"atomic": True}
        state.save_json(path, data)

        # No leftover tmp files in the directory.
        tmp_files = list(fake_home.glob(".state_*.tmp"))
        assert tmp_files == []

        assert state.load_json(path) == data

    def test_creates_parent_dirs(self, fake_home):
        path = fake_home / "deep" / "nested" / "dir" / "file.json"
        state.save_json(path, {"deep": True})
        assert state.load_json(path) == {"deep": True}


# ---------------------------------------------------------------------------
# Course operation tests
# ---------------------------------------------------------------------------

class TestLoadCourse:
    def test_returns_none_when_missing(self, fake_home):
        result = state.load_course("nonexistent-course")
        assert result is None

    def test_returns_tuple(
        self, fake_home, sample_knowledge_graph, sample_curriculum, sample_config
    ):
        state.init_course(
            "test-course", sample_knowledge_graph, sample_curriculum, sample_config
        )
        result = state.load_course("test-course")
        assert result is not None
        kg, cur, cfg = result
        assert kg["course_name"] == "test-course"
        assert cur["total_concepts"] == 3
        assert cfg["domain_type"] == "language"


class TestListCourses:
    def test_returns_names(
        self, fake_home, sample_knowledge_graph, sample_curriculum, sample_config
    ):
        state.init_course(
            "alpha-course", sample_knowledge_graph, sample_curriculum, sample_config
        )
        state.init_course(
            "beta-course", sample_knowledge_graph, sample_curriculum, sample_config
        )
        courses = state.list_courses()
        assert courses == ["alpha-course", "beta-course"]

    def test_empty_when_no_courses(self, fake_home):
        state.init_teaching()
        assert state.list_courses() == []


# ---------------------------------------------------------------------------
# Progress operation tests
# ---------------------------------------------------------------------------

class TestUpdateConceptProgress:
    def test_merges(self, fake_home, sample_knowledge_graph):
        state.init_progress("test-course", sample_knowledge_graph)

        updated = state.update_concept_progress(
            "test-course",
            "greetings",
            {
                "status": "learning",
                "mastery_score": 0.5,
                "practice_count": 3,
                "correct_count": 2,
            },
        )
        concept = updated["concepts"]["greetings"]
        assert concept["status"] == "learning"
        assert concept["mastery_score"] == 0.5
        assert concept["practice_count"] == 3
        # Unchanged fields should still be present.
        assert concept["bloom_level"] == "remember"

    def test_merges_fsrs_subdict(self, fake_home, sample_knowledge_graph):
        state.init_progress("test-course", sample_knowledge_graph)

        updated = state.update_concept_progress(
            "test-course",
            "greetings",
            {"fsrs": {"reps": 5, "difficulty": 4.2}},
        )
        fsrs = updated["concepts"]["greetings"]["fsrs"]
        assert fsrs["reps"] == 5
        assert fsrs["difficulty"] == 4.2
        # Other fsrs keys preserved.
        assert fsrs["stability"] == 1.0
        assert fsrs["lapses"] == 0

    def test_unknown_concept_raises(self, fake_home, sample_knowledge_graph):
        state.init_progress("test-course", sample_knowledge_graph)
        with pytest.raises(KeyError, match="Unknown concept"):
            state.update_concept_progress("test-course", "nonexistent", {"status": "learning"})

    def test_no_progress_raises(self, fake_home):
        with pytest.raises(ValueError, match="No progress found"):
            state.update_concept_progress("missing", "x", {})


class TestUpdateStats:
    def test_recalculates(self, fake_home, sample_knowledge_graph):
        state.init_progress("test-course", sample_knowledge_graph)
        progress = state.load_progress("test-course")

        # Simulate some learning.
        progress["concepts"]["greetings"]["status"] = "mastered"
        progress["concepts"]["numbers"]["status"] = "learning"
        # "food" stays "not_started"

        updated = state.update_stats("test-course", progress)
        assert updated["stats"]["concepts_mastered"] == 1
        assert updated["stats"]["concepts_learning"] == 1
        assert updated["stats"]["concepts_not_started"] == 1


# ---------------------------------------------------------------------------
# Session log tests
# ---------------------------------------------------------------------------

class TestAppendSessionLog:
    def test_creates_file(self, fake_home, sample_knowledge_graph):
        # Need progress dir to exist.
        state.init_progress("test-course", sample_knowledge_graph)

        session = {
            "started": "2026-02-20T10:00:00+00:00",
            "ended": "2026-02-20T10:22:00+00:00",
            "duration_minutes": 22,
            "concepts_practiced": ["greetings"],
            "exercises": [
                {
                    "concept_id": "greetings",
                    "exercise_type": "recall",
                    "correct": True,
                    "rating": 3,
                    "time_seconds": 45,
                }
            ],
            "summary": "First session",
        }
        log_path = state.append_session_log("test-course", session)
        assert log_path.exists()
        assert log_path.parent.name == "sessions"
        assert log_path.suffix == ".json"

        loaded = json.loads(log_path.read_text())
        assert loaded["duration_minutes"] == 22
        assert loaded["concepts_practiced"] == ["greetings"]
