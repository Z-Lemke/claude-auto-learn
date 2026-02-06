"""Shared fixtures for claude-auto-learn tests."""

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCRIPTS_DIR = REPO_ROOT / "skills" / "auto-learn" / "scripts"
HOOKS_DIR = REPO_ROOT / "hooks" / "templates"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def transcript_corrections():
    return FIXTURES_DIR / "transcript_corrections.jsonl"


@pytest.fixture
def transcript_repeated_failures():
    return FIXTURES_DIR / "transcript_repeated_failures.jsonl"


@pytest.fixture
def transcript_context_sharing():
    return FIXTURES_DIR / "transcript_context_sharing.jsonl"


@pytest.fixture
def transcript_clean():
    return FIXTURES_DIR / "transcript_clean.jsonl"


@pytest.fixture
def transcript_empty():
    return FIXTURES_DIR / "transcript_empty.jsonl"


@pytest.fixture
def transcript_many_failures():
    return FIXTURES_DIR / "transcript_many_failures.jsonl"


@pytest.fixture
def detect_script():
    return SCRIPTS_DIR / "detect-learning-opportunity.py"


@pytest.fixture
def stop_hook():
    return HOOKS_DIR / "stop-and-learn.sh"


@pytest.fixture
def tmp_transcript(tmp_path):
    """Factory fixture for creating temporary transcript files."""
    def _make(lines):
        import json
        path = tmp_path / "transcript.jsonl"
        with open(path, "w") as f:
            for entry in lines:
                f.write(json.dumps(entry) + "\n")
        return path
    return _make
