# Queue Sync Model

How `.queue` and `.queue-complete` move between machines. Read this when a sync
looks wrong — an item reappearing, a completion not sticking, a stale
`[in-progress]` marker. The day-to-day pull flow in `SKILL.md` doesn't need any
of it.

## Transport

Both files are gitignored — this is a local working queue, not tracked history.
They sync through the password store via `make secrets-save` / `secrets-load`
and the git hooks that call them.

Pulling `~/.password-store` by hand does **not** update `.queue`; it only moves
the encrypted blob. The decrypted files are rewritten solely by
`scripts/secrets.sh load`, which runs from the dotfiles `post-merge` hook or
`make secrets-load` (and does its own `pass git pull` first).

## Merge, not overwrite

Both directions merge. `secrets.sh` routes these two paths through
`queue_cli.py merge-queue` / `merge-completed` instead of copying, so items
added on either machine survive a sync.

`.queue` ends up as the union of both sides by title, minus every title
recorded in the merged `.queue-complete`. **Completions are the tombstones** —
that's why an already-completed item doesn't resurrect.

`secrets.sh` reconciles `.queue-complete` before `.queue` (`MERGE_PATHS`),
independent of the order the store's manifest lists them in. The queue merge
needs the tombstones already merged.

## Consequence: complete items, don't hand-delete them

Deleting a `##` section from `.queue` without running `queue complete` leaves
no tombstone, so the other machine's copy syncs it right back.

## Stale `[in-progress]` markers

The marker lives in `.queue` itself, so it syncs through the same mechanism. A
stale snapshot can make an item look claimed when the claiming session already
finished (or vice versa). If `queue claim` errors as already-in-progress but no
other agent is actually running, ask before assuming the claim is real.

## Trimming

`trim_content` in `scripts/queue_cli.py` caps a completed item's body at 50
lines, appending `_[Trimmed from N to 50 lines]_`. This only affects what lands
in `.queue-complete`; `.queue` is never modified by it.

Nothing trims `.queue` while an item is still active, so reading the full file
can still be large if someone pasted a huge log in. That's expected.
