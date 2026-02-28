#!/usr/bin/env python3
"""State management for the teaching agent plugin.

Pure Python 3.8+ module with no external dependencies.
Manages all persistent state under ~/.claude/teaching/.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_teaching_root() -> Path:
    """Return ~/.claude/teaching/, creating it if it does not exist."""
    root = Path.home() / ".claude" / "teaching"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_course_dir(course_name: str) -> Path:
    """Return the directory for a specific course."""
    return get_teaching_root() / "courses" / course_name


def get_learner_dir() -> Path:
    """Return the global learner directory."""
    return get_teaching_root() / "learner"


def get_progress_dir(course_name: str) -> Path:
    """Return the learner's per-course progress directory."""
    return get_learner_dir() / course_name


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Optional[dict]:
    """Read a JSON file and return its contents, or None if it does not exist."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    """Atomically write *data* as JSON to *path*.

    Writes to a temporary file in the same directory, then renames it into
    place so that readers never see a partially-written file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
        prefix=".state_",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, str(path))
    except BaseException:
        # Clean up the temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def append_session_log(course_name: str, session_data: dict) -> Path:
    """Save a session log with a timestamp-based filename, return the path."""
    sessions_dir = get_progress_dir(course_name) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = sessions_dir / f"{timestamp}.json"
    save_json(log_path, session_data)
    return log_path


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init_teaching() -> Path:
    """Create the full directory structure and return the root path."""
    root = get_teaching_root()
    (root / "courses").mkdir(parents=True, exist_ok=True)
    (root / "learner").mkdir(parents=True, exist_ok=True)
    return root


def init_course(
    course_name: str,
    knowledge_graph: dict,
    curriculum: dict,
    config: dict,
) -> Path:
    """Write knowledge-graph, curriculum, and config for a course.

    Returns the course directory path.
    """
    course_dir = get_course_dir(course_name)
    course_dir.mkdir(parents=True, exist_ok=True)
    save_json(course_dir / "knowledge-graph.json", knowledge_graph)
    save_json(course_dir / "curriculum.json", curriculum)
    save_json(course_dir / "config.json", config)
    return course_dir


def init_progress(course_name: str, knowledge_graph: dict) -> Path:
    """Create initial progress.json with all concepts set to "not_started".

    Returns the path to progress.json.
    """
    progress_dir = get_progress_dir(course_name)
    progress_dir.mkdir(parents=True, exist_ok=True)
    (progress_dir / "sessions").mkdir(parents=True, exist_ok=True)

    concepts: Dict[str, dict] = {}
    for concept_id in knowledge_graph.get("concepts", {}):
        concepts[concept_id] = {
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
            "recent_results": [],
            "error_history": [],
            "last_practiced": None,
        }

    total = len(concepts)
    progress: dict = {
        "course_name": course_name,
        "last_session": None,
        "concepts": concepts,
        "stats": {
            "total_sessions": 0,
            "total_practice_time_minutes": 0,
            "concepts_mastered": 0,
            "concepts_learning": 0,
            "concepts_not_started": total,
        },
    }

    progress_path = progress_dir / "progress.json"
    save_json(progress_path, progress)
    return progress_path


def init_profile() -> Path:
    """Create a default profile.json if one does not already exist.

    Returns the path to profile.json.
    """
    learner_dir = get_learner_dir()
    learner_dir.mkdir(parents=True, exist_ok=True)
    profile_path = learner_dir / "profile.json"

    if not profile_path.exists():
        default_profile = {
            "created": datetime.now(timezone.utc).isoformat(),
            "learning_preferences": {
                "session_duration_minutes": 25,
                "explanation_style": "examples_first",
            },
            "active_courses": [],
        }
        save_json(profile_path, default_profile)

    return profile_path


# ---------------------------------------------------------------------------
# Course operations
# ---------------------------------------------------------------------------

def load_course(
    course_name: str,
) -> Optional[Tuple[dict, dict, dict]]:
    """Load (knowledge_graph, curriculum, config) for a course.

    Returns None if any of the three files is missing.
    """
    course_dir = get_course_dir(course_name)
    kg = load_json(course_dir / "knowledge-graph.json")
    cur = load_json(course_dir / "curriculum.json")
    cfg = load_json(course_dir / "config.json")
    if kg is None or cur is None or cfg is None:
        return None
    return (kg, cur, cfg)


def list_courses() -> List[str]:
    """Return a sorted list of available course names."""
    courses_dir = get_teaching_root() / "courses"
    if not courses_dir.exists():
        return []
    return sorted(
        d.name
        for d in courses_dir.iterdir()
        if d.is_dir()
    )


# ---------------------------------------------------------------------------
# Progress operations
# ---------------------------------------------------------------------------

def load_progress(course_name: str) -> Optional[dict]:
    """Load progress.json for a course, or None if it does not exist."""
    return load_json(get_progress_dir(course_name) / "progress.json")


def save_progress(course_name: str, progress: dict) -> None:
    """Atomically save progress.json for a course."""
    progress_dir = get_progress_dir(course_name)
    progress_dir.mkdir(parents=True, exist_ok=True)
    save_json(progress_dir / "progress.json", progress)


def update_concept_progress(
    course_name: str,
    concept_id: str,
    updates: dict,
) -> dict:
    """Merge *updates* into a single concept's progress and persist.

    Returns the full updated progress dict.
    """
    progress = load_progress(course_name)
    if progress is None:
        raise ValueError(
            f"No progress found for course '{course_name}'. "
            "Call init_progress() first."
        )
    if concept_id not in progress["concepts"]:
        raise KeyError(f"Unknown concept '{concept_id}'")

    concept_data = progress["concepts"][concept_id]
    for key, value in updates.items():
        if key == "fsrs" and isinstance(value, dict):
            concept_data.setdefault("fsrs", {}).update(value)
        else:
            concept_data[key] = value

    progress = update_stats(course_name, progress)
    save_progress(course_name, progress)
    return progress


def update_stats(course_name: str, progress: dict) -> dict:
    """Recalculate stats from concept data, update in place, and return."""
    mastered = 0
    learning = 0
    not_started = 0
    for concept in progress.get("concepts", {}).values():
        status = concept.get("status", "not_started")
        if status == "mastered":
            mastered += 1
        elif status == "not_started":
            not_started += 1
        else:
            learning += 1

    progress.setdefault("stats", {})
    progress["stats"]["concepts_mastered"] = mastered
    progress["stats"]["concepts_learning"] = learning
    progress["stats"]["concepts_not_started"] = not_started
    return progress


# ---------------------------------------------------------------------------
# Profile operations
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    """Load the learner profile, creating a default one if needed."""
    profile_path = init_profile()
    data = load_json(profile_path)
    if data is None:
        # Should not happen since init_profile creates it, but be safe.
        return {}
    return data


def save_profile(profile: dict) -> None:
    """Persist the learner profile."""
    learner_dir = get_learner_dir()
    learner_dir.mkdir(parents=True, exist_ok=True)
    save_json(learner_dir / "profile.json", profile)
