"""Claude process launcher with TTY passthrough.

Lifecycle:
  1. Stage quest snapshot into .quest-<name>/ in CWD (read-only context)
  2. Launch claude with system prompt referencing CLI commands for mutations
  3. On exit: wipe .quest-<name>/ from CWD
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import state


def _local_dir_name(quest_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", quest_name).strip("-").lower()
    return f".quest-{slug}"


def _stage_quest(quest_id: str, cwd: Path) -> Path:
    """Snapshot quest data into CWD/.quest-<name>/ for Claude to read."""
    meta = state.get_quest(quest_id)
    local = cwd / _local_dir_name(meta.name)
    if local.exists():
        shutil.rmtree(local)
    local.mkdir()

    quest_dir = state.get_quest_dir(quest_id)

    # Core files
    for fname in ("meta.json", "state.md", "log.md"):
        src = quest_dir / fname
        if src.exists():
            shutil.copy2(src, local / fname)

    # files/ directory
    src_files = state.get_files_dir(quest_id)
    dst_files = local / "files"
    if src_files.exists() and any(src_files.iterdir()):
        shutil.copytree(src_files, dst_files)
    else:
        dst_files.mkdir()

    # Stage side quest snapshots into children/<id>/
    children = state.get_children(quest_id)
    if children:
        children_dir = local / "children"
        children_dir.mkdir()
        for child in children:
            child_local = children_dir / child.id
            child_local.mkdir()
            child_quest_dir = state.get_quest_dir(child.id)
            for fname in ("meta.json", "state.md", "log.md"):
                src = child_quest_dir / fname
                if src.exists():
                    shutil.copy2(src, child_local / fname)

    return local


def _cleanup(local_dir: Path):
    """Remove the staged .quest-<name>/ directory from CWD."""
    if local_dir.exists():
        shutil.rmtree(local_dir)


def build_system_prompt(quest_id: str, local_dir_name: str) -> str:
    meta = state.get_quest(quest_id)
    depth = state.quest_depth(quest_id)
    state_content = state.get_state(quest_id)

    # Build side quest summaries
    children_lines = []
    children = state.get_children(quest_id)
    for child in children:
        status_marker = "open" if child.status == "open" else "merged"
        desc = f" — {child.description}" if child.description else ""
        children_lines.append(
            f"  - {child.name} ({child.id}) [{status_marker}]{desc}"
            f"  → {local_dir_name}/children/{child.id}/"
        )
    children_section = "\n".join(children_lines) if children_lines else "  (none)"

    # Build ancestry chain
    ancestry = []
    current = meta
    while current.parent:
        parent = state.get_quest(current.parent)
        ancestry.append(f"{parent.name} ({parent.id})")
        current = parent
    ancestry.reverse()
    ancestry_str = (
        " → ".join(ancestry + [f"{meta.name} ({meta.id})"])
        if ancestry
        else f"{meta.name} ({meta.id}) [root]"
    )

    prompt = f"""\
# Quest Context

You are operating within a **quest** — a persistent, branching context that survives across Claude Code sessions.

## Identity
- **Quest**: {meta.name}
- **ID**: {meta.id}
- **Lineage**: {ancestry_str}
- **Depth**: {depth}
- **Sessions so far**: {meta.session_count}
- **Description**: {meta.description or "(none)"}

## Side Quests (children)
{children_section}

## Accumulated State
{state_content}

## Reading Quest Data

A snapshot of quest state is available at `{local_dir_name}/` in your working directory:
```
{local_dir_name}/
  meta.json       # Quest identity and relationships
  state.md        # Accumulated knowledge state
  log.md          # Session log history
  files/          # Attached artifacts
  children/       # Side quest snapshots
    <child-id>/
      meta.json
      state.md
      log.md
```
You can read any of these files for context. This is a **read-only snapshot** — do NOT edit these files directly.

## Mutating Quest State

**All mutations MUST go through `claude-quest` CLI commands.** Do not edit quest files directly.

### Commit (persist state)
When the user says "commit" or you want to save progress, run:
```bash
claude-quest commit --state "$(cat <<'QUEST_EOF'
# Updated state content here
...summarize what you know, what was done, what's next...
QUEST_EOF
)"
```
You can also append to the session log:
```bash
claude-quest commit --log "Session N: did X, Y, Z"
```
Or both at once:
```bash
claude-quest commit --state "..." --log "..."
```

### Attach files
To save artifacts (code, notes, research) to the quest:
```bash
claude-quest attach <filepath>
```

### Rename
```bash
claude-quest rename {meta.id} "new-name"
```

### Describe
```bash
claude-quest describe                              # show description
claude-quest describe {meta.id} --set "new desc"   # set description
```

### Show quest tree
```bash
claude-quest tree
```

### Show quest status
```bash
claude-quest status
```

### Merge a side quest
Read the side quest's state from `{local_dir_name}/children/<id>/state.md`, then commit a merged version:
```bash
claude-quest commit --state "...merged state..." --merge <child-id>
```

## Important
- `{local_dir_name}/` is a **read-only snapshot** staged for this session. It will be wiped when the session ends.
- To persist anything, you MUST use `claude-quest commit`, `claude-quest attach`, etc.
- Changes made via CLI commands are saved to the global quest store immediately.
- Do NOT write to `{local_dir_name}/` or `~/.quests/` directly.

## Environment Variables Available
- `CLAUDE_QUEST_ID={meta.id}`
- `CLAUDE_QUEST_NAME={meta.name}`
- `CLAUDE_QUEST_ROOT={state.QUESTS_ROOT}`
"""
    return prompt


def launch_claude(quest_id: str, extra_args: list[str] | None = None):
    meta = state.get_quest(quest_id)
    cwd = Path.cwd()

    state.increment_session(quest_id)

    local_dir_name = _local_dir_name(meta.name)
    local_dir = _stage_quest(quest_id, cwd)

    prompt = build_system_prompt(quest_id, local_dir_name)

    env = os.environ.copy()
    env["CLAUDE_QUEST_ID"] = meta.id
    env["CLAUDE_QUEST_DIR"] = str(local_dir)
    env["CLAUDE_QUEST_FILES"] = str(local_dir / "files")
    env["CLAUDE_QUEST_NAME"] = meta.name
    env["CLAUDE_QUEST_ROOT"] = str(state.QUESTS_ROOT)

    cmd = ["claude", "--append-system-prompt", prompt]
    if extra_args:
        cmd.extend(extra_args)

    try:
        # No stdin/stdout/stderr capture = inherits parent's TTY
        subprocess.run(cmd, env=env, check=False)
    finally:
        # Wipe the snapshot on exit
        _cleanup(local_dir)
