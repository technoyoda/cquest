"""Click command group and all CLI commands."""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import claude, state

console = Console()


@click.group()
def cli():
    """claude-quest: Manage longitudinal project context across Claude Code sessions."""
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("name")
@click.option("--system-prompt", "-s", default=None, help="Additional system prompt text.")
@click.option("--prompt-mode", type=click.Choice(["append", "replace"]), default="append", help="How to inject the quest prompt: append to default or replace it.")
@click.option("--max-state-size", default=claude.DEFAULT_MAX_STATE_KB, type=int, help="Max state.md size in KB (default: 80).")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def new(name: str, system_prompt: str | None, prompt_mode: str, max_state_size: int, extra_args: tuple):
    """Create a new root quest and launch Claude.

    Extra args after -- are passed through to claude.
    """
    if state.name_exists(name):
        console.print(f"[red]Quest named '{name}' already exists.[/red]")
        raise SystemExit(1)
    meta = state.create_quest(name)
    state.set_active(meta.id)
    console.print(f"[green]Created quest[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
    claude.launch_claude(
        meta.id,
        extra_args=list(extra_args) if extra_args else None,
        extra_system_prompt=system_prompt,
        prompt_mode=prompt_mode,
        max_state_kb=max_state_size,
    )


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("id_or_name", required=False)
@click.option("--system-prompt", "-s", default=None, help="Additional system prompt text.")
@click.option("--prompt-mode", type=click.Choice(["append", "replace"]), default="append", help="How to inject the quest prompt: append to default or replace it.")
@click.option("--max-state-size", default=claude.DEFAULT_MAX_STATE_KB, type=int, help="Max state.md size in KB (default: 80).")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def go(id_or_name: str | None, system_prompt: str | None, prompt_mode: str, max_state_size: int, extra_args: tuple):
    """Resume a quest and launch Claude.

    Extra args after -- are passed through to claude.
    """
    # If id_or_name looks like a flag, it's a passthrough arg, not a quest name
    if id_or_name is not None and id_or_name.startswith("-"):
        extra_args = (id_or_name,) + extra_args
        id_or_name = None

    if id_or_name is None:
        active = state.get_active()
        if active is None:
            console.print("[red]No active quest. Specify a quest name/id or create one with 'claude-quest new'.[/red]")
            raise SystemExit(1)
        meta = active
    else:
        try:
            meta = state.get_quest(id_or_name)
        except FileNotFoundError:
            console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
            raise SystemExit(1)

    state.set_active(meta.id)
    console.print(f"[green]Resuming quest[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
    claude.launch_claude(
        meta.id,
        extra_args=list(extra_args) if extra_args else None,
        extra_system_prompt=system_prompt,
        prompt_mode=prompt_mode,
        max_state_kb=max_state_size,
    )


@cli.command(context_settings={"ignore_unknown_options": True})
@click.option("--name", "-n", default=None, help="Name for the new quest (auto-generated if omitted).")
@click.option("--from", "from_quest", default=None, help="Source quest name or ID (default: active quest).")
@click.option("--fork", is_flag=True, help="Fork as independent root instead of a child branch.")
@click.option("--system-prompt", "-s", default=None, help="Additional system prompt text.")
@click.option("--prompt-mode", type=click.Choice(["append", "replace"]), default="append", help="How to inject the quest prompt: append to default or replace it.")
@click.option("--max-state-size", default=claude.DEFAULT_MAX_STATE_KB, type=int, help="Max state.md size in KB (default: 80).")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def side(name: str | None, from_quest: str | None, fork: bool, system_prompt: str | None, prompt_mode: str, max_state_size: int, extra_args: tuple):
    """Branch or fork from an existing quest and launch Claude.

    By default, creates a side quest (child branch) under the source quest.
    Use --fork to create an independent root that copies the source's state
    but has no parent link.

    Extra args after -- are passed through to claude.
    """
    if from_quest:
        try:
            source = state.get_quest(from_quest)
        except FileNotFoundError:
            console.print(f"[red]Quest '{from_quest}' not found.[/red]")
            raise SystemExit(1)
    else:
        source = state.get_active()
        if source is None:
            console.print("[red]No active quest. Use --from <quest> or create one with 'claude-quest new' first.[/red]")
            raise SystemExit(1)

    prefix = "fork" if fork else "side"
    side_name = name or f"{prefix}-{source.name}"
    if state.name_exists(side_name):
        console.print(f"[red]Quest named '{side_name}' already exists.[/red]")
        raise SystemExit(1)
    meta = state.create_quest(side_name, parent_id=source.id, fork=fork)
    state.set_active(meta.id)

    if fork:
        console.print(
            f"[green]Forked[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]"
            f" from [bold]{source.name}[/bold] [dim](independent root)[/dim]"
        )
    else:
        console.print(
            f"[green]Created side quest[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]"
            f" from [bold]{source.name}[/bold]"
        )
    claude.launch_claude(
        meta.id,
        extra_args=list(extra_args) if extra_args else None,
        extra_system_prompt=system_prompt,
        prompt_mode=prompt_mode,
        max_state_kb=max_state_size,
    )


@cli.command()
@click.argument("root_id", required=False)
def tree(root_id: str | None):
    """Print the quest tree."""
    if root_id:
        try:
            meta = state.get_quest(root_id)
            state.render_tree(meta.id)
        except FileNotFoundError:
            console.print(f"[red]Quest '{root_id}' not found.[/red]")
            raise SystemExit(1)
    else:
        state.render_tree()


@cli.command()
@click.argument("id_or_name", required=False)
def status(id_or_name: str | None):
    """Show details for a quest (default: active quest)."""
    if id_or_name:
        try:
            meta = state.get_quest(id_or_name)
        except FileNotFoundError:
            console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
            raise SystemExit(1)
    else:
        meta = state.get_active()
        if meta is None:
            console.print("[red]No active quest.[/red]")
            raise SystemExit(1)
    state.render_status(meta)


@cli.command()
@click.argument("id_or_name")
@click.argument("name")
def rename(id_or_name: str, name: str):
    """Rename a quest."""
    try:
        meta = state.get_quest(id_or_name)
    except FileNotFoundError:
        console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
        raise SystemExit(1)
    if state.name_exists(name):
        console.print(f"[red]Quest named '{name}' already exists.[/red]")
        raise SystemExit(1)
    state.update_meta(meta.id, name=name)
    console.print(f"[green]Renamed[/green] [dim]({meta.id})[/dim] → [bold]{name}[/bold]")


@cli.command()
@click.argument("id_or_name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
def delete(id_or_name: str, force: bool):
    """Delete a quest and all its children."""
    try:
        meta = state.get_quest(id_or_name)
    except FileNotFoundError:
        console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
        raise SystemExit(1)

    children = state.get_children(meta.id)
    if not force:
        msg = f"Delete [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]"
        if children:
            msg += f" and [bold]{len(children)}[/bold] children"
        msg += "? [dim](y/N)[/dim] "
        answer = console.input(msg).strip().lower()
        if answer not in ("y", "yes"):
            console.print("[dim]Cancelled.[/dim]")
            return

    state.delete_quest(meta.id)
    console.print(f"[red]Deleted[/red] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")


@cli.command("list")
def list_cmd():
    """List all root quests."""
    roots = state.list_roots()
    if not roots:
        console.print("[dim]No quests found.[/dim]")
        return

    active = state.get_active()
    active_id = active.id if active else None

    table = Table(show_header=True)
    table.add_column("Name", style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Sessions", justify="right")
    table.add_column("Children", justify="right")
    table.add_column("Description", style="dim")

    for r in roots:
        marker = " [yellow]●[/yellow]" if r.id == active_id else ""
        children_count = len(state.get_children(r.id))
        table.add_row(
            f"{r.name}{marker}",
            r.id,
            r.status,
            str(r.session_count),
            str(children_count),
            r.description or "",
        )
    console.print(table)


@cli.command("init-git")
def init_git():
    """Initialize git versioning for all quests that don't have it yet."""
    all_quests = state.list_all()
    if not all_quests:
        console.print("[dim]No quests found.[/dim]")
        return

    initialized = 0
    skipped = 0
    for q in all_quests:
        if state._has_git(q.id):
            skipped += 1
        else:
            state.git_init(q.id)
            console.print(f"  [green]Initialized[/green] [bold]{q.name}[/bold] [dim]({q.id})[/dim]")
            initialized += 1

    if initialized == 0:
        console.print(f"[dim]All {skipped} quest(s) already have git.[/dim]")
    else:
        console.print(f"[green]Initialized {initialized} quest(s)[/green], {skipped} already had git.")


@cli.command()
@click.argument("id_or_name", required=False)
def log(id_or_name: str | None):
    """Show session log for a quest."""
    if id_or_name:
        try:
            meta = state.get_quest(id_or_name)
        except FileNotFoundError:
            console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
            raise SystemExit(1)
    else:
        meta = state.get_active()
        if meta is None:
            console.print("[red]No active quest.[/red]")
            raise SystemExit(1)

    log_content = state.get_log(meta.id)
    if log_content.strip():
        console.print(log_content)
    else:
        console.print("[dim]No log entries yet.[/dim]")


@cli.command()
@click.argument("id_or_name", required=False)
@click.option("--set", "new_desc", default=None, help="Set a new description.")
def describe(id_or_name: str | None, new_desc: str | None):
    """Show or set a quest's description."""
    if id_or_name:
        try:
            meta = state.get_quest(id_or_name)
        except FileNotFoundError:
            console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
            raise SystemExit(1)
    else:
        meta = state.get_active()
        if meta is None:
            console.print("[red]No active quest.[/red]")
            raise SystemExit(1)

    if new_desc is not None:
        state.update_meta(meta.id, description=new_desc)
        console.print(f"[green]Updated description for[/green] [bold]{meta.name}[/bold]")
    elif meta.description:
        console.print(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
        console.print(meta.description)
    else:
        console.print(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
        console.print("[dim]No description set.[/dim]")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--quest", "-q", default=None, help="Quest ID (reads CLAUDE_QUEST_ID from env if omitted).")
def attach(file: str, quest: str | None):
    """Copy a file into the quest's files/ directory in the global store."""
    quest_id = quest or os.environ.get("CLAUDE_QUEST_ID")
    if not quest_id:
        console.print("[red]No quest specified. Use --quest or set CLAUDE_QUEST_ID.[/red]")
        raise SystemExit(1)

    try:
        state.get_quest(quest_id)
    except FileNotFoundError:
        console.print(f"[red]Quest '{quest_id}' not found.[/red]")
        raise SystemExit(1)

    src = Path(file)
    dest_dir = state.get_files_dir(quest_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    console.print(f"[green]Attached[/green] {src.name} → [dim]{dest}[/dim]")


@cli.command()
@click.option("--state", "state_content", default=None, help="New state.md content.")
@click.option("--log", "log_entry", default=None, help="Entry to append to log.md.")
@click.option("--quest", "-q", default=None, help="Quest ID (reads CLAUDE_QUEST_ID from env if omitted).")
def commit(state_content: str | None, log_entry: str | None, quest: str | None):
    """Persist quest state changes to the global store.

    Called by Claude during a session to save progress. Writes directly
    to ~/.quests/quests/<id>/.
    """
    quest_id = quest or os.environ.get("CLAUDE_QUEST_ID")
    if not quest_id:
        console.print("[red]No quest specified. Use --quest or set CLAUDE_QUEST_ID.[/red]")
        raise SystemExit(1)

    try:
        meta = state.get_quest(quest_id)
    except FileNotFoundError:
        console.print(f"[red]Quest '{quest_id}' not found.[/red]")
        raise SystemExit(1)

    if state_content is None and log_entry is None:
        console.print("[red]Nothing to commit. Use --state or --log.[/red]")
        raise SystemExit(1)

    if state_content is not None:
        state.write_state(quest_id, state_content)
        console.print(f"[green]Committed state for[/green] [bold]{meta.name}[/bold]")

    if log_entry is not None:
        state.append_log(quest_id, log_entry)
        console.print(f"[green]Appended log entry for[/green] [bold]{meta.name}[/bold]")

    # Implicit git commit — history moves forward
    parts = []
    if state_content is not None:
        parts.append("state")
    if log_entry is not None:
        parts.append("log")
    state.git_commit(quest_id, f"commit: {', '.join(parts)}")


@cli.command()
@click.argument("id_or_name")
def merge(id_or_name: str):
    """Mark a quest as merged."""
    try:
        meta = state.get_quest(id_or_name)
    except FileNotFoundError:
        console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
        raise SystemExit(1)

    if meta.status == "merged":
        console.print(f"[yellow]{meta.name}[/yellow] [dim]({meta.id})[/dim] is already merged.")
        return

    state.update_meta(meta.id, status="merged")
    console.print(f"[green]Merged[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")


@cli.command()
@click.argument("id_or_name")
@click.option("--state", "dump_state", is_flag=True, help="Dump state.md.")
@click.option("--log", "dump_log", is_flag=True, help="Dump log.md.")
@click.option("--meta", "dump_meta", is_flag=True, help="Dump meta.json.")
@click.option("--files", "dump_files", is_flag=True, help="Dump files/ directory.")
@click.option("-o", "--output", default=None, help="Output directory (default: .quest-<name>/ in CWD).")
def dump(id_or_name: str, dump_state: bool, dump_log: bool, dump_meta: bool, dump_files: bool, output: str | None):
    """Dump a quest's contents into a directory for reading.

    Creates .quest-<name>/ in the current directory by default, or at
    the path given by -o. If no filters are given, dumps everything.
    Use filters to pick specific files.

    Clean up the dumped directory when you're done with it.
    """
    try:
        meta = state.get_quest(id_or_name)
    except FileNotFoundError:
        console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
        raise SystemExit(1)

    # No flags = dump everything
    dump_all = not (dump_state or dump_log or dump_meta or dump_files)

    quest_dir = state.get_quest_dir(meta.id)
    local = Path(output) if output else Path.cwd() / f".quest-{meta.name}"
    local.mkdir(parents=True, exist_ok=True)

    dumped = []
    if dump_all or dump_meta:
        src = quest_dir / "meta.json"
        if src.exists():
            shutil.copy2(src, local / "meta.json")
            dumped.append("meta.json")

    if dump_all or dump_state:
        src = quest_dir / "state.md"
        if src.exists():
            shutil.copy2(src, local / "state.md")
            dumped.append("state.md")

    if dump_all or dump_log:
        src = quest_dir / "log.md"
        if src.exists():
            shutil.copy2(src, local / "log.md")
            dumped.append("log.md")

    if dump_all or dump_files:
        src_files = state.get_files_dir(meta.id)
        dst_files = local / "files"
        if src_files.exists() and any(src_files.iterdir()):
            if dst_files.exists():
                shutil.rmtree(dst_files)
            shutil.copytree(src_files, dst_files)
            dumped.append("files/")

    console.print(
        f"[green]Dumped[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim] → [dim]{local}[/dim]"
    )
    for f in dumped:
        console.print(f"  {f}")


@cli.command()
@click.option("--quest", "-q", default=None, help="Quest name or ID (reads CLAUDE_QUEST_ID from env if omitted).")
@click.option("--limit", "-n", default=20, help="Number of entries to show.")
def history(quest: str | None, limit: int):
    """Show version history for a quest."""
    quest_ref = quest or os.environ.get("CLAUDE_QUEST_ID")
    if quest_ref:
        try:
            meta = state.get_quest(quest_ref)
        except FileNotFoundError:
            console.print(f"[red]Quest '{quest_ref}' not found.[/red]")
            raise SystemExit(1)
    else:
        meta = state.get_active()
        if meta is None:
            console.print("[red]No quest specified. Use --quest, set CLAUDE_QUEST_ID, or have an active quest.[/red]")
            raise SystemExit(1)

    entries = state.git_history(meta.id, limit=limit)
    if not entries:
        console.print("[dim]No history yet.[/dim]")
        return

    table = Table(show_header=True)
    table.add_column("Hash", style="dim", width=7)
    table.add_column("Date", style="dim")
    table.add_column("Message")

    for e in entries:
        table.add_row(e["hash"][:7], e["date"][:19], e["message"])
    console.print(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim] — version history")
    console.print(table)


@cli.command()
@click.argument("commit_hash")
@click.option("--quest", "-q", default=None, help="Quest ID (reads CLAUDE_QUEST_ID from env if omitted).")
@click.option("--file", "-f", "filename", default=None, help="Show a specific file (default: state.md and log.md).")
def show(commit_hash: str, quest: str | None, filename: str | None):
    """Show quest contents at a specific version."""
    quest_id = quest or os.environ.get("CLAUDE_QUEST_ID")
    if not quest_id:
        active = state.get_active()
        if active is None:
            console.print("[red]No quest specified. Use --quest, set CLAUDE_QUEST_ID, or have an active quest.[/red]")
            raise SystemExit(1)
        quest_id = active.id

    try:
        meta = state.get_quest(quest_id)
    except FileNotFoundError:
        console.print(f"[red]Quest '{quest_id}' not found.[/red]")
        raise SystemExit(1)

    if filename:
        content = state.git_show(quest_id, commit_hash, filename)
        if content is None:
            console.print(f"[red]File '{filename}' not found at {commit_hash[:7]}.[/red]")
            raise SystemExit(1)
        console.print(content)
    else:
        console.print(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim] @ [dim]{commit_hash[:7]}[/dim]\n")
        for fname in ("state.md", "log.md"):
            content = state.git_show(quest_id, commit_hash, fname)
            if content is not None:
                console.print(f"[bold]── {fname} ──[/bold]")
                console.print(content)
            else:
                console.print(f"[bold]── {fname} ──[/bold]")
                console.print("[dim](not present)[/dim]")


@cli.command()
@click.argument("commit_hash")
@click.option("--quest", "-q", default=None, help="Quest ID (reads CLAUDE_QUEST_ID from env if omitted).")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
def restore(commit_hash: str, quest: str | None, force: bool):
    """Restore quest state to a specific version. History moves forward."""
    quest_id = quest or os.environ.get("CLAUDE_QUEST_ID")
    if not quest_id:
        active = state.get_active()
        if active is None:
            console.print("[red]No quest specified. Use --quest, set CLAUDE_QUEST_ID, or have an active quest.[/red]")
            raise SystemExit(1)
        quest_id = active.id

    try:
        meta = state.get_quest(quest_id)
    except FileNotFoundError:
        console.print(f"[red]Quest '{quest_id}' not found.[/red]")
        raise SystemExit(1)

    if not force:
        msg = (
            f"Restore [bold]{meta.name}[/bold] [dim]({meta.id})[/dim] "
            f"to version [dim]{commit_hash[:7]}[/dim]? "
            f"This creates a new forward commit. [dim](y/N)[/dim] "
        )
        answer = console.input(msg).strip().lower()
        if answer not in ("y", "yes"):
            console.print("[dim]Cancelled.[/dim]")
            return

    ok = state.git_restore(quest_id, commit_hash)
    if ok:
        console.print(
            f"[green]Restored[/green] [bold]{meta.name}[/bold] to version [dim]{commit_hash[:7]}[/dim]"
        )
    else:
        console.print(
            f"[yellow]Nothing to restore[/yellow] — version [dim]{commit_hash[:7]}[/dim] "
            f"is identical to current state, or commit not found."
        )


@cli.command("export")
@click.argument("id_or_name", required=False)
@click.option("--tree", "export_tree", is_flag=True, help="Export the full quest tree.")
@click.option("--all", "export_all", is_flag=True, help="Export all quests.")
@click.option("-o", "--output", default=None, help="Output file path (default: auto-generated).")
def export_cmd(id_or_name: str | None, export_tree: bool, export_all: bool, output: str | None):
    """Export quests as a .tar.gz archive."""
    if export_all:
        quests = state.list_all()
        if not quests:
            console.print("[red]No quests to export.[/red]")
            raise SystemExit(1)
        default_name = "quests-all.tar.gz"
    elif id_or_name:
        try:
            meta = state.get_quest(id_or_name)
        except FileNotFoundError:
            console.print(f"[red]Quest '{id_or_name}' not found.[/red]")
            raise SystemExit(1)

        if export_tree:
            quests = state.get_tree(meta.id)
            default_name = f"quests-{meta.name}.tar.gz"
        else:
            quests = [meta]
            default_name = f"quest-{meta.name}.tar.gz"
    else:
        console.print("[red]Specify a quest name/id, or use --all.[/red]")
        raise SystemExit(1)

    out_path = Path(output) if output else Path.cwd() / default_name

    with tarfile.open(out_path, "w:gz") as tar:
        for q in quests:
            quest_dir = state.get_quest_dir(q.id)
            if quest_dir.exists():
                tar.add(quest_dir, arcname=f"quests/{q.id}")

    console.print(f"[green]Exported {len(quests)} quest(s)[/green] → [dim]{out_path}[/dim]")
    for q in quests:
        label = "[red](orphan)[/red] " if state.is_orphan(q) else ""
        console.print(f"  {label}[bold]{q.name}[/bold] [dim]({q.id})[/dim]")


@cli.command("import")
@click.argument("archive", type=click.Path(exists=True))
@click.option("--force", "-f", is_flag=True, help="Overwrite existing quests on ID collision.")
def import_cmd(archive: str, force: bool):
    """Import quests from a .tar.gz archive."""
    archive_path = Path(archive)

    with tarfile.open(archive_path, "r:gz") as tar:
        # Validate structure: expect quests/<id>/meta.json
        members = tar.getnames()
        quest_ids = set()
        for name in members:
            parts = name.split("/")
            if len(parts) >= 2 and parts[0] == "quests":
                quest_ids.add(parts[1])

        if not quest_ids:
            console.print("[red]No quests found in archive.[/red]")
            raise SystemExit(1)

        # Check for collisions
        collisions = []
        for qid in quest_ids:
            if state.get_quest_dir(qid).exists():
                collisions.append(qid)

        if collisions and not force:
            console.print(f"[yellow]Warning:[/yellow] {len(collisions)} quest(s) already exist locally:")
            for qid in collisions:
                try:
                    existing = state.get_quest(qid)
                    console.print(f"  [bold]{existing.name}[/bold] [dim]({qid})[/dim]")
                except FileNotFoundError:
                    console.print(f"  [dim]({qid})[/dim]")
            console.print("Use [bold]--force[/bold] to overwrite.")
            raise SystemExit(1)

        # Extract
        state._ensure_root()
        tar.extractall(path=state.QUESTS_ROOT)

    # Report what was imported
    imported = []
    for qid in quest_ids:
        try:
            m = state.get_quest(qid)
            imported.append(m)
        except FileNotFoundError:
            pass

    console.print(f"[green]Imported {len(imported)} quest(s)[/green] from [dim]{archive_path.name}[/dim]")
    for q in imported:
        label = "[red](orphan)[/red] " if state.is_orphan(q) else ""
        console.print(f"  {label}[bold]{q.name}[/bold] [dim]({q.id})[/dim]")
