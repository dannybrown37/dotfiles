# Overview

dotfiles for a mostly WSL2-based setup with a growing list of compatible distros/environments.

## Clone and Run

Install `apt` packages and basic Bash profile:

``` bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash
```

## Additional Install Options

```bash
make help
```

Use this to see in-terminal help message for available Makefile options.

### Bash

```bash
make bash
```

This has already been run initially, but use this to sync `apt` packages.
This will happen with any run of the script, including with an `--install`
arg.

### Python

```bash
make python
```

This installs Python build dependencies, `pyenv`, `Python 3.12`, `pipx`, a
few `pipx` packages that I like to have globally, and creates a symlink
for the `.ruff.toml` file in the `~` directory to provide global `ruff` rules.

### Node

```bash
make node
```

This installs `nvm`, `Node 18`, and a few `NPM` packages that I like to
have globally.

### Golang

```bash
make golang
```

This deletes the current installation of Golang, installs the latest version,
and copies needed environment variables to the `~/.bashrc` file.

### Rust

```bash
make rust
```

This installs Rust/Cargo.

### VS Code Configuration

```bash
make vscode
```

This installs various VSCode extensions and merges the `settings.json` with
any existing user settings on the system.

### The Full Suite

```bash
make all
```

Install all of the above with this.

## Commands Available

* `ahk`: run all AutoHotKey scripts in the `./ahk` directory from WSL or Git Bash in the Windows environment
* `ahk help`: feed all available hotstrings into `fzf` for review (not selection)
* `ahk kill`: kill all running autohotkey processes
* `ahk open`: open ahk/hotstrings.ahk in VSCode
* `ahk secrets`: open ahk/secrets.ahk in VSCode
* `buildlogs`: see the latest build logs for configured AWS CodePipeline stack
* `cdp`: move directly to any directory in ~/projects (with tab autocomplete)
* `cf`: use fzf to open one or more (with tab) files in VS Code
* `cht`: curl cht.sh for commonly used tools/languages. Add new ones as needed in cht/.cht_sh_index
* `cpw`: copy files from WSL to Windows easily, defaults to Downloads folder (with tab autocomplete)
* `ff`: Fuzzy find current folder with a preview panel.
* `fh`: Run bash history into `fzf` and select command to run from there.
* `gg/google`: google something from the terminal, no quotes needed, pops open a web browser
* `lopen`: open to the monitoring tab of a specific AWS Lambda
* `mk`: mkdir and cd into it
* `node_project_init`: spin up a git repo, gitignore file, and package.json for a Node project
* `nvi`: use fzf to open one or more (with tab) files in Neovim
* `pip_project_init`: spin up a Python package starter set of files via `cookiecutter` and [my configuration for it](https://github.com/dannybrown37/pip_package_cookiecutter)
* `push`: Send a push alert to your phone
* `push_to_topic`: Send a push alert to a custom topic
* `url`: Open up a URL directly using the system browser

### Config Options

* In the `ahk/` directory, set up any number of AutoHotKey scripts:
  * `hotstrings.ahk` for generalized shortcuts
  * `secrets.ahk` for non-public shortcuts not to be committed
  * etc.
* In the `bin/` directory, configure scripts that use dynamic data and need to invoke other functions outside of the main function
* In the `config/` directory, configure a Bash profile based on various settings:
  * `.bashrc` holds a full config file that is symlinked to `~`
  * `.gitconfig` holds git config info that is symlinked to `~`
  * `.inputrc` for Bash prompt customizations
  * `.ruff.toml` holds Python linting rules symlinked to `~` for global use
  * `.secrets` holds data not for committing to git
* In the `./nvim` directory, configure a Neovim profile.
* In the `./.vscode` directory:
  * `settings.json` for VS Code user settings
  * `extensions.txt` for essential VS Code extensions

### Bash Customizations

* Use Ctrl+J/Ctrl+K to scroll up and down through command history
* Use escape to clear current prompt entry

### Handling Secrets

Assuming you are properly authorized to do so on the machine in question:

```bash
make insert-secrets
```

Push `./config/.secrets` and `./ahk/secrets.ahk` into the encrypted `password-store`.

Or push individually:
* `make insert-ahk`
* `make insert-bash`

```bash
make pull-secrets
```

Pull data from the `password-store` into locations at `./config/.secrets` and `./ahk/secrets.ahk`

Or pull individually:
* `make pull-ahk`
* `make pull-bash`

```bash
make sync-secrets
```

Attempt to sync data between `password-store` and local secrets files. Because this may
have unintended consequences, local secrets files are backed up first (`password-store`
would require a commit to truly overwrite).

## Initial Windows Setup Notes

For when you're truly starting from scratch.

### Downloads

* [Google Chrome](https://www.google.com/search?q=google+chrome+download)
* [Windows Terminal](https://www.google.com/search?q=windows+terminal+download)
* [Visual Studio Code](https://www.google.com/search?q=vs+code+download)
* [AutoHotKey](https://www.autohotkey.com/download/)

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
