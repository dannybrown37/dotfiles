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
| `git fix` | Edit an earlier commit instead of adding a new one (new work: `git commit`) |
| `git ship` | Push, PR, auto-merge, watch CI, then `git done` |
| `git done` | Back to base, pull (keeps uncommitted changes) |
| `git rescue <topic>` | Move commits made after the merge to `<topic>` |
| `git purge` | Delete local branches whose origin branch is gone. `--all`: every branch but base/main/master/develop and worktrees (asks) |

- Committed on `main` by mistake? `git start <topic>` moves the commits.
- Committed while CI ran? `git rescue <topic>`, then `git ship`.
- No auto-merge (`--no-auto` or repo off)? `git ship` skips the CI watch. Merge by hand.
- Repo without auto-merge? PR body uses the work template (Why/What, Evidence of Testing, QA Testing Instructions).
- `git ship` skips `git done` on `--no-done`, no auto-merge, or no merge.
- PR title = top commit prefix + branch: `feat:` + `a-b` -> `feat: a b`.
- Prefix rank: feat>fix>perf>refactor>revert>build>ci>docs>test>style>chore
