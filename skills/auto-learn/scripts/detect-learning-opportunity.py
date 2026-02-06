#!/usr/bin/env python3
"""
Analyzes a Claude Code session transcript to detect learning opportunities.

Used by the stop-and-learn hook to determine if Claude should continue
the session to perform auto-learning.

Input: transcript file path as first argument
Output: JSON to stdout with learning opportunity details

Exit codes:
  0 - learning opportunity detected (stdout has JSON with details)
  1 - no learning opportunity detected
  2 - error reading/parsing transcript
"""

import json
import re
import sys
from pathlib import Path

# Patterns that indicate user corrections
CORRECTION_PHRASES = [
    r"\bno[,.]?\s+(?:we|you|it)\s+(?:should|need|use|want)",
    r"\bthat'?s\s+(?:not|wrong|incorrect)",
    r"\binstead\s+(?:of|use|do|try)",
    r"\bdon'?t\s+(?:do|use|run)\b",
    r"\bactually[,.]?\s+(?:we|you|it)\s+(?:should|need|use)",
    r"\bstop\b.*\bthat'?s\s+not",
    r"\bwrong\s+(?:approach|way|command|file|directory)",
    r"\bshould\s+(?:be|have\s+been|use)",
    r"\bnever\s+(?:do|use|run)\b",
    r"\balways\s+(?:do|use|run)\b",
    r"\bin\s+this\s+(?:project|repo|codebase)\s+we",
    r"\bour\s+convention\s+is",
    r"\bwe\s+(?:always|never|usually|prefer)",
    r"\bremember\s+(?:to|that)\b",
]

# Patterns that indicate tool failures
FAILURE_INDICATORS = [
    r"error:",
    r"failed",
    r"command\s+not\s+found",
    r"no\s+such\s+file",
    r"permission\s+denied",
    r"exit\s+code\s+[1-9]",
    r"traceback",
    r"exception",
    r"syntax\s+error",
]


def read_transcript(path):
    """Read and parse a JSONL transcript file."""
    entries = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def extract_text(entry):
    """Extract readable text from a transcript entry."""
    content = entry.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


def detect_corrections(entries):
    """Detect user correction patterns in the transcript."""
    corrections = []
    for i, entry in enumerate(entries):
        role = entry.get("role", entry.get("type", ""))
        if role not in ("user", "human"):
            continue
        text = extract_text(entry).lower()
        for pattern in CORRECTION_PHRASES:
            if re.search(pattern, text):
                corrections.append({
                    "index": i,
                    "type": "correction",
                    "snippet": extract_text(entry)[:200],
                })
                break
    return corrections


def detect_repeated_failures(entries):
    """Detect when the same tool was called multiple times suggesting struggle."""
    tool_attempts = {}
    failures = []

    for i, entry in enumerate(entries):
        # Look for tool use entries
        content = entry.get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            # Tool use
            if block.get("type") == "tool_use":
                tool_name = block.get("name", "")
                tool_input = json.dumps(block.get("input", {}))[:100]
                key = tool_name
                if key not in tool_attempts:
                    tool_attempts[key] = []
                tool_attempts[key].append(i)

            # Tool result with error
            if block.get("type") == "tool_result":
                text = str(block.get("content", "")).lower()
                for pattern in FAILURE_INDICATORS:
                    if re.search(pattern, text):
                        failures.append(i)
                        break

    repeated = []
    for tool, indices in tool_attempts.items():
        if len(indices) >= 3:
            repeated.append({
                "type": "repeated_attempts",
                "tool": tool,
                "count": len(indices),
                "indices": indices[:5],
            })

    return repeated, failures


def detect_context_sharing(entries):
    """Detect when user shared project-specific knowledge."""
    context_patterns = [
        r"in\s+this\s+(?:project|repo|codebase)",
        r"our\s+(?:convention|standard|pattern|workflow|process)",
        r"we\s+(?:use|prefer|follow|have)",
        r"the\s+(?:team|project)\s+(?:uses|prefers|follows)",
        r"make\s+sure\s+(?:to|you)\s+(?:always|never)",
        r"(?:fyi|for\s+your\s+info|heads\s+up)",
        r"(?:here'?s|this\s+is)\s+how\s+we",
    ]

    context_entries = []
    for i, entry in enumerate(entries):
        role = entry.get("role", entry.get("type", ""))
        if role not in ("user", "human"):
            continue
        text = extract_text(entry).lower()
        for pattern in context_patterns:
            if re.search(pattern, text):
                context_entries.append({
                    "index": i,
                    "type": "context_sharing",
                    "snippet": extract_text(entry)[:200],
                })
                break

    return context_entries


def analyze_transcript(path):
    """Main analysis: detect learning opportunities in a transcript."""
    entries = read_transcript(path)

    if not entries:
        return None

    corrections = detect_corrections(entries)
    repeated, failures = detect_repeated_failures(entries)
    context = detect_context_sharing(entries)

    opportunities = corrections + repeated + context

    if not opportunities and len(failures) < 3:
        return None

    return {
        "corrections": len(corrections),
        "repeated_attempts": len(repeated),
        "context_shared": len(context),
        "tool_failures": len(failures),
        "details": opportunities[:10],
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: detect-learning-opportunity.py <transcript_path>"}))
        sys.exit(2)

    transcript_path = sys.argv[1]

    if not Path(transcript_path).exists():
        print(json.dumps({"error": f"Transcript not found: {transcript_path}"}))
        sys.exit(2)

    result = analyze_transcript(transcript_path)

    if result is None:
        sys.exit(1)

    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
