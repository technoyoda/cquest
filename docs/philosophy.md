# Why `cquest` Exist

cquest operates on assumptions about how language models work: pre-training embedding a distribution over language, reinforcement learning embedding behaviors upon certain tokens present in context, and inference as policy unrolling over tokens in context. It takes those assumptions and extrapolates: if this is how these systems are built, what interaction model emerges when you want to work with them over long time horizons? The project operates at a meta layer: it is not concerned with what the agent does on any particular task, but with shaping the context that determines how the agent approaches every task.

This project exists now because models from Anthropic, OpenAI, and others have crossed a capability threshold where natural language functions as a reliablish programming interface (for short horizon situations). The system prompt in cquest is written in English. The commit instructions are English. The state that shapes the agent's behavior is a markdown file. None of this works if the model cannot reliably execute behavioral specifications written in natural language. Five years ago, it could not. Today, it can. That threshold is what makes a project like this possible.

The premise is simple. The agent's entire reality is its context window. Everything upon which the model makes decisions, takes actions, and navigates the world exists as tokens in that window. What is not in context does not exist for the agent. If that is how these systems fundamentally work, then the design question becomes: how do you shape what enters that window, across hundreds of sessions, over months and years of collaboration? The sections below are the answer this project arrives at.

## How models work

Language models operate on two foundations: pre-training embeds a conditional distribution over language, and reinforcement learning embeds behavioral patterns (instruction following, tool use, long-form trajectory unrolling). Every token that enters the context window reshapes the model's entire search space for the next token. Context isn't decoration. It is the computational substrate that determines how the model searches for solutions.

There is a second dimension to this. No model, however large, can capture the shape of all possible data in the universe. Pre-training covers a distribution over publicly available human knowledge, but it cannot contain a private company's internal architecture, an individual's unpublished research, the state of a codebase that was modified ten minutes ago, or any of the countless details that exist only in specific contexts at specific times. The model's weights carry general capability. The specifics of any real task live outside the weights.

This means the problem of what the model needs to know at runtime will always exist. It is structural, not a limitation that scales away. As long as these systems operate by unrolling a policy over tokens in context, there will be a gap between what the model knows from training and what it needs to know to be effective in a particular situation. Someone has to bridge that gap by putting the right information into the context window.

This leads to two conclusions. First, the quality and structure of context directly controls the quality of what the model produces. Your file system, your accumulated knowledge, the way you organize information around a task, all of it ends up shaping how quickly and effectively the model finds answers. Second, if you want a model to operate well across long time horizons (weeks, months, years of work on the same project) you need a mechanism to curate and evolve that context deliberately.

cquest exists because of this premise. If it is correct, then this tool is as relevant fifty years from now as it is today. The specific model and interface are incidental. The problem of shaping context for long-horizon agent collaboration is fundamental.


## The quest metaphor

The word "quest" was chosen over "project", "context", "thread", or any technical term because the concept is broader than any of those.

A quest is a journey that transforms both the person on it and the companion traveling with them. When you go on a quest, the NPC following you should evolve as you evolve. They should accumulate the knowledge you've gained together, forget what's no longer relevant, and carry forward what matters for where the quest is heading next.

This maps directly to working with Claude on long-horizon tasks. A six-month project accumulates enormous context: decisions made, dead ends explored, architecture evolved, understanding deepened. That context normally lives only in your head. Every new Claude session starts blank. The quest is the structure that lets Claude's understanding evolve alongside yours.

Quests can involve exploration (open-ended research, trying approaches, gathering information). They can involve exploitation (applying what you've learned, building on stable foundations, executing efficiently). Side quests let you branch into focused investigations and return to the main quest with new knowledge. The metaphor holds across all of these because it describes the shape of the work, not its content.

## Why explicit control

cquest has a deliberate policy: Claude never auto-commits state changes. No auto-checkpoints, no automatic summarization, no implicit state mutations. Every evolution of the quest state is a human decision.

This isn't about distrust or caution. It's about who holds the long-horizon policy.

The human knows where the quest is going. They know which information is load-bearing and which is transient. They know that what mattered during the building phase of a project may be irrelevant six months later during maintenance. They know when an exploration has yielded insight worth crystallizing versus noise worth discarding.

Claude operates within a session. The human operates across the arc of the quest. Letting Claude auto-commit would invert this: the agent with the shorter horizon would be deciding what the agent with the longer horizon needs to remember. The person who has been on the quest longest should be the one deciding how their companion evolves with each new piece of information.

This extends to pruning. As you evolve and the kind of information you carry in your head changes, you want the NPC following you to change in the same surgical way. State should be actively maintained (grown, restructured, compressed, and sometimes discarded) by the person who understands the trajectory of the quest.

## [Form and essence](https://en.wikipedia.org/wiki/Theory_of_forms)

Strip away the specific agent, the specific CLI, the specific flags, and ask what actually needs to exist for long-horizon agent collaboration. The answer is small: a way to accumulate knowledge across sessions, a way for the human to curate it, and a way to inject it back. The quest can branch, merge, and evolve. The agent's effectiveness compounds because its context improves. That is the essence.

Everything else is form. Claude Code, the `--append-system-prompt` flag, the `.jsonl` transcripts, the CLI wrapping a subprocess: these are implementation details of the current form factor. They could be replaced tomorrow and the essence would not change.

The leanness is a deliberate design choice. Consider the agent's environment: the codebases it reads, the databases it queries, the APIs it calls, the file systems it navigates. All of these evolve on their own. They are separate from the agent and the human working with it. The information that the agent needs to operate in these environments (how to call an API, what a schema looks like, how to run a build) is completely isolated from the knowledge the agent accumulates while working alongside the human (what we've tried, what we've decided, where the project is heading).

cquest is concerned only with the second kind. It exists purely to help the agent evolve alongside the human, not to manage the environments the agent interacts with. That separation is what keeps it lean. A state file, a tree structure, explicit commit semantics, and a way to inject accumulated context into each session. That's it. cquest is a simple implementation of this essence in software form.

The entire project is roughly 1,200 lines of code. This is intentional. Users configure Claude Code in arbitrarily many ways: custom MCP servers, specific tool permissions, esoteric git workflows, project-specific CLAUDE.md files, hooks, skills, environment variables, and whatever else emerges. The space of how users work and what they bring to their setup is vast and varied. cquest never intrudes into any of it. The only thing it does at runtime is inject a shim so that if the user wants to record and carry forward anything important for long-horizon collaboration, they can. It does not opinion on how you structure your codebase, how you configure Claude, what tools you allow, or what style you work in. Everything about the user's setup stays exactly as it is. cquest sits alongside it, not on top of it.

This means users can use quests for whatever they want. Curate detailed state that shapes every session. Or keep state minimal and just use the log as a record of what happened with the agent over time. Attach elaborate artifacts or attach nothing. The abstraction enables long-horizon collaboration without prescribing what that collaboration looks like. The user paints the reality the agent operates in. cquest just makes sure that reality persists.

## Why not more machinery

cquest does not use MCP servers, hooks, custom tool definitions, or any other mechanism that would skin or modify how the agent operates. This is not a limitation. It is the central design choice.

The reasoning starts from the computational premise. Models do tool calls. One of those tool calls is Bash. If the model can reliably call a bash command, then quest operations are just bash commands: `cquest commit`, `cquest attach`, `cquest dump`. The entropy in these calls is not about tool selection (the model is not choosing between competing tool types). It is about the information the user wants to persist: the state content, the log entry, the file to attach. Environment variables eliminate even the targeting entropy. The model does not need to figure out which quest it is operating on. The runtime already knows.

This means cquest relies on exactly one capability that models already have and will only get better at: calling a shell command with the right arguments based on context. No new tool schemas. No custom MCP protocol. No hook registrations. The project bets on the same premise that makes models useful in the first place: they can follow instructions and make decisions based on tokens in context. As models improve, the system prompt that shapes quest behavior becomes more effective automatically. The project compounds with model quality without adding machinery.

Every additional abstraction layer would shrink the user's solution space. An MCP server for quests would be one more server in the user's MCP configuration. Quest-level hooks would compete with the user's own hooks. Custom tool definitions would add to the tool namespace the model has to search over. Users bring their own environments, their own MCP servers, their own hooks, their own git workflows, their own CLAUDE.md files, their own methodologies and tastes. cquest refuses to add to that surface area. It sits in the gap between what models can already do (call bash, follow system prompt instructions) and what users need for long-horizon work (persistent, curated context). Nothing more.

The project changes three things at runtime:

1. **System prompt injection.** The curated state enters the context window so the shape of accumulated knowledge keeps shaping the agent's behavior.
2. **Environment variables.** Set before launch so that quest commands called by the agent target the right quest without the agent needing to know internal IDs.
3. **Workspace staging.** The quest's files are present in the agent's working directory so the agent can read and reference them as needed.

Outside of these, cquest makes no modifications to how Claude operates.

A consequence of this: you do not need to launch Claude through `cquest go` to use quests. The quest CLI is a standalone set of bash commands that read from and write to `~/.quests/`. A user can launch Claude (or any other agent) independently, give it the project's README or a condensed command reference, and the agent can call `cquest commit`, `cquest status`, `cquest dump`, and everything else directly from its shell. The commands work the same way regardless of how the agent was started. `cquest go` is a convenience that handles system prompt injection, environment variables, and workspace staging in one step. But quests are usable without it because they are just bash commands operating on a directory. This is the payoff of not building machinery: the tool is not locked to any particular launch path, agent runtime, or integration protocol.

Any addition to the project should be a convenience for user visibility (cost tracking, session history, version browsing), not a new abstraction layer. The core quest concept stays orthogonal to whatever model providers offer. If there is a theoretical breakthrough in how models work that fundamentally changes how context should be managed, the project adapts. Until then, the foundation stays minimal because the premises it is built on have not changed.

## The exploration-to-exploitation pipeline

When building agents that need to run autonomously, you first do a lot of exploration. You try prompt strategies, test environment configurations, iterate on reward signals, stabilize tool use patterns. Only after extensive iteration do you arrive at prompts and environments stable enough to let things run free.

Getting to that point requires an iterative medium: a way to accumulate learnings across dozens of sessions, branch into experiments, merge back what works, and gradually converge. Quests are that medium. They sit in the gap between "I have a vague idea" and "I have a production system", providing structure for the long exploratory phase where most of the real work happens.

The endgame is that through enough exploration, the human curates state and attached artifacts to the point where the agent can manage tasks with less supervision. Short-horizon tasks that the agent handles autonomously. Longer-horizon tasks that the agent can take further before needing human input. The quest is the vehicle through which the human explores, learns, figures things out, and then distills that into context that makes the agent increasingly effective. Exploration produces the knowledge. Exploitation is what happens when that knowledge is good enough.
