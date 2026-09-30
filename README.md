# Overview

Debian dotfiles for a WSL2-based setup.

## Clone and Run

In WSL, install `apt` packages and basic Bash profile in one command:

```bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/bootstrap.sh | bash
```

## Install Options

The output of `just` in the root directory:

<!-- make:start -->

```
Usage: just [option]

Start Here:
  bootstrap       Full machine setup (apt, bash, cli-tools, python, password-store)
  extras          Languages, editors, and opt-in tools, with ✓ for installed

Environment-Specific:
  gnome           Install Gnome extensions (dash-to-dock, just-perfection)
  windows         Windows-side tools (winget, npm, uv, win32yank), with ✓ for installed
  vscode          Install VS Code extensions and settings

Secrets (requires GPG keys):
  secrets-save    Save local secrets to password-store, push to private repo
  secrets-load    Pull private repo, load secrets from password-store to local files

Verification:
  check           Run every prek hook over the whole repo
  test            Run all tests (pytest + shell syntax check)
  audit           Audit this machine against every dotfiles dependency (read-only)
  doctor          Diagnose a refused git push -- credentials, remotes, transport (read-only)
  bench-shell     Benchmark interactive shell startup time
```

<!-- make:end -->

## Commands Available

Commands are auto-documented with a # @doc comment on the same line as the command definition.

<!-- @doc:commands:start -->

| Command | Description | Source |
| --- | --- | --- |
| `ahk` | Start AutoHotkey (ahk/main.ahk); ahk --help for more (Windows only) | `config/.bash_aliases` |
| `app_toggle` | Ctrl+Shift+X/C/D - Toggle focus for VS Code / Chrome / Teams; Alt+A - jump to tmux in VSCode's terminal; Alt+S - same, but to the spotify_player tmux window | `ahk/app_toggle.ahk` |
| `asciinema` | Record and replay terminal sessions | asciinema rec session.cast | `bin/stubs.sh` |
| `atuin` | Shell history search/sync (replaces Ctrl+R) | atuin search | `bin/stubs.sh` |
| `autocorrect` | Fixes ~7,000 common typos as you type, everywhere except VS Code and terminals (community list, fetched by `ahk`) | `ahk/autocorrect.ahk` |
| `awsconfig` | Edit AWS config file in Neovim | `config/.bash_aliases` |
| `beep` | Play a beep sound (Windows only) | `config/.bash_aliases` |
| `bl` | Alias for backlog command from skill-tree | `config/.bash_aliases` |
| `cartoon` | Compress noisy CLI output for AI agents | cartoon pytest | `bin/stubs.sh` |
| `cb` | Copy stdin to clipboard. <command> | cb | `config/.bash_aliases` |
| `cdf` | Code Dot Files: Open the dotfiles repo in VSCode | `config/.bash_aliases` |
| `cdp` | Cd to any project directory from anywhere (with tab autocomplete) | `bin/cdp.sh` |
| `chafa` | Render an image as terminal ANSI art -- powers `screenshot pick` previews | chafa <image> | `bin/stubs.sh` |
| `chrome` | Alt+C in Chrome - copy the current tab as a markdown link, tracking params stripped | `ahk/chrome.ahk` |
| `chrome` | Google Chrome browser | chrome <url> | `bin/stubs.sh` |
| `cht` | Query cht.sh for info on many technologies | `bin/chtsh.sh` |
| `claude` | Claude Code coding agent | claude | `bin/stubs.sh` |
| `clip` | Copy a screen recording to OneDrive with fzf selection: clip [--reset] | `bin/clip.sh` |
| `cmds` | Search all commands, aliases, and AHK hotkeys via fzf | `bin/cmds.sh` |
| `copilot` | GitHub Copilot CLI coding agent | copilot | `bin/stubs.sh` |
| `cowsay` | ASCII cow speech bubbles | echo hi | cowsay | `bin/stubs.sh` |
| `croc` | Send files between machines securely | croc send <file> | `bin/stubs.sh` |
| `delta` | Syntax-highlighting pager for git diffs (replaces less) | `bin/stubs.sh` |
| `deno` | Deno JavaScript/TypeScript runtime | deno run <file> | `bin/stubs.sh` |
| `difftastic` | Diff that understands syntax | difft <old> <new> | `bin/stubs.sh` |
| `docker-doctor` | Diagnose why the docker CLI can't reach a daemon under WSL | docker-doctor | `bin/docker.sh` |
| `docker-up` | Start Docker Desktop from WSL and block until the daemon answers | docker-up [timeout_seconds] | `bin/docker.sh` |
| `docker` | Containers -- via Docker Desktop on the Windows host | docker-up to start it | `bin/stubs.sh` |
| `dotaudit` | Audit system for dotfile setup compliance | `config/.bash_aliases` |
| `du` | Disk usage sorted and human-readable | `config/.bash_aliases` |
| `epoch_timestamp` | Print the current epoch timestamp in milliseconds, copy to clipboard | `bin/timestamps.sh` |
| `eza` | Modern ls replacement with git status and icons | `bin/stubs.sh` |
| `faker` | Generate fake test data | faker name | `bin/stubs.sh` |
| `fastfetch` | System info summary (neofetch successor) | fastfetch | `bin/stubs.sh` |
| `fd` | Fast find that respects .gitignore | fd <pattern> | `bin/stubs.sh` |
| `fzf` | Interactive fuzzy finder for any list | `bin/stubs.sh` |
| `gab` | Fold staged fixes into the commits they belong to | `config/.bash_aliases` |
| `gb` | Fuzzy-find and checkout a git branch | `config/.bash_aliases` |
| `gem` | Ask Gemini questions from the terminal (lazy-loaded on first use) | `bin/gem.sh` |
| `generate_random_uuid_and_put_in_clipboard` | Generate a random UUID and copy to clipboard | `bin/uuid.sh` |
| `gh-dash` | Terminal GitHub dashboard -- PRs, issues, notifications | gh-dash | `bin/stubs.sh` |
| `ghautomerge` | Enable auto-merge + auto-delete head branches: ghautomerge [owner/repo] | `bin/ghautomerge.sh` |
| `ghpr` | Push branch and open GitHub PR creation page in browser | ghprc [--draft] | `config/.bash_aliases` |
| `ghrun` | github-action-run: ghrun [repo] [workflow] | `bin/ghrun.sh` |
| `ghwatch` | github-action-watch: watch the current repo's in-progress CI | ghwatch [--any-branch] | `bin/ghwatch.sh` |
| `gh` | GitHub CLI -- PRs, issues, workflows, and more | `bin/stubs.sh` |
| `git-absorb` | Auto-fixup commits by matching hunks to the right commit | git-absorb | `bin/stubs.sh` |
| `git-open` | Open current repo/branch in browser | git-open [remote] [branch] | `bin/stubs.sh` |
| `gitdoctor` | Diagnose why a GitHub push is refused (HTTPS chain or SSH): gitdoctor [repo-dir] | `config/.bash_aliases` |
| `gitlines` | Count lines of code in all files from current branch | `config/.bash_aliases` |
| `gitwf` | Show the git workflow cheat sheet (git start / ship / done) | `config/.bash_aliases` |
| `git_workflow` | Backs the git start/ship/rescue/done/purge aliases in config/.gitconfig | git_workflow.sh help | `scripts/git_workflow.sh` |
| `glog` | Graph log of all branches | `config/.bash_aliases` |
| `glow` | Render markdown in the terminal | glow <file> | `bin/stubs.sh` |
| `glo` | Show last commit message (Git Log One-Line) | `config/.bash_aliases` |
| `gpup` | Push new branch and open PR in browser | `config/.bash_aliases` |
| `gp` | Git push; if remote is ahead, pull --rebase and push again | `config/.bash_aliases` |
| `grl` | List recent CI runs on current branch | `config/.bash_aliases` |
| `grw` | Watch CI run for current branch live | grw | `config/.bash_aliases` |
| `gsl` | Git stash list | `config/.bash_aliases` |
| `gsp` | Git stash pop | `config/.bash_aliases` |
| `gss` | Git stash save | `config/.bash_aliases` |
| `gwt` | git-worktree: gwt <add|list|rm|cd> [branch] [options] | `bin/gwt.sh` |
| `htmlq` | jq for HTML | htmlq <selector> < page.html | `bin/stubs.sh` |
| `httpie` | Friendly HTTP client (httpie) | http GET <url> | `bin/stubs.sh` |
| `hyperfine` | Benchmark commands head-to-head | hyperfine 'cmd1' 'cmd2' | `bin/stubs.sh` |
| `jless` | Pager for JSON | jless <file.json> | `bin/stubs.sh` |
| `just` | Command runner (modern Make alternative) | just <recipe> | `bin/stubs.sh` |
| `komo` | Reset komorebi window manager (Windows only) | `config/.bash_aliases` |
| `lazygit` | TUI git client | lg (alias) | `bin/stubs.sh` |
| `lg` | Open lazygit TUI | `config/.bash_aliases` |
| `lolcat` | Rainbow text | echo hi | lolcat | `bin/stubs.sh` |
| `media` | Read educational media in glow (links: refs links media) | `config/.bash_aliases` |
| `mentalmodels` | Read mental models in glow (links: refs links mental-models) | `config/.bash_aliases` |
| `mkwebapp` | Create a Chrome --app= shortcut on the Windows Desktop | mkwebapp <name> <url> [--taskbar] | `bin/mkwebapp.sh` |
| `mk` | Create a directory and cd into it | `bin/mk.sh` |
| `mprocs` | Run several commands side by side | mprocs 'cmd1' 'cmd2' | `bin/stubs.sh` |
| `mystats` | Top commands I typed, excluding Claude Code's atuin entries | mystats [count] | `config/.bash_aliases` |
| `neofetch` | Alias for fastfetch, for muscle memory | neofetch | `bin/stubs.sh` |
| `noteion` | Create Notion pages from the terminal (lazy-loaded on first use) | `bin/noteion.sh` |
| `open_url_in_browser` | Open a URL in the browser, system-agnostic | `bin/browser.sh` |
| `pass` | Password store -- manage secrets via GPG | pass show <name> | `bin/stubs.sh` |
| `pcb` | Print clipboard contents | `config/.bash_aliases` |
| `picker` | Alt+, - fuzzy-search every ,, snippet and bash alias, Enter inserts it into the window you were in | `ahk/picker.ahk` |
| `push_to_topic` | Push a message to ntfy.sh at a topic | push_to_topic <topic> <message> | `bin/ntfy.sh` |
| `push` | Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message> | `bin/ntfy.sh` |
| `quick_run` | Alt+P - show/hide an always-warm WSL terminal on the `quickrun` tmux session | `ahk/quick_run.ahk` |
| `refs` | Read references and repo guides in glow (bare: pick one) | refs [links] [media|mental-models] | `config/.bash_aliases` |
| `rg` | Fast regex search across files (ripgrep) | rg <pattern> | `bin/stubs.sh` |
| `screenshot` | Take a Windows screenshot from WSL, or find existing ones: screenshot, screenshot open, screenshot latest, screenshot pick, screenshot move [dest] | `config/.bash_aliases` |
| `selection` | Alt+T - transform selected text (case, JSON, URL) from a keyboard menu; Alt+G - open selection (or clipboard) as URL / Jira key / Google search | `ahk/selection.ahk` |
| `shot` | Alias for screenshot | `config/.bash_aliases` |
| `song` | ,,song -- insert a Spotify link for the currently playing track | `ahk/hotstrings.ahk` |
| `song` | Copy the Spotify link for the currently playing track: song | `config/.bash_aliases` |
| `sorn` | ,,sorn -- insert "Song On Right Now" markdown for the currently playing track | `ahk/hotstrings.ahk` |
| `sorn` | Copy a "Song On Right Now" markdown blurb for the currently playing Spotify track: sorn | `config/.bash_aliases` |
| `src` | Reload bash configuration | `config/.bash_aliases` |
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
| `ahk/` | AutoHotkey v2 scripts for Windows, run as one process from main.ahk |
| `aws/` | AWS helper scripts and configuration |
| `bin/` | Sourced shell scripts loaded into the current session |
| `config/` | Dotfiles (.bashrc, .gitconfig, .inputrc, .ruff.toml, .secrets) symlinked to ~ |
| `docs/` | Long-form documentation extracted from the README |
| `githooks/` | Tracked git hooks (core.hooksPath) -- forward pre-commit, commit-msg and pre-push to prek |
| `install/` | Bootstrap install scripts invoked via justfile recipes |
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
- [Git Workflow](docs/git-workflow.md) — branch, PR, auto-merge on green CI (`gitwf` to view)

## Initial Windows Setup Notes

For when you're truly starting from scratch. `just windows --all` installs Windows Terminal, VS Code, AutoHotkey v2, and the rest of the winget-managed toolchain (plain `just windows` picks items one by one); only Chrome and the WSL distro itself are manual.

### Downloads

- [Google Chrome](https://www.google.com/search?q=google+chrome+download)

After WSL is up and this repo is cloned, run `just windows --all`, then `ahk && ahk startup` from WSL.

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
