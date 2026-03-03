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

    return local


def _cleanup(local_dir: Path):
    """Remove the staged .quest-<name>/ directory from CWD."""
    if local_dir.exists():
        shutil.rmtree(local_dir)


def build_system_prompt(quest_id: str, local_dir_name: str) -> str:
    meta = state.get_quest(quest_id)
    depth = state.quest_depth(quest_id)
    state_content = state.get_state(quest_id)

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

## Accumulated State
{state_content}

## Quest Snapshot

A read-only snapshot is at `{local_dir_name}/` in your working directory:
```
{local_dir_name}/
  meta.json, state.md, log.md, files/
```

To read another quest's contents, use `claude-quest dump <name|id>` to copy it into the working directory.

## Quest Commands Reference

**NEVER run these unless the user explicitly asks you to.** Do not auto-commit, auto-attach, auto-merge, or auto-dump.

**Before any commit:** Always read the current `{local_dir_name}/state.md` and `{local_dir_name}/log.md` first. Then draft what you plan to write and show it to the user for confirmation before running the commit command. Commits are versioned — every commit creates a permanent forward entry in history.

**Dumped snapshots are temporary.** When you dump another quest's content for reference, clean up the `.quest-<name>/` directory (rm -rf) once you're done reading it. Don't leave dumped snapshots lying around.

| Command | What it does |
|---|---|
| `claude-quest commit --state "..."` | Overwrite state.md |
| `claude-quest commit --log "..."` | Append to log.md |
| `claude-quest merge <id>` | Mark a quest as merged |
| `claude-quest dump <id>` | Dump a quest's contents into CWD for reading |
| `claude-quest dump <id> --state --log` | Dump only specific files |
| `claude-quest attach <file>` | Save a file to quest storage |
| `claude-quest rename {meta.id} "name"` | Rename this quest |
| `claude-quest describe {meta.id} --set "desc"` | Set description |
| `claude-quest tree` | Show quest tree |
| `claude-quest status` | Show quest details |
| `claude-quest history` | Show version history |
| `claude-quest show <hash>` | Inspect contents at a specific version |
| `claude-quest restore <hash>` | Restore to a specific version (forward commit) |
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

    # Auto-approve read operations and dump
    ALLOWED_TOOLS = [
        "Bash(claude-quest status*)",
        "Bash(claude-quest tree*)",
        "Bash(claude-quest list*)",
        "Bash(claude-quest log*)",
        "Bash(claude-quest describe*)",
        "Bash(claude-quest history*)",
        "Bash(claude-quest show*)",
        "Bash(claude-quest dump*)",
    ]

    prompt_flag = "--system-prompt" if prompt_mode == "replace" else "--append-system-prompt"
    cmd = ["claude", prompt_flag, prompt]
    for tool in ALLOWED_TOOLS:
        cmd.extend(["--allowedTools", tool])
    if extra_args:
        cmd.extend(extra_args)

    try:
        # No stdin/stdout/stderr capture = inherits parent's TTY
        subprocess.run(cmd, env=env, check=False)
    finally:
        # Wipe the snapshot on exit
        _cleanup(local_dir)
