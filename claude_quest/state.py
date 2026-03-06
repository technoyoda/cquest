"""Quest tree and state file management."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.tree import Tree

QUESTS_ROOT = Path.home() / ".quests"
QUESTS_DIR = QUESTS_ROOT / "quests"
ACTIVE_QUEST_FILENAME = ".active_quest"


class QuestMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    root: Optional[str] = None      # root quest ID (self for root quests)
    parent: Optional[str] = None    # immediate parent (null for root quests)
    created_dir: Optional[str] = None  # CWD where quest was created
    status: str = "open"  # open | merged
    created: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_count: int = 0


def _short_id() -> str:
    return uuid.uuid4().hex[:6]


def _quest_dir(quest_id: str) -> Path:
    return QUESTS_DIR / quest_id


def _meta_path(quest_id: str) -> Path:
    return _quest_dir(quest_id) / "meta.json"


def _state_path(quest_id: str) -> Path:
    return _quest_dir(quest_id) / "state.md"


def _log_path(quest_id: str) -> Path:
    return _quest_dir(quest_id) / "log.md"


def _files_dir(quest_id: str) -> Path:
    return _quest_dir(quest_id) / "files"


def _ensure_root():
    QUESTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_meta(meta: QuestMeta):
    meta.updated = datetime.now(timezone.utc).isoformat()
    _meta_path(meta.id).write_text(json.dumps(meta.model_dump(), indent=2) + "\n")


def _load_meta(quest_id: str) -> QuestMeta:
    path = _meta_path(quest_id)
    if not path.exists():
        raise FileNotFoundError(f"Quest '{quest_id}' not found")
    return QuestMeta.model_validate_json(path.read_text())


# --- Public API ---


def create_quest(name: str, parent_id: str | None = None, fork: bool = False) -> QuestMeta:
    _ensure_root()
    qid = _short_id()
    qdir = _quest_dir(qid)
    qdir.mkdir(parents=True)

    if parent_id:
        parent = _load_meta(parent_id)
        cwd = str(Path.cwd())

        if fork:
            # Fork: copy state but become independent root (no parent link)
            meta = QuestMeta(id=qid, name=name, root=qid, parent=None, created_dir=cwd)
        else:
            # Side quest: branch under parent, stay in the tree
            root_id = parent.root or parent.id
            meta = QuestMeta(id=qid, name=name, root=root_id, parent=parent_id, created_dir=cwd)
        _save_meta(meta)

        # Copy source quest's state, log, and files
        parent_dir = _quest_dir(parent_id)
        for fname in ("state.md", "log.md"):
            src = parent_dir / fname
            if src.exists():
                shutil.copy2(src, qdir / fname)
        parent_files = _files_dir(parent_id)
        if parent_files.exists() and any(parent_files.iterdir()):
            shutil.copytree(parent_files, _files_dir(qid))
        else:
            _files_dir(qid).mkdir()
    else:
        # New root quest
        cwd = str(Path.cwd())
        meta = QuestMeta(id=qid, name=name, root=qid, created_dir=cwd)
        _save_meta(meta)
        _files_dir(qid).mkdir()
        _state_path(qid).write_text(f"# {name}\n\n_No state recorded yet._\n")
        _log_path(qid).write_text(f"# Session Log: {name}\n\n")

    # Initialize git repo (fresh history for every quest, including forks)
    git_init(qid)

    return meta


def get_quest(id_or_name: str) -> QuestMeta:
    """Look up a quest by ID or name. ID match takes priority."""
    path = _meta_path(id_or_name)
    if path.exists():
        return QuestMeta.model_validate_json(path.read_text())
    # Scan by name
    if QUESTS_DIR.exists():
        for d in QUESTS_DIR.iterdir():
            mp = d / "meta.json"
            if mp.exists():
                m = QuestMeta.model_validate_json(mp.read_text())
                if m.name == id_or_name:
                    return m
    raise FileNotFoundError(f"Quest '{id_or_name}' not found")


def _active_file() -> Path:
    return Path.cwd() / ACTIVE_QUEST_FILENAME


def set_active(quest_id: str):
    _active_file().write_text(quest_id)


def get_active() -> QuestMeta | None:
    af = _active_file()
    if not af.exists():
        return None
    qid = af.read_text().strip()
    if not qid:
        return None
    try:
        return _load_meta(qid)
    except FileNotFoundError:
        return None


def is_orphan(meta: QuestMeta) -> bool:
    return meta.parent is not None and not _meta_path(meta.parent).exists()


def list_roots() -> list[QuestMeta]:
    """List root quests and orphans (quests whose parent no longer exists)."""
    results = []
    if not QUESTS_DIR.exists():
        return results
    for d in sorted(QUESTS_DIR.iterdir()):
        mp = d / "meta.json"
        if mp.exists():
            m = QuestMeta.model_validate_json(mp.read_text())
            if m.parent is None or is_orphan(m):
                results.append(m)
    return results


def list_all() -> list[QuestMeta]:
    results = []
    if not QUESTS_DIR.exists():
        return results
    for d in sorted(QUESTS_DIR.iterdir()):
        mp = d / "meta.json"
        if mp.exists():
            results.append(QuestMeta.model_validate_json(mp.read_text()))
    return results


def get_tree(quest_id: str) -> list[QuestMeta]:
    """Get all quests that share the same root as quest_id."""
    meta = _load_meta(quest_id)
    root_id = meta.root or meta.id
    results = []
    if not QUESTS_DIR.exists():
        return results
    for d in QUESTS_DIR.iterdir():
        mp = d / "meta.json"
        if mp.exists():
            m = QuestMeta.model_validate_json(mp.read_text())
            if m.root == root_id or m.id == root_id:
                results.append(m)
    return results


def name_exists(name: str) -> bool:
    if not QUESTS_DIR.exists():
        return False
    for d in QUESTS_DIR.iterdir():
        mp = d / "meta.json"
        if mp.exists():
            m = QuestMeta.model_validate_json(mp.read_text())
            if m.name == name:
                return True
    return False


def get_children(quest_id: str) -> list[QuestMeta]:
    """Find all quests whose parent is quest_id."""
    children = []
    if not QUESTS_DIR.exists():
        return children
    for d in QUESTS_DIR.iterdir():
        mp = d / "meta.json"
        if mp.exists():
            m = QuestMeta.model_validate_json(mp.read_text())
            if m.parent == quest_id:
                children.append(m)
    return children


def delete_quest(quest_id: str):
    """Delete a quest and all its descendants."""
    _load_meta(quest_id)  # validate exists

    # Recursively delete children (discovered by scan)
    for child in get_children(quest_id):
        delete_quest(child.id)

    # Clear active if this was the active quest
    # Clear active if this was the active quest in CWD
    af = _active_file()
    if af.exists() and af.read_text().strip() == quest_id:
        af.unlink()

    # Remove the quest directory
    qdir = _quest_dir(quest_id)
    if qdir.exists():
        shutil.rmtree(qdir)


def update_meta(quest_id: str, **kwargs):
    meta = _load_meta(quest_id)
    for k, v in kwargs.items():
        if hasattr(meta, k):
            setattr(meta, k, v)
    _save_meta(meta)


def increment_session(quest_id: str):
    meta = _load_meta(quest_id)
    meta.session_count += 1
    _save_meta(meta)


def get_state(quest_id: str) -> str:
    path = _state_path(quest_id)
    if path.exists():
        return path.read_text()
    return ""


def write_state(quest_id: str, content: str):
    _state_path(quest_id).write_text(content)
    _load_meta(quest_id)  # validate quest exists
    meta = _load_meta(quest_id)
    _save_meta(meta)  # touch updated timestamp


def get_log(quest_id: str) -> str:
    path = _log_path(quest_id)
    if path.exists():
        return path.read_text()
    return ""


def append_log(quest_id: str, entry: str):
    path = _log_path(quest_id)
    existing = path.read_text() if path.exists() else ""
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + entry + "\n")


def get_quest_dir(quest_id: str) -> Path:
    return _quest_dir(quest_id)


def get_files_dir(quest_id: str) -> Path:
    return _files_dir(quest_id)


# Sessions live outside quest directories intentionally. Quests are long-horizon
# knowledge state — every object in a quest gets first-class version control.
# Sessions are operational metadata (which Claude process ran when) that shouldn't
# intermingle with real state, get copied on side-quests, or pollute git history.
def _sessions_dir() -> Path:
    return QUESTS_ROOT / "sessions"


def log_session(quest_id: str, session_id: str):
    """Append a session ID to the quest's session log (outside quest dir)."""
    sdir = _sessions_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    path = sdir / f"{quest_id}.json"
    sessions = json.loads(path.read_text()) if path.exists() else []
    sessions.append({
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    path.write_text(json.dumps(sessions, indent=2) + "\n")


def get_sessions(quest_id: str) -> list[dict]:
    """Read session log for a quest, deduplicated by session_id."""
    path = _sessions_dir() / f"{quest_id}.json"
    if not path.exists():
        return []
    sessions = json.loads(path.read_text())
    seen = set()
    unique = []
    for s in sessions:
        sid = s.get("session_id")
        if sid not in seen:
            seen.add(sid)
            unique.append(s)
    return unique


def find_transcript(session_id: str) -> Path | None:
    """Find the .jsonl transcript for a session ID."""
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return None
    for project_dir in claude_projects.iterdir():
        candidate = project_dir / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate
    return None


# Cost data isn't exposed by the claude CLI when wrapping over the shell.
# As a naive workaround we calculate prices lazily in the cost function
# from token counts + a hardcoded pricing table. If there's ever a simpler
# way (e.g. cost field in transcripts or a CLI flag), replace this.
# Per-million-token pricing. Update when Anthropic changes prices.
MODEL_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0, "cache_write": 1.00, "cache_read": 0.08},
}


def parse_transcript_usage(transcript_path: Path) -> dict:
    """Sum token usage and compute USD cost from a transcript."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    model = None
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            msg = d.get("message", {})
            if isinstance(msg, dict):
                if "model" in msg and model is None:
                    model = msg["model"]
                if "usage" in msg:
                    u = msg["usage"]
                    for key in totals:
                        totals[key] += u.get(key, 0)

    totals["model"] = model
    pricing = MODEL_PRICING.get(model, {})
    if pricing:
        cost = (
            totals["input_tokens"] * pricing["input"]
            + totals["output_tokens"] * pricing["output"]
            + totals["cache_creation_input_tokens"] * pricing["cache_write"]
            + totals["cache_read_input_tokens"] * pricing["cache_read"]
        ) / 1_000_000
        totals["cost_usd"] = round(cost, 4)
    else:
        totals["cost_usd"] = None

    return totals


def quest_total_cost(quest_id: str) -> float | None:
    """Sum USD cost across all sessions for a quest. Returns None if no data."""
    sessions = get_sessions(quest_id)
    if not sessions:
        return None
    total = 0.0
    found_any = False
    for s in sessions:
        t = find_transcript(s["session_id"])
        if t:
            usage = parse_transcript_usage(t)
            if usage.get("cost_usd") is not None:
                total += usage["cost_usd"]
                found_any = True
    return round(total, 4) if found_any else None


# --- Git versioning ---


def _git(quest_id: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=_quest_dir(quest_id),
        capture_output=True,
        text=True,
        check=check,
    )


def _has_git(quest_id: str) -> bool:
    return (_quest_dir(quest_id) / ".git").exists()


def git_init(quest_id: str):
    """Initialize a git repo in the quest directory."""
    qdir = _quest_dir(quest_id)
    if (qdir / ".git").exists():
        return
    _git(quest_id, "init", "-q")
    _git(quest_id, "add", "-A")
    _git(quest_id, "commit", "-q", "-m", "quest created")


def git_commit(quest_id: str, message: str):
    """Stage all changes and commit. No-op if nothing changed."""
    if not _has_git(quest_id):
        git_init(quest_id)
    _git(quest_id, "add", "-A")
    # Check if there's anything to commit
    result = _git(quest_id, "diff", "--cached", "--quiet", check=False)
    if result.returncode == 0:
        return  # nothing staged
    _git(quest_id, "commit", "-q", "-m", message)


def git_history(quest_id: str, limit: int = 20) -> list[dict]:
    """Return recent commit history as a list of {hash, date, message}."""
    if not _has_git(quest_id):
        return []
    result = _git(
        quest_id, "log",
        f"--max-count={limit}",
        "--format=%H|%aI|%s",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    entries = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split("|", 2)
        if len(parts) == 3:
            entries.append({"hash": parts[0], "date": parts[1], "message": parts[2]})
    return entries


def git_show(quest_id: str, commit_hash: str, filename: str) -> str | None:
    """Show the contents of a file at a specific commit.

    Returns file contents, or None if the commit/file doesn't exist.
    """
    if not _has_git(quest_id):
        return None
    result = _git(quest_id, "show", f"{commit_hash}:{filename}", check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def git_restore(quest_id: str, commit_hash: str) -> bool:
    """Restore quest files to the state at a given commit.

    Wipes current files and writes the version from commit_hash,
    then creates a NEW forward commit. History only moves forward.

    Returns True if restore succeeded, False otherwise.
    """
    if not _has_git(quest_id):
        return False
    # Validate the commit exists
    result = _git(quest_id, "cat-file", "-t", commit_hash, check=False)
    if result.returncode != 0 or result.stdout.strip() != "commit":
        return False
    # Wipe tracked files, then checkout the target version's content
    _git(quest_id, "rm", "-rf", "--quiet", ".", check=False)
    _git(quest_id, "checkout", commit_hash, "--", ".")
    _git(quest_id, "add", "-A")
    # Only commit if there's actually a diff
    diff = _git(quest_id, "diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        return False  # target version is identical to current
    short = commit_hash[:7]
    _git(quest_id, "commit", "-q", "-m", f"restore: reverted to {short}")
    return True


def quest_depth(quest_id: str) -> int:
    depth = 0
    meta = _load_meta(quest_id)
    while meta.parent:
        depth += 1
        meta = _load_meta(meta.parent)
    return depth


# --- Tree rendering ---


def _relative_time(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        return f"{months}mo ago"
    except (ValueError, TypeError):
        return "?"


def _build_tree_node(tree: Tree, quest_id: str, active_id: str | None):
    try:
        meta = _load_meta(quest_id)
    except FileNotFoundError:
        tree.add(f"[red]? {quest_id} (missing)[/red]")
        return

    status_icon = "[green]●[/green]" if meta.status == "open" else "[dim]◌[/dim]"
    active_marker = " [bold yellow]← active[/bold yellow]" if meta.id == active_id else ""
    orphan_marker = " [red](orphan)[/red]" if is_orphan(meta) else ""
    desc = f" [dim]— {meta.description}[/dim]" if meta.description else ""
    created = _relative_time(meta.created)
    updated = _relative_time(meta.updated)
    timestamps = f" [dim]created {created}, updated {updated}[/dim]"
    label = f"{status_icon} [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]{desc}{orphan_marker}{active_marker}{timestamps}"

    children = get_children(meta.id)
    if children:
        branch = tree.add(label)
        for child in children:
            _build_tree_node(branch, child.id, active_id)
    else:
        tree.add(label)


def render_tree(root_id: str | None = None):
    console = Console()
    active = get_active()
    active_id = active.id if active else None

    if root_id:
        meta = _load_meta(root_id)
        tree = Tree("")
        _build_tree_node(tree, meta.id, active_id)
        console.print(tree)
    else:
        roots = list_roots()
        if not roots:
            console.print("[dim]No quests found.[/dim]")
            return
        for root in roots:
            tree = Tree("")
            _build_tree_node(tree, root.id, active_id)
            console.print(tree)


def render_status(meta: QuestMeta):
    from rich.panel import Panel
    from rich.table import Table as RichTable
    from rich.columns import Columns
    from rich.text import Text

    console = Console()
    active = get_active()
    is_active = active and active.id == meta.id
    children = get_children(meta.id)

    # Key-value grid
    grid = RichTable.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()

    status_str = "[green]open[/green]" if meta.status == "open" else f"[dim]{meta.status}[/dim]"
    grid.add_row("Status", status_str)
    grid.add_row("ID", f"[dim]{meta.id}[/dim]")

    if meta.parent:
        try:
            parent = _load_meta(meta.parent)
            grid.add_row("Parent", f"{parent.name} [dim]({parent.id})[/dim]")
        except FileNotFoundError:
            grid.add_row("Parent", f"[red]{meta.parent} (missing)[/red]")
    else:
        grid.add_row("Parent", "[dim]—[/dim]")

    if meta.root and meta.root != meta.id:
        try:
            root = _load_meta(meta.root)
            grid.add_row("Root", f"{root.name} [dim]({root.id})[/dim]")
        except FileNotFoundError:
            grid.add_row("Root", f"[red]{meta.root} (missing)[/red]")

    grid.add_row("Sessions", str(meta.session_count))
    cost = quest_total_cost(meta.id)
    if cost is not None:
        grid.add_row("Cost", f"[green]${cost:.4f}[/green]")
    grid.add_row("Children", str(len(children)))
    grid.add_row("Created", f"[dim]{meta.created[:19]}[/dim]")
    grid.add_row("Updated", f"[dim]{meta.updated[:19]}[/dim]")
    grid.add_row("Directory", f"[dim]{_quest_dir(meta.id)}[/dim]")
    if meta.created_dir:
        grid.add_row("Created in", f"[dim]{meta.created_dir}[/dim]")

    if meta.description:
        grid.add_row("", "")
        grid.add_row("Description", meta.description)

    # Child tree
    if children:
        grid.add_row("", "")
        child_tree = Tree("[bold]Children[/bold]")
        active_id = active.id if active else None
        for child in children:
            _build_tree_node(child_tree, child.id, active_id)
        grid.add_row("", child_tree)

    # Panel
    title = f"[bold]{meta.name}[/bold]"
    if is_active:
        title += " [yellow]● active[/yellow]"
    panel = Panel(grid, title=title, border_style="blue", expand=False)
    console.print(panel)
