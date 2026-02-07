"""Shared fixtures for llm-toolkit tests."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


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
def transcript_corrections_nested():
    return FIXTURES_DIR / "transcript_corrections_nested.jsonl"


@pytest.fixture
def transcript_clean_nested():
    return FIXTURES_DIR / "transcript_clean_nested.jsonl"


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
