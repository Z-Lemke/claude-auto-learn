#!/usr/bin/env bash
set -euo pipefail

# Auto-learn stop hook
#
# Fires at the end of each Claude response. Analyzes the session transcript
# for learning opportunities (user corrections, repeated failures, context
# sharing). If opportunities are detected, signals Claude to continue the
# session for automatic .claude configuration updates.
#
# Registered automatically via hooks/hooks.json when the plugin is enabled.
#
# Exit codes:
#   0 - always (Stop hooks should not block)
#
# Output:
#   {"continue": true}  - when learning opportunities detected
#   {}                   - when no opportunities detected

INPUT=$(cat)

# Extract transcript path from the hook event (tolerate invalid JSON)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('transcript_path', ''))
" 2>/dev/null || echo "")

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    echo '{}'
    exit 0
fi

# Derive detect script path from this script's location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DETECT_SCRIPT="$PLUGIN_ROOT/skills/auto-learn/scripts/detect-learning-opportunity.py"

if [ -f "$DETECT_SCRIPT" ]; then
    # Use the full detection script
    if python3 "$DETECT_SCRIPT" "$TRANSCRIPT_PATH" >/dev/null 2>&1; then
        echo '{"continue": true}'
    else
        echo '{}'
    fi
    exit 0
fi

# Fallback: inline detection using Python
python3 -c "
import json, re, sys

path = '$TRANSCRIPT_PATH'
try:
    with open(path) as f:
        lines = f.readlines()

    corrections = 0
    patterns = [
        r'\bno[,.]?\s+(?:we|you|it)\s+(?:should|need|use)',
        r'\bthat.?s\s+(?:not|wrong|incorrect)',
        r'\binstead\s+(?:of|use|do)',
        r'\bin\s+this\s+(?:project|repo|codebase)\s+we',
        r'\bour\s+convention',
        r'\bwe\s+(?:always|never|usually|prefer)',
        r'\bremember\s+(?:to|that)\b',
        r'\bactually[,.]?\s+(?:we|you|it)\s+(?:should|need|use)',
    ]

    for line in lines[-100:]:
        try:
            entry = json.loads(line)
        except:
            continue
        role = entry.get('role', entry.get('type', ''))
        if role not in ('user', 'human'):
            continue
        content = entry.get('content', '')
        if isinstance(content, list):
            content = ' '.join(
                b.get('text', '') if isinstance(b, dict) else str(b)
                for b in content
            )
        text = content.lower()
        for p in patterns:
            if re.search(p, text):
                corrections += 1
                break

    if corrections > 0:
        print(json.dumps({'continue': True}))
    else:
        print('{}')
except Exception:
    print('{}')
" 2>/dev/null

exit 0
