# Why Quests Exist

claude-quest operates on assumptions about how language models work: pre-training embedding a distribution over language, reinforcement learning embedding behaviors upon certain tokens present in context, and inference as policy unrolling over tokens in context. It takes those assumptions and extrapolates: if this is how these systems are built, what interaction model emerges when you want to work with them over long time horizons? The project operates at a meta layer: it is not concerned with what the agent does on any particular task, but with shaping the context that determines how the agent approaches every task.

This project exists now because models from Anthropic, OpenAI, and others have crossed a capability threshold where natural language functions as a reliable programming interface. The system prompt in claude-quest is written in English. The commit instructions are English. The state that shapes the agent's behavior is a markdown file. None of this works if the model cannot reliably execute behavioral specifications written in natural language. Five years ago, it could not. Today, it can. That threshold is what makes a project like this possible.

The premise is simple. The agent's entire reality is its context window. Everything upon which the model makes decisions, takes actions, and navigates the world exists as tokens in that window. What is not in context does not exist for the agent. If that is how these systems fundamentally work, then the design question becomes: how do you shape what enters that window, across hundreds of sessions, over months and years of collaboration? The sections below are the answer this project arrives at.

## The computational premise

Language models operate on two foundations: pre-training embeds a conditional distribution over language, and reinforcement learning embeds behavioral patterns (instruction following, tool use, long-form trajectory unrolling). Every token that enters the context window reshapes the model's entire search space for the next token. Context isn't decoration. It is the computational substrate that determines how the model searches for solutions.

There is a second dimension to this. No model, however large, can capture the shape of all possible data in the universe. Pre-training covers a distribution over publicly available human knowledge, but it cannot contain a private company's internal architecture, an individual's unpublished research, the state of a codebase that was modified ten minutes ago, or any of the countless details that exist only in specific contexts at specific times. The model's weights carry general capability. The specifics of any real task live outside the weights.

This means the problem of what the model needs to know at runtime will always exist. It is structural, not a limitation that scales away. As long as these systems operate by unrolling a policy over tokens in context, there will be a gap between what the model knows from training and what it needs to know to be effective in a particular situation. Someone has to bridge that gap by putting the right information into the context window.

This leads to two conclusions. First, the quality and structure of context directly controls the quality of what the model produces. Your file system, your accumulated knowledge, the way you organize information around a task, all of it ends up shaping how quickly and effectively the model finds answers. Second, if you want a model to operate well across long time horizons (weeks, months, years of work on the same project) you need a mechanism to curate and evolve that context deliberately.

claude-quest exists because of this premise. If it is correct, then this tool is as relevant fifty years from now as it is today. The specific model and interface are incidental. The problem of shaping context for long-horizon agent collaboration is fundamental.


## The quest metaphor

The word "quest" was chosen over "project", "context", "thread", or any technical term because the concept is broader than any of those.

A quest is a journey that transforms both the person on it and the companion traveling with them. When you go on a quest, the NPC following you should evolve as you evolve. They should accumulate the knowledge you've gained together, forget what's no longer relevant, and carry forward what matters for where the quest is heading next.

This maps directly to working with Claude on long-horizon tasks. A six-month project accumulates enormous context: decisions made, dead ends explored, architecture evolved, understanding deepened. That context normally lives only in your head. Every new Claude session starts blank. The quest is the structure that lets Claude's understanding evolve alongside yours.

Quests can involve exploration (open-ended research, trying approaches, gathering information). They can involve exploitation (applying what you've learned, building on stable foundations, executing efficiently). Side quests let you branch into focused investigations and return to the main quest with new knowledge. The metaphor holds across all of these because it describes the shape of the work, not its content.

## Why explicit control

claude-quest has a deliberate policy: Claude never auto-commits state changes. No auto-checkpoints, no automatic summarization, no implicit state mutations. Every evolution of the quest state is a human decision.

This isn't about distrust or caution. It's about who holds the long-horizon policy.

The human knows where the quest is going. They know which information is load-bearing and which is transient. They know that what mattered during the building phase of a project may be irrelevant six months later during maintenance. They know when an exploration has yielded insight worth crystallizing versus noise worth discarding.

Claude operates within a session. The human operates across the arc of the quest. Letting Claude auto-commit would invert this: the agent with the shorter horizon would be deciding what the agent with the longer horizon needs to remember. The person who has been on the quest longest should be the one deciding how their companion evolves with each new piece of information.

This extends to pruning. As you evolve and the kind of information you carry in your head changes, you want the NPC following you to change in the same surgical way. State should be actively maintained (grown, restructured, compressed, and sometimes discarded) by the person who understands the trajectory of the quest.

## Form and essence

Claude Code is the current medium. The `--append-system-prompt` flag, the `.jsonl` transcripts, the CLI wrapping a subprocess: these are implementation details. They are the form.

The essence is simpler: a human and an agent go on a quest together. The quest accumulates knowledge. The knowledge shapes how the agent operates. The human curates what the agent remembers. The quest can branch, merge, and evolve. The agent's effectiveness compounds over time because its context improves over time.

The leanness is a deliberate design choice. Consider the agent's environment: the codebases it reads, the databases it queries, the APIs it calls, the file systems it navigates. All of these evolve on their own. They are separate from the agent and the human working with it. The information that the agent needs to operate in these environments (how to call an API, what a schema looks like, how to run a build) is completely isolated from the knowledge the agent accumulates while working alongside the human (what we've tried, what we've decided, where the project is heading).

claude-quest is concerned only with the second kind. It exists purely to help the agent evolve alongside the human, not to manage the environments the agent interacts with. That separation is what keeps it lean. A state file, a tree structure, explicit commit semantics, and a way to inject accumulated context into each session. That's it. claude-quest is a simple implementation of this essence in software form.

## The exploration-to-exploitation pipeline

When building agents that need to run autonomously, you first do a lot of exploration. You try prompt strategies, test environment configurations, iterate on reward signals, stabilize tool use patterns. Only after extensive iteration do you arrive at prompts and environments stable enough to let things run free.

Getting to that point requires an iterative medium: a way to accumulate learnings across dozens of sessions, branch into experiments, merge back what works, and gradually converge. Quests are that medium. They sit in the gap between "I have a vague idea" and "I have a production system", providing structure for the long exploratory phase where most of the real work happens.

The endgame is that through enough exploration, the human curates state and attached artifacts to the point where the agent can manage tasks with less supervision. Short-horizon tasks that the agent handles autonomously. Longer-horizon tasks that the agent can take further before needing human input. The quest is the vehicle through which the human explores, learns, figures things out, and then distills that into context that makes the agent increasingly effective. Exploration produces the knowledge. Exploitation is what happens when that knowledge is good enough.
