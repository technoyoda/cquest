"""Quest tree and state file management."""

from __future__ import annotations

import json
import shutil
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


def create_quest(name: str, parent_id: str | None = None) -> QuestMeta:
    _ensure_root()
    qid = _short_id()
    qdir = _quest_dir(qid)
    qdir.mkdir(parents=True)

    if parent_id:
        # Fork: inherit root from parent
        parent = _load_meta(parent_id)
        root_id = parent.root or parent.id
        cwd = str(Path.cwd())
        meta = QuestMeta(id=qid, name=name, root=root_id, parent=parent_id, created_dir=cwd)
        _save_meta(meta)

        # Copy parent's state, log, and files into the new quest
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

        # No need to update parent — children are discovered by scanning
    else:
        # Root quest: root is self
        cwd = str(Path.cwd())
        meta = QuestMeta(id=qid, name=name, root=qid, created_dir=cwd)
        _save_meta(meta)
        _files_dir(qid).mkdir()
        _state_path(qid).write_text(f"# {name}\n\n_No state recorded yet._\n")
        _log_path(qid).write_text(f"# Session Log: {name}\n\n")

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
    console = Console()
    active = get_active()
    is_active = active and active.id == meta.id
    children = get_children(meta.id)

    console.print(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
    if is_active:
        console.print("[yellow]  Active quest[/yellow]")
    console.print(f"  Status: {meta.status}")
    if meta.description:
        console.print(f"  Description: {meta.description}")
    if meta.parent:
        try:
            parent = _load_meta(meta.parent)
            console.print(f"  Parent: {parent.name} ({parent.id})")
        except FileNotFoundError:
            console.print(f"  Parent: {meta.parent} (missing)")
    if meta.root and meta.root != meta.id:
        try:
            root = _load_meta(meta.root)
            console.print(f"  Root: {root.name} ({root.id})")
        except FileNotFoundError:
            console.print(f"  Root: {meta.root} (missing)")
    console.print(f"  Children: {len(children)}")
    console.print(f"  Sessions: {meta.session_count}")
    if meta.created_dir:
        console.print(f"  Created in: {meta.created_dir}")
    console.print(f"  Created: {meta.created}")
    console.print(f"  Updated: {meta.updated}")
    console.print(f"  Dir: {_quest_dir(meta.id)}")
