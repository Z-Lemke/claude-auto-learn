"""Tests that validate the plugin structure, manifests, and file integrity."""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent


class TestPluginManifest:
    def test_plugin_json_exists(self):
        assert (REPO_ROOT / ".claude-plugin" / "plugin.json").exists()

    def test_plugin_json_is_valid_json(self):
        with open(REPO_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_plugin_json_required_fields(self):
        with open(REPO_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert isinstance(data["name"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["description"], str)

    def test_plugin_json_name_matches(self):
        with open(REPO_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert data["name"] == "auto-learn"

    def test_plugin_json_repository_is_string(self):
        with open(REPO_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        if "repository" in data:
            assert isinstance(data["repository"], str), "repository must be a string URL, not an object"


class TestMarketplaceManifest:
    """Marketplace manifest lives at the monorepo root."""

    MONOREPO_ROOT = REPO_ROOT.parent.parent

    def test_marketplace_json_exists(self):
        assert (self.MONOREPO_ROOT / ".claude-plugin" / "marketplace.json").exists()

    def test_marketplace_json_is_valid_json(self):
        with open(self.MONOREPO_ROOT / ".claude-plugin" / "marketplace.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_marketplace_json_required_fields(self):
        with open(self.MONOREPO_ROOT / ".claude-plugin" / "marketplace.json") as f:
            data = json.load(f)
        assert "name" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)
        assert len(data["plugins"]) >= 1

    def test_marketplace_lists_this_plugin(self):
        with open(self.MONOREPO_ROOT / ".claude-plugin" / "marketplace.json") as f:
            marketplace = json.load(f)
        plugin_names = [p["name"] for p in marketplace["plugins"]]
        assert "auto-learn" in plugin_names


class TestSkillStructure:
    def test_skill_directory_exists(self):
        assert (REPO_ROOT / "skills" / "auto-learn").is_dir()

    def test_skill_md_exists(self):
        assert (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").exists()

    def test_skill_md_has_frontmatter(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "SKILL.md must have opening and closing --- for frontmatter"

    def test_skill_frontmatter_has_required_fields(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        frontmatter_text = content.split("---", 2)[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        assert "name" in frontmatter, "Skill frontmatter must have 'name'"
        assert "description" in frontmatter, "Skill frontmatter must have 'description'"

    def test_skill_name_is_kebab_case(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        frontmatter_text = content.split("---", 2)[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        name = frontmatter["name"]
        assert name == name.lower(), "Skill name must be lowercase"
        assert " " not in name, "Skill name must not contain spaces"

    def test_skill_description_under_1024_chars(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        frontmatter_text = content.split("---", 2)[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        desc = frontmatter["description"]
        assert len(desc) <= 1024, f"Skill description is {len(desc)} chars, must be <= 1024"

    def test_skill_description_has_trigger_phrases(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        frontmatter_text = content.split("---", 2)[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        desc = frontmatter["description"].lower()
        trigger_words = ["learn", "remember", "update", "improve", "config", "setup"]
        found = [w for w in trigger_words if w in desc]
        assert len(found) >= 2, f"Description should contain trigger phrases. Found: {found}"

    def test_skill_md_under_5000_words(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "SKILL.md").read_text()
        word_count = len(content.split())
        assert word_count <= 5000, f"SKILL.md is {word_count} words, should be <= 5000"

    def test_scripts_directory_exists(self):
        assert (REPO_ROOT / "skills" / "auto-learn" / "scripts").is_dir()


class TestCommandStructure:
    def test_learn_command_exists(self):
        assert (REPO_ROOT / "commands" / "learn.md").exists()

    def test_learn_command_has_frontmatter(self):
        content = (REPO_ROOT / "commands" / "learn.md").read_text()
        assert content.startswith("---"), "learn.md must start with YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3

    def test_learn_command_has_description(self):
        content = (REPO_ROOT / "commands" / "learn.md").read_text()
        frontmatter_text = content.split("---", 2)[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        assert "description" in frontmatter


class TestHooksJson:
    def test_hooks_json_exists(self):
        assert (REPO_ROOT / "hooks" / "hooks.json").exists()

    def test_hooks_json_is_valid_json(self):
        with open(REPO_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_hooks_json_has_hooks_key(self):
        with open(REPO_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert "hooks" in data

    def test_hooks_json_has_stop_hook(self):
        with open(REPO_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert "Stop" in data["hooks"]
        assert isinstance(data["hooks"]["Stop"], list)
        assert len(data["hooks"]["Stop"]) >= 1

    def test_hooks_json_stop_hook_references_template(self):
        with open(REPO_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        hook_entry = data["hooks"]["Stop"][0]
        assert "hooks" in hook_entry
        command = hook_entry["hooks"][0]["command"]
        assert "stop-and-learn.sh" in command


class TestScriptFiles:
    def test_detect_script_exists(self):
        assert (REPO_ROOT / "skills" / "auto-learn" / "scripts" / "detect-learning-opportunity.py").exists()

    def test_detect_script_is_executable(self):
        path = REPO_ROOT / "skills" / "auto-learn" / "scripts" / "detect-learning-opportunity.py"
        assert os.access(path, os.X_OK), "detect-learning-opportunity.py must be executable"

    def test_detect_script_has_shebang(self):
        content = (REPO_ROOT / "skills" / "auto-learn" / "scripts" / "detect-learning-opportunity.py").read_text()
        assert content.startswith("#!/usr/bin/env python3")

    def test_stop_hook_exists(self):
        assert (REPO_ROOT / "hooks" / "templates" / "stop-and-learn.sh").exists()

    def test_stop_hook_is_executable(self):
        path = REPO_ROOT / "hooks" / "templates" / "stop-and-learn.sh"
        assert os.access(path, os.X_OK), "stop-and-learn.sh must be executable"

    def test_stop_hook_has_shebang(self):
        content = (REPO_ROOT / "hooks" / "templates" / "stop-and-learn.sh").read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_stop_hook_has_safety_flags(self):
        content = (REPO_ROOT / "hooks" / "templates" / "stop-and-learn.sh").read_text()
        assert "set -euo pipefail" in content

    def test_stop_hook_uses_path_derivation(self):
        content = (REPO_ROOT / "hooks" / "templates" / "stop-and-learn.sh").read_text()
        assert 'SCRIPT_DIR=' in content, "stop-and-learn.sh must derive paths from its own location"
        assert 'PLUGIN_ROOT=' in content


class TestReferenceTemplates:
    """Validate that reference template files exist and are well-formed."""

    TEMPLATES_DIR = REPO_ROOT / "skills" / "auto-learn" / "references" / "templates"

    def test_templates_directory_exists(self):
        assert self.TEMPLATES_DIR.is_dir()

    def test_claude_md_structure_exists(self):
        assert (self.TEMPLATES_DIR / "claude-md-structure.md").exists()

    def test_claude_md_structure_has_sections(self):
        content = (self.TEMPLATES_DIR / "claude-md-structure.md").read_text()
        assert "## Build & Test" in content
        assert "## Architecture" in content
        assert "## Conventions" in content

    def test_hook_template_exists(self):
        assert (self.TEMPLATES_DIR / "hook-template.sh").exists()

    def test_hook_template_is_executable(self):
        path = self.TEMPLATES_DIR / "hook-template.sh"
        assert os.access(path, os.X_OK)

    def test_hook_template_has_shebang(self):
        content = (self.TEMPLATES_DIR / "hook-template.sh").read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_hook_template_has_safety_flags(self):
        content = (self.TEMPLATES_DIR / "hook-template.sh").read_text()
        assert "set -euo pipefail" in content

    def test_hook_template_valid_bash(self):
        path = self.TEMPLATES_DIR / "hook-template.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert result.returncode == 0, f"hook-template.sh has syntax errors: {result.stderr.decode()}"

    def test_hook_settings_exists(self):
        assert (self.TEMPLATES_DIR / "hook-settings.json").exists()

    def test_hook_settings_is_valid_json(self):
        with open(self.TEMPLATES_DIR / "hook-settings.json") as f:
            data = json.load(f)
        assert "hooks" in data

    def test_skill_template_exists(self):
        assert (self.TEMPLATES_DIR / "skill-template.md").exists()

    def test_skill_template_has_frontmatter(self):
        content = (self.TEMPLATES_DIR / "skill-template.md").read_text()
        assert content.startswith("---")
        parts = content.split("---", 2)
        assert len(parts) >= 3

    def test_learning_entry_exists(self):
        assert (self.TEMPLATES_DIR / "learning-entry.md").exists()

    def test_learning_entry_has_required_fields(self):
        content = (self.TEMPLATES_DIR / "learning-entry.md").read_text()
        assert "**Trigger**" in content
        assert "**Type**" in content
        assert "**Change**" in content
        assert "**File(s)**" in content

    def test_learnings_header_exists(self):
        assert (self.TEMPLATES_DIR / "learnings-header.md").exists()

    def test_learnings_header_has_title(self):
        content = (self.TEMPLATES_DIR / "learnings-header.md").read_text()
        assert "# Auto-Learn Log" in content


class TestNoInlineScripts:
    """Verify that markdown files reference actual scripts instead of embedding them."""

    @staticmethod
    def _max_code_block_lines(filepath, lang):
        """Return the max number of lines in any code block of the given language."""
        content = filepath.read_text()
        in_block = False
        block_lines = 0
        max_block = 0
        for line in content.split("\n"):
            if line.strip().startswith(f"```{lang}"):
                in_block = True
                block_lines = 0
            elif line.strip() == "```" and in_block:
                in_block = False
                max_block = max(max_block, block_lines)
            elif in_block:
                block_lines += 1
        return max_block

    def test_skill_md_no_large_inline_bash(self):
        path = REPO_ROOT / "skills" / "auto-learn" / "SKILL.md"
        max_block = self._max_code_block_lines(path, "bash")
        assert max_block <= 5, (
            f"SKILL.md has a bash block of {max_block} lines. "
            "Inline scripts should be extracted to reference files."
        )

    def test_skill_md_no_large_inline_json(self):
        path = REPO_ROOT / "skills" / "auto-learn" / "SKILL.md"
        max_block = self._max_code_block_lines(path, "json")
        assert max_block <= 5, (
            f"SKILL.md has a JSON block of {max_block} lines. "
            "Inline templates should be extracted to reference files."
        )

    def test_skill_md_no_large_inline_markdown(self):
        path = REPO_ROOT / "skills" / "auto-learn" / "SKILL.md"
        max_block = self._max_code_block_lines(path, "markdown")
        assert max_block <= 5, (
            f"SKILL.md has a markdown block of {max_block} lines. "
            "Inline templates should be extracted to reference files."
        )

    def test_skill_md_no_large_inline_yaml(self):
        path = REPO_ROOT / "skills" / "auto-learn" / "SKILL.md"
        max_block = self._max_code_block_lines(path, "yaml")
        assert max_block <= 5, (
            f"SKILL.md has a YAML block of {max_block} lines. "
            "Inline templates should be extracted to reference files."
        )
