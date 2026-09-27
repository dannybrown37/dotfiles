# git-branchless

Stacked-diff workflow + smartlog for git. Installed via `install/git-branchless.sh`.

## Setup

- Installed via `cargo install --locked git-branchless`
- `install/git-branchless.sh` runs `git branchless init --main-branch main` after install,
  which generates hooks into `githooks/` (where `core.hooksPath` points)
- Generated hooks are `.gitignore`d — they're regenerated per-machine by the install script
- `githooks/pre-commit` is the only committed hook (runs prek)

## Workflow Overview

Branchless replaces the branch-per-feature model with a commit-stack model.
You work on a stack of commits on `main`, then push them as PRs.

```bash
# Start work (no branch needed, but you can use one)
git switch -c my-feature

# Make commits as usual
git commit -m "add widget"
git commit -m "test widget"

# See your commit graph
git sl                    # smartlog — shows your commits relative to main

# Push to GitHub and open a PR
git submit --create       # pushes branch, opens PR via `gh`

# After PR merges
git sync                  # fetches main, rebases your stack, cleans up merged commits
```

### Key Commands

| Command | What it does |
|---------|-------------|
| `git sl` | Smartlog — visual commit graph |
| `git submit --create` | Push + open PR (uses `gh` CLI) |
| `git submit` | Update existing PRs with new commits |
| `git sync` | Fetch main, rebase stack, hide merged |
| `git sw` | Interactive switch between commits/branches |
| `git amend` | Amend the current commit |
| `git reword` | Edit a commit message |
| `git move` | Reorder/reparent commits in your stack |
| `git restack` | Rebase dependent commits after amend/reword |
| `git undo` | Undo the last branchless operation |
| `git prev` / `git next` | Navigate the commit stack |

### Stacked PRs (the real power)

When you have commits A → B → C, `git submit --create` can open one PR per commit.
Each PR targets the previous one. When A merges, B's PR auto-retargets to `main`.
This lets you get reviews on small, focused changes without blocking on merge order.

## How It Fits This Repo

This is a solo dotfiles repo, so stacked PRs are overkill. The main value here:

- **`git sl`** — better than `git log --oneline --graph` for seeing where you are
- **`git submit --create`** — one command to push + open PR, CI runs, merge when green
- **`git sync`** — keeps main clean after merging
- **`git undo`** — safety net for rebases and amends

The "green before merge" guarantee comes from the PR workflow: CI runs on the PR,
you only merge when it's green. No branch protection rules needed.

## Deciding Whether to Adopt

**Low commitment:** just use `git sl` and `git undo`. These work without changing
your workflow at all.

**Medium commitment:** use `git submit` for PRs instead of manual `git push` + `gh pr create`.
Slightly different muscle memory but same conceptual model.

**Full commitment:** stacked commits on main, no feature branches. This is the big
workflow shift — worth trying on a project with more PRs in flight than dotfiles.
