"""Auto-learn plugin test fixtures."""

from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "auto-learn" / "scripts"
HOOKS_DIR = PLUGIN_ROOT / "hooks" / "templates"


@pytest.fixture
def detect_script():
    return SCRIPTS_DIR / "detect-learning-opportunity.py"


@pytest.fixture
def stop_hook():
    return HOOKS_DIR / "stop-and-learn.sh"
