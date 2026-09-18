# Handling Secrets

Assuming you are properly authorized to do so on the machine in question:

```bash
make secrets-save    # git pull → local → password-store → git push
make secrets-load    # git pull → password-store → local (backs up changed files first)
```

Manages local gitignored files via the encrypted `password-store`.

The store lives at `~/.password-store` and is its own private git repo, so nothing about it
lands in this repo. `pass` commits on every insert; the `secrets-save`/`secrets-load` recipes push and pull.

**What gets synced** is the `manifest` entry inside the store — one `pass-entry:path` pair per
line. It lives in the store rather than in this repo so the list of synced files stays private
too. Paths resolve three ways:

| Path form | Resolves to |
| --- | --- |
| `some/path` | relative to this repo's root |
| `@repo/some/path` | inside another repo, wherever that repo is cloned |
| `~/some/path` | relative to `$HOME`, regardless of this repo — e.g. a bare dotfile |

The `@repo` anchor exists because not every synced file belongs to this repo, and a sibling
repo isn't at a fixed path on every machine. It resolves in order: `$REPO_HOME` (the anchor
name uppercased, with `-` → `_`, plus `_HOME`), then `${PROJECTS_DIR:-~/projects}/repo`. If
neither is a directory, the entry is reported `not installed` and skipped, and the rest of the
manifest syncs normally — so a machine that never cloned that repo doesn't get a stray
decrypted file dropped into this one.

The `~/` form exists for entries that don't belong to any one repo — a bare home path always
resolves, so it's never reported `not installed`.

`not installed` and `missing` are deliberately different: the first means the repo isn't on
this machine, the second means it is but the file isn't there. An `@` path with no `/`, or a
`~` not followed by `/`, is malformed and fails the whole run rather than being silently
skipped.

Every entry is copied whole, in both directions — nothing is merged line by line. A `load`
therefore overwrites the local file with the store's copy, saving the displaced version
alongside it as `<file>.bak` first. Keep a file out of the manifest if both machines edit it
independently and you'd want both sets of edits back.

**Sync is opt-in:** run `make secrets-save` (encrypt changed files, push the store) and
`make secrets-load` (pull the store, decrypt to local files) yourself. Earlier versions ran these
automatically from `pre-push`/`post-merge` git hooks; those hooks are gone, so a plain
`git push`/`git pull` here no longer touches the store. Unchanged entries are skipped, so a
`secrets-save` with nothing to do adds no commit.

**New machine setup:** `make password-store` clones the store if `~/.password-store` doesn't exist yet —
tries `gh auth login` + `gh repo clone` first (no token to copy by hand), falling back to a
`PASSWORD_STORE_REMOTE` prompt (may embed a token — treat as a raw secret) if `gh` can't. Requires
your GPG private key already imported — that transfer stays manual/out-of-band.

Both targets pull the store first, with `--rebase`: `pass` commits on every insert, so two
machines that each saved have diverged as a matter of course. The old `--ff-only` refused that
outright, and under the pull hook the failure was only a warning — so the store silently stayed
behind.

**Caveat:** entries are encrypted blobs, so git can't merge them. If both machines change the
same entry before syncing, the rebase conflicts; the sync aborts it (leaving the store usable)
and tells you to resolve by picking a side (`pass git checkout --ours/--theirs <entry>.gpg`),
not by merging. Saving before switching machines avoids this.
