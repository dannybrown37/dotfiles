# Fleet

One dashboard for every Claude Code and Copilot CLI session on the machine,
a launcher for new agents in their own git worktrees, and a review radar that
ranks the PRs waiting on you and pre-reviews them locally.

```
 Alt+W (Windows)  ─┐
 prefix F (tmux)  ─┼─► fleet cockpit ─► tmux session "fleet", window "dash"
 fleet            ─┘                     ┌──────────────────────────────────┐
                                         │ Agents  │ Reviews  │  Ctrl+P      │
                                         ├─────────┴──────────┴──────────────┤
                                         │ every agent session + live state  │
                                         │ live preview of the selected pane │
                                         └──────────────────────────────────┘
```

## Quick start

```bash
fleet hooks install                    # once: lets fleet see every session's state
fleet                                  # dashboard (or Alt+W from anywhere on Windows)
fleet new fix-flaky -p "fix the flaky gwt test"            # Claude, new worktree
fleet new api-spike -a copilot -C ~/projects/api -b main   # Copilot, explicit repo/base
gh issue view 42 --json body -q .body | fleet new issue-42 # task from stdin
fleet radar --review                   # rank review requests, pre-review the new ones
```

## Agents tab

Lists **every** interactive `claude` / `copilot` session, not only the ones
fleet started. Sessions that need you sort to the top, and the tab title
counts them: `Agents (2/8)` means 2 of 8 are waiting on you.

| State | Meaning |
|---|---|
| `● waiting` | Blocked on you: a permission prompt or a question |
| `✓ your turn` | Finished its turn |
| `⟳ working` | Busy |
| `■ exited` | The agent quit; its window stays so the last output is readable |
| `· no data` | Found running, but no hook has fired since hooks were installed |

| Key | Action |
|---|---|
| `enter` | Jump into the session's tmux pane (`prefix F` comes back) |
| `s` | Type a message into it (sent as one bracketed paste) |
| `d` / `g` | Diff (fleet agents: since branching; others: uncommitted) / lazygit |
| `o` | Open its PR in the browser |
| `n` | New agent |
| `x` / `X` | Stop / stop and delete the worktree. Fleet's own agents only; the branch is always kept |

### How sessions are found

```
 claude / copilot (any session)
     │ hook event (prompt, tool use, stop, notification, ...)
     ▼
 scripts/fleet-hook.sh ──► walks parent pids up to the agent CLI
     │                       └► ~/.local/state/fleet/sessions/<pid>.json
     ▼
 /proc scan (every 2s) ──► live agent processes: pid, cwd, TMUX_PANE
     │
     └─ join on pid ──► a dashboard row; jump/send use the tmux pane
```

- The hook runs on every agent event, so it imports only `os` and `sys`
  (about 38 ms). It is silent and always exits 0.
- A row with no tmux pane (a VS Code terminal, a Claude background session)
  still shows state and diff, but cannot be jumped to or typed into.
- The pid file stores the process start time, so a reused pid never inherits
  stale state.

### Hooks

| Agent | Where | Installed by |
|---|---|---|
| Claude Code | `~/.claude/settings.json` (merged in, other hooks kept, one-time `.pre-fleet.bak`) | `fleet hooks install` (`fleet hooks uninstall` reverses it) |
| Copilot CLI | `~/.copilot/hooks/fleet.json` → `config/copilot/hooks/fleet.json` | `install/symlinks.sh` (`just bootstrap`) |

`fleet hooks` prints the status of both.

## Launching agents

```
 fleet new NAME ─► git worktree add  <repo>-worktrees/NAME  (branch NAME, base = current branch)
               ─► tmux window "NAME" in session "fleet", running claude/copilot with the task
               ─► answers the folder-trust dialog if you already trust the source repo
```

- **Worktrees** use the same layout as `gwt add`.
- **Trust dialog**: both CLIs ask again for every new folder. Fleet answers
  only when the dialog names the exact worktree it just made *and* the source
  repo is already trusted in Claude's or Copilot's own records. For Copilot
  it picks "this session" only, never "remember". `--no-trust` leaves the
  dialog to you.
- **Extra CLI args** go after `--`: `fleet new x -p "go" -- --permission-mode acceptEdits`.
- An agent that crashes on start keeps its window (`remain-on-exit`), so the
  error stays readable.

## Reviews tab (radar)

Ranks `gh search prs --review-requested=@me` by an impact score; every point
has a reason shown next to it.

| Signal | Effect |
|---|---|
| Touches migrations, auth, infra, CI, deps | Up |
| Size (log scale), no tests for changed code, waiting time | Up |
| Pre-review says high / medium risk | Up |
| Bot author, red CI | Down |
| `⚡` | Small, low-risk, green: a quick win |

| Key | Action |
|---|---|
| `r` / `R` | Pre-review the selected PR / every PR without one |
| `a` | Deep review: an agent in a worktree of your local clone runs `gh pr checkout` and the tests |
| `o` / `enter` | Open in the browser |

**Local only.** Pre-reviews run through your local `claude -p` or `copilot`
with tools off (the diff is untrusted input), from an empty temp directory.
Results are cached in `~/.local/state/fleet/reviews/`, keyed by head commit,
so a PR is re-reviewed only when it changes. Nothing is posted to GitHub.

## Ctrl+P palette

Fuzzy search over every action: jump/send/diff for each session, open or
deep-review each PR, start an agent in any repo under `~/projects`. If the
clipboard holds a GitHub PR URL, "agent review clipboard PR" comes first.

## Settings

| Variable | Default | Effect |
|---|---|---|
| `FLEET_DEFAULT_AGENT` | `claude` | Agent for `fleet new` and the `n` dialog |
| `FLEET_REVIEW_AGENT` | default agent | CLI that writes pre-reviews |
| `FLEET_REVIEW_MODEL` | CLI default | `--model` for pre-reviews |
| `FLEET_PROJECTS_DIR` | `~/projects` | Where the palette and deep review look for repos |
| `FLEET_SESSION` | `fleet` | tmux session for fleet's agents and the dashboard |
| `FLEET_STATE_DIR` | `~/.local/state/fleet` | Records, hook state, review cache |

## Code

`scripts/fleet/` (Python, Textual). `scripts/fleet.sh` runs it with the
dotfiles venv without changing directory. Tests: `uv run pytest scripts/test_fleet_*.py`.

| Module | Role |
|---|---|
| `events.py`, `proclite.py`, `hook.py` | Hook hot path: stdlib-only, no heavy imports |
| `procs.py` | `/proc` scan for live agent sessions |
| `store.py` | On-disk records and state |
| `agents.py`, `ops.py`, `tmux.py`, `worktree.py`, `trust.py` | Launching and supervising |
| `radar.py` | Review ranking and local pre-reviews |
| `palette.py`, `tui.py`, `cli.py` | Palette model, dashboard, CLI |
| `hooks_install.py` | `fleet hooks install/uninstall` |
