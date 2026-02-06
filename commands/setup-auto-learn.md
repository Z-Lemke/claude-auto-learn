---
description: Install auto-learn hooks in the current project for automatic learning detection
argument-hint: [--force]
allowed-tools: Bash(mkdir:*) Bash(chmod:*) Bash(cp:*) Read Write Edit Glob
---

# /setup-auto-learn - Install Auto-Learn Hooks

Install the stop-and-learn hook in this project so that learning opportunities are detected automatically at the end of each Claude session.

## Instructions

### Step 1: Check Prerequisites

1. Verify this is a project directory (has a `.git` directory or other project indicators)
2. Check if `.claude/` directory exists; create it if not
3. Check if hooks are already installed; if so, inform the user and ask if they want to reinstall (unless `--force` was passed)

### Step 2: Create Hook Directory

```bash
mkdir -p .claude/hooks
```

### Step 3: Install the Stop Hook Script

Copy the hook template from the plugin into the project:

```bash
cp hooks/templates/stop-and-learn.sh .claude/hooks/stop-and-learn.sh
chmod +x .claude/hooks/stop-and-learn.sh
```

If the `cp` source path does not resolve (plugin may be installed elsewhere), locate the plugin's `hooks/templates/stop-and-learn.sh` by checking these paths in order:
1. `$HOME/.claude/plugins/auto-claude-builder/hooks/templates/stop-and-learn.sh`
2. Relative to the plugin installation directory

### Step 4: Register the Hook in Settings

Read the existing `.claude/settings.json` (or create it if it doesn't exist). Add the Stop hook entry:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "command": ".claude/hooks/stop-and-learn.sh",
        "timeout": 30000
      }
    ]
  }
}
```

**Important**: Merge with any existing settings. Do not overwrite existing hooks or permissions. If a Stop hook array already exists, append to it.

### Step 5: Confirm Installation

Output the result:
```
STATUS=CREATED
Auto-learn hooks installed:
  - .claude/hooks/stop-and-learn.sh (Stop hook)
  - .claude/settings.json updated

The auto-learn system will now detect learning opportunities at the end of
each Claude session. When corrections or patterns are detected, Claude will
automatically analyze the session and update .claude configuration.

You can also manually trigger learning with: /learn
```

### If Already Installed

If the hook already exists and `--force` was not passed:
```
STATUS=EXISTS
Auto-learn hooks are already installed in this project.
Run /setup-auto-learn --force to reinstall.
```
