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

# Resume with an additional system prompt
claude-quest go build-rl-agent -s "Focus on the reward function today"

# Fork a side quest from the active quest
claude-quest side
claude-quest side -n "reward-shaping"

# Combine system prompt and passthrough flags
claude-quest new "my-project" -s "You are an expert in Rust" -- --model sonnet
claude-quest side -n "experiment" -s "Try a different approach" -- --allowedTools "Bash,Read"
```

## Commands

### Session launchers

All session launchers support:
- `-s / --system-prompt "..."` — append additional text to the system prompt
- `--max-state-size <KB>` — max state.md size in KB (default: 80). Increase for models with larger context windows
- `-- <flags>` — pass through extra flags to the underlying `claude` command

| Command | Description |
|---|---|
| `claude-quest new <name> [-s sytem-prompt] [-- claude-flags]` | Create a root quest, set active, launch Claude |
| `claude-quest go [name\|id] [-s sytem-prompt] [-- claude-flags]` | Resume a quest (default: active), launch Claude |
| `claude-quest side [-n name] [-s sytem-prompt] [-- claude-flags]` | Fork from active quest, launch Claude |

*-s* will add to the SYSTEM PROMPT given to claude. The state saved on `commit` commands run by claude is also adding to the system prompt.

### Read operations

| Command | Description |
|---|---|
| `claude-quest status [name\|id]` | Show quest details (default: active) |
| `claude-quest tree [name\|id]` | Print quest tree with timestamps |
| `claude-quest list` | List all root quests |
| `claude-quest log [name\|id]` | Show session log |
| `claude-quest describe [name\|id]` | Show quest description |
| `claude-quest history [name\|id] [-n 20]` | Show version history |

### Write operations

| Command | Description |
|---|---|
| `claude-quest commit --state "..."` | Persist state.md to global store |
| `claude-quest commit --log "..."` | Append entry to log.md |
| `claude-quest merge <name\|id>` | Mark a quest as merged |
| `claude-quest dump <name\|id>` | Dump quest contents into CWD for reading |
| `claude-quest dump <name\|id> --state --log` | Dump only specific files |
| `claude-quest attach <file> [-q id]` | Copy file into quest's files/ directory |
| `claude-quest rename <name\|id> <new-name>` | Rename any quest |
| `claude-quest describe <name\|id> --set "..."` | Set quest description |
| `claude-quest delete <name\|id> [-f]` | Delete a quest and its children |
| `claude-quest restore <commit-hash> [-q id] [-f]` | Restore quest to a specific version (forward commit) |

### Export / Import

| Command | Description |
|---|---|
| `claude-quest export <name\|id>` | Export a single quest as `.tar.gz` |
| `claude-quest export <name\|id> --tree` | Export the full quest tree (all quests sharing the same root) |
| `claude-quest export --all` | Export all quests |
| `claude-quest import <archive.tar.gz>` | Import quests from archive |
| `claude-quest import <archive.tar.gz> -f` | Import and overwrite on ID collision |

```bash
# Export a tree to share with someone
claude-quest export my-project --tree -o my-project.tar.gz

# Import on another machine
claude-quest import my-project.tar.gz
```

Exported quests are self-contained. Lineage (`root`/`parent` references) survives export/import because the whole family travels together. Importing a single quest without its parent creates an orphan — fully usable, just labeled `(orphan)` in tree/list output.

## How It Works

### Session lifecycle

```
1. STAGE    .quest-<name>/ snapshot into CWD (read-only context for Claude)
2. LAUNCH   claude --append-system-prompt <quest context + optional extra prompt>
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

Claude's system prompt provides quest context as passive background information. All mutations are user-initiated:

- **Commit state**: `claude-quest commit --state "..." --log "..."`
- **Attach files**: `claude-quest attach <file>`
- **Dump another quest**: `claude-quest dump <name|id>` — copies into CWD for reading, clean up when done
- **Merge side quest**: Dump it, synthesize state, commit, then `claude-quest merge <child-id>`
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

Side quests fork the parent's `state.md`, `log.md`, and `files/` — they pick up where the parent left off. Merge a side quest back by reading its state from the snapshot and committing a synthesized version.

### Name uniqueness

Quest names must be unique. `new`, `side`, and `rename` will reject duplicate names.

### Version history

Every `claude-quest commit` automatically creates a git commit inside the quest directory (`~/.quests/quests/<id>/.git`). History only moves forward — no rewrites, no rebase.

```bash
# See version history
claude-quest history my-project

# Restore to a previous version (creates a new forward commit)
claude-quest restore abc1234 -q my-project-id
```

Side quests start with a fresh git history — they don't inherit the parent's commits.

### State size budget

`state.md` is injected into every session's system prompt. To keep it within the model's context window, its size is budgeted — default 80KB (~20K tokens). The system prompt tells Claude the current size and limit, so it nudges users to summarize or restructure when state grows large.

The `files/` knowledge base has **no size limit**. Detailed research, artifacts, and reference material should live in attached files, with `state.md` serving as a concise summary pointing to them.

```bash
# Default: 80KB state budget
claude-quest go my-project

# Larger budget for models with bigger context windows
claude-quest go my-project --max-state-size 150
```

## meta.json schema

```json
{
  "id": "abc123",
  "name": "build-rl-agent",
  "description": "Training a small RL-based code agent",
  "root": "abc123",
  "parent": null,
  "created_dir": "/home/user/projects",
  "status": "open",
  "created": "2026-03-02T10:00:00+00:00",
  "updated": "2026-03-02T14:30:00+00:00",
  "session_count": 5
}
```

Status values: `open`, `merged`.
