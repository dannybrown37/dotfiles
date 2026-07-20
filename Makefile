.PHONY: help python deno node golang rust vscode all gnome windows komo wsl-fonts secrets-save secrets-load lazygit

help:
	@echo "Usage: make [option]"
	@echo ""
	@echo "Bootstrap scripts:"
	@echo "  bash            Install Bash profile (tmux, apt packages, etc.)"
	@echo "  python          Install Python environment (uv, select uv tools)"
	@echo "  node            Install Node.js environment (n, Node 22, select global packages)"
	@echo "  deno            Install Deno 2"
	@echo "  golang          Install Go environment (latest Golang version)"
	@echo "  rust            Install Rust environment (latest Rust version, select global packages)"
	@echo "  nvim            Install Neovim"
	@echo "  lazygit         Install lazygit TUI git client"
	@echo "  vscode          Install VS Code extensions and settings"
	@echo "  all             Install all of the above"
	@echo "  gnome           Install Gnome extensions"
	@echo "  windows         Install Windows extensions (NerdFonts and Komorebi)"
	@echo "  wsl-fonts       Install Starship + JetBrainsMono Nerd Font (WSL to Windows)"
	@echo "  komo            Reset komorebi (useful for after configuration changes)"
	@echo ""
	@echo "These commands require GPG keys and secrets:"
	@echo "  secrets-save    Save local secrets to password-store"
	@echo "  secrets-load    Load secrets from password-store to local files"


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

lazygit:
	bash -c ". $(root_dir)/install/lazygit.sh"

vscode:
	bash -c ". $(root_dir)/.vscode/vsc_extensions.sh"
	bash -c ". $(root_dir)/.vscode/sync_vsc_settings.sh"

all: bash python deno node golang rust nvim lazygit vscode

gnome:
	bash -c ". $(root_dir)/install/gnome.sh"

windows:
	powershell.exe -ExecutionPolicy Bypass -File "$(root_dir)/install/windows.ps1"

wsl-fonts:
	bash -c ". $(root_dir)/install/wsl_fonts.sh"

komo:
	powershell.exe -ExecutionPolicy Bypass -File "$(root_dir)/install/reset_komo.ps1"

# pass secret store

secrets-save:
	bash -c "pass insert -m ahk/secrets < $(root_dir)/ahk/secrets.ahk"
	bash -c "pass insert -m bash/secrets < $(root_dir)/config/.secrets"
	bash -c "pass insert -m project_manager/env < $(root_dir)/project_manager/.env"

secrets-load:
	bash -c "mv $(root_dir)/ahk/secrets.ahk $(root_dir)/ahk/secrets.ahk.bak"
	bash -c "pass ahk/secrets > $(root_dir)/ahk/secrets.ahk"
	bash -c "mv $(root_dir)/config/.secrets $(root_dir)/config/.secrets.bak"
	bash -c "pass bash/secrets > $(root_dir)/config/.secrets"
	bash -c "mv $(root_dir)/project_manager/.env $(root_dir)/project_manager/.env.bak"
	bash -c "pass project_manager/env > $(root_dir)/project_manager/.env"
