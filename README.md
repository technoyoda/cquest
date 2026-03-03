# claude-quest

Persistent, branching context manager for Claude Code sessions. Maintains longitudinal project state across hundreds of sessions so context is never lost.

## Problem

Claude Code sessions are isolated. Over time, context is lost. You re-explain project structure, past decisions, and accumulated knowledge every session.

## Solution

`claude-quest` wraps `claude`, injecting accumulated quest state into each session via `--append-system-prompt`. State mutations happen explicitly through CLI commands that Claude calls during the session.

## Install

```bash
conda activate aft-poc
cd claude-quest
pip install -e .
```

## Quick Start

```bash
# Start a new quest — creates state, launches Claude
claude-quest new "build-rl-agent"

# Resume the active quest
claude-quest go

# Resume a specific quest by name
claude-quest go build-rl-agent

# Resume with extra flags passed through to claude
claude-quest go build-rl-agent -- --model sonnet

# Fork a side quest from the active quest
claude-quest side
claude-quest side -n "reward-shaping"
```

## Commands

### Session launchers

| Command | Description |
|---|---|
| `claude-quest new <name>` | Create a root quest, set active, launch Claude |
| `claude-quest go [name\|id] [-- claude-flags]` | Resume a quest (default: active), launch Claude |
| `claude-quest side [-n name]` | Fork from active quest, launch Claude |

### Read operations

| Command | Description |
|---|---|
| `claude-quest status [name\|id]` | Show quest details (default: active) |
| `claude-quest tree [name\|id]` | Print quest tree with Rich formatting |
| `claude-quest list` | List all root quests |
| `claude-quest log [name\|id]` | Show session log |
| `claude-quest describe [name\|id]` | Show quest description |

### Write operations

| Command | Description |
|---|---|
| `claude-quest commit --state "..."` | Persist state.md to global store |
| `claude-quest commit --log "..."` | Append entry to log.md |
| `claude-quest commit --merge <id>` | Mark a child quest as merged |
| `claude-quest attach <file> [-q id]` | Copy file into quest's files/ directory |
| `claude-quest rename <name\|id> <new-name>` | Rename any quest |
| `claude-quest describe <name\|id> --set "..."` | Set quest description |

## How It Works

### Session lifecycle

```
1. STAGE    .quest-<name>/ snapshot into CWD (read-only context for Claude)
2. LAUNCH   claude --append-system-prompt <quest context + instructions>
3. SESSION  Claude reads .quest-<name>/, mutates via `claude-quest` CLI commands
4. EXIT     .quest-<name>/ wiped from CWD
```

### Data flow

```
~/.quests/                          CWD/
  quests/<id>/                      .quest-<name>/        (read-only snapshot)
    meta.json     ──snapshot──→       meta.json
    state.md      ──snapshot──→       state.md
    log.md        ──snapshot──→       log.md
    files/        ──snapshot──→       files/
                                      children/<child-id>/
                                        meta.json
                                        state.md
                                        log.md

Claude reads from .quest-<name>/
Claude writes via CLI commands → directly to ~/.quests/
```

The snapshot is a read-only dump of quest state so Claude never leaves the user's working directory. All mutations go through `claude-quest` CLI commands which write directly to `~/.quests/`.

### Global store layout

```
~/.quests/
  active                    # Text file: current active quest ID
  quests/
    <quest-id>/
      meta.json             # Identity + relationships
      state.md              # Accumulated knowledge
      log.md                # Append-only session log
      files/                # Attached artifacts
```

### In-session operations

Claude's system prompt instructs it to use CLI commands for all mutations:

- **Commit state**: `claude-quest commit --state "..." --log "..."`
- **Attach files**: `claude-quest attach <file>`
- **Merge side quest**: `claude-quest commit --state "...merged..." --merge <child-id>`
- **Rename/describe**: `claude-quest rename`, `claude-quest describe --set`

Environment variables (`CLAUDE_QUEST_ID`, `CLAUDE_QUEST_NAME`, etc.) are set automatically so commands like `claude-quest commit` and `claude-quest attach` know which quest to target without arguments.

### Quest branching

```
claude-quest new "project-x"          # root quest
claude-quest side -n "experiment-a"   # side quest under project-x
claude-quest side -n "experiment-b"   # another side quest
claude-quest tree

└── ● project-x (a1b2c3)
    ├── ● experiment-a (d4e5f6)
    └── ● experiment-b (g7h8i9)
```

Side quests inherit nothing — they start fresh but are linked in the tree. Merge a side quest back by reading its state from the snapshot and committing a synthesized version.

## meta.json schema

```json
{
  "id": "abc123",
  "name": "build-rl-agent",
  "description": "Training a small RL-based code agent",
  "parent": null,
  "children": ["d4e5f6", "g7h8i9"],
  "status": "open",
  "created": "2026-03-02T10:00:00+00:00",
  "updated": "2026-03-02T14:30:00+00:00",
  "session_count": 5
}
```

Status values: `open`, `merged`.
