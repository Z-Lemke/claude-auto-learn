"""Tests for detect-learning-opportunity.py"""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "auto-learn" / "scripts"
DETECT_SCRIPT = SCRIPTS_DIR / "detect-learning-opportunity.py"


def run_detect(transcript_path):
    """Run the detect script and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(DETECT_SCRIPT), str(transcript_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# --- Import and unit-test the module directly ---

sys.path.insert(0, str(SCRIPTS_DIR))
detect_module = importlib.import_module("detect-learning-opportunity")


class TestReadTranscript:
    def test_reads_valid_jsonl(self, transcript_corrections):
        entries = detect_module.read_transcript(str(transcript_corrections))
        assert len(entries) > 0
        assert all(isinstance(e, dict) for e in entries)

    def test_empty_file_returns_empty_list(self, transcript_empty):
        entries = detect_module.read_transcript(str(transcript_empty))
        assert entries == []

    def test_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "bad.jsonl"
        f.write_text('{"role": "user", "content": "hello"}\nnot json\n{"role": "assistant", "content": "hi"}\n')
        entries = detect_module.read_transcript(str(f))
        assert len(entries) == 2


class TestExtractText:
    def test_string_content(self):
        assert detect_module.extract_text({"content": "hello"}) == "hello"

    def test_list_content_with_text_blocks(self):
        entry = {"content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}
        assert detect_module.extract_text(entry) == "hello world"

    def test_list_content_with_mixed_blocks(self):
        entry = {"content": [{"type": "tool_use", "name": "Bash"}, {"type": "text", "text": "result"}]}
        assert detect_module.extract_text(entry) == "result"

    def test_empty_content(self):
        assert detect_module.extract_text({"content": ""}) == ""
        assert detect_module.extract_text({}) == ""

    def test_list_with_string_elements(self):
        entry = {"content": ["hello", "world"]}
        assert detect_module.extract_text(entry) == "hello world"


class TestDetectCorrections:
    def test_finds_corrections(self, transcript_corrections):
        entries = detect_module.read_transcript(str(transcript_corrections))
        corrections = detect_module.detect_corrections(entries)
        assert len(corrections) >= 1
        assert all(c["type"] == "correction" for c in corrections)

    def test_no_corrections_in_clean(self, transcript_clean):
        entries = detect_module.read_transcript(str(transcript_clean))
        corrections = detect_module.detect_corrections(entries)
        assert len(corrections) == 0

    def test_correction_patterns(self, tmp_transcript):
        test_cases = [
            "No, we should use yarn instead",
            "That's not how it works here",
            "Instead of npm, use pnpm",
            "In this project we use tabs",
            "Our convention is to use snake_case",
            "We always run lint before committing",
            "Actually, you should use the v2 API",
        ]
        for phrase in test_cases:
            path = tmp_transcript([{"role": "user", "content": phrase}])
            entries = detect_module.read_transcript(str(path))
            corrections = detect_module.detect_corrections(entries)
            assert len(corrections) >= 1, f"Failed to detect correction in: {phrase}"

    def test_ignores_assistant_messages(self, tmp_transcript):
        path = tmp_transcript([
            {"role": "assistant", "content": "No, we should use pytest instead"},
        ])
        entries = detect_module.read_transcript(str(path))
        corrections = detect_module.detect_corrections(entries)
        assert len(corrections) == 0

    def test_snippet_truncation(self, tmp_transcript):
        long_msg = "No, we should use " + "x" * 300
        path = tmp_transcript([{"role": "user", "content": long_msg}])
        entries = detect_module.read_transcript(str(path))
        corrections = detect_module.detect_corrections(entries)
        assert len(corrections) == 1
        assert len(corrections[0]["snippet"]) <= 200


class TestDetectRepeatedFailures:
    def test_finds_repeated_tool_calls(self, transcript_repeated_failures):
        entries = detect_module.read_transcript(str(transcript_repeated_failures))
        repeated, failures = detect_module.detect_repeated_failures(entries)
        assert len(repeated) >= 1
        assert repeated[0]["count"] >= 3

    def test_finds_failure_indicators(self, transcript_repeated_failures):
        entries = detect_module.read_transcript(str(transcript_repeated_failures))
        _, failures = detect_module.detect_repeated_failures(entries)
        assert len(failures) >= 1

    def test_no_repeats_in_clean(self, transcript_clean):
        entries = detect_module.read_transcript(str(transcript_clean))
        repeated, failures = detect_module.detect_repeated_failures(entries)
        assert len(repeated) == 0

    def test_two_calls_not_flagged(self, tmp_transcript):
        path = tmp_transcript([
            {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {}}]},
            {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "input": {}}]},
        ])
        entries = detect_module.read_transcript(str(path))
        repeated, _ = detect_module.detect_repeated_failures(entries)
        assert len(repeated) == 0


class TestDetectContextSharing:
    def test_finds_context(self, transcript_context_sharing):
        entries = detect_module.read_transcript(str(transcript_context_sharing))
        context = detect_module.detect_context_sharing(entries)
        assert len(context) >= 1
        assert all(c["type"] == "context_sharing" for c in context)

    def test_no_context_in_clean(self, transcript_clean):
        entries = detect_module.read_transcript(str(transcript_clean))
        context = detect_module.detect_context_sharing(entries)
        assert len(context) == 0

    def test_context_patterns(self, tmp_transcript):
        test_cases = [
            "In this project we use microservices",
            "Our convention is REST over GraphQL",
            "We prefer composition over inheritance",
            "The team uses trunk-based development",
            "FYI, the database migrations are in db/migrate",
            "Here's how we handle authentication",
        ]
        for phrase in test_cases:
            path = tmp_transcript([{"role": "user", "content": phrase}])
            entries = detect_module.read_transcript(str(path))
            context = detect_module.detect_context_sharing(entries)
            assert len(context) >= 1, f"Failed to detect context sharing in: {phrase}"


class TestAnalyzeTranscript:
    def test_corrections_detected(self, transcript_corrections):
        result = detect_module.analyze_transcript(str(transcript_corrections))
        assert result is not None
        assert result["corrections"] >= 1

    def test_repeated_failures_detected(self, transcript_repeated_failures):
        result = detect_module.analyze_transcript(str(transcript_repeated_failures))
        assert result is not None
        assert result["repeated_attempts"] >= 1

    def test_context_sharing_detected(self, transcript_context_sharing):
        result = detect_module.analyze_transcript(str(transcript_context_sharing))
        assert result is not None
        assert result["context_shared"] >= 1

    def test_clean_returns_none(self, transcript_clean):
        result = detect_module.analyze_transcript(str(transcript_clean))
        assert result is None

    def test_empty_returns_none(self, transcript_empty):
        result = detect_module.analyze_transcript(str(transcript_empty))
        assert result is None

    def test_details_capped_at_10(self, tmp_transcript):
        entries = [{"role": "user", "content": f"No, we should use thing{i}"} for i in range(20)]
        path = tmp_transcript(entries)
        result = detect_module.analyze_transcript(str(path))
        assert result is not None
        assert len(result["details"]) <= 10


class TestCLI:
    def test_no_args_exits_2(self):
        result = subprocess.run(
            [sys.executable, str(DETECT_SCRIPT)],
            capture_output=True, text=True,
        )
        assert result.returncode == 2

    def test_missing_file_exits_2(self):
        code, stdout, _ = run_detect("/nonexistent/path.jsonl")
        assert code == 2
        parsed = json.loads(stdout)
        assert "error" in parsed

    def test_corrections_exits_0(self, transcript_corrections):
        code, stdout, _ = run_detect(transcript_corrections)
        assert code == 0
        result = json.loads(stdout)
        assert result["corrections"] >= 1

    def test_clean_exits_1(self, transcript_clean):
        code, _, _ = run_detect(transcript_clean)
        assert code == 1

    def test_empty_exits_1(self, transcript_empty):
        code, _, _ = run_detect(transcript_empty)
        assert code == 1

    def test_output_is_valid_json(self, transcript_corrections):
        code, stdout, _ = run_detect(transcript_corrections)
        assert code == 0
        parsed = json.loads(stdout)
        assert "corrections" in parsed
        assert "repeated_attempts" in parsed
        assert "context_shared" in parsed
        assert "tool_failures" in parsed
        assert "details" in parsed
