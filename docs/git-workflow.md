# Git workflow

`main` changes only through a PR. A PR merges only when CI is green.

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
| `git start <topic>` | Go to `main`, pull the latest, make a new branch `<topic>` |
| `git ship` | Push, open a PR, turn on auto-merge, watch CI live, then `git done` once merged |
| `git done` | After the merge: go back to `main` and pull (carries uncommitted changes) |

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

PRs that build on each other: `main <- a <- b <- c`. Uses `gh stack` (`stack setup` once).

| Command | What it does |
|---|---|
| `stack start <name>` | Start a stack, first branch |
| `stack next <name>` | New branch on top of the current one |
| `stack ship` | Push all, open a PR per branch |
| `stack sync` | Rebase the stack after a lower PR changes or merges |
| `stack land` | Merge the stack (all or nothing) |

`stack help` for all commands.
