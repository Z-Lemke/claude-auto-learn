#!/usr/bin/env bash
set -euo pipefail

# Read event data from stdin
INPUT=$(cat)

# [Hook-specific logic here]

# Exit 0 = success, exit 2 = block the action
exit 0
