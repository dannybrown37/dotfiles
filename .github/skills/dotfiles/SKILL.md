---
name: dotfiles
description: "Invoke when the user is asking about the repo layout, adding new tools or commands, modifying install scripts, or working with dotfile configuration files."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Dotfiles Repo

You're a cracked software consultant who is helping me maintain top productivity by helping to keep tools useful and at-hand.

This repo contains Debian-focused dotfiles for WSL2 (also works on native Linux and Git Bash). Bootstrap a full dev environment from a clean machine with `make`.

## Repo Layout

```
├── ahk/            AutoHotKey scripts for Windows (hotstrings, secrets)
├── aws/            AWS helper scripts
├── bin/            **Sourced** scripts — loaded into the current shell session, no shebang
├── config/         Dotfiles symlinked to ~ (.bashrc, .gitconfig, .tmux.conf, .ruff.toml, etc.)
│   └── .secrets    Untracked secrets file managed via password-store
├── install/        Per-tool bootstrap scripts invoked by Make targets
├── nvim/           Neovim config (lazy.nvim, Lua)
├── pass/           password-store related config
├── project_manager/ Python package (uv, pytest, ruff) for project management
├── scripts/        **Non-sourced** scripts — standalone executables, use shebang + set -euo pipefail
├── wsl/            WSL-specific scripts and config
├── .vscode/        VS Code settings and extension list
├── Makefile        Entry point for all install/bootstrap commands
└── .pre-commit-config.yaml
```

## Key Conventions

- **Install scripts** live in `install/` and are wired up via `Makefile` targets. Each script is self-contained and idempotent.
- **Shell utilities** in `bin/` are **sourced** by `.bashrc`. They can call other functions and use dynamic shell state. No shebang needed.
- **Standalone scripts** in `scripts/` are **non-sourced** executables. Use `#!/usr/bin/env bash` and `set -euo pipefail`.
- **Config files** in `config/` are symlinked to `~` by the bash install script. Edit them here, not in `~`.
- **Secrets** are never committed. Use `password-store` (`pass`) and the `make insert-*`/`pull-*` targets.

## Adding a New Tool

1. Create `install/<tool>.sh` — idempotent, sources cleanly.
2. Add a Make target in `Makefile` wired to that script.
3. If the tool needs shell aliases/functions, add them to `config/.bash_aliases` or a new file in `bin/`.
4. Update the `.PHONY` list in `Makefile`.
5. Add a passthrough stub to `bin/stubs.sh` so the tool appears in `cmds` with documentation (see below).

## Third-Party Tool Stubs

All third-party CLI tools must have a passthrough stub in `bin/stubs.sh`. This is the canonical way to document installed tools so they show up in `cmds`. Do not use aliases for this purpose.

```bash
# Pattern: one line per tool, inline @doc comment
mytool() { command mytool "$@"; }  # @doc Brief description | mytool <usage>
```

- Use `command mytool` (not just `mytool`) to avoid infinite recursion.
- If the installed binary name differs from the logical name (e.g. `fdfind` → `fd`), handle it in the stub.
- Keep descriptions short: what it does, and the most common invocation after `|`.

## Adding a New Shell Command

- If the command needs to call other functions or use dynamic shell state → add to `bin/` (sourced, no shebang).
- If it's a standalone utility that runs in a subshell → add to `scripts/` (non-sourced, executable, with shebang).
- Scripts in `bin/` are automatically available after sourcing `.bashrc`.

## Pre-commit

Managed via `.pre-commit-config.yaml`. Active hooks:

- **shfmt** — shell formatting (4-space indent)
- **ruff check + format** — Python linting and formatting
- **sync-readme-make** — keeps README install options in sync with `make help` output
- Standard pre-commit-hooks (EOF fixer, shebangs, JSON/YAML/TOML checks, symlinks)

## Gotchas

- Config files use relative symlinks — don't move them without updating the bash install script.
- The `project_manager/` directory is a standalone Python package with its own `pyproject.toml` and venv.
