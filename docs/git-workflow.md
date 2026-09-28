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
| `git ship` | Push, PR, auto-merge, watch CI, then `git done` |
| `git done` | Back to base, pull (keeps uncommitted changes) |
| `git rescue <topic>` | Move commits made after the merge to `<topic>` |

- Committed on `main` by mistake? `git start <topic>` moves the commits.
- Committed while CI ran? `git rescue <topic>`, then `git ship`.
- `git ship` skips `git done` on `--no-done`, `--no-auto`, or no merge.
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
- Conflict: fix, `git rebase --continue`, `git push --force-with-lease`.
