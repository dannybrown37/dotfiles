<!-- markdownlint-disable-file MD025 -->
# Git Workflow

The base branch (origin's default: `main`, `master`, ...) changes only by PR. A PR merges only when CI is green.

```
git start my-topic      git ship              git done (ship runs it)
      │                     │                               │
main ─●─────────────────────┼───────────────────────────────●── main
       \                    │                              /
        commit ── commit ── push ── PR ── CI green ── auto-merge
```

| Command | What it does |
|---|---|
| `git start <topic>` | Pull base, make branch `<topic>` |
| `gab` | Before ship: fold staged fixes into commits |
| `git ship` | Push, PR, auto-merge, watch CI, then `git done` |
| `git fix` | Fold staged fixes into their commits anywhere in the stack, push what moved |
| `git done` | Back to base, pull (keeps uncommitted changes) |
| `git rescue <topic>` | Move commits made after the merge to `<topic>` |
| `git purge` | Delete local branches whose origin branch is gone. `--all`: every branch but base/main/master/develop and worktrees (asks) |

- Committed on `main` by mistake? `git start <topic>` moves the commits.
- Committed while CI ran? `git rescue <topic>`, then `git ship`.
- No auto-merge (`--no-auto`, repo off, or stacked)? `git ship` skips the CI watch. Merge by hand.
- Repo without auto-merge? PR body uses the work template (Why/What, Evidence of Testing, QA Testing Instructions).
- `git ship` skips `git done` on `--no-done`, no auto-merge, or no merge.
- PR title = top commit prefix + branch: `feat:` + `a-b` -> `feat: a b`.
- Prefix rank: feat>fix>perf>refactor>revert>build>ci>docs>test>style>chore

# Stacked PRs

Waiting on review? `git start -s b` branches `b` off the current branch `a`.

```
main ─●────────────●── main
       \          / \
        a1 ── a2 ─┘  b1'  a merged; git done on b: rebase, PR b → main
               \
                b1   git ship on b: PR b → a, no auto-merge
```

- `git done` on `b` rebases onto `a` if `a` moved. Repeat down the stack.
- `git ship` on `b` force-pushes (with lease) any lower branch that moved, bottom-up, then links the PRs into a GitHub stack (`gh stack link`; needs the `gh-stack` extra, warns if missing). It refuses if a lower branch is behind origin: pull it first.
- Fix for a lower PR? Stay on the top branch, stage it, `git fix`. It folds the fix into `a`'s commit (git-absorb), rebases with `rebase.updateRefs` so `a` moves too, and pushes `a` and `b`. No editor. Changes with no commit to fold into stay staged and nothing is pushed.
- A lower branch made without `git start -s`? Its open PR's base stands in, and gets recorded.
- Plain `gab` skips commits other branches can reach, so on `b` it only touches `b`'s own commits.
- Conflict: fix, `git rebase --continue`, `git push --force-with-lease`.
