# Landscape: Long-Horizon Context Tools for AI Coding Agents

*[fully ai generated]*

Every tool in this space is trying to solve the same problem: context gets lost between sessions, and that makes agents less effective over time. The approaches differ in what they believe about who should control context, what the right unit of work is, and how much structure to impose. This document maps those approaches.

## Automatic context capture

These tools assume the system can figure out what's relevant. The human works, the tool records, and context is rebuilt or retrieved automatically.

**[Context Mode](https://github.com/mksglu/context-mode)** — Captures every session event into a per-project SQLite database. Auto-rebuilds working state on resume or compaction. The assumption: if you record everything, you can reconstruct what the agent needs. The human does not decide what to remember. The system does.

**[CodeFire](https://github.com/websitebutlers/codefire-app)** — Desktop app that auto-discovers projects, tracks tasks and sessions, exposes project data back to AI via MCP. Persistent memory across sessions through automatic tracking. The assumption: project structure and session history are sufficient context if surfaced correctly.

**[Mem0](https://mem0.ai/blog/memory-in-agents-what-why-and-how)** — General-purpose agent memory layer. Three-stage pipeline: segment, summarize, retrieve. Research shows 26% higher response accuracy vs stateless. The assumption: memory is a retrieval problem. If you can store and retrieve the right fragments, the agent performs better. The human is not in the curation loop.

**[Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3)** — Maintains state via "ledgers and handoffs." Agent orchestration with isolated context windows. MCP-based. The assumption: context pollution across agents is the problem, and structured handoffs between isolated windows solve it.

## Task-centric workflows

These tools organize around completable units of work. A task has a beginning, an end, and a defined scope.

**[cc-sessions](https://github.com/GWUDCAP/cc-sessions)** — The closest neighbor in spirit. Tasks are markdown files with frontmatter that persist through session restarts. Every task gets its own git branch. Has a "Context Gathering Agent" that builds context manifests so Claude doesn't re-learn things. Opinionated: enforces discussion-before-implementation via hooks. The assumption: work decomposes into tasks, and each task needs its own persistent context. The unit is the task (finite, completable), not an evolving open-ended journey.

**[OneContext](https://github.com/AlexMikhalev/onecontext)** — Agent self-managed context layer. Unified context across agents and team members. The assumption: context should be shared and consistent across participants. More about coordination than long-horizon evolution.

## Session persistence

These tools take the session as the right unit and try to make it last longer or be more portable.

**[ccmanager](https://github.com/kbwo/ccmanager)** — Copies session data when creating git worktrees. Maintains context across branches. Operational: ensures the agent doesn't lose its place when you switch branches.

**[claude-sessions](https://github.com/iannuttall/claude-sessions)** — Custom slash commands for session tracking and documentation. Lightweight logging of what happened in each session.

**[Context Manager](https://contextmanager.cc/)** — macOS menubar app for monitoring and organizing Claude sessions with git-like workflows. The session is the object being managed.

## Claude Code's own mechanisms

- **Tasks** (native) — Persist in `~/.claude/tasks/`, survive session crashes, support dependencies. Scoped to task execution, not longitudinal knowledge.
- **Session memory** — "Recalled/Wrote memories" across sessions. Automatic, not curated. Claude decides what to store and surface.
- **Compaction** — Context summarization when the window fills up. Addresses context window limits. Claude decides what to keep.

For a deeper analysis of how these mechanisms interact with long-horizon work, see [why-quests-on-claude-code.md](why-quests-on-claude-code.md).

## Where cquest's taste differs

cquest approaches the problem from a different angle than most tools in this space. The difference is not in features but in starting assumptions.

Most tools start from a practical problem: sessions are too short, context gets lost, agents forget things. They build tooling to solve that problem directly, whether through automatic capture, structured task workflows, or session persistence.

cquest starts from [how models work](philosophy.md#how-models-work). If the agent's entire reality is its context window, and if the gap between what models know from training and what they need at runtime is structural and permanent, then the question is not "how do we make sessions last longer" but "how does the human shape what enters the context window across months and years of collaboration." The [interaction model](philosophy.md) follows from that premise.

This leads to specific design taste:

- **The human curates, not the system.** No automatic capture, no retrieval heuristics. The human [decides what persists](philosophy.md#why-explicit-control) because the human holds the long-horizon policy.
- **The unit is an open-ended journey, not a task.** Quests evolve, pivot, branch, and merge. They describe the [shape of the work](philosophy.md#the-quest-metaphor), not a completable item.
- **Knowledge itself branches and merges.** Side quests create isolated problem spaces. Merging synthesizes findings back. The knowledge tree is the object, not the session tree.
- **The implementation stays minimal.** No MCPs, no hooks, no custom tools. Just [bash commands and system prompt injection](philosophy.md#why-not-more-machinery). The tool bets on models getting better rather than adding machinery.

These are taste differences, not quality judgments. Automatic context capture is the right choice for many workflows. Task-centric organization is the right choice for well-scoped work. cquest's taste is for long-horizon, open-ended collaboration where the human needs to actively shape how the agent evolves. Different problem, different assumptions, different design.

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
