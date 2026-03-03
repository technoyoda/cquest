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
# Quest Context (Background)

This session is running inside a quest. The information below is background context — use it to inform your work but do NOT take any quest actions unless the user explicitly asks.

**Quest**: {meta.name} ({meta.id})
**Lineage**: {ancestry_str}
**Session**: #{meta.session_count + 1} | Depth: {depth}
**Description**: {meta.description or "(none)"}

## Side Quests
{children_section}

## Accumulated State
{state_content}

## Quest Snapshot

A read-only snapshot is at `{local_dir_name}/` in your working directory:
```
{local_dir_name}/
  meta.json, state.md, log.md, files/
  children/<child-id>/meta.json, state.md, log.md
```

## Quest Commands Reference

**NEVER run these unless the user explicitly asks you to.** Do not auto-commit, auto-attach, or auto-merge.

| Command | What it does |
|---|---|
| `claude-quest commit --state "..."` | Overwrite state.md |
| `claude-quest commit --log "..."` | Append to log.md |
| `claude-quest commit --state "..." --merge <id>` | Merge a side quest |
| `claude-quest attach <file>` | Save a file to quest storage |
| `claude-quest rename {meta.id} "name"` | Rename this quest |
| `claude-quest describe {meta.id} --set "desc"` | Set description |
| `claude-quest tree` | Show quest tree |
| `claude-quest status` | Show quest details |
"""
    return prompt


def launch_claude(
    quest_id: str,
    extra_args: list[str] | None = None,
    extra_system_prompt: str | None = None,
    prompt_mode: str = "append",
):
    from rich.console import Console
    console = Console()

    meta = state.get_quest(quest_id)
    cwd = Path.cwd()

    if meta.created_dir and str(cwd) != meta.created_dir:
        console.print(
            f"[yellow]Warning:[/yellow] Quest [bold]{meta.name}[/bold] was created in "
            f"[dim]{meta.created_dir}[/dim]\n"
            f"         You are launching from [dim]{cwd}[/dim]"
        )

    # Gate against system prompt args in passthrough — quest manages these
    BLOCKED_ARGS = {"--append-system-prompt", "--system-prompt", "-s"}
    if extra_args:
        for arg in extra_args:
            if arg in BLOCKED_ARGS:
                console.print(
                    f"[red]Cannot pass '{arg}' as a claude flag.[/red]\n"
                    f"Use [bold]-s / --system-prompt[/bold] on the claude-quest command instead."
                )
                raise SystemExit(1)

    state.increment_session(quest_id)

    local_dir_name = _local_dir_name(meta.name)
    local_dir = _stage_quest(quest_id, cwd)

    prompt = build_system_prompt(quest_id, local_dir_name)
    if extra_system_prompt:
        prompt += f"\n{extra_system_prompt}"

    env = os.environ.copy()
    env["CLAUDE_QUEST_ID"] = meta.id
    env["CLAUDE_QUEST_DIR"] = str(local_dir)
    env["CLAUDE_QUEST_FILES"] = str(local_dir / "files")
    env["CLAUDE_QUEST_NAME"] = meta.name
    env["CLAUDE_QUEST_ROOT"] = str(state.QUESTS_ROOT)

    prompt_flag = "--system-prompt" if prompt_mode == "replace" else "--append-system-prompt"
    cmd = ["claude", prompt_flag, prompt]
    if extra_args:
        cmd.extend(extra_args)

    try:
        # No stdin/stdout/stderr capture = inherits parent's TTY
        subprocess.run(cmd, env=env, check=False)
    finally:
        # Wipe the snapshot on exit
        _cleanup(local_dir)
