.PHONY: help python node golang rust vscode all sync-secrets pull-ahk pull-bash pull-secrets insert-ahk insert-bash insert-secrets

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  bash            Install Bash profile (run before any of the following)"
	@echo "  python          Install Python environment"
	@echo "  node            Install Node.js environment"
	@echo "  golang          Install Go environment"
	@echo "  rust            Install Rust environment"
	@echo "  vscode          Install VS Code extensions"
	@echo "  all             Install all environments"
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

bash:
	@bash -c ". $(bash_bootstrap_script)"

python: bash
	bash -c ". $(root_dir)/install/python.sh"

node: bash
	bash -c ". $(root_dir)/install/node.sh"

golang: bash
	bash -c ". $(root_dir)/install/golang.sh"

rust: bash
	bash -c ". $(root_dir)/install/rust.sh"

vscode: bash
	bash -c ". $(root_dir)/.vscode/vsc_extensions.sh"

all: python node golang rust vscode

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
