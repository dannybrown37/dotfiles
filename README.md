# Overview

Debian dotfiles for a WSL2-based setup.

## Clone and Run

Install `apt` packages and basic Bash profile:

```bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash
```

## Install Options

The output of `make` (aliased to `just`) in the root directory:

<!-- make:start -->

```
Usage: make [option]

Start Here:
  bootstrap       Set up a new machine end to end (every target below it)
  apt             Update apt and install every apt package this repo needs
  bash            Install the Bash profile (symlinks, prompt, completion, history)
  symlinks        Symlink every tracked config into $HOME (idempotent, no network)
  cli-tools       Install the core CLI tools with no usable distro package
  chrome          Install Google Chrome
  password-store  Clone the private password-store for secret sync

Languages & Runtimes:
  python          Install Python environment (uv, select uv tools)
  node            Install Node.js environment (n, Node 22, select global packages)
  deno            Install Deno 2
  golang          Install Go environment (latest Golang version)
  rust            Install the Rust toolchain (rustup, latest stable)

Developer Tools:
  nvim            Install Neovim
  lazygit         Install lazygit TUI git client
  cartoon         Install cartoon CLI and hook
  spotify         Install spotify_player TUI (remote control, no audio)
  terraform       Install Terraform (latest release)
  vscode          Install VS Code extensions and settings
  git-tools       Install git workflow tools (ghstack, git-absorb, git-branchless, gh-dash)
  rust-tools      Install the optional cargo utilities (htmlq, jless, difftastic, mprocs)

Environment-Specific:
  gnome           Install Gnome extensions
  select-nerdfont Interactively pick and install a Nerd Font (Windows)
  win32yank       Install win32yank clipboard bridge (WSL only)
  win-dev         Install Windows-side dev tooling (git, uv, node, typescript, etc.)
  wsl-fonts       Install Starship + JetBrainsMono Nerd Font (WSL to Windows)
  komo            Install komorebi/whkd if needed, then (re)start it

Secrets (requires GPG keys):
  secrets-save    Save local secrets to password-store, push to private repo
  secrets-load    Pull private repo, load secrets from password-store to local files

My Dev Tooling:
  projects        Clone and install skill-tree, gtd, and git-a-grip
  skill-tree      Clone skill-tree and run its setup script
  gtd             Clone gtd and install it with uv
  git-a-grip      Clone git-a-grip and install it with uv

Verification:
  check           Run every prek hook over the whole repo
  test            Run the scripts/ test suite with coverage
  audit           Audit this machine against every dotfiles dependency (read-only)
  doctor          Diagnose a refused git push -- credentials, remotes, transport (read-only)
```

<!-- make:end -->

## Commands Available

Commands are auto-documented with a # @doc comment on the same line as the command definition.

<!-- @doc:commands:start -->

| Command | Description | Source |
| --- | --- | --- |
| `ahk` | Run all AutoHotKey scripts (Windows only) | `config/.bash_aliases` |
| `app_toggle` | Ctrl+Shift+X/C/D - Toggle focus for VS Code / Chrome / Teams; Alt+A - jump to tmux in VSCode's terminal; Alt+S - same, but to the spotify_player tmux window | `ahk/app_toggle.ahk` |
| `asciinema` | Record and replay terminal sessions | asciinema rec session.cast | `bin/stubs.sh` |
| `atuin` | Shell history search/sync (replaces Ctrl+R) | atuin search | `bin/stubs.sh` |
| `awsconfig` | Edit AWS config file in Neovim | `config/.bash_aliases` |
| `beep` | Play a beep sound (Windows only) | `config/.bash_aliases` |
| `bl` | Alias for backlog command from skill-tree | `config/.bash_aliases` |
| `cartoon` | Compress noisy CLI output for AI agents | cartoon pytest | `bin/stubs.sh` |
| `cb` | Copy stdin to clipboard. <command> | cb | `config/.bash_aliases` |
| `cdf` | Code Dot Files: Open the dotfiles repo in VSCode | `config/.bash_aliases` |
| `cdp` | Cd to any project directory from anywhere (with tab autocomplete) | `bin/cdp.sh` |
| `chafa` | Render an image as terminal ANSI art -- powers `screenshot pick` previews | chafa <image> | `bin/stubs.sh` |
| `cht` | Query cht.sh for info on many technologies | `bin/chtsh.sh` |
| `cinplay` | Replay session.cast recording | `config/.bash_aliases` |
| `cinrec` | Record terminal session to session.cast | `config/.bash_aliases` |
| `clip` | Copy a screen recording to OneDrive with fzf selection: clip [--reset] | `bin/clip.sh` |
| `cmds` | Search all commands, aliases, and AHK hotkeys via fzf | `bin/cmds.sh` |
| `croc` | Send files between machines securely | croc send <file> | `bin/stubs.sh` |
| `delta` | Syntax-highlighting pager for git diffs (replaces less) | `bin/stubs.sh` |
| `docker` | Containers -- via Docker Desktop on the Windows host | docker-up to start it | `bin/stubs.sh` |
| `docker-doctor` | Diagnose why the docker CLI can't reach a daemon under WSL | docker-doctor | `bin/docker.sh` |
| `docker-up` | Start Docker Desktop from WSL and block until the daemon answers | docker-up [timeout_seconds] | `bin/docker.sh` |
| `dotaudit` | Audit system for dotfile setup compliance | `config/.bash_aliases` |
| `du` | Disk usage sorted and human-readable | `config/.bash_aliases` |
| `epoch_timestamp` | Print the current epoch timestamp in milliseconds, copy to clipboard | `bin/timestamps.sh` |
| `eza` | Modern ls replacement with git status and icons | `bin/stubs.sh` |
| `fd` | Fast find that respects .gitignore | fd <pattern> | `bin/stubs.sh` |
| `fzf` | Interactive fuzzy finder for any list | `bin/stubs.sh` |
| `gb` | Fuzzy-find and checkout a git branch | `config/.bash_aliases` |
| `gem` | Ask Gemini questions from the terminal (lazy-loaded on first use) | `bin/gem.sh` |
| `generate_random_uuid_and_put_in_clipboard` | Generate a random UUID and copy to clipboard | `bin/uuid.sh` |
| `gh-dash` | Terminal GitHub dashboard -- PRs, issues, notifications | gh-dash | `bin/stubs.sh` |
| `gh` | GitHub CLI -- PRs, issues, workflows, and more | `bin/stubs.sh` |
| `ghpr` | Push branch and open GitHub PR creation page in browser | ghprc [--draft] | `config/.bash_aliases` |
| `ghrun` | github-action-run: ghrun [repo] [workflow] | `bin/ghrun.sh` |
| `ghstack` | GitHub stacked PRs extension (fast passthrough) | ghstack view | `bin/stubs.sh` |
| `ghwatch` | github-action-watch: watch the current repo's in-progress CI | ghwatch [--any-branch] | `bin/ghwatch.sh` |
| `git-absorb` | Auto-fixup commits by matching hunks to the right commit | git-absorb | `bin/stubs.sh` |
| `git-branchless` | Stacked-diff workflow + smartlog for git | git-branchless smartlog | `bin/stubs.sh` |
| `gitdoctor` | Diagnose why a GitHub push is refused (HTTPS chain or SSH): gitdoctor [repo-dir] | `config/.bash_aliases` |
| `gitlines` | Count lines of code in all files from curren branch | `config/.bash_aliases` |
| `git-open` | Open current repo/branch in browser | git-open [remote] [branch] | `bin/stubs.sh` |
| `gitpurge` | Delete all local branches except main, develop, and the current branch | `config/.bash_aliases` |
| `glog` | Graph log of all branches | `config/.bash_aliases` |
| `glo` | Show last commit message (Git Log One-Line) | `config/.bash_aliases` |
| `glow` | Render markdown in the terminal | glow <file> | `bin/stubs.sh` |
| `gpup` | Push new branch and open PR in browser | `config/.bash_aliases` |
| `grl` | List recent CI runs on current branch | `config/.bash_aliases` |
| `grw` | Watch CI run for current branch live | grw | `config/.bash_aliases` |
| `gsl` | Git stash list | `config/.bash_aliases` |
| `gsp` | Git stash pop | `config/.bash_aliases` |
| `gss` | Git stash save | `config/.bash_aliases` |
| `gstk` | Short alias for stacked PR helper | `config/.bash_aliases` |
| `gwt` | git-worktree: gwt <add|list|rm|cd> [branch] [options] | `bin/gwt.sh` |
| `hyperfine` | Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2' | `bin/stubs.sh` |
| `just` | Command runner (modern Make alternative) | just <recipe> | `bin/stubs.sh` |
| `komo` | Reset komorebi window manager (Windows only) | `config/.bash_aliases` |
| `lazygit` | TUI git client | lg (alias) | `bin/stubs.sh` |
| `lg` | Open lazygit TUI | `config/.bash_aliases` |
| `make` | Run make, or just if a justfile exists and no Makefile | make <target> | `bin/make.sh` |
| `media` | Open educational media reference | `config/.bash_aliases` |
| `mentalmodels` | Open mental models reference | `config/.bash_aliases` |
| `mk` | Create a directory and cd into it | `bin/mk.sh` |
| `mkwebapp` | Create a Chrome --app= shortcut on the Windows Desktop | mkwebapp <name> <url> [--taskbar] | `bin/mkwebapp.sh` |
| `noteion` | Create Notion pages from the terminal (lazy-loaded on first use) | `bin/noteion.sh` |
| `open_url_in_browser` | Open a URL in the browser, system-agnostic | `bin/browser.sh` |
| `pass` | Password store -- manage secrets via GPG | pass show <name> | `bin/stubs.sh` |
| `pcb` | Print clipboard contents | `config/.bash_aliases` |
| `push` | Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message> | `bin/ntfy.sh` |
| `push_to_topic` | Push a message to ntfy.sh at a topic | push_to_topic <topic> <message> | `bin/ntfy.sh` |
| `quick_run` | Alt+P - show/hide an always-warm WSL terminal on the `quickrun` tmux session | `ahk/quick_run.ahk` |
| `rg` | Fast regex search across files (ripgrep) | rg <pattern> | `bin/stubs.sh` |
| `screenshot` | Take a Windows screenshot from WSL, or find existing ones: screenshot, screenshot open, screenshot latest, screenshot pick, screenshot move [dest] | `config/.bash_aliases` |
| `shot` | Alias for screenshot | `config/.bash_aliases` |
| `song` | Copy the Spotify link for the currently playing track: song | `config/.bash_aliases` |
| `song` | ,,song -- insert a Spotify link for the currently playing track | `ahk/hotstrings.ahk` |
| `sorn` | Copy a "Song On Right Now" markdown blurb for the currently playing Spotify track: sorn | `config/.bash_aliases` |
| `sorn` | ,,sorn -- insert "Song On Right Now" markdown for the currently playing track | `ahk/hotstrings.ahk` |
| `src` | Reload bash configuration | `config/.bash_aliases` |
| `stack` | Ergonomic wrapper for GitHub stacked PRs (gh stack) | stack help | `scripts/stack.sh` |
| `stack` | Stacked PR helper wrapper | stack doctor | `config/.bash_aliases` |
| `starship` | Cross-shell prompt with git/lang context | `bin/stubs.sh` |
| `terraform` | Provision infrastructure as code | terraform plan | `bin/stubs.sh` |
| `tldr` | Simplified man pages with practical examples | tldr <cmd> | `bin/stubs.sh` |
| `tmconf` | Reload tmux config | `config/.bash_aliases` |
| `tms` | Start or attach to tmux Session | `config/.bash_aliases` |
| `tmux` | Terminal multiplexer -- sessions, windows, panes | `bin/stubs.sh` |
| `tokei` | Count lines of code by language in current repo | `bin/stubs.sh` |
| `tree` | Show a tree view of files and directories | `config/.bash_aliases` |
| `utc_timestamp` | Print the current UTC timestamp in ISO format with microseconds, copy to clipboard | `bin/timestamps.sh` |
| `vc` | Vim cheatsheet fuzzy finder | `config/.bash_aliases` |
| `vsi` | Fuzzy find files and open in Neovim (git-aware) | `config/.bash_aliases` |
| `win32yank` | Fast Windows clipboard bridge for WSL | echo foo | win32yank.exe -i | `bin/stubs.sh` |
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
| `docs/` | Long-form documentation extracted from the README |
| `githooks/` | Tracked git hooks (core.hooksPath) -- forwards commits to pre-commit |
| `install/` | Bootstrap install scripts invoked via Make targets |
| `nvim/` | Neovim configuration (lazy.nvim, Lua) |
| `references/` | Reference documentation — mental models, LLM rules, and other persistent reference material |
| `scripts/` | Non-sourced standalone executable scripts |
| `wsl/` | WSL-specific settings, functions, and komorebi config |

<!-- @doc:structure:end -->

### Bash Customizations

- Use Ctrl+J/Ctrl+K to scroll up and down through command history
- Use escape to clear current prompt entry
- bash-preexec hooks provide smart warnings, context awareness, and auto-activation

### Shell Startup Benchmark

Updated with `just bench-shell`:

<!-- bench:start -->
10 runs — min: 0.042s · median: 0.044s · avg: 0.045s · max: 0.052s (updated 2026-09-18)
<!-- bench:end -->

### Further Reading

- [Handling Secrets](docs/secrets.md) — password-store sync, manifest format, new machine setup
- [Multiple GitHub Accounts](docs/github-accounts.md) — identity routing, credential helpers, `gitdoctor`

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
