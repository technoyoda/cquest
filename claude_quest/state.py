"""Quest tree and state file management."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.tree import Tree

QUESTS_ROOT = Path.home() / ".quests"
QUESTS_DIR = QUESTS_ROOT / "quests"
ACTIVE_FILE = QUESTS_ROOT / "active"


class QuestMeta(BaseModel):
    id: str
    name: str
    description: str = ""
    parent: Optional[str] = None
    children: list[str] = Field(default_factory=list)
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
    _files_dir(qid).mkdir()

    meta = QuestMeta(id=qid, name=name, parent=parent_id)
    _save_meta(meta)

    _state_path(qid).write_text(f"# {name}\n\n_No state recorded yet._\n")
    _log_path(qid).write_text(f"# Session Log: {name}\n\n")

    if parent_id:
        parent = _load_meta(parent_id)
        parent.children.append(qid)
        _save_meta(parent)

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


def set_active(quest_id: str):
    _ensure_root()
    ACTIVE_FILE.write_text(quest_id)


def get_active() -> QuestMeta | None:
    if not ACTIVE_FILE.exists():
        return None
    qid = ACTIVE_FILE.read_text().strip()
    if not qid:
        return None
    try:
        return _load_meta(qid)
    except FileNotFoundError:
        return None


def list_roots() -> list[QuestMeta]:
    results = []
    if not QUESTS_DIR.exists():
        return results
    for d in sorted(QUESTS_DIR.iterdir()):
        mp = d / "meta.json"
        if mp.exists():
            m = QuestMeta.model_validate_json(mp.read_text())
            if m.parent is None:
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


def get_children(quest_id: str) -> list[QuestMeta]:
    meta = _load_meta(quest_id)
    children = []
    for cid in meta.children:
        try:
            children.append(_load_meta(cid))
        except FileNotFoundError:
            pass
    return children


def add_child(parent_id: str, child_id: str):
    parent = _load_meta(parent_id)
    if child_id not in parent.children:
        parent.children.append(child_id)
        _save_meta(parent)


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


def _build_tree_node(tree: Tree, quest_id: str, active_id: str | None):
    try:
        meta = _load_meta(quest_id)
    except FileNotFoundError:
        tree.add(f"[red]? {quest_id} (missing)[/red]")
        return

    status_icon = "[green]●[/green]" if meta.status == "open" else "[dim]◌[/dim]"
    active_marker = " [bold yellow]← active[/bold yellow]" if meta.id == active_id else ""
    desc = f" [dim]— {meta.description}[/dim]" if meta.description else ""
    label = f"{status_icon} [bold]{meta.name}[/bold] [dim]({meta.id})[/dim]{desc}{active_marker}"

    if meta.children:
        branch = tree.add(label)
        for cid in meta.children:
            _build_tree_node(branch, cid, active_id)
    else:
        tree.add(label)


def render_tree(root_id: str | None = None):
    console = Console()
    active = get_active()
    active_id = active.id if active else None

    if root_id:
        meta = _load_meta(root_id)
        tree = Tree(f"[bold]{meta.name}[/bold] [dim]({meta.id})[/dim]")
        for cid in meta.children:
            _build_tree_node(tree, cid, active_id)
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
    console.print(f"  Children: {len(meta.children)}")
    console.print(f"  Sessions: {meta.session_count}")
    console.print(f"  Created: {meta.created}")
    console.print(f"  Updated: {meta.updated}")
    console.print(f"  Dir: {_quest_dir(meta.id)}")
