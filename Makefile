.PHONY: help python deno node golang rust vscode all gnome windows resestkomo sync-secrets pull-ahk pull-bash pull-secrets insert-ahk insert-bash insert-secrets

help:
	@echo "Usage: make [option]"
	@echo ""
	@echo "Bootstrap scripts:"
	@echo "  bash            Install Bash profile (tmux, apt packages, etc.)"
	@echo "  python          Install Python environment (uv, select uv tools)"
	@echo "  node            Install Node.js environment (nvm, Node 18, select global packages)"
	@echo "  deno            Install Deno 2"
	@echo "  golang          Install Go environment (latest Golang version)"
	@echo "  rust            Install Rust environment (latest Rust version, select global packages)"
	@echo "  nvim            Install Neovim"
	@echo "  vscode          Install VS Code extensions and settings"
	@echo "  all             Install all of the above"
	@echo "  gnome           Install Gnome extensions"
	@echo "  windows         Install Windows extensions (NerdFonts and Komorebi)"
	@echo "  komo       Reset komorebi (useful for after configuration changes)"
	@echo ""
	@echo "These commands require GPG keys and secrets:"
	@echo "  sync-secrets    Attempt to sync local secrets and password-store"
	@echo "  insert-ahk      Push local ahk secrets to password-store"
	@echo "  insert-bash     Push local bash secrets to password-store"
	@echo "  insert-secrets  Write all secrets files to password-store"
	@echo "  pull-ahk        Pull ahk secrets from password-store to local files"
	@echo "  pull-bash       Pull bash secrets from password-store to local files"
	@echo "  pull-secrets    Read all secrets files from password-store"


root_dir := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

ifeq ($(MSYSTEM), MINGW64)
    bash_bootstrap_script := $(root_dir)/install/git_bash.sh
else
    bash_bootstrap_script := $(root_dir)/install/bash.sh
endif

# installs

bash:
	@bash -c ". $(bash_bootstrap_script)"

python:
	bash -c ". $(root_dir)/install/python.sh"

deno:
	bash -c ". $(root_dir)/install/deno.sh"

node:
	bash -c ". $(root_dir)/install/node.sh"

golang:
	bash -c ". $(root_dir)/install/golang.sh"

rust:
	bash -c ". $(root_dir)/install/rust.sh"

nvim:
	bash -c ". $(root_dir)/install/nvim.sh"

vscode:
	bash -c ". $(root_dir)/.vscode/vsc_extensions.sh"

all: bash python deno node golang rust nvim vscode

gnome:
	bash -c ". $(root_dir)/install/gnome.sh"

windows:
	powershell.exe -ExecutionPolicy Bypass -File "$(root_dir)/install/windows.ps1"

komo:
	powershell.exe -ExecutionPolicy Bypass -File "$(root_dir)/install/reset_komo.ps1"

# pass secret store

sync-secrets:
	bash -c ". $(root_dir)/bin/sync-secrets.sh && sync-secrets"

pull-ahk:
	bash -c "mv $(root_dir)/ahk/secrets.ahk $(root_dir)/ahk/secrets.ahk.bak"
	bash -c "pass ahk/secrets > $(root_dir)/ahk/secrets.ahk"

pull-bash:
	bash -c "mv $(root_dir)/config/.secrets $(root_dir)/config/.secrets.bak"
	bash -c "pass bash/secrets > $(root_dir)/config/.secrets"

pull-secrets: pull-ahk pull-bash

insert-ahk:
	bash -c "pass insert -m ahk/secrets < $(root_dir)/ahk/secrets.ahk"

insert-bash:
	bash -c "pass insert -m bash/secrets < $(root_dir)/config/.secrets"

insert-secrets: insert-ahk insert-bash
