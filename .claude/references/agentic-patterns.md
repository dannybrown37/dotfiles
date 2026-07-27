# Multi-Agent & Agentic Patterns

Decision framework for inline vs. delegated execution, tool-call batching, and chaining async work. Companion to `model-strategy.md` (that one is *which model*; this one is *inline vs. delegated*).

## Agent vs. fork vs. inline

**Inline (default)** — do the work directly in the main session. Most tasks: single-file edits, straightforward lookups, anything the user is actively iterating on.

**`fork`** — use when the sub-task:

- shares the current session's full context (no need to re-explain), and
- would otherwise dump a lot of raw tool output (large greps, multi-file reads, long command output) into the main session that isn't worth keeping.

Forks run in the background and free up the main session to keep chatting. Never fabricate or guess a fork's result before its completion notification arrives as a later turn.

**Fresh `Agent`** (no `subagent_type`, or a named one) — use when the sub-task:

- is independent research/verification that benefits from *not* inheriting the main session's framing (e.g. an independent second opinion), or
- matches a specialized agent already defined for the job (`quick-task` for mechanical/fully-specified work, `Explore` for locating code, `Plan` for implementation design).

Fresh agents start cold — the prompt must be self-contained (file paths, what's already ruled out, what "done" looks like).

**Don't spawn agents reflexively.** A task with multiple parts isn't automatically a reason to delegate — round-tripping through a subagent costs more than doing bounded work directly, unless the point is specifically to keep noisy output out of context or to run something in true parallel/background.

## Multi-step tool use

- Batch independent tool calls into a single message (e.g. `git status` + `git diff` + `git log` at the start of a review). Only go sequential when a later call's input depends on an earlier call's output.
- Use `TaskCreate`/`TaskUpdate` to track multi-step in-session work instead of ad hoc todo comments — mark items done as you go, not in a batch at the end.

## Chaining async work

- **Background shell**: `run_in_background: true` on `Bash` for long-running commands, then `Monitor` to watch/poll rather than sleep-looping. Use an until-loop inside `Monitor`, not repeated short `sleep`s.
- **Self-pacing recurring work** (`/loop` in dynamic mode): `ScheduleWakeup` to pick the next check-in interval. Match the delay to what's actually being waited on — short for something actively changing (a CI run), long (20-30 min) for idle ticks with no specific signal.
- **Background agents**: an `Agent` call without `fork`, or with `isolation: "worktree"`/`"remote"`, reports back via a task notification, not a return value in this turn. To continue one, `SendMessage` to its name/id — that resumes it with full context. A brand-new `Agent` call has no memory of a prior run.
- Across all of the above: the notification is the only source of truth for an async result. Don't predict, summarize, or narrate what a background/forked task "probably" found before it actually reports back.

## Deferred

- MCP integration examples — parked as its own queue item ("Learn about Claude Code MCP integration"); this repo has no MCP servers configured yet.
