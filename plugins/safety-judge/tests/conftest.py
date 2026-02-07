"""Safety-judge plugin test fixtures."""

import sys
from pathlib import Path

# Add hooks directory to path so tests can import safety_judge module
PLUGIN_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks"))
