# Git workflow

`main` changes only through a PR. A PR merges only when CI is green.

```
git start my-topic      git ship                        git done
      │                     │                               │
main ─●─────────────────────┼───────────────────────────────●── main
       \                    │                              /
        commit ── commit ── push ── PR ── CI green ── auto-merge
```

## The 3 commands

| Command | What it does |
|---|---|
| `git start <topic>` | Go to `main`, pull the latest, make a new branch `<topic>` |
| `git ship` | Push, open a PR, turn on auto-merge, watch CI live |
| `git done` | After the merge: go back to `main` and pull |

Between `start` and `ship`: make commits as usual.

## Rules

- Never commit on `main`. `git ship` refuses to run there.
- Every commit starts with a prefix: `feat:`, `fix:`, `docs:`, `ci:`, `chore:`, ...
  A hook checks this when you commit.
- Name the branch so it reads like a title: `main-branch-protection`, not `stuff`.
- PR title is made for you: `<top prefix>: <branch name>`. The PR is squashed into one commit on `main` with that title.
  Branch `main-branch-protection` + commits `ci:` and `feat:` -> `feat: main branch protection`.
  Rank: feat > fix > perf > refactor > revert > build > ci > docs > test > style > chore.
- Auto-merge waits for CI. Red CI = no merge. Fix, commit, `git push`. PR updates itself.
- `git ship` again is safe: it pushes, reuses the open PR, and watches CI.
  If the PR already merged, it stops and tells you to run `git done`.

## Plain-English git words

| Command | Means |
|---|---|
| `git switch <branch>` | Move to a branch |
| `git switch -c <name>` | Create a branch and move to it (old form: `git checkout -b`) |
| `git add -p` | Pick which pieces of a change go in the next commit, one at a time |
| `git stash` / `git stash pop` | Put uncommitted changes aside / bring them back |
| `git pull --ff-only` | Get new commits; refuse if your copy has split from GitHub's |
| `gh pr checks --watch` | Show CI status for this PR until it finishes |
| `gh pr view --web` | Open this PR in the browser |
