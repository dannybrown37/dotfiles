# Overview

dotfiles for a mostly WSL2-based setup with a growing list of compatible distros/environments.

## Clone and Run

Install `apt` packages and basic Bash profile:

``` bash
curl -s https://raw.githubusercontent.com/dannybrown37/dotfiles/main/install/this_repo.sh | bash
```

## Additional Install Options

### Bash

```bash
~/projects/dotfiles/setup
```

This has already been run initially, but use this to sync `apt` packages.
This will happen with any run of the script, including with an `--install`
arg.

### Python

```bash
~/projects/dotfiles/setup --install python
```

This installs Python build dependencies, `pyenv`, `Python 3.12`, `pipx`, a
few `pipx` packages that I like to have globally, and creates a symlink
for the `.ruff.toml` file in the `~` directory to provide global `ruff` rules.

### Node

```bash
~/projects/dotfiles/setup --install node
```

This installs `nvm`, `Node 18`, and a few `NPM` packages that I like to
have globally.

### Golang

```bash
~/projects/dotfiles/setup --install golang
```

This deletes the current installation of Golang, installs the latest version,
and copies needed environment variables to the `~/.bashrc` file.

### Rust

```bash
~/projects/dotfiles/setup --install rust
```

This installs Rust/Cargo.

### VS Code Configuration

```bash
~/projects/dotfiles/setup --install vscode
```

This installs various VSCode extensions and merges the `settings.json` with
any existing user settings on the system.

### The Full Suite

```bash
~/projects/dotfiles/setup --install all
```

Install all of the above with this.

## Commands Available

* `ahk`: run all AutoHotKey scripts in the `./ahk` directory from WSL or Git Bash in the Windows environment
* `ahk kill`: kill all running autohotkey processes
* `ahk open`: open ahk/dev_shortcuts.ahk in VSCode
* `ahk open_secrets`: open ahk/secrets.ahk in VSCode
* `cdp`: move directly to any directory in ~/projects (with tab autocomplete)
* `cht`: curl cht.sh for commonly used tools/languages. Add new ones as needed in cht/.cht_sh_index
* `cpw`: copy files from WSL to Windows easily, defaults to Downloads folder (with tab autocomplete)
* `gg/google`: google something from the terminal, no quotes needed, pops open a web browser
* `mk`: mkdir and cd into it
* `node_project_init`: spin up a git repo, gitignore file, and package.json for a Node project
* `pip_project_init`: spin up a Python package starter set of files via `cookiecutter` and [my configuration for it](https://github.com/dannybrown37/pip_package_cookiecutter)

### Config Options

* In the `./ahk` directory, set up any AutoHotKey scripts"
  * `dev_shortcuts.ahk` for generalized shortcuts
  * `secrets.ahk` for non-public shortcuts not to be committed here
* In the `config/` directory, configure a Bash profile based on various settings:
  * `.aliases` for any aliases we want to use
  * `.aws` for AWS CLI functions to speed up feedback loops
  * `.envvars` to set environment variables we want permanently set
  * `.functions` to store simple Bash functions to improve the scripting/CLI experience
  * `.secrets` holds secret data such as tokens and keys that aren't committed to Git
* In the `./.vscode` directory:
  * `settings.json` for VS Code user settings
  * `extensions.txt` for essential VS Code extensions

## Initial Windows Setup Notes

For when you're truly starting from scratch.

### Downloads

* [Google Chrome](https://www.google.com/search?q=google+chrome+download)
* [Windows Terminal](https://www.google.com/search?q=windows+terminal+download)
* [Visual Studio Code](https://www.google.com/search?q=vs+code+download)
* [AutoHotKey](https://www.autohotkey.com/download/)

### Set Up a WSL Debian Distro

In PowerShell, choose a repo:

```powershell
  wsl --set-default-version 2
  wsl --install -d Debian
```

To reset (for example):

```powershell
  wsl --install kali-linux
```

### Set Up Git, Clone Dotfiles, Install

In Debian:

``` bash
 sudo apt update
 sudo apt install git -y
 mkdir projects
 cd projects
 git clone https://www.github.com/dannybrown37/dotfiles
 cd dotfiles
 source install.sh
```
