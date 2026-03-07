# claude-quest

> Making claude useful for long timehorizon evolutionary problem solving

## Why

Every token in a language model's context shapes how it searches for solutions. Context isn't decoration; it is the computational substrate. The way information is organized around a task determines how effectively the model works for you.

As projects evolve, the humans working on them develop a deeper and better understanding of the problem space. The agents that these humans work with, the instances of "Claude" they manage, need to evolve with that newer understanding. When the human learns something, the agent should know it too. When the human's mental model shifts, the agent's context should shift with it. 

### Framing

Think of a game where you're on a quest. There's an NPC companion traveling with you. As you make decisions, explore new areas, and learn about the world, the NPC adapts: it nudges you based on what you've discovered together, recalls past encounters, warns you about things you've already tried. The NPC's usefulness comes from the fact that it evolves with you through the quest.

The same philosophy applies here. Every time a human and Claude work together on something that spans more than a single session, they are going on a quest. Claude is the companion NPC. It evolves alongside the human: accumulating what they've learned together, forgetting what's no longer relevant, carrying forward what matters for where things are heading next.

But unlike a game NPC that updates automatically, the evolution here is explicit. The human holds the long-horizon policy. Claude operates within a single session. The human operates across the arc of the quest, across dozens or hundreds of sessions over weeks and months. The person who knows where the quest is going decides what their companion needs to remember, what to prune, and how the shared knowledge should be restructured as understanding deepens.

For the full reasoning, see [docs/philosophy.md](docs/philosophy.md).

## How

`claude-quest` is a CLI that wraps `claude`. Because it wraps the process, it can do a few useful things: inject the quest's accumulated state into Claude's system prompt, set environment variables so Claude can call quest commands (committing state, attaching files, logging milestones) without needing to know internal IDs, and clean up staged snapshots when the session ends.

When you start a session, `state.md` is injected as background context. During the session, the human decides when to crystallize knowledge by telling Claude to commit. State gets updated, a log entry records what happened and why, and next session Claude starts with the evolved context. The quest remembers so you don't have to re-explain.

Quests branch into side quests for focused exploration and merge back when findings are ready. Every commit is version-controlled. The tool is deliberately lean: a state file, a log, a tree, explicit commits, and system prompt injection.

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

# Resume the active quest (fresh session)
claude-quest go

# Resume a specific quest by name
claude-quest go build-rl-agent

# Continue the last conversation (claude session) where you left off
claude-quest go build-rl-agent -r

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
| `claude-quest new <name>` | Create a root quest, set active, launch Claude |
| `claude-quest go [name\|id]` | Resume a quest and launch new claude session |
| `claude-quest go [name\|id] -r` | Resume quest and continue from last claude session |
| `claude-quest side [-n name] [--from quest]` | Branch a side quest (child) from a quest, launch Claude |
| `claude-quest side [-n name] [--from quest] --fork` | Fork as independent root — copies state but no parent link |

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

When a quest session is running, Claude has the quest's accumulated state as background context but does not act on it unless you ask. You drive all mutations. The typical flow looks like:

1. You and Claude work on the task at hand (writing code, researching, debugging, etc.)
2. When something worth preserving emerges, you tell Claude to commit it: *"commit state"* or *"log that we decided to use approach X"*
3. Claude runs the `claude-quest commit` command with the updated content
4. You continue working. Repeat as needed.

Claude never auto-commits, auto-logs, or auto-attaches. You decide when knowledge crystallizes.

The available in-session commands:

- **Commit state**: `claude-quest commit --state "..." --log "..."`
- **Attach files**: `claude-quest attach <file>`
- **Dump another quest**: `claude-quest dump <name|id>` — copies into CWD for reading, clean up when done
- **Merge side quest**: Dump it, synthesize state, commit, then `claude-quest merge <child-id>`
- **Rename/describe**: `claude-quest rename`, `claude-quest describe --set`

Environment variables (`CLAUDE_QUEST_ID`, `CLAUDE_QUEST_NAME`, etc.) are set automatically so commands like `claude-quest commit` and `claude-quest attach` know which quest to target without arguments.

### State and logs

A quest has two files that capture its evolution: `state.md` and `log.md`. They serve different purposes.

**state.md** is the accumulated knowledge of the quest. It is injected into every session's system prompt. It should be concise, current, and actively maintained. As the quest evolves, state gets restructured, compressed, and pruned. Old information that no longer matters gets removed. State represents what the quest *is right now*.

**log.md** is the append-only record of the quest's journey. It book-keeps the evolution of the quest itself: milestones reached, decisions made, approaches tried and abandoned, things learned. Unlike state, log entries are never edited or removed. The log represents *how the quest got here*.

```bash
# Commit both state and a log entry in one call
claude-quest commit --state "$(cat .quest-myproject/state.md)" --log "Finished migrating to new API. Old endpoints removed."

# Just log a milestone without changing state
claude-quest commit --log "Explored approach B. Dead end — failed to repro bug."
```

The log is especially valuable when returning to a quest after a long break or when merging side quests. It answers "what happened and why" without cluttering the state that Claude reads every session.

### Branching and forking

**Side quest** — a child branch that stays in the parent's tree. Use for exploration that might merge back.

**Fork** — copies state but becomes an independent root. Use when a quest outgrows its parent or takes a new direction.

Both copy `state.md`, `log.md`, and `files/` from the source quest.

```bash
# Side quest: branches under project-x
claude-quest side -n "experiment-a"

# Side quest from a specific quest (not just active quest in cwd)
claude-quest side -n "experiment-b" --from project-x

# Fork: independent root with project-x's state
claude-quest side -n "project-x-v2" --from project-x --fork

claude-quest tree

└── ● project-x (a1b2c3)
    ├── ● experiment-a (d4e5f6)
    └── ● experiment-b (g7h8i9)
● project-x-v2 (j0k1l2)              # independent root
```

To merge a side quest back: dump it (`claude-quest dump <id>`), synthesize its findings into the parent's state, commit, then mark it merged (`claude-quest merge <id>`).

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

`state.md` is injected into every session's system prompt. To keep it within the model's context window, its size is budgeted (default 80KB ~20K tokens). The system prompt tells Claude the current size and limit, so it nudges users to summarize or restructure when state grows large. But there is no explicit enforcements since future models would ideally accomodate for size growth. The 80KB size is a recommendation not a rule. 

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
