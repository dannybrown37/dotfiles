---
name: queue
description: "Invoke when the user wants to pull work from the .queue file — list queued items, pick one, implement it, and mark it complete."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# Queue

`.queue` (repo root, gitignored) holds work items the user has dropped in for later. Format:

```markdown
# Queue

## Item Title
Free-form description. Can be multi-line.

## Another Item
More details.
```

`queue` (sourced from `bin/queue.sh`, backed by `scripts/queue.py`) is the CLI:

- `queue list` — preview the next items (title + first line)
- `queue next` — show the full first item
- `queue titles` — bare titles, one per line (what the picker reads)
- `queue complete [--item-title "..."] [--start-time "<iso>"] [--end-time "<iso>"]` — move an item to `.queue-complete` with timestamps

With no `--item-title`, `queue complete` opens fzf over the current titles; timestamps default
to now when omitted. Pass `--start-time` explicitly to record a real duration.

`bin/` is sourced only by interactive shells, so `queue` is often **not** on `PATH` in a tool
call. Call the script directly instead of assuming the function exists:

```bash
uv run python scripts/queue.py --queue-path .queue --complete-path .queue-complete <action> ...
```

## Manual invocation flow

1. Read `.queue` directly (not just `queue list`) so you have the full text of every item, not just previews.
2. If there's more than one item, **ask which one to work on** — use `AskUserQuestion` listing the item titles. Don't assume the first item is wanted; the user has explicitly said they might not want to start with it.
3. Once picked, discuss the approach in chat before touching code — confirm scope, check for ambiguity, agree on a plan. This is the same human-in-the-loop discussion CLAUDE.md always requires.
4. Capture the start time: `date -Iseconds`.
5. Implement per the repo's standing conventions (see `.claude/CLAUDE.md`): TDD, discrete reviewable steps, invoke the relevant language skill (`bash`, `node`, `python`, `dotfiles`, `project-manager`) for the code being touched. Never `git add`/`commit`/`push` — that stays manual.
6. When the user confirms the item is done, capture the end time (`date -Iseconds`) and run:
   ```
   queue complete --item-title "<exact title>" --start-time "<start>" --end-time "<end>"
   ```
   Pass all three from a tool call: the fzf picker needs a terminal, and the recorded start
   time is the only way the duration reflects the real work. The title must match the `##`
   header **exactly** — `queue.py` matches by exact string equality, and omitting it in a
   non-interactive context just prints the available titles and exits 1.
7. Confirm the item moved to `.queue-complete`. There's no tool that lets the assistant clear
   the session directly, so the assistant MUST end its own reply with a loud, unmissable
   reminder written in markdown (big heading, bold, emoji — vary the wording each time) telling
   the user to run `/clear`. Do this every single time, immediately after confirming
   completion — never silently move on. This only matters for this LLM-driven flow; `queue.py`
   itself has no banner-printing code since raw terminal output doesn't render in the chat
   transcript anyway.

## Notes

- `.queue` and `.queue-complete` are both gitignored — this is a local working queue, not tracked history.
- Both files sync between machines through the password store (`make secrets-save` / `secrets-load`,
  and the git hooks that call them). A `load` overwrites the local file from the store, so a stale
  store snapshot can **resurrect an already-completed item** into `.queue`. If an item appears in
  both files, that is what happened — verify against `.queue-complete` before working it again.
- Autonomous/late-night processing (no discussion step, just pick the first item and run) is a separate future mode — don't skip the discussion/selection step unless the user has explicitly asked for autonomous execution.
