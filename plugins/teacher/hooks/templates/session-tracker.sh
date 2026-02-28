#!/usr/bin/env bash
set -euo pipefail

# Teacher plugin stop hook
#
# Fires at the end of each Claude response. Detects if a teaching session
# is active and performs lightweight session tracking.
#
# This hook is intentionally minimal — heavy tracking logic lives in the
# skill instructions. The hook's job is to:
# 1. Detect if we're in a teaching session (active course exists)
# 2. Check if the transcript suggests a study/quiz session is underway
# 3. Allow normal stop (teaching sessions are managed by the skill)
#
# Exit codes:
#   0 - always (Stop hooks should not block)
#
# Output:
#   {}  - always (teaching flow is managed by skills, not the hook)

INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Extract transcript path from the hook event
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('transcript_path', ''))
" 2>/dev/null || echo "")

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    echo '{}'
    exit 0
fi

# Check if any courses exist (fast check — just look for the directory)
TEACHING_DIR="$HOME/.claude/teaching/courses"
if [ ! -d "$TEACHING_DIR" ] || [ -z "$(ls -A "$TEACHING_DIR" 2>/dev/null)" ]; then
    echo '{}'
    exit 0
fi

# Lightweight session analysis — detect if study/quiz patterns in recent transcript
# and log basic session activity for progress tracking
python3 -c "
import json, sys, os
from pathlib import Path
from datetime import datetime, timezone

transcript_path = '$TRANSCRIPT_PATH'
teaching_dir = Path.home() / '.claude' / 'teaching'

try:
    # Read last few transcript entries to detect session type
    with open(transcript_path) as f:
        lines = f.readlines()

    # Look for teaching-related tool calls in the last 20 entries
    # This detects if the skill scripts were invoked (state.py, fsrs.py, planner.py)
    teaching_signals = 0
    for line in lines[-20:]:
        try:
            entry = json.loads(line)
        except:
            continue
        content = str(entry.get('content', ''))
        if any(marker in content for marker in [
            'from state import', 'from planner import', 'from fsrs import',
            'init_course', 'load_progress', 'plan_session', 'update_concept_progress'
        ]):
            teaching_signals += 1

    # If teaching session detected, update a lightweight activity log
    if teaching_signals > 0:
        activity_file = teaching_dir / 'activity.jsonl'
        activity_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'session_activity',
            'signals': teaching_signals
        }
        with open(activity_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    print('{}')
except Exception:
    print('{}')
" 2>/dev/null

exit 0
