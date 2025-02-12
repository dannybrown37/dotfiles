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
  node            Install Node.js environment (nvm, Node 18, select global packages)
  deno            Install Deno 2
  golang          Install Go environment (latest Golang version)
  rust            Install Rust environment (latest Rust version, select global packages)
  nvim            Install Neovim
  vscode          Install VS Code extensions and settings
  all             Install all of the above
  gnome           Install Gnome extensions

These commands require GPG keys and secrets:
  sync-secrets    Attempt to sync local secrets and password-store
  insert-ahk      Push local ahk secrets to password-store
  insert-bash     Push local bash secrets to password-store
  insert-secrets  Write all secrets files to password-store
  pull-ahk        Pull ahk secrets from password-store to local files
  pull-bash       Pull bash secrets from password-store to local files
  pull-secrets    Read all secrets files from password-store
```

## Commands Available (Incomplete)

- `ahk`: run all AutoHotKey scripts in the `./ahk` directory from WSL or Git Bash in the Windows environment
- `ahk help`: feed all available hotstrings into `fzf` for review (not selection)
- `ahk kill`: kill all running autohotkey processes
- `ahk open`: open ahk/hotstrings.ahk in VSCode
- `ahk secrets`: open ahk/secrets.ahk in VSCode
- `buildlogs`: see the latest build logs for configured AWS CodePipeline stack
- `cdp`: move directly to any directory in ~/projects (with tab autocomplete)
- `cf`: use fzf to open one or more (with tab) files in VS Code
- `cht`: curl cht.sh for commonly used tools/languages. Add new ones as needed in cht/.cht_sh_index
- `cpw`: copy files from WSL to Windows easily, defaults to Downloads folder (with tab autocomplete)
- `ff`: Fuzzy find current folder with a preview panel.
- `fh`: Run bash history into `fzf` and select command to run from there.
- `gg/google`: google something from the terminal, no quotes needed, pops open a web browser
- `lopen`: open to the monitoring tab of a specific AWS Lambda
- `mk`: mkdir and cd into it
- `node_project_init`: spin up a git repo, gitignore file, and package.json for a Node project
- `nvi`: use fzf to open one or more (with tab) files in Neovim
- `pip_project_init`: spin up a Python package starter set of files via `cookiecutter` and [my configuration for it](https://github.com/dannybrown37/pip_package_cookiecutter)
- `push`: Send a push alert to your phone
- `push_to_topic`: Send a push alert to a custom topic
- `url`: Open up a URL directly using the system browser

### Config Options

- In the `ahk/` directory, set up any number of AutoHotKey scripts:
  - `hotstrings.ahk` for generalized shortcuts
  - `secrets.ahk` for non-public shortcuts not to be committed
  - etc.
- In the `bin/` directory, configure scripts that use dynamic data and need to invoke other functions outside of the main function
- In the `config/` directory, configure a Bash profile based on various settings:
  - `.bashrc` holds a full config file that is symlinked to `~`
  - `.gitconfig` holds git config info that is symlinked to `~`
  - `.inputrc` for Bash prompt customizations
  - `.ruff.toml` holds Python linting rules symlinked to `~` for global use
  - `.secrets` holds data not for committing to git
- In the `./nvim` directory, configure a Neovim profile.
- In the `./.vscode` directory:
  - `settings.json` for VS Code user settings
  - `extensions.txt` for essential VS Code extensions
- In the `./wsl/` directory, configure WSL-only settings and functions

### Bash Customizations

- Use Ctrl+J/Ctrl+K to scroll up and down through command history
- Use escape to clear current prompt entry

### Handling Secrets

Assuming you are properly authorized to do so on the machine in question:

```bash
make insert-secrets
```

Push `./config/.secrets` and `./ahk/secrets.ahk` into the encrypted `password-store`.

Or push individually:

- `make insert-ahk`
- `make insert-bash`

```bash
make pull-secrets
```

Pull data from the `password-store` into locations at `./config/.secrets` and `./ahk/secrets.ahk`

Or pull individually:

- `make pull-ahk`
- `make pull-bash`

```bash
make sync-secrets
```

Attempt to sync data between `password-store` and local secrets files. Because this may
have unintended consequences, local secrets files are backed up first (`password-store`
would require a commit to truly overwrite).

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
