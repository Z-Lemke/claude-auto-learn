"""Tests for hooks/templates/stop-and-learn.sh"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HOOKS_DIR = REPO_ROOT / "hooks" / "templates"
SCRIPTS_DIR = REPO_ROOT / "skills" / "auto-learn" / "scripts"
STOP_HOOK = HOOKS_DIR / "stop-and-learn.sh"


def run_hook(transcript_path, detect_script_dir=None):
    """Run the stop hook with a mock event on stdin.

    Returns (exit_code, stdout, stderr).
    """
    event = {"transcript_path": str(transcript_path)}
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(SCRIPTS_DIR.parent.parent.parent)

    if detect_script_dir:
        env["HOME"] = str(detect_script_dir)

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestStopHookExitCodes:
    def test_always_exits_0(self, transcript_corrections):
        code, _, _ = run_hook(transcript_corrections)
        assert code == 0

    def test_exits_0_on_clean(self, transcript_clean):
        code, _, _ = run_hook(transcript_clean)
        assert code == 0

    def test_exits_0_on_empty(self, transcript_empty):
        code, _, _ = run_hook(transcript_empty)
        assert code == 0

    def test_exits_0_on_missing_transcript(self):
        code, stdout, _ = run_hook("/nonexistent/transcript.jsonl")
        assert code == 0
        assert stdout == "{}"


class TestStopHookOutput:
    def test_continue_on_corrections(self, transcript_corrections):
        code, stdout, _ = run_hook(transcript_corrections)
        assert code == 0
        parsed = json.loads(stdout)
        assert parsed.get("continue") is True

    def test_no_continue_on_clean(self, transcript_clean):
        code, stdout, _ = run_hook(transcript_clean)
        assert code == 0
        parsed = json.loads(stdout)
        assert "continue" not in parsed or parsed.get("continue") is not True

    def test_no_continue_on_empty(self, transcript_empty):
        code, stdout, _ = run_hook(transcript_empty)
        assert code == 0
        parsed = json.loads(stdout)
        assert "continue" not in parsed or parsed.get("continue") is not True

    def test_output_is_valid_json(self, transcript_corrections):
        _, stdout, _ = run_hook(transcript_corrections)
        parsed = json.loads(stdout)
        assert isinstance(parsed, dict)

    def test_output_is_valid_json_clean(self, transcript_clean):
        _, stdout, _ = run_hook(transcript_clean)
        parsed = json.loads(stdout)
        assert isinstance(parsed, dict)


class TestStopHookMissingInput:
    def test_empty_transcript_path(self):
        event = {"transcript_path": ""}
        result = subprocess.run(
            ["bash", str(STOP_HOOK)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"

    def test_no_transcript_path_key(self):
        event = {"some_other_key": "value"}
        result = subprocess.run(
            ["bash", str(STOP_HOOK)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"

    def test_invalid_json_input(self):
        result = subprocess.run(
            ["bash", str(STOP_HOOK)],
            input="not valid json",
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"


class TestStopHookContextSharing:
    def test_continue_on_context(self, transcript_context_sharing):
        code, stdout, _ = run_hook(transcript_context_sharing)
        assert code == 0
        parsed = json.loads(stdout)
        assert parsed.get("continue") is True
