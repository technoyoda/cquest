# Why Quests on Top of Claude Code

## The raw form factor

Claude Code in its raw form is a clean system. The models it houses work like an RL policy unrolling as tokens enter the context. The session is the medium: it holds the current tokens being processed, the tokens that have been processed, and all the rough work done during the agent's execution. The user has their own environment (file system, tools, databases, APIs) and the agent interacts with that environment during the session to creates the observable universe for the agent and even influences it's future actions. 

This is theoretically sound. The policy searches over a solution space shaped by whatever tokens are in the context window. The session represents that faithfully. The user provides intent, the agent executes, and the context window holds everything that matters for the current trajectory.

## Where things get complicated

Claude Code adds layers on top of this raw form factor: memory, skills, and compaction. Each of these is useful in isolation, but they interact in ways that create problems for long-horizon work.

### Memory

Claude's [auto-memory system](https://code.claude.com/docs/en/memory) writes notes to `MEMORY.md` and topic files as it works. The first 200 lines of `MEMORY.md` are loaded at the start of every session. Claude decides what to store and what fits in those 200 lines. The user can inspect and edit these files, but the default flow is Claude curating its own persistent context.

The problem is not that memory is opaque. The files are right there. The problem is that **memory is not contextual to the user's intent**.

When Claude picks which memories to surface or act on, it is matching against its own representation of relevance based on the current tokens. The user has a different model of what matters right now. They know they are returning to a quest after a two-week break and need the agent to recall a specific architectural decision, not a general preference. They know the project has pivoted and half the stored memories are from an abandoned direction. They know which phase of the work they are in and what context that phase demands.

Claude cannot know any of this from retrieval alone. Two different phrasings of the same question might pull completely different memories. The user cannot predict what will be activated because the contextualization of memory (which entries matter, in what situation, for what purpose) is a function of the model's retrieval heuristics, not the user's intent.

For short-horizon, routine work this is fine. "User prefers tabs" does not need careful contextualization. But for long-horizon work where accumulated context directly shapes the quality of output, having the model decide what the user's agent remembers is a serious mismatch. Six months into a project, you have hundreds of memory entries from different phases. The probability that Claude retrieves context from an abandoned approach or an outdated decision grows. The user has evolved. The memory has not been curated to match.

The core issue: if something needs to persist across sessions, the [user should be the one deciding](philosophy.md#why-explicit-control) what and when. Not because Claude's memory is bad, but because the user is the only one who holds the full context of where the work is heading.

### Skills

Skills in Claude Code are [lazy-loaded context](https://code.claude.com/docs/en/skills). Claude reads each skill's name and description at session start, then loads the full body when it decides a skill is relevant. Skills can be [user-invocable](https://code.claude.com/docs/en/skills) (you type `/skill-name`) or auto-invocable (Claude decides to fire them based on context). They can run in the current context window or fork into an [isolated sub-agent session](https://code.claude.com/docs/en/skills).

The same contextualization problem from memory appears here: for auto-invocable skills, Claude decides what is relevant based on its own assessment. But there are additional structural issues:

1. **Composability is hard.** Projects are evolutionary, fluid things. What capabilities you need changes as the project changes. Figuring out which skills to compose together, for which task, in which configuration, at which point in the project's lifecycle is a hard problem. Static skill definitions don't match the pace at which the problem space evolves.

2. **Skills are often specific to a moment.** You don't want Claude to have all skills at all times in all places. You want skills to be specific to the project and task at hand. The set of relevant skills shifts as the work shifts. A skill that was essential during the prototyping phase may be irrelevant or even counterproductive during the optimization phase.

3. **Skills can be created at runtime.** A skill is fundamentally pre-specified context plus execution. The agent can achieve the same thing during a session by pulling files, saving artifacts, running sub-processes. If a separate sub-agent execution is needed, that can be figured out in the moment. The user and agent can build capabilities as they go, as part of the work, rather than pre-defining them as static abstractions. Capabilities acquired during a [quest](philosophy.md#the-quest-metaphor) are contextual to the quest and evolve with it.

### Compaction

[Compaction](https://platform.claude.com/docs/en/build-with-claude/compaction) triggers when context reaches approximately 95% of the 200K token window. Claude analyzes the conversation, identifies what it considers key information, and creates a summary that replaces older messages. Detailed instructions from early in the conversation [may be lost](https://code.claude.com/docs/en/how-claude-code-works).

Compaction is useful within a single session. It lets you keep working without hitting the context window limit. But it operates at the wrong level for long-horizon work:

1. **No meta-structure.** Compaction allows you to move forward with a single linear problem, but it doesn't give you the ability to create isolated problem spaces where you can further iterate. There is no way to say "take the learnings but not the mess." It keeps the session going; it does not help you structure the work across sessions.

2. **Forking carries cruft.** If you fork a session, you carry over everything from the parent, including all the compacted noise that the model decided to keep. It is like working on a git branch with 200 messy commits and never being able to squash-merge. You cannot cleanly separate signal from noise at the session boundary. A [side quest](philosophy.md#the-quest-metaphor) starts with curated state. A forked session starts with whatever compaction left behind.

3. **The model decides what to keep.** The compressed representation is Claude's interpretation of what matters, not the human's curation. For work that spans many sessions, the human is in a better position to know what is signal and what is noise. The human knows the project pivoted two weeks ago. Compaction does not.

The common thread across memory, skills, and compaction: in all three systems, **Claude controls the contextualization**. Claude decides what memories to surface, what skills to load, and what to preserve during compaction. The user has setup control (they can edit memory files, define skills, write CLAUDE.md) but not runtime control over what actually enters the context window at the moment it matters.

## What quests provide

Quests sit on top of Claude Code's raw form factor. They don't replace sessions, memory, skills, or compaction. They provide a coherent abstraction that addresses the gaps these systems leave for long-horizon work.

### Human-controlled state propagation

State flows from the human, not from Claude's internal machinery. The human decides what gets [committed](philosophy.md#why-explicit-control) to the quest, when to prune, and how to restructure accumulated knowledge. There are no retrieval heuristics, no compaction ambiguity. The path is simple: human decides, [`state.md`](../README.md#state-and-logs) gets updated, next session gets the updated state as tokens in the context.

### Memory through state and logs

The quest abstraction doesn't lack memory. It reframes what memory means.

[`state.md`](../README.md#state-and-logs) is active memory: the curated knowledge the agent needs right now. It gets restructured, compressed, and pruned as the quest evolves. [`log.md`](../README.md#state-and-logs) is temporal memory: the append-only record of what happened, in order, never edited. Together they cover what Claude's auto-memory tries to do, but with the user controlling both the content and the contextualization.

When you return to a quest after two weeks, you don't depend on retrieval heuristics to surface the right context. The state tells the agent where things stand. The log tells you how things got there. The agent's memory for any quest comes from what the user decided to curate into state and what the user decided to log. Not from what Claude auto-recorded.

### Skills as first-class quest citizens

Quests provide raw building blocks for skills to emerge naturally from the work rather than being pre-defined as static abstractions.

The mechanism is straightforward. As you work on a quest, useful capabilities emerge: a script that automates a workflow, a markdown file with instructions for a specific task, a compositional pattern that combines multiple tools. You tell Claude to attach these to the quest (`cquest attach`). You put a reference in `state.md` so Claude knows "when you need to do X, read this file and execute it." At runtime, Claude loads the file when the task demands it.

This is lazy-loading, but driven by human-curated state rather than Claude's auto-invocation heuristics. The system prompt acts as the routing layer: it tells the model which files hold which capabilities and when to use them. This composes naturally because the user is the one deciding which capabilities are relevant at this phase of the work.

There are skills in Claude Code that are useful across the spectrum, across different projects and settings. But many capabilities need to evolve as first-class citizens of the specific work being done. If the agent is going to be a first-class participant in a project, it needs first-class knowledge of how those capabilities behave, at least in their most condensed form, which is what state provides. Skills acquired during a [quest](philosophy.md#the-quest-metaphor) are contextual to the quest and evolve with it.

### Clean problem spaces

[Side quests](../README.md#branching-and-forking) start with curated state (the signal), not a compacted session history (signal plus whatever noise the model kept). When a side quest merges back, the human synthesizes findings into the parent's state. Only the learnings cross the boundary, not the conversation history.

### Orthogonal to compaction

Quests don't replace compaction. They work orthogonal to it.

You can keep compacting within a long linear session chain. Compaction handles that chain well. But because you are also committing to the quest as you go, the system prompt keeps getting better with each session: it has the synthesized, curated information that compaction might have missed or mangled. The state represents the best accumulated knowledge, independent of what happened inside any particular session's compaction cycle.

And at any point you can fork out from the quest (not from the compacted session) and get a clean agent with the best accumulated knowledge to work further on a new problem space. Compaction handles the linear chain. Quests handle the meta-structure. Since you can keep continuing in your linear chain and keep compacting, the system prompt keeps having newer synthesized information while also giving you the ability to fork out and create fresh setups from curated state. They compose rather than compete.

### Works with the raw form factor

Quests customize Claude through four knobs that the `claude` CLI exposes:

- **`--append-system-prompt`**: Injects the quest's accumulated state into the session. This is the core mechanism. The agent starts every session knowing what the quest knows because state.md is in its context window.
- **`--allowedTools`**: Pre-approves read-only quest commands (`cquest status`, `tree`, `log`, `dump`, etc.) so the agent can run them without triggering permission prompts. This removes friction for operations that don't mutate state.
- **Environment variables**: `CLAUDE_QUEST_ID`, `CLAUDE_QUEST_NAME`, `CLAUDE_QUEST_DIR`, and others are set before launch. The agent inherits these, so when it runs `cquest commit` or `cquest attach` inside a session, the CLI knows which quest to target without the agent needing to pass IDs explicitly.
- **`--session-id`**: Assigns a unique session ID for tracking. This is purely a convenience for the user, so that sessions have lineage and can be resumed. The quest concept does not need session IDs. It is an implementation detail of the current form factor for user happiness.

That is the full surface area. Quests don't fight against Claude's [session model](#the-raw-form-factor). They don't depend on memory or skills. They skin a few knobs on the `claude` CLI to add a thin layer of [human-curated persistence](philosophy.md#form-and-essence) on top of what is already a clean execution environment.


## The core claim

The core claim is not that quests are the best or only way. It is that when you think through what sessions, memory, skills, and compaction each provide and where they fall short for long-horizon work, quests feel like a good abstraction that fits on top. They give the human explicit control over what persists, clean boundaries for creating and merging problem spaces, and a simple mechanism (state injection) that works with Claude Code's raw form factor rather than against it.

## Design choices

Some things that look like limitations are deliberate.

### The human carries the cognitive load

There is no automatic context gathering. The user maintains state, writes logs, decides when to commit. This is the point, not a shortcoming.

The human is the captain navigating toward the North Star: they see what the global minima for the problem space looks like. The problem space is messy. It has multiple signals of information, tons of variance, unstructured inputs from environments the agent cannot observe (conversations with colleagues, shifting business requirements, intuitions from adjacent projects, maybe ci signals outside agent's control). The quality of instructions the human provides and the knowledge they curate into state is what guides the agent's behavior and determines how quickly the work converges.

If the agent auto-curated this, it would be optimizing for a local view of what matters. The human optimizes for the trajectory of the quest. The cognitive load is the cost of holding the [long-horizon policy](philosophy.md#why-explicit-control). Logs reduce the burden (you can review what happened before deciding what to commit), but the responsibility stays with the human because the human is the only one who knows where things are heading.

### Skills are informal by design

The skill mechanism in quests is deliberately unstructured. Skills are behavioral traits embedded in state and attached files, not separate runtime installations with schemas and invocation protocols.

This is a design choice rooted in the same [computational premise](philosophy.md#the-computational-premise) that drives everything else. If the agent operates over tokens in context, then skills are just raw bits of text that describe how to do things and when to do things when different situations emerge. A markdown file with instructions, a script, a reference in `state.md` that tells the model "when you encounter X, read this file." These are behavioral traits that live in the quest and evolve with it.

This allows for interplay with Claude Code's own skill system. At the end of the day, a [skill is a markdown file](https://code.claude.com/docs/en/skills) and possibly some additional program files. MCP servers can be present in the working directory. Configuration variables can be passed at runtime. cquest does not try to skin Claude to do different things. It changes a few knobs to allow large spaces of exploration with Claude. The intention is not to replace Claude; it is to complement Claude, or any other agent for that matter.

### Portability beyond Claude Code

cquest has been built on top of Claude Code because Claude Code is one form factor that offers the mechanisms needed: system prompt injection, environment variables, session management. But the quest abstraction does not depend on Claude-specific constructs.

If you extrapolate the idea, it can work on top of an arbitrary agent. The policy can change to whatever it wants. The environment needs to have the right information in it. There has to be the right information loaded in the context so that the agent can do what it needs to do. That is all quests provide: a way to curate that information and inject it. Any coding agent that accepts a system prompt or context injection (Codex, Aider, OpenCode, or whatever comes next) could be wrapped the same way. The quest is the abstraction. The agent is the runtime.

## Limitations

Some things are genuinely not solved yet or thought through yet.

- **Sub-agent execution is possible but not formalized.** The compositional pieces exist: `cquest side` can create isolated quest branches, `cquest dump` can surface another quest's state, and sub-agents in Claude Code [inherit the parent's system prompt](https://github.com/anthropics/claude-code/issues/6825), which means a sub-agent spawned during a quest session gets the quest context. A user can also run `cquest go <quest> -- -p "do X"` to launch an autonomous execution with full quest context (the `-p` flag is passed through to `claude`), effectively getting sub-agent behavior without formalizing it. In practice, the pieces are all there. Formalizing this (e.g., a flag that launches a side quest as a sub-agent with a specific system prompt, returning output to the parent) is possible but not built yet.

- **No quest-level hooks or automation.** Claude Code has [hooks](https://code.claude.com/docs/en/hooks) that fire at specific points in a session's lifecycle: `SessionStart`, `SessionEnd`, `Stop` (when Claude finishes responding), `PreToolUse`/`PostToolUse` (before and after tool calls), `PreCompact` (before context compaction), and others. Hooks are configured in settings JSON files and can run shell commands, HTTP endpoints, or LLM prompts. They receive JSON context on stdin and can return decisions (e.g., blocking a tool call). Since `cquest` commands are just shell commands that Claude runs via Bash, a user could wire hooks to quest operations today. For example, a `PostToolUse` hook matching `Bash` could detect `cquest commit` calls and run validation, or a `SessionEnd` hook could auto-log session metadata. Quests don't provide quest-level hook abstractions (e.g., "on commit, run this" or "on merge, auto-summarize"), but Claude Code's hook system is expressive enough that users can build these themselves. The explicit-over-automatic philosophy means this is low priority, but the building blocks exist.

- **Quests are not concurrency safe.** Quests assume sequential sessions. If two sessions for the same quest run simultaneously and both commit, the last write wins. There is no merge resolution for concurrent state mutations. This is by design: the quest model assumes a single human working with a single agent instance at a time. If you need concurrent exploration, use `cquest side` or `cquest side --fork` to create isolated branches. That is what side quests are for.

- **No native multiplayer.** Quests are designed as atomic units: one quest, one human, one agent. There is no built-in story for multiple people working on the same quest simultaneously. This is deliberate. Keeping quests atomic means they compose cleanly (side quests, forks, merges all work because there is a single owner making decisions). The multiplayer building blocks exist, though. Every quest has a git repository internally, and commit history only moves forward (no rewrites, no rebase), so the state is always a clean linear history. If a team needs shared quest state, they can sync the quest's git directory via a managed remote. The pattern: maintain a shared quest that gets synced via git pulls, and have each team member fork or side-quest from it for their own work. The coordination happens at the git layer, not the quest layer. This keeps the quest machinery simple during runtime while letting users build whatever collaboration patterns they need on top.
