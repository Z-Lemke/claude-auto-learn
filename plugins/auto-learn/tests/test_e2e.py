"""End-to-end integration tests for the auto-learn pipeline.

Tests the full lifecycle:
1. Detection: Stop hook identifies learning opportunities in real transcripts
2. Creation: Auto-learn skill creates correct config artifacts
3. Usage: Created config influences Claude's behavior in subsequent sessions

Uses Claude's built-in sandbox (Seatbelt on macOS, bubblewrap on Linux) to
restrict writes to the test project directory. Claude runs on the host with
full auth — sandbox provides the filesystem boundary.

Gated behind RUN_E2E=1 since they make API calls.
Run: RUN_E2E=1 python -m pytest tests/test_e2e.py -v -s
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_E2E"),
    reason="E2E tests require RUN_E2E=1 (makes API calls)",
)


@pytest.fixture
def test_project(tmp_path):
    """Create a sandboxed test project directory.

    Drops sandbox settings so Claude's bash commands are restricted to
    this directory via OS-level sandboxing (Seatbelt/bubblewrap).
    """
    (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
    (tmp_path / "test_app.py").write_text(
        "def test_hello():\n    assert hello() == 'world'\n"
    )

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text(
        json.dumps(
            {
                "sandbox": {
                    "enabled": True,
                    "autoAllowBashIfSandboxed": True,
                }
            }
        )
    )

    return tmp_path


def run_claude(prompt, cwd, timeout=120, extra_flags=None, debug_file=None):
    """Run claude CLI with sandbox isolation.

    Returns:
        (returncode, stdout, stderr) tuple.
    """
    cmd = [
        "claude",
        "--plugin-dir",
        str(REPO_ROOT),
        "--dangerously-skip-permissions",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        "haiku",
    ]
    if debug_file:
        cmd += ["--debug-file", str(debug_file)]
    if extra_flags:
        cmd += extra_flags
    cmd += ["-p", prompt]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def get_assistant_text(stdout):
    """Extract the assistant's text response from stream-json output."""
    text = ""
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "assistant":
            for block in msg.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
    return text


# ---------------------------------------------------------------------------
# Detection: stop hook identifies learning opportunities
# ---------------------------------------------------------------------------


class TestDetectionPipeline:
    """Verify the stop hook detects learning opportunities in real sessions.

    The stop hook reads the session transcript, runs the detection script,
    and returns {"continue": true} when it finds correction patterns.
    These tests verify the full detection chain works with real CLI transcripts
    (which use the nested message format).
    """

    def test_correction_triggers_continue(self, test_project):
        """A user correction in the prompt makes the stop hook signal continue."""
        debug_file = test_project / "debug.log"
        code, stdout, stderr = run_claude(
            "No, we should use pytest in this project, not Jest. "
            "In this project we always run tests with pytest tests/ -v.",
            cwd=test_project,
            debug_file=debug_file,
            timeout=120,
        )
        assert code == 0, f"exit {code}. stderr: {stderr[:500]}"

        debug_log = debug_file.read_text() if debug_file.exists() else ""
        assert '"continue"' in debug_log, (
            f"Stop hook did not detect correction (no continue:true in debug log). "
            f"Debug log excerpt: {debug_log[:2000]}"
        )

    def test_clean_session_no_detection(self, test_project):
        """A clean prompt without corrections: no continue, no config created."""
        debug_file = test_project / "debug.log"
        code, stdout, stderr = run_claude(
            "What is 2 + 2?",
            cwd=test_project,
            debug_file=debug_file,
        )
        assert code == 0

        debug_log = debug_file.read_text() if debug_file.exists() else ""
        assert (
            '"continue": true' not in debug_log
            and '"continue":true' not in debug_log
        ), (
            f"Clean session should not trigger continue:true. "
            f"Debug log excerpt: {debug_log[:2000]}"
        )

        assert not (test_project / ".claude" / "CLAUDE.md").exists(), (
            "CLAUDE.md should not be created from a clean session"
        )
        assert not (test_project / ".claude" / "learnings.md").exists(), (
            "learnings.md should not be created from a clean session"
        )


# ---------------------------------------------------------------------------
# Full pipeline: learn → config created → config used in next session
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Test the complete auto-learn pipeline end-to-end.

    Each test has two phases:
      Phase 1 (Learn): A prompt with correction/learning patterns triggers
        the auto-learn skill, which creates config artifacts.
      Phase 2 (Use): A fresh Claude call picks up the config created in
        phase 1 and its behavior changes accordingly.

    No pre-created files — everything flows through the learning pipeline.
    """

    def test_convention_learned_and_used(self, test_project):
        """Learn linting convention -> CLAUDE.md -> followed in next session."""
        # Phase 1: Learn the convention
        code, stdout, stderr = run_claude(
            "No, we don't use flake8 in this project. "
            "We always use ruff for linting. The command is 'ruff check .'. "
            "Remember this for future sessions.",
            cwd=test_project,
            timeout=120,
        )
        assert code == 0, f"Learning call failed: exit {code}. stderr: {stderr[:500]}"

        claude_md = test_project / ".claude" / "CLAUDE.md"
        assert claude_md.exists(), (
            f"Learning didn't create CLAUDE.md. "
            f"Files: {list((test_project / '.claude').rglob('*'))}"
        )
        assert "ruff" in claude_md.read_text().lower(), (
            f"CLAUDE.md doesn't mention ruff. "
            f"Content: {claude_md.read_text()[:500]}"
        )

        # Phase 2: Fresh call should follow the learned convention
        code, stdout, stderr = run_claude(
            "What linting tool does this project use and what is the command?",
            cwd=test_project,
        )
        assert code == 0

        response = get_assistant_text(stdout).lower()
        assert "ruff" in response, (
            f"Claude didn't follow learned convention. "
            f"Response: {get_assistant_text(stdout)[:500]}"
        )

    def test_hook_learned_and_fires(self, test_project):
        """Learn enforcement rule -> hook created -> fires in next session."""
        # Phase 1: Learn the enforcement rule
        code, stdout, stderr = run_claude(
            "No, we should always check syntax after editing Python files. "
            "In this project, after every file edit we must run "
            "'python3 -m py_compile' on the edited file to catch syntax errors. "
            "Create a hook script to enforce this automatically. "
            "Register it in .claude/settings.json under hooks.PostToolUse.",
            cwd=test_project,
            timeout=120,
        )
        assert code == 0, f"Learning call failed: exit {code}. stderr: {stderr[:500]}"

        # Verify hook script was created
        hook_scripts = list((test_project / ".claude").rglob("*.sh"))
        assert len(hook_scripts) > 0, (
            f"Learning didn't create any hook scripts. "
            f"Files: {list((test_project / '.claude').rglob('*'))}"
        )

        # Verify hook is registered in settings.json
        settings = json.loads(
            (test_project / ".claude" / "settings.json").read_text()
        )
        assert "hooks" in settings, (
            f"Learning didn't register hook. "
            f"settings.json keys: {list(settings.keys())}"
        )

        # Phase 2: Hook should fire when Claude edits a file
        debug_file = test_project / "debug.log"
        code, stdout, stderr = run_claude(
            "Add a docstring to the hello function in app.py",
            cwd=test_project,
            debug_file=debug_file,
            timeout=120,
        )
        assert code == 0

        debug_log = debug_file.read_text() if debug_file.exists() else ""
        # The learned hook should appear in the debug log (by script name)
        hook_names = [h.name for h in hook_scripts]
        hook_evidence = any(name in debug_log for name in hook_names)
        assert hook_evidence, (
            f"Learned hook didn't fire. Scripts: {hook_names}. "
            f"Debug log excerpt: {debug_log[:2000]}"
        )

    def test_skill_learned_and_used(self, test_project):
        """Learn deploy workflow -> skill created -> used in next session."""
        # Phase 1: Learn the workflow
        code, stdout, stderr = run_claude(
            "No, that's not how we deploy. In this project the deploy steps are: "
            "1) run 'python3 -m pytest tests/', "
            "2) run 'echo building...', "
            "3) run 'echo deploying to staging via codepipeline'. "
            "Create a skill for this workflow under "
            ".claude/skills/deploy/ with a SKILL.md file. "
            "The skill description should say: use when the user says 'deploy'.",
            cwd=test_project,
            timeout=120,
        )
        assert code == 0, f"Learning call failed: exit {code}. stderr: {stderr[:500]}"

        skills_dir = test_project / ".claude" / "skills"
        skill_files = (
            list(skills_dir.rglob("SKILL.md")) if skills_dir.exists() else []
        )
        assert len(skill_files) > 0, (
            f"Learning didn't create SKILL.md. "
            f"Files: {list((test_project / '.claude').rglob('*'))}"
        )

        # Phase 2: Fresh call should reference the learned workflow
        code, stdout, stderr = run_claude(
            "Deploy this project",
            cwd=test_project,
            timeout=120,
        )
        assert code == 0

        response = get_assistant_text(stdout).upper()
        assert "CODEPIPELINE" in response or "STAGING" in response, (
            f"Claude didn't use learned deploy skill. "
            f"Response: {get_assistant_text(stdout)[:500]}"
        )
