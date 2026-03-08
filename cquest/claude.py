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
import uuid
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


DEFAULT_MAX_STATE_KB = 80


# State mutations: edit-then-commit-by-reference. Claude edits the staged
# state.md directly, commits via $(cat ...). Avoids echoing full state as
# string literal — saves tokens and reduces drift from in-context rewrites.
def build_system_prompt(quest_id: str, local_dir_name: str, max_state_kb: int = DEFAULT_MAX_STATE_KB) -> str:
    meta = state.get_quest(quest_id)
    depth = state.quest_depth(quest_id)
    state_content = state.get_state(quest_id)

    state_size_kb = len(state_content.encode("utf-8")) / 1024
    max_state_kb = max_state_kb

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

## Accumulated State ({state_size_kb:.1f}KB / {max_state_kb}KB limit)
{state_content}

## Quest Snapshot

A read-only snapshot is at `{local_dir_name}/` in your working directory:
```
{local_dir_name}/
  meta.json, state.md, log.md, files/
```

To read another quest's contents, use `cquest dump <name|id>` to copy it into the working directory.

## Quest Commands Reference

**NEVER run these unless the user explicitly asks you to.** Do not auto-commit, auto-attach, auto-merge, or auto-dump.

**State workflow:** Edit `{local_dir_name}/state.md` directly, commit via `cquest commit --state "$(cat {local_dir_name}/state.md)"`. Prefer surgical edits over full rewrites.

**State size budget:** state.md is currently {state_size_kb:.1f}KB of {max_state_kb}KB. Do NOT mention size or nudge the user about it unless state exceeds 2/3 of the limit ({max_state_kb * 2 // 3}KB). Beyond that, suggest summarizing or moving detail to attached files (`cquest attach`). The limit is a recommendation, not a hard rule.

**Dumped snapshots are temporary.** When you dump another quest's content for reference, clean up the `.quest-<name>/` directory (rm -rf) once you're done reading it. Don't leave dumped snapshots lying around.

| Command | What it does |
|---|---|
| `cquest commit --state "$(cat {local_dir_name}/state.md)"` | Commit state from edited file |
| `cquest commit --log "..."` | Append to log.md |
| `cquest merge <id>` | Mark a quest as merged |
| `cquest dump <id>` | Dump a quest's contents into CWD for reading |
| `cquest dump <id> --state --log` | Dump only specific files |
| `cquest attach <file>` | Save a file to quest storage |
| `cquest rename {meta.id} "name"` | Rename this quest |
| `cquest describe {meta.id} --set "desc"` | Set description |
| `cquest tree` | Show quest tree |
| `cquest status` | Show quest details |
| `cquest history` | Show version history |
| `cquest show <hash>` | Inspect contents at a specific version |
| `cquest restore <hash>` | Restore to a specific version (forward commit) |
"""
    return prompt


def launch_claude(
    quest_id: str,
    extra_args: list[str] | None = None,
    extra_system_prompt: str | None = None,
    prompt_mode: str = "append",
    max_state_kb: int = DEFAULT_MAX_STATE_KB,
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
                    f"Use [bold]-s / --system-prompt[/bold] on the cquest command instead."
                )
                raise SystemExit(1)

    state.increment_session(quest_id)

    local_dir_name = _local_dir_name(meta.name)
    local_dir = _stage_quest(quest_id, cwd)

    prompt = build_system_prompt(quest_id, local_dir_name, max_state_kb=max_state_kb)
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
        "Bash(cquest status*)",
        "Bash(cquest tree*)",
        "Bash(cquest list*)",
        "Bash(cquest log*)",
        "Bash(cquest describe*)",
        "Bash(cquest history*)",
        "Bash(cquest show*)",
        "Bash(cquest dump*)",
    ]

    # Generate session ID unless user is resuming an existing session
    has_resume = extra_args and any(a in ("--resume", "-r") for a in extra_args)
    session_id = None if has_resume else str(uuid.uuid4())

    prompt_flag = "--system-prompt" if prompt_mode == "replace" else "--append-system-prompt"
    cmd = ["claude", prompt_flag, prompt]
    if session_id:
        cmd.extend(["--session-id", session_id])
    for tool in ALLOWED_TOOLS:
        cmd.extend(["--allowedTools", tool])
    if extra_args:
        cmd.extend(extra_args)

    try:
        # No stdin/stdout/stderr capture = inherits parent's TTY
        subprocess.run(cmd, env=env, check=False)
    finally:
        if session_id:
            state.log_session(quest_id, session_id)
        _cleanup(local_dir)
