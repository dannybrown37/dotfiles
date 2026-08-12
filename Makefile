root_dir := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

# Every target below is derived from the `## @make` header its script carries --
# see scripts/make-help.sh. Adding that one header registers the target, adds it
# to .PHONY, and puts it in `make help` (and so in the README, via the
# embed-command hook). There is no list to keep in sync.
#
# Static pattern rules, not implicit ones: GNU Make skips implicit-rule search
# for .PHONY targets, and `nvim` has to stay phony because nvim/ is a real
# directory.

install_scripts := $(shell grep -ls '^## @make ' $(root_dir)/install/*.sh)
install_targets := $(patsubst $(root_dir)/install/%.sh,%,$(install_scripts))

windows_scripts := $(shell grep -ls '^## @make ' $(root_dir)/install/*.ps1)
windows_targets := $(patsubst $(root_dir)/install/%.ps1,%,$(windows_scripts))

.PHONY: help $(install_targets) $(windows_targets) bootstrap vscode secrets-save secrets-load \
	projects check test audit doctor

help:
	@bash $(root_dir)/scripts/make-help.sh

$(install_targets): %: $(root_dir)/install/%.sh
	bash -c ". $<"

$(windows_targets): %: $(root_dir)/install/%.ps1
	powershell.exe -ExecutionPolicy Bypass -File "$<"

# A composite, not a script -- it was install/bash.sh, which named about two
# lines of what it did. Each phase is now separately re-runnable.
#
# Order is load-bearing: apt delivers curl/wget/jq/git/gh that everything else
# assumes, and rust delivers the cargo that cli-tools needs for eza. Make only
# guarantees that order serially, so this is one target you should not `make -j`.
#
# The `## @make` header has to sit directly above the target line -- a comment
# in between and makefile_headers() in scripts/make-help.sh drops it.
## @make 10 Start Here | Set up a new machine end to end (every target below it)
bootstrap: apt rust bash cli-tools chrome lazygit password-store

## @make 35 Developer Tools | Install VS Code extensions and settings
vscode:
	bash -c ". $(root_dir)/.vscode/vsc_extensions.sh"
	bash -c ". $(root_dir)/.vscode/sync_vsc_settings.sh"

## @make 50 Secrets (requires GPG keys) | Save local secrets to password-store, push to private repo
secrets-save:
	bash -c "$(root_dir)/scripts/secrets.sh save"

## @make 51 Secrets (requires GPG keys) | Pull private repo, load secrets from password-store to local files
secrets-load:
	bash -c "$(root_dir)/scripts/secrets.sh load"

## @make 60 My Projects | Clone and install skill-tree, gtd, and ccgarden
projects: skill-tree gtd ccgarden

## @make 70 Verification | Run every pre-commit hook over the whole repo
check:
	pre-commit run --all-files --show-diff-on-failure

## @make 71 Verification | Run the scripts/ test suite with coverage
test:
	uv run --with pytest --with pytest-cov pytest --cov=scripts --cov-report=term-missing $(root_dir)/scripts/

## @make 72 Verification | Audit this machine against every dotfiles dependency (read-only)
audit:
	bash $(root_dir)/scripts/dotfiles_audit.sh

## @make 73 Verification | Diagnose a refused git push -- credentials, remotes, transport (read-only)
doctor:
	bash $(root_dir)/scripts/git_auth_doctor.sh
