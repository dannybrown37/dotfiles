# Overview

dotfiles for a WSL2-based Debian setup.

## Clone and Run

``` bash
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles
source install.sh
```

## Commands Available

* ahk: run all autohotkey scripts in ahk/ directory from WSL in Windows environment
* ahk kill: kill all running autohotkey processes
* ahk open: open ahk/dev_shortcuts.ahk in VSCode
* ahk open_secrets: open ahk/secrets.ahk in VSCode
* cdp: move immediately to any directory in ~/projects (with tab autocomplete)
* cpw: copy files from WSL to Windows easily, defaults to Downloads folder (with tab autocomplete)
* cht: curl cht.sh for commonly used tools/languages. Add new ones as needed in cht/.cht_sh_index
* gg/google: google something from the terminal, no quotes needed, pops open a web browser
* mk: mkdir and cd into it
* pr: open pull request from current branch into default branch. GitHub and Bitbucket supported

## Other Config Options

* In the bash/ directory, configure bash profile in various files
* In the vscode/ directory, configure VSCode settings and extensions

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
