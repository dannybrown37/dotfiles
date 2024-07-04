.PHONY: help python node golang rust vscode all

help:
	@echo "Usage: make [target]"
	@echo "Targets:"
	@echo "  bash           Install Bash profile"
	@echo "  python         Install Python environment"
	@echo "  node           Install Node.js environment"
	@echo "  golang         Install Go environment"
	@echo "  rust           Install Rust environment"
	@echo "  vscode         Install VS Code extensions"
	@echo "  all            Install all environments"
	@echo "  help           Show this help message"

root_dir := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

bash:
	bash -c ". $(root_dir)/install/bash.sh"

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

secrets-in:
	bash -c "pass insert -m bash/secrets < $(root_dir)/config/.secrets"
	bash -c "pass insert -m ahk/secrets < $(root_dir)/ahk/secrets.ahk"

secrets-out:
	bash -c "pass ahk/secrets > $(root_dir)/ahk/secrets.ahk"
	bash -c "pass bash/secrets > $(root_dir)/config/.secrets"
