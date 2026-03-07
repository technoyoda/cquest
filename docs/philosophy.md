# Why Quests Exist

## The computational premise

Language models operate on two foundations: pre-training embeds a conditional distribution over language, and reinforcement learning embeds behavioral patterns (instruction following, tool use, long-form trajectory unrolling). Every token that enters the context window reshapes the model's entire search space for the next token. Context isn't decoration. It is the computational substrate that determines how the model searches for solutions.

This means two things. First, the quality and structure of context directly controls the quality of what the model produces. Your file system, your accumulated knowledge, the way you organize information around a task, all of it ends up shaping how quickly and effectively the model finds answers. Second, if you want a model to operate well across long time horizons (weeks, months, years of work on the same project) you need a mechanism to curate and evolve that context deliberately.

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

This essence requires very little machinery. A state file, a tree structure, explicit commit semantics, and a way to inject accumulated context into each session. That's it. The leanness is intentional. Quests are the simplest software form that captures this capability.

## The exploration-to-exploitation pipeline

When building agents that need to run autonomously, you first do a lot of exploration. You try prompt strategies, test environment configurations, iterate on reward signals, stabilize tool use patterns. Only after extensive iteration do you arrive at prompts and environments stable enough to let things run free.

Getting to that point requires an iterative medium: a way to accumulate learnings across dozens of sessions, branch into experiments, merge back what works, and gradually converge. Quests are that medium. They sit in the gap between "I have a vague idea" and "I have a production system", providing structure for the long exploratory phase where most of the real work happens.
