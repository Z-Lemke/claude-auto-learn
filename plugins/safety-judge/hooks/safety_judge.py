#!/usr/bin/env python3
"""
PreToolUse Safety Hook: Permission Rules + LLM Judge

Layered security model:
1. Regex denylist → hard deny (obvious threats, no API call)
2. Settings deny rules → hard deny
3. Settings allow rules → auto-approve (after regex + LLM check)
4. Settings ask rules → prompt developer
5. LLM judge → escalate to "ask" (never hard-deny, developer can override)
6. No matching rule → prompt developer
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class PermissionMatcher:
    """Matches tool calls against Claude Code permission rules.

    Rule format (from Claude Code docs):
      Tool              - matches all uses of a tool
      Tool(pattern)     - glob-style pattern matching
      Tool(prefix:*)    - deprecated colon syntax (same as 'prefix *')

    Bash patterns:
      'Bash(git *)'  matches 'git status' but NOT 'gitignore' (word boundary)
      'Bash(git*)'   matches both 'git status' and 'gitignore'

    WebFetch patterns:
      'WebFetch(domain:github.com)' matches fetches to github.com

    Read/Edit patterns use gitignore-style globs:
      'Read(.env)'        - specific file relative to cwd
      'Edit(src/**/*.ts)' - recursive match
    """

    @staticmethod
    def parse_rule(rule: str) -> Tuple[str, Optional[str]]:
        """Parse 'Tool(pattern)' into (tool_name, pattern)."""
        match = re.match(r"^(\w+)(?:\((.*)\))?$", rule.strip(), re.DOTALL)
        if not match:
            return rule.strip(), None
        tool_name = match.group(1)
        pattern = match.group(2)
        return tool_name, pattern

    @staticmethod
    def _normalize_bash_pattern(pattern: str) -> str:
        """Convert deprecated colon syntax to space syntax.

        'git:*' → 'git *' (deprecated form)
        'git *' → 'git *' (preferred form, unchanged)
        """
        # Handle the deprecated colon syntax: 'prefix:*' → 'prefix *'
        colon_match = re.match(r"^(.+?):\*$", pattern)
        if colon_match:
            return colon_match.group(1) + " *"
        return pattern

    @staticmethod
    def _bash_pattern_matches(command: str, pattern: str) -> bool:
        """Match a command against a Bash permission pattern.

        Key behavior from Claude docs:
        - 'ls *' matches 'ls -la' but NOT 'lsof' (space = word boundary)
        - 'ls*' matches both 'ls -la' and 'lsof' (no space = prefix)
        """
        pattern = PermissionMatcher._normalize_bash_pattern(pattern)

        if pattern == "*":
            return True

        # Escape regex special chars, then convert glob * to regex .*
        # We process char by char to handle * correctly
        regex_parts = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == "*":
                regex_parts.append(".*")
            else:
                regex_parts.append(re.escape(c))
            i += 1

        regex_str = "^" + "".join(regex_parts) + "$"
        return bool(re.match(regex_str, command))

    @staticmethod
    def matches_rule(tool_name: str, tool_input: Dict, rule: str) -> bool:
        """Check if a tool call matches a permission rule."""
        rule_tool, rule_pattern = PermissionMatcher.parse_rule(rule)

        if rule_tool != tool_name:
            return False

        if rule_pattern is None:
            return True

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            return PermissionMatcher._bash_pattern_matches(command, rule_pattern)

        if tool_name == "WebFetch":
            if rule_pattern.startswith("domain:"):
                domain = rule_pattern[7:]
                url = tool_input.get("url", "")
                return domain in url
            return False

        if tool_name == "WebSearch":
            # WebSearch with no pattern matches all searches
            return True

        if tool_name in ("Read", "Edit", "Write", "Glob", "Grep"):
            file_path = tool_input.get("file_path", tool_input.get("path", ""))
            if not file_path or not rule_pattern:
                return rule_pattern is None
            # Simple path matching - check if pattern appears in path
            from fnmatch import fnmatch

            return fnmatch(file_path, rule_pattern) or fnmatch(
                os.path.basename(file_path), rule_pattern
            )

        return False


class SettingsLoader:
    """Loads permission rules from Claude Code settings files."""

    @staticmethod
    def find_settings_files() -> List[Path]:
        """Find settings files in priority order (highest first)."""
        files = []
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))

        candidates = [
            project_dir / ".claude" / "settings.local.json",
            project_dir / ".claude" / "settings.json",
            Path.home() / ".claude" / "settings.json",
        ]

        for path in candidates:
            if path.exists():
                files.append(path)

        return files

    @staticmethod
    def load_permissions() -> Dict[str, List[str]]:
        """Load and merge permission rules. Higher priority files win."""
        merged: Dict[str, List[str]] = {"allow": [], "deny": [], "ask": []}

        # Load in reverse order so higher priority prepends
        for settings_file in reversed(SettingsLoader.find_settings_files()):
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                perms = settings.get("permissions", {})
                for key in ("allow", "deny", "ask"):
                    if key in perms:
                        merged[key] = perms[key] + merged[key]
            except (json.JSONDecodeError, OSError) as e:
                print(
                    f"Warning: Failed to load {settings_file}: {e}", file=sys.stderr
                )

        return merged


class RegexDenylist:
    """Instant-deny patterns for obviously dangerous commands.

    These are hard denies - developer cannot override.
    For ambiguous cases, use the LLM judge (which escalates to 'ask').
    """

    PATTERNS = [
        (r"rm\s+-rf\s+/", "Recursive delete from root"),
        (r"rm\s+-rf\s+~", "Recursive delete from home"),
        (r"rm\s+-rf\s+\.\s*$", "Recursive delete current directory"),
        (r"DROP\s+DATABASE", "SQL database drop"),
        (r"TRUNCATE\s+TABLE", "SQL table truncation"),
        (r":\(\)\{.*:\|:&.*\};:", "Fork bomb"),
        (r">\s*/dev/sd[a-z]", "Direct disk write"),
        (r"mkfs\.", "Filesystem format"),
        (r"dd\s+.*of=/dev/", "Raw disk overwrite"),
    ]

    @staticmethod
    def check(command: str) -> Optional[str]:
        """Returns reason if command is obviously dangerous, None if okay."""
        for pattern, reason in RegexDenylist.PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return reason
        return None


class LLMJudge:
    """Uses Haiku to evaluate ambiguous tool calls.

    Key design: the LLM judge never hard-denies. If it thinks something
    is dangerous, it returns "ask" so the developer can override.
    """

    PROMPT_TEMPLATE = """You are a security judge for an AI coding assistant running in a development environment. Review this tool call.

Tool: {tool_name}
Input: {tool_input}

Check for:
1. Credential exfiltration (reading secrets, encoding them, sending to external URLs)
2. Destructive operations (deleting important files, force-pushing, dropping databases)
3. Privilege escalation (sudo, chmod on system binaries)
4. Data exfiltration (sending project data to unexpected external services)
5. Obfuscated intent (command substitution hiding dangerous operations)

Respond ONLY with JSON:
{{"safe": true/false, "reason": "brief explanation", "risk_level": "low/medium/high"}}"""

    def __init__(self, client=None):
        self.client = client
        if self.client is None and ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.client = Anthropic(api_key=api_key)

    @property
    def available(self) -> bool:
        return self.client is not None

    def judge(
        self, tool_name: str, tool_input: Dict
    ) -> Tuple[bool, str, str]:
        """Returns (is_safe, reason, risk_level)."""
        if not self.available:
            return True, "LLM judge unavailable", "unknown"

        prompt = self.PROMPT_TEMPLATE.format(
            tool_name=tool_name,
            tool_input=json.dumps(tool_input, indent=2),
        )

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            result = json.loads(text)
            return (
                result.get("safe", False),
                result.get("reason", "No reason provided"),
                result.get("risk_level", "unknown"),
            )
        except Exception as e:
            print(f"Warning: LLM judge error: {e}", file=sys.stderr)
            # Fail to "ask" on error — let the developer decide
            return False, f"LLM judge error: {e}", "unknown"


def enforce_permissions(
    tool_name: str,
    tool_input: Dict,
    permissions: Optional[Dict[str, List[str]]] = None,
    llm_judge: Optional[LLMJudge] = None,
) -> Tuple[str, str]:
    """Main enforcement logic.

    Returns (decision, reason) where decision is 'allow', 'deny', or 'ask'.

    Evaluation order:
    1. Regex denylist → hard deny (catastrophic commands only)
    2. Settings deny rules → hard deny
    3. Settings allow rules → allow (after regex + LLM safety check)
    4. Settings ask rules → ask
    5. No match → ask
    """
    if permissions is None:
        permissions = SettingsLoader.load_permissions()
    if llm_judge is None:
        llm_judge = LLMJudge()

    matcher = PermissionMatcher

    # Step 1: Regex denylist (hard deny, catastrophic only)
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        danger = RegexDenylist.check(command)
        if danger:
            return "deny", f"Blocked by safety denylist: {danger}"

    # Step 2: Settings deny rules (hard deny)
    for rule in permissions.get("deny", []):
        if matcher.matches_rule(tool_name, tool_input, rule):
            return "deny", f"Blocked by deny rule: {rule}"

    # Step 3: Settings allow rules
    for rule in permissions.get("allow", []):
        if matcher.matches_rule(tool_name, tool_input, rule):
            # Allowed by config, but consult LLM judge as safety net
            if llm_judge.available:
                is_safe, reason, risk_level = llm_judge.judge(tool_name, tool_input)
                if not is_safe:
                    # LLM thinks it's dangerous → escalate to ask, don't hard deny
                    return "ask", f"LLM Judge flagged ({risk_level} risk): {reason}"
            return "allow", f"Approved by allow rule: {rule}"

    # Step 4: Settings ask rules
    for rule in permissions.get("ask", []):
        if matcher.matches_rule(tool_name, tool_input, rule):
            return "ask", f"Requires approval per ask rule: {rule}"

    # Step 5: No matching rule → ask
    return "ask", "No matching permission rule (default: ask)"


def make_hook_response(decision: str, reason: str) -> Optional[str]:
    """Build hook JSON response. Returns None for allow (silent pass-through)."""
    if decision == "allow":
        return None

    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": reason,
            }
        }
    )


def main():
    """Hook entry point. Reads from stdin, writes to stdout."""
    try:
        hook_input = json.load(sys.stdin)
        tool_name = hook_input.get("tool_name")
        tool_input = hook_input.get("tool_input", {})

        decision, reason = enforce_permissions(tool_name, tool_input)

        print(f"Safety hook: {decision} - {reason}", file=sys.stderr)

        response = make_hook_response(decision, reason)
        if response:
            print(response)

        sys.exit(0)

    except Exception as e:
        # Fail closed on unexpected errors
        print(f"Safety hook error: {e}", file=sys.stderr)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Safety hook error: {e}",
                    }
                }
            )
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
