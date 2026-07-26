# Model Delegation Strategy

Decision framework for delegating a sub-task to a cheaper/faster model instead of running everything through the main session.

## What this isn't

- Not automatic — Claude Code doesn't switch the main session's model based on perceived difficulty. This governs when *I* choose to delegate a sub-task.
- Not usage-limit-aware — no tool exposes session/weekly quota to the agent. Decisions are difficulty-based only.

## Mechanism

- Agent frontmatter `model:` pins a subagent to `haiku`/`sonnet`/`opus`/`inherit`.
- The `Agent` tool also takes a one-off `model` override, independent of any agent definition.
- `quick-task` (`.claude/agents/quick-task.md`) is the Haiku delegate-down agent. No static delegate-up agent exists — override `model: opus` on an `Agent` call instead.

## Delegate to `quick-task` when all of

- Fully specified — nothing left to design
- Success is verifiable at a glance
- Failure is cheap to retry

Examples: mechanical renames, run-and-report, pattern lookups, template boilerplate.

## Keep in the main session when any of

- Requires tradeoffs or design judgment
- Needs reasoning across many files at once
- User is actively iterating (round-trip latency isn't worth it)
- Action is destructive or hard to reverse

## Don't

- Automate the difficulty judgment (hook/script/heuristic) — no reliable signal, wrong calls fail silently
