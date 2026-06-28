# Overview

Debian dotfiles for a mostly WSL2-based setup with a growing list of compatible distros/environments.

## Clone and Run

Install `apt` packages and basic Bash profile:

```bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash
```

## Install Options

The output of `make` in the root directory:

```txt
Usage: make [option]

Bootstrap scripts:
  bash            Install Bash profile (tmux, apt packages, etc.)
  python          Install Python environment (uv, select uv tools)
  node            Install Node.js environment (n, Node 22, select global packages)
  deno            Install Deno 2
  golang          Install Go environment (latest Golang version)
  rust            Install Rust environment (latest Rust version, select global packages)
  nvim            Install Neovim
  vscode          Install VS Code extensions and settings
  all             Install all of the above
  gnome           Install Gnome extensions
  windows         Install Windows extensions (NerdFonts and Komorebi)
  komo            Reset komorebi (useful for after configuration changes)

These commands require GPG keys and secrets:
  secrets-save    Save local secrets to password-store
  secrets-load    Load secrets from password-store to local files
```

## Commands Available

Commmands are auto-documented with a # @doc comment on the same line as the command definition.

<!-- @doc:commands:start -->

| Command | Description | Source |
| --- | --- | --- |
| `ahk` | Run all AutoHotKey scripts (Windows only) | `config/.bash_aliases` |
| `awsconfig` | Edit AWS config file in Neovim | `config/.bash_aliases` |
| `beep` | Play a beep sound (Windows only) | `config/.bash_aliases` |
| `cb` | Copy stdin to clipboard. <command> | cb | `config/.bash_aliases` |
| `cdf` | Code Dot Files: Open the dotfiles repo in VSCode | `config/.bash_aliases` |
| `cdp` | Cd to any project directory from anywhere (with tab autocomplete) | `bin/cdp.sh` |
| `chrome_focus` | Ctrl+Shift+C - Cycle through open Chrome windows | `ahk/chrome_focus.ahk` |
| `cht` | Query cht.sh for info on many technologies | `config/.bashrc` |
| `cmds` | Search all commands, aliases, and AHK hotkeys via fzf | `bin/cmds.sh` |
| `crocinstall` | Install Croc | `config/.bash_aliases` |
| `crocsend` | Send a file via a Croc server | croc send <file> | `config/.bash_aliases` |
| `du` | Disk usage sorted and human-readable | `config/.bash_aliases` |
| `epoch` | Alias for epoch_timestamp | `config/.bash_aliases` |
| `epoch_timestamp` | Print the current epoch timestamp in milliseconds, copy to clipboard | `config/.bashrc` |
| `gb` | Fuzzy-find and checkout a git branch | `config/.bash_aliases` |
| `gem` | Ask Gemini a question from the terminal | `bin/gem.sh` |
| `gitlines` | Count lines of code in all files from curren branch | `config/.bash_aliases` |
| `gitpurge` | Delete all local branches except main, develop, and the current branch | `config/.bash_aliases` |
| `glo` | Show last commit message (Git Log One-Line) | `config/.bash_aliases` |
| `google` | Pop open a browser to google search results type in command line | `config/.bashrc` |
| `gpup` | Push new branch and open PR in browser | `config/.bash_aliases` |
| `komo` | Reset komorebi window manager (Windows only) | `config/.bash_aliases` |
| `llmedit` | Edit LLM rules in Neovim | `config/.bash_aliases` |
| `llmrules` | Copy LLM rules to clipboard for chatbot copy-paste | `config/.bash_aliases` |
| `mk` | Create a directory and cd into it | `config/.bashrc` |
| `note` | Create a note file from the command line | `config/.bashrc` |
| `noteion` | Create Notion pages from the terminal | `bin/noteion.sh` |
| `notes` | Open a note file from the command line from $NOTES_DIR using fzf | `config/.bashrc` |
| `open_url_in_browser` | Open a URL in the browser, system-agnostic | `config/.bashrc` |
| `pcb` | Print clipboard contents | `config/.bash_aliases` |
| `push` | Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message> | `config/.bashrc` |
| `push_to_topic` | Push a message to ntfy.sh at a topic | push_to_topic <topic> <message> | `config/.bashrc` |
| `quick_google` | Ctrl+Shift+G - Search Google for selected text | `ahk/quick_google.ahk` |
| `src` | Reload bash configuration | `config/.bash_aliases` |
| `teams_toggle` | Ctrl+Shift+D - Toggle Microsoft Teams focus | `ahk/teams_toggle.ahk` |
| `tmconf` | Reload tmux config | `config/.bash_aliases` |
| `tms` | Start or attach to tmux Session | `config/.bash_aliases` |
| `tree` | Show a tree view of files and directories | `config/.bash_aliases` |
| `url` | Open a URL in the system browser | `config/.bash_aliases` |
| `utc` | Alias for utc_timestamp | `config/.bash_aliases` |
| `utc_timestamp` | Print the current UTC timestamp in ISO format with microseconds, copy to clipboard | `config/.bashrc` |
| `uuid` | Generate a random UUID and put it in the clipboard | `config/.bash_aliases` |
| `vc` | Vim cheatsheet fuzzy finder | `config/.bash_aliases` |
| `vscode_toggle` | Ctrl+Shift+X - Toggle VS Code focus | `ahk/vscode_toggle.ahk` |
| `vsi` | Fuzzy find files and open in Neovim | `config/.bash_aliases` |
| `windows_terminal_toggle` | Ctrl+Shift+Z - Toggle Windows Terminal focus | `ahk/windows_terminal_toggle.ahk` |
<!-- @doc:commands:end -->

### Directory Structure

<!-- @doc:structure:start -->
| Directory | Description |
| --- | --- |
| `ahk/` | AutoHotKey scripts for Windows (hotstrings, secrets) |
| `aws/` | AWS helper scripts and configuration |
| `bin/` | Sourced shell scripts loaded into the current session |
| `config/` | Dotfiles (.bashrc, .gitconfig, .inputrc, .ruff.toml, .secrets) symlinked to ~ |
| `install/` | Bootstrap install scripts invoked via Make targets |
| `nvim/` | Neovim configuration (lazy.nvim, Lua) |
| `pass/` | password-store (pass) configuration and GPG setup |
| `project_manager/` | Python CLI for GTD and 12-Week Year planning |
| `scripts/` | Non-sourced standalone executable scripts |
| `wsl/` | WSL-specific settings, functions, and komorebi config |

<!-- @doc:structure:end -->

### Bash Customizations

- Use Ctrl+J/Ctrl+K to scroll up and down through command history
- Use escape to clear current prompt entry

### Handling Secrets

Assuming you are properly authorized to do so on the machine in question:

```bash
make secrets-save    # local → password-store
make secrets-load    # password-store → local (backs up existing files first)
```

Manages `./config/.secrets` and `./ahk/secrets.ahk` via the encrypted `password-store`.

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
