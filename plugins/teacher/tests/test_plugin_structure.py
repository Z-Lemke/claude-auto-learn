"""Tests that validate the teacher plugin structure, manifests, and file integrity."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

PLUGIN_ROOT = Path(__file__).parent.parent
MONOREPO_ROOT = PLUGIN_ROOT.parent.parent


class TestPluginManifest:
    def test_plugin_json_exists(self):
        assert (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").exists()

    def test_plugin_json_is_valid_json(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_plugin_json_required_fields(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert isinstance(data["name"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["description"], str)

    def test_plugin_json_name_matches(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        assert data["name"] == "teacher"

    def test_plugin_json_repository_is_string(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            data = json.load(f)
        if "repository" in data:
            assert isinstance(data["repository"], str)


class TestMarketplaceManifest:
    def test_marketplace_json_exists(self):
        assert (MONOREPO_ROOT / ".claude-plugin" / "marketplace.json").exists()

    def test_marketplace_lists_teacher_plugin(self):
        with open(MONOREPO_ROOT / ".claude-plugin" / "marketplace.json") as f:
            marketplace = json.load(f)
        plugin_names = [p["name"] for p in marketplace["plugins"]]
        assert "teacher" in plugin_names


class TestHooksJson:
    def test_hooks_json_exists(self):
        assert (PLUGIN_ROOT / "hooks" / "hooks.json").exists()

    def test_hooks_json_is_valid_json(self):
        with open(PLUGIN_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_hooks_json_has_hooks_key(self):
        with open(PLUGIN_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert "hooks" in data

    def test_hooks_json_has_stop_hook(self):
        with open(PLUGIN_ROOT / "hooks" / "hooks.json") as f:
            data = json.load(f)
        assert "Stop" in data["hooks"]
        assert isinstance(data["hooks"]["Stop"], list)
        assert len(data["hooks"]["Stop"]) >= 1


class TestScriptFiles:
    def test_session_tracker_exists(self):
        assert (PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh").exists()

    def test_session_tracker_is_executable(self):
        path = PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh"
        assert os.access(path, os.X_OK)

    def test_session_tracker_has_shebang(self):
        content = (PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh").read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_session_tracker_has_safety_flags(self):
        content = (PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh").read_text()
        assert "set -euo pipefail" in content

    def test_session_tracker_has_path_derivation(self):
        content = (PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh").read_text()
        assert "SCRIPT_DIR=" in content
        assert "PLUGIN_ROOT=" in content

    def test_session_tracker_valid_bash(self):
        path = PLUGIN_ROOT / "hooks" / "templates" / "session-tracker.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True)
        assert result.returncode == 0, f"session-tracker.sh has syntax errors: {result.stderr.decode()}"


class TestDirectoryStructure:
    def test_skills_directory_exists(self):
        assert (PLUGIN_ROOT / "skills").is_dir()

    def test_commands_directory_exists(self):
        assert (PLUGIN_ROOT / "commands").is_dir()

    def test_hooks_directory_exists(self):
        assert (PLUGIN_ROOT / "hooks").is_dir()

    def test_tests_directory_exists(self):
        assert (PLUGIN_ROOT / "tests").is_dir()

    def test_scripts_directory_exists(self):
        assert (PLUGIN_ROOT / "scripts").is_dir()
