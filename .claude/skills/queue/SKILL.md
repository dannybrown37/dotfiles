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
- `queue titles` — bare titles, one per line (what the picker reads); an in-progress item's
  title carries a literal `[in-progress]` suffix
- `queue claim [--item-title "..."]` — mark an item in-progress by appending `[in-progress]`
  to its `##` header in `.queue`, so a concurrent agent reading the file (or `queue
  titles`/`list`/`next`) can see it's taken. Errors (exit 1) if the item is already marked.
- `queue complete [--item-title "..."] [--end-time "<iso>"]` — move an item to
  `.queue-complete`, stamped with the time it was completed. If the item's body is over 50
  lines (e.g. a pasted CI log), it's capped at 50 lines with a `_[Trimmed from N to 50
  lines]_` note appended — `.queue` itself is never modified, only what lands in
  `.queue-complete`.

With no `--item-title`, `queue claim` and `queue complete` both open fzf over the current
titles. `--item-title` matches regardless of whether it includes the `[in-progress]` suffix.
`--end-time` defaults to now if omitted.

`bin/` is sourced only by interactive shells, so `queue` is often **not** on `PATH` in a tool
call. Call the script directly instead of assuming the function exists:

```bash
uv run python scripts/queue.py --queue-path .queue --complete-path .queue-complete <action> ...
```

## Manual invocation flow

1. Read `.queue` directly (not just `queue list`) so you have the full text of every item, not
   just previews. Skip any item whose header already carries `[in-progress]` — another agent
   has it — and surface that to the user rather than silently ignoring it.
2. If there's more than one eligible item, **ask which one to work on** — use `AskUserQuestion`
   listing the item titles. Don't assume the first item is wanted; the user has explicitly said
   they might not want to start with it.
3. Once picked, immediately claim it so other concurrently-running agents don't grab the same
   item during the discussion/implementation that follows:
   ```
   queue claim --item-title "<exact title>"
   ```
   If this errors because it's already in-progress, another agent beat you to it — stop and
   tell the user instead of proceeding.
4. Discuss the approach in chat before touching code — confirm scope, check for ambiguity,
   agree on a plan. This is the same human-in-the-loop discussion CLAUDE.md always requires.
5. Implement per the repo's standing conventions (see `.claude/CLAUDE.md`): TDD, discrete
   reviewable steps, invoke the relevant language skill (`bash`, `node`, `python`, `dotfiles`)
   for the code being touched — `gtd/CLAUDE.md` covers package-specific conventions when the
   item is in `gtd/`. Never `git add`/`commit`/`push` — that stays manual.
6. When the user confirms the item is done, run:
   ```
   queue complete --item-title "<exact title>"
   ```
   Pass it from a tool call: the fzf picker needs a terminal. The title matches the `##`
   header regardless of whether it still carries `[in-progress]`, and omitting it in a
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
  and the git hooks that call them). Both directions **merge** rather than overwrite: `secrets.sh`
  routes these two paths through `queue.py merge-queue` / `merge-completed` instead of copying, so
  items added on either machine survive a sync. `.queue` is the union of both sides by title, minus
  every title recorded in the merged `.queue-complete` — completions are the tombstones, which is why
  an already-completed item no longer resurrects.
- Consequence: **complete items, don't hand-delete them.** Deleting a `##` section from `.queue`
  without running `queue complete` leaves no tombstone, so the other machine's copy syncs it back.
- `secrets.sh` reconciles `.queue-complete` before `.queue` (`MERGE_PATHS`), independent of the order
  the store's manifest lists them in — the queue merge needs the tombstones already merged.
- Pulling `~/.password-store` by hand does **not** update `.queue`; it only moves the encrypted blob.
  The decrypted files are rewritten solely by `scripts/secrets.sh load`, which runs from the dotfiles
  `post-merge` hook or `make secrets-load` (and does its own `pass git pull` first).
- Autonomous/late-night processing (no discussion step, just pick the first item and run) is a separate future mode — don't skip the discussion/selection step unless the user has explicitly asked for autonomous execution.
- The `[in-progress]` marker lives in `.queue` itself, so it syncs through the same password-store
  mechanism. A stale snapshot can make an item look claimed when the claiming session already
  finished (or vice versa) — if `queue claim` errors as already-in-progress but no other agent
  is actually running, ask the user before assuming the claim is real.
- The 50-line trim on completion (`trim_content` in `scripts/queue.py`) only affects
  `.queue-complete`. Nothing trims `.queue` while an item is still active, so step 1's full
  read of the file can still be large if someone pastes a huge log in — that's expected.
