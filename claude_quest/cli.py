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
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def new(name: str, system_prompt: str | None, prompt_mode: str, extra_args: tuple):
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
    )


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("id_or_name", required=False)
@click.option("--system-prompt", "-s", default=None, help="Additional system prompt text.")
@click.option("--prompt-mode", type=click.Choice(["append", "replace"]), default="append", help="How to inject the quest prompt: append to default or replace it.")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def go(id_or_name: str | None, system_prompt: str | None, prompt_mode: str, extra_args: tuple):
    """Resume a quest and launch Claude.

    Extra args after -- are passed through to claude.
    """
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
    )


@cli.command(context_settings={"ignore_unknown_options": True})
@click.option("--name", "-n", default=None, help="Name for the side quest (auto-generated if omitted).")
@click.option("--system-prompt", "-s", default=None, help="Additional system prompt text.")
@click.option("--prompt-mode", type=click.Choice(["append", "replace"]), default="append", help="How to inject the quest prompt: append to default or replace it.")
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def side(name: str | None, system_prompt: str | None, prompt_mode: str, extra_args: tuple):
    """Fork a side quest from the active quest and launch Claude.

    Extra args after -- are passed through to claude.
    """
    active = state.get_active()
    if active is None:
        console.print("[red]No active quest. Create one with 'claude-quest new' first.[/red]")
        raise SystemExit(1)

    side_name = name or f"side-{active.name}"
    if state.name_exists(side_name):
        console.print(f"[red]Quest named '{side_name}' already exists.[/red]")
        raise SystemExit(1)
    meta = state.create_quest(side_name, parent_id=active.id)
    state.set_active(meta.id)
    console.print(
        f"[green]Created side quest[/green] [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]"
        f" from [bold]{active.name}[/bold]"
    )
    claude.launch_claude(
        meta.id,
        extra_args=list(extra_args) if extra_args else None,
        extra_system_prompt=system_prompt,
        prompt_mode=prompt_mode,
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
@click.option("--merge", "merge_id", default=None, help="Mark a child quest as merged.")
@click.option("--quest", "-q", default=None, help="Quest ID (reads CLAUDE_QUEST_ID from env if omitted).")
def commit(state_content: str | None, log_entry: str | None, merge_id: str | None, quest: str | None):
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

    if state_content is None and log_entry is None and merge_id is None:
        console.print("[red]Nothing to commit. Use --state, --log, or --merge.[/red]")
        raise SystemExit(1)

    if state_content is not None:
        state.write_state(quest_id, state_content)
        console.print(f"[green]Committed state for[/green] [bold]{meta.name}[/bold]")

    if log_entry is not None:
        state.append_log(quest_id, log_entry)
        console.print(f"[green]Appended log entry for[/green] [bold]{meta.name}[/bold]")

    if merge_id is not None:
        try:
            child = state.get_quest(merge_id)
            state.update_meta(child.id, status="merged")
            console.print(f"[green]Marked[/green] [bold]{child.name}[/bold] [dim]({child.id})[/dim] as merged")
        except FileNotFoundError:
            console.print(f"[red]Child quest '{merge_id}' not found.[/red]")
            raise SystemExit(1)


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
