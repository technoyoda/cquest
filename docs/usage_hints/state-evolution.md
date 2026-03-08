# Viewing State Evolution

Every quest has git-versioned history. You can see how state changed over time without touching internals — just CLI commands.

## See the timeline

```bash
claude-quest history
```
```
Hash     Date                 Message
a3f7b2   2026-03-03T22:03    quest created
e1c4d8   2026-03-03T23:15    commit: state
9b2f01   2026-03-04T14:30    commit: state, log
```

## Read state at any point

```bash
claude-quest show a3f7b2          # state.md + log.md at that version
claude-quest show a3f7b2 -f state.md   # just state.md
```

## Compare two points

Dump state from two versions and diff them:

```bash
claude-quest show a3f7b2 -f state.md > /tmp/before.md
claude-quest show 9b2f01 -f state.md > /tmp/after.md
diff /tmp/before.md /tmp/after.md
```

That's it. History is date-ordered, so Claude can reason about which versions to compare — "show me how state changed since yesterday" is just picking the right hashes from `history` and dumping both.

## Roll back if needed

```bash
claude-quest restore a3f7b2   # creates a new forward commit with old state
```

History only moves forward — restore doesn't erase anything.
