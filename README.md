# Overview

Debian dotfiles for a WSL2-based setup.

## Clone and Run

Install `apt` packages and basic Bash profile:

```bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash
```

## Install Options

The output of `make` in the root directory:

```txt
Usage: make [option]

Start Here:

  bash            Install Bash profile (tmux, apt packages, etc.)

Languages & Runtimes:
  python          Install Python environment (uv, select uv tools)
  node            Install Node.js environment (n, Node 22, select global packages)
  deno            Install Deno 2
  golang          Install Go environment (latest Golang version)
  rust            Install Rust environment (latest Rust version, select global packages)

Developer Tools:
  nvim            Install Neovim
  lazygit         Install lazygit TUI git client
  cartoon         Install cartoon CLI (pinned version, no hook)
  vscode          Install VS Code extensions and settings

Environment-Specific:
  gnome           Install Gnome extensions
  select-nerdfont Interactively pick and install a Nerd Font (Windows)
  wsl-fonts       Install Starship + JetBrainsMono Nerd Font (WSL to Windows)
  komo            Install komorebi/whkd if needed, then (re)start it

Secrets (requires GPG keys):
  secrets-save    Save local secrets to password-store, push to private repo
  secrets-load    Pull private repo, load secrets from password-store to local files
```

## Commands Available

Commmands are auto-documented with a # @doc comment on the same line as the command definition.

<!-- @doc:commands:start -->

| Command | Description | Source |
| --- | --- | --- |
| `ahk` | Run all AutoHotKey scripts (Windows only) | `config/.bash_aliases` |
| `asciinema` | Record and replay terminal sessions | asciinema rec session.cast | `bin/stubs.sh` |
| `atuin` | Shell history search/sync (replaces Ctrl+R) | atuin search | `bin/stubs.sh` |
| `awsconfig` | Edit AWS config file in Neovim | `config/.bash_aliases` |
| `beep` | Play a beep sound (Windows only) | `config/.bash_aliases` |
| `cartoon` | Compress noisy CLI output for AI agents | cartoon pytest | `bin/stubs.sh` |
| `cb` | Copy stdin to clipboard. <command> | cb | `config/.bash_aliases` |
| `ccstats` | Claude Code usage stats from local session logs, broken out per repo | ccstats --json, ccstats --record, ccstats --explain | `config/.bash_aliases` |
| `cdf` | Code Dot Files: Open the dotfiles repo in VSCode | `config/.bash_aliases` |
| `cdp` | Cd to any project directory from anywhere (with tab autocomplete) | `bin/cdp.sh` |
| `chrome_focus` | Ctrl+Shift+C - Cycle through open Chrome windows | `ahk/chrome_focus.ahk` |
| `cht` | Query cht.sh for info on many technologies | `config/.bashrc` |
| `cinplay` | Replay session.cast recording | `config/.bash_aliases` |
| `cinrec` | Record terminal session to session.cast | `config/.bash_aliases` |
| `clip` | Copy a screen recording to OneDrive with fzf selection: clip [--reset] | `bin/clip.sh` |
| `cmds` | Search all commands, aliases, and AHK hotkeys via fzf | `bin/cmds.sh` |
| `croc` | Send files between machines securely | croc send <file> | `bin/stubs.sh` |
| `delta` | Syntax-highlighting pager for git diffs (replaces less) | `bin/stubs.sh` |
| `dotaudit` | Audit system for dotfile setup compliance | `config/.bash_aliases` |
| `du` | Disk usage sorted and human-readable | `config/.bash_aliases` |
| `epoch` | Alias for epoch_timestamp | `config/.bash_aliases` |
| `epoch_timestamp` | Print the current epoch timestamp in milliseconds, copy to clipboard | `config/.bashrc` |
| `eza` | Modern ls replacement with git status and icons | `bin/stubs.sh` |
| `fd` | Fast find that respects .gitignore | fd <pattern> | `bin/stubs.sh` |
| `fzf` | Interactive fuzzy finder for any list | `bin/stubs.sh` |
| `gb` | Fuzzy-find and checkout a git branch | `config/.bash_aliases` |
| `gem` | Ask Gemini questions from the terminal (lazy-loaded on first use) | `bin/gem.sh` |
| `gh` | GitHub CLI -- PRs, issues, workflows, and more | `bin/stubs.sh` |
| `ghpr` | Push branch and open GitHub PR creation page in browser | ghprc [--draft] | `config/.bash_aliases` |
| `gitdoctor` | Diagnose why a GitHub push is refused (HTTPS chain or SSH): gitdoctor [repo-dir] | `config/.bash_aliases` |
| `gitlines` | Count lines of code in all files from curren branch | `config/.bash_aliases` |
| `git-open` | Open current repo/branch in browser | git-open [remote] [branch] | `bin/stubs.sh` |
| `gitpurge` | Delete all local branches except main, develop, and the current branch | `config/.bash_aliases` |
| `glog` | Graph log of all branches | `config/.bash_aliases` |
| `glo` | Show last commit message (Git Log One-Line) | `config/.bash_aliases` |
| `glow` | Render markdown in the terminal | glow <file> | `bin/stubs.sh` |
| `google` | Pop open a browser to google search results type in command line | `config/.bashrc` |
| `gpup` | Push new branch and open PR in browser | `config/.bash_aliases` |
| `grl` | List recent CI runs on current branch | `config/.bash_aliases` |
| `grw` | Watch CI run for current branch live | grw | `config/.bash_aliases` |
| `gsl` | Git stash list | `config/.bash_aliases` |
| `gsp` | Git stash pop | `config/.bash_aliases` |
| `gss` | Git stash save | `config/.bash_aliases` |
| `gwt` | git-worktree: gwt <add|list|rm|cd> [branch] [options] | `bin/gwt.sh` |
| `hyperfine` | Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2' | `bin/stubs.sh` |
| `komo` | Reset komorebi window manager (Windows only) | `config/.bash_aliases` |
| `lazygit` | TUI git client | lg (alias) | `bin/stubs.sh` |
| `lg` | Open lazygit TUI | `config/.bash_aliases` |
| `llmedit` | Edit LLM rules in Neovim | `config/.bash_aliases` |
| `llmrules` | Copy LLM rules to clipboard for chatbot copy-paste | `config/.bash_aliases` |
| `media` | Open educational media reference | `config/.bash_aliases` |
| `mentalmodels` | Open mental models reference | `config/.bash_aliases` |
| `mk` | Create a directory and cd into it | `config/.bashrc` |
| `mkwebapp` | Create a Chrome --app= shortcut on the Windows Desktop | mkwebapp <name> <url> [--taskbar] | `bin/mkwebapp.sh` |
| `note` | Create a note file from the command line | `config/.bashrc` |
| `noteion` | Create Notion pages from the terminal (lazy-loaded on first use) | `bin/noteion.sh` |
| `notes` | Open a note file from the command line from $NOTES_DIR using fzf | `config/.bashrc` |
| `open_url_in_browser` | Open a URL in the browser, system-agnostic | `config/.bashrc` |
| `pass` | Password store -- manage secrets via GPG | pass show <name> | `bin/stubs.sh` |
| `pcb` | Print clipboard contents | `config/.bash_aliases` |
| `push` | Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message> | `config/.bashrc` |
| `push_to_topic` | Push a message to ntfy.sh at a topic | push_to_topic <topic> <message> | `config/.bashrc` |
| `queue` | AI work queue -- add items, discuss, track completion | queue list | `bin/queue.sh` |
| `quick_google` | Ctrl+Shift+G - Search Google for selected text | `ahk/quick_google.ahk` |
| `rg` | Fast regex search across files (ripgrep) | rg <pattern> | `bin/stubs.sh` |
| `skills` | Export a dotfiles skill into another repo (.claude + .github bridge) | skill-export <name> [target-dir] | `bin/skills.sh` |
| `src` | Reload bash configuration | `config/.bash_aliases` |
| `starship` | Cross-shell prompt with git/lang context | `bin/stubs.sh` |
| `teams_toggle` | Ctrl+Shift+D - Toggle Microsoft Teams focus | `ahk/teams_toggle.ahk` |
| `tldr` | Simplified man pages with practical examples | tldr <cmd> | `bin/stubs.sh` |
| `tmconf` | Reload tmux config | `config/.bash_aliases` |
| `tms` | Start or attach to tmux Session | `config/.bash_aliases` |
| `tmux` | Terminal multiplexer -- sessions, windows, panes | `bin/stubs.sh` |
| `tokei` | Count lines of code by language in current repo | `bin/stubs.sh` |
| `tree` | Show a tree view of files and directories | `config/.bash_aliases` |
| `url` | Open a URL in the system browser | `config/.bash_aliases` |
| `utc` | Alias for utc_timestamp | `config/.bash_aliases` |
| `utc_timestamp` | Print the current UTC timestamp in ISO format with microseconds, copy to clipboard | `config/.bashrc` |
| `uuid` | Generate a random UUID and put it in the clipboard | `config/.bash_aliases` |
| `vc` | Vim cheatsheet fuzzy finder | `config/.bash_aliases` |
| `vscode_toggle` | Ctrl+Shift+X - Toggle VS Code focus | `ahk/vscode_toggle.ahk` |
| `vsi` | Fuzzy find files and open in Neovim (git-aware) | `config/.bash_aliases` |
| `windows_terminal_toggle` | Ctrl+Shift+Z - Toggle Windows Terminal focus | `ahk/windows_terminal_toggle.ahk` |
| `zoxide` | Smarter cd that learns your most-used directories (alias: cd) | `bin/stubs.sh` |
<!-- @doc:commands:end -->

### Directory Structure

<!-- @doc:structure:start -->
| Directory | Description |
| --- | --- |
| `ahk/` | AutoHotKey scripts for Windows (hotstrings, secrets) |
| `aws/` | AWS helper scripts and configuration |
| `bin/` | Sourced shell scripts loaded into the current session |
| `config/` | Dotfiles (.bashrc, .gitconfig, .inputrc, .ruff.toml, .secrets) symlinked to ~ |
| `githooks/` | Tracked git hooks (core.hooksPath) that sync the private password-store on dotfiles push/pull |
| `install/` | Bootstrap install scripts invoked via Make targets |
| `nvim/` | Neovim configuration (lazy.nvim, Lua) |
| `references/` | Reference documentation — mental models, LLM rules, and other persistent reference material |
| `scripts/` | Non-sourced standalone executable scripts |
| `wsl/` | WSL-specific settings, functions, and komorebi config |

<!-- @doc:structure:end -->

### Bash Customizations

- Use Ctrl+J/Ctrl+K to scroll up and down through command history
- Use escape to clear current prompt entry

### Handling Secrets

Assuming you are properly authorized to do so on the machine in question:

```bash
make secrets-save    # git pull → local → password-store → git push
make secrets-load    # git pull → password-store → local (backs up changed files first)
```

Manages local gitignored files via the encrypted `password-store`.

The store lives at `~/.password-store` and is its own private git repo, so nothing about it
lands in this repo. `pass` commits on every insert; the make targets push and pull.

**What gets synced** is the `manifest` entry inside the store — one `pass-entry:path` pair per
line. It lives in the store rather than in this repo so the list of synced files stays private
too. Paths resolve three ways:

| Path form | Resolves to |
| --- | --- |
| `some/path` | relative to this repo's root |
| `@repo/some/path` | inside another repo, wherever that repo is cloned |
| `~/some/path` | relative to `$HOME`, regardless of this repo — e.g. the shared `/queue` |

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

**Automatic sync:** `make bash` sets `core.hooksPath` to the tracked `githooks/` dir. From then
on a plain `git push` here runs `secrets-save` first (encrypt changed files, push the store) and
a plain `git pull` runs `secrets-load` after (pull the store, decrypt to local files) — so an
ordinary push or pull in this repo is enough to carry every synced file (the queue included) to
the other machine, with no separate `secrets-save`/`secrets-load` call needed. Unchanged entries
are skipped so the store doesn't collect a commit per push. If the store errors, the hook warns
but never blocks the dotfiles push/pull.

**New machine setup:** `make bash` clones the store if `~/.password-store` doesn't exist yet —
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

### Multiple GitHub Accounts

More than one GitHub account shares these machines. Both the commit author and the push token
are chosen from the repo's **remote**, via `includeIf "hasconfig:remote.*.url:..."` — not from
its directory, so a repo cloned somewhere unexpected still gets the right account.

| Remote | Author | Token |
| --- | --- | --- |
| personal account | personal email | `$MY_GITHUB_TOKEN` |
| anything else | *none — commit refused* | `gh` / `$GITHUB_TOKEN` |

The global `[user]` block deliberately has **no email** and sets `useConfigOnly = true`, so a
repo matching no rule fails with *"Author identity unknown"* rather than quietly committing as
the wrong person.

Any **non-personal** identity — the addresses, and the remote patterns that select them — lives
in `~/.gitconfig-private`, which is gitignored and never enters this repo. It reaches other
machines through the password store, not through git. Machines without that file simply inherit
the fail-loud default, since git ignores a missing include.

Personal repos get their token from `scripts/git-credential-personal.sh`, which emits
`$MY_GITHUB_TOKEN` and falls back to `gh` when unset. No token is stored in the repo — the
helper only reads the environment. The dotfiles audit verifies the whole wiring.

When a push is refused, run `gitdoctor` in the offending repo. It walks the chain end to end —
git version, which includes resolved, helper order, whether the token is actually exported into
git's subprocess environment, what `git credential fill` hands back, and whether the account
that token resolves to can actually push to this repo — and names the first broken link. That
last check is the one the audit cannot do: a present-but-wrong or expired token passes every
config-level check and only fails at push time. Tokens are printed as a prefix plus digest, so
the output is safe to paste.

Which helper *should* win depends on who owns the remote, so the doctor checks against that
rather than demanding the personal helper everywhere. On an **SSH** remote it diagnoses SSH
instead — agent, loaded keys, whether GitHub accepts the key — then runs the HTTPS chain as a
preview and, if that chain is healthy, tells you to switch transport:

```bash
git remote set-url origin https://github.com/OWNER/REPO.git
```

This setup routes identity and tokens by *HTTPS remote URL*, so an SSH remote bypasses all of
it. Switching is usually the fix, and it survives WSL forgetting your ssh-agent.

## Initial Windows Setup Notes

For when you're truly starting from scratch.

### Downloads

- [Google Chrome](https://www.google.com/search?q=google+chrome+download)
- [Windows Terminal](https://www.google.com/search?q=windows+terminal+download)
- [Visual Studio Code](https://www.google.com/search?q=vs+code+download)
- [AutoHotKey](https://www.autohotkey.com/download/)

### Set Up a WSL Debian Distro

In PowerShell, choose a distro:

```powershell
  wsl --set-default-version 2
  wsl --install -d Debian
```

To reset a WSL distro (for example):

```powershell
  wsl --unregister kali-linux
```
