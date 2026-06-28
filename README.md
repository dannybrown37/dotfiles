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

<!-- @doc:commands:start -->


- `ahk`: Run all AutoHotKey scripts
- `beep`: Play a beep sound
- `cb`: Copy stdin to clipboard
- `cdp`: Cd to any project directory from anywhere (with tab autocomplete)
- `gb`: Fuzzy-find and checkout a git branch
- `gem`: Ask Gemini a question from the terminal
- `gpup`: Push branch and open PR in browser
- `komo`: Reset komorebi window manager
- `llmedit`: Edit LLM rules in Neovim
- `llmrules`: Copy LLM rules to clipboard
- `noteion`: Create Notion pages from the terminal
- `pcb`: Print clipboard contents
- `src`: Reload bash configuration
- `tms`: Start or attach to tmux Session
- `url`: Open a URL in the system browser
- `vc`: Vim cheatsheet fuzzy finder
- `vsi`: Fuzzy find files and open in Neovim
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
