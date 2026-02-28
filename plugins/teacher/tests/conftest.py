"""Shared test configuration for teacher plugin tests."""

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent

# Add scripts to path for importing
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
