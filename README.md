# Overview

dotfiles for a WSL2-based Debian setup.

## Clone and Run

``` bash
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles
source install.sh
```

## Features Summary

* Installs programming languages/packages:
  * Python (all versions available via `pyenv`)
  * NodeJS/NPM/TypeScript (gets latest available in Linux distribution, not always the most recent)
  * Golang (overwrites existing install with latest version)
  * Rust (latest stable version)
  * An assortment of preferred `apt` packages
* [Makes custom CLI commands globally available](#commands-available)
* [Provides various configuration options](#config-options)
* Installs the `autoenv` package to execute local `.env` files on each `cd` command
* Adds to `~/.bashrc` an invocation of the `./bash/profile.sh` script

### Commands Available

* ahk: run all AutoHotKey scripts in the `./ahk` directory from WSL in Windows
* ahk kill: kill all running autohotkey processes
* ahk open: open ahk/dev_shortcuts.ahk in VSCode
* ahk open_secrets: open ahk/secrets.ahk in VSCode
* cdp: move directly to any directory in ~/projects (with tab autocomplete)
* cht: curl cht.sh for commonly used tools/languages. Add new ones as needed in cht/.cht_sh_index
* cpw: copy files from WSL to Windows easily, defaults to Downloads folder (with tab autocomplete)
* gg/google: google something from the terminal, no quotes needed, pops open a web browser
* mk: mkdir and cd into it
* node_project_init: spin up a git repo, gitignore file, and package.json for a Node project
* pr: open pull request from current branch into default branch. GitHub and Bitbucket supported

### Config Options

* In the `bash/` directory, configure a Bash profile based on the types of settings:
  * `.aliases` for any aliases we want to use
  * `.apt_packages` to track `apt` packages to install in the distro
  * `.envvars` to set environment variables we want permanently set
  * `.functions` to store Bash functions meant to be invoked from other Bash scripts (not CLI commands)
  * `.language_config` stores any programming language-specific settings
  * `.npm_init` holds global NPM packages to install and configurations to set
  * `.secrets` holds secret data such as tokens and keys that aren't committed to Git
* In the `./ahk` directory, set up any number of AutoHotKey scripts
* In the `./scripts` directory, define functions meant to be invoked as CLI commands
* In the `./vscode` directory, configure VSCode settings and extensions
* Initial `git` config is done in `./install.sh`

## Initial Windows Setup Notes

For when you're truly starting from scratch.

### Downloads

* [Google Chrome](https://www.google.com/search?q=google+chrome+download)
* [Windows Terminal](https://www.google.com/search?q=windows+terminal+download)
* [Visual Studio Code](https://www.google.com/search?q=vs+code+download)
* [AutoHotKey](https://www.autohotkey.com/download/)

### Set Up a WSL Debian Distro

In PowerShell:

``` powershell
    wsl --set-default-version 2
    wsl --install -d Debian
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
