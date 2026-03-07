# Landscape: Long-Horizon Context Tools for AI Coding Agents

*[fully ai generated]*

## Closest to claude-quest (long-horizon context persistence)

**[cc-sessions](https://github.com/GWUDCAP/cc-sessions)** — The most similar in spirit. Tasks are markdown files with frontmatter that persist through session restarts. Every task gets its own git branch. Has a "Context Gathering Agent" that builds context manifests so Claude doesn't re-learn things. Opinionated: enforces discussion-before-implementation via hooks. Key difference from claude-quest: it's task-centric (one branch per task), not quest-centric (evolving knowledge container). No branching/merging of context itself.

**[Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)** — Maintains state via "ledgers and handoffs." Agent orchestration with isolated context windows. MCP-based. More about preventing context pollution in multi-agent setups than about long-horizon human-directed evolution.

**[Context Mode](https://github.com/mksglu/context-mode)** — Captures every session event into a per-project SQLite database. Auto-rebuilds working state on resume or compaction. Interesting approach but automatic, not human-curated. The opposite philosophy from claude-quest on who decides what to remember.

## Context/memory layers (not Claude-specific)

**[OneContext](https://github.com/AlexMikhalev/onecontext)** — Agent self-managed context layer. Unified context across agents and team members. More about shared state than personal long-horizon quests.

**[CodeFire](https://github.com/websitebutlers/codefire-app)** — Desktop app that auto-discovers projects, tracks tasks/sessions, exposes project data back to AI via MCP. Persistent memory across sessions. Auto-tracking rather than explicit commits.

**[Mem0](https://mem0.ai/blog/memory-in-agents-what-why-and-how)** — General-purpose agent memory. Three-stage pipeline: segment, summarize, retrieve. Research shows 26% higher response accuracy vs stateless. But it's a memory retrieval system, not a knowledge evolution tool.

## Session management (lighter weight)

**[ccmanager](https://github.com/kbwo/ccmanager)** — Copies session data when creating git worktrees. Maintains context across branches. More operational than strategic.

**[claude-sessions](https://github.com/iannuttall/claude-sessions)** — Custom slash commands for session tracking and documentation. Lightweight logging.

**[Context Manager](https://contextmanager.cc/)** — macOS menubar app for monitoring/organizing Claude sessions with git-like workflows.

## Claude's own built-in features

- **Tasks** (native, Jan 2025) — Persist in `~/.claude/tasks/`, survive session crashes, support dependencies. But scoped to task execution, not longitudinal knowledge.
- **Session memory** (v2.1.30+) — "Recalled/Wrote memories" across sessions. Automatic, not curated.
- **Compaction API** — Server-side context summarization for long conversations. Addresses context window limits, not knowledge persistence.

## Where claude-quest is different

None of these tools have the combination of:
1. **Human-curated state evolution** (explicit commit, never auto)
2. **Branching/merging of knowledge itself** (side quests, forks, merge-back)
3. **The quest as a first-class longitudinal object** (not a task, not a session, not a memory store)
4. **Version-controlled state history** (git inside the quest, rollback, diff)
5. **State size budgeting** (deliberate context window management)

The closest philosophical neighbor is cc-sessions, but it's task-oriented (finite, completable) rather than quest-oriented (evolving, open-ended). Most other tools lean automatic where claude-quest leans explicit.

## Sources

- [cc-sessions](https://github.com/GWUDCAP/cc-sessions)
- [Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)
- [Context Mode](https://github.com/mksglu/context-mode)
- [OneContext](https://github.com/AlexMikhalev/onecontext)
- [CodeFire](https://github.com/websitebutlers/codefire-app)
- [Mem0](https://mem0.ai/blog/memory-in-agents-what-why-and-how)
- [ccmanager](https://github.com/kbwo/ccmanager)
- [claude-sessions](https://github.com/iannuttall/claude-sessions)
- [Context Manager](https://contextmanager.cc/)
- [Claude Code Task Management](https://claudefa.st/blog/guide/development/task-management)
- [Claude Session Memory](https://claudefa.st/blog/guide/mechanics/session-memory)
