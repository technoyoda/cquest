# Resuming Conversations

`claude-quest go -r` continues a previous Claude conversation instead of starting a fresh one.

## When to use it

A fresh `go` gives Claude the full quest state via the system prompt. This is usually enough — the quest state *is* the context.

Use `-r` when the conversation itself holds context that the quest state doesn't capture yet: you were mid-debug, Claude had just read specific files, or you're in the middle of an approach that hasn't been committed to state.

## How it works

```bash
# Fresh session (default) — new conversation, quest state injected
claude-quest go myquest

# Resume last conversation — picks up mid-thread, quest state also re-injected
claude-quest go myquest -r
```

When `-r` is used:
- **One previous session**: resumes it directly
- **Multiple sessions**: shows a picker

```
myquest — sessions:

 # | Session  | Date                  | Cost
 1 | f6c2cea4 | Mar 4, 00:40 (3d ago) | $157.32
 2 | a5a35728 | Mar 3, 19:04 (3d ago) | $133.01
 3 | 344c9698 | Mar 3, 15:35 (4d ago) | $1.22

Resume session [1]:
```

Most recent first. Press enter for the default (latest), or type a number.

- **No previous sessions**: falls back to a fresh session with a warning

## What happens under the hood

`-r` passes `--resume <session-id>` to the underlying `claude` command. The quest system prompt is still injected via `--append-system-prompt`, so Claude gets both the conversation history *and* the latest quest state. This matters because state may have changed since the last session (other side quests merged, manual edits, etc.).

No new session ID is generated for resumed sessions — it's the same conversation, same transcript file.

## When not to use it

If the quest state is well-maintained, a fresh `go` is almost always better. Claude gets clean context without stale conversation baggage. Reserve `-r` for the cases where you genuinely need mid-conversation continuity.
