# Git workflow

The base branch changes only through a PR. A PR merges only when CI is green.

The base branch is origin's default branch: `main`, `master`, `develop`, etc.
The diagram says `main`; read it as "the base branch".

```
git start my-topic      git ship              git done (ship runs it)
      │                     │                               │
main ─●─────────────────────┼───────────────────────────────●── main
       \                    │                              /
        commit ── commit ── push ── PR ── CI green ── auto-merge
```

## The 3 commands

| Command | What it does |
|---|---|
| `git start <topic>` | Go to the base branch, pull the latest, make a new branch `<topic>` |
| `git ship` | Push, open a PR, turn on auto-merge, watch CI live, then `git done` once merged |
| `git done` | After the merge: go back to the base branch and pull (carries uncommitted changes) |

`git ship` skips `git done` (you stay on the branch) when:

- you pass `--no-done`
- auto-merge is off
- the PR is not merged 60s after CI goes green
- you committed while CI ran: run `git rescue <topic>`

Between `start` and `ship`: make commits as usual.

## Rules

- PR title = top commit prefix + branch name: `feat:` + `main-branch-protection` -> `feat: main branch protection`.
  Rank: feat > fix > perf > refactor > revert > build > ci > docs > test > style > chore.
- Committed after the merge? `git rescue <topic>`, then `git ship`.

## Stacked PRs

For work that waits on review (auto-merge off): keep going on top of an open PR.

```
git start a      git start -s b     (a merges)      git done (on b)
main ─●──────────────────────────────────●──────────────●── main
       \                                              \
        a1 ── a2   PR a → main                         b1   PR b → main
                \
                 b1   PR b → a
```

| Command | On a stacked branch |
|---|---|
| `git start -s <topic>` | New branch `<topic>` on top of the current branch (its parent) |
| `git ship` | PR targets the parent, lists only this branch's commits, no auto-merge |
| `git done` | Parent merged: rebase onto the base branch, retarget the PR, force-push. Parent moved: rebase onto it. Else: nothing to do |

Stacks go deeper (`a <- b <- c`): after `a` merges, `git done` on `b`, then on `c`.
Rebase conflict: fix, `git rebase --continue`, `git push --force-with-lease`.
