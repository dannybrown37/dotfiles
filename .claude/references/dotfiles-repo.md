# Dotfiles Repo

This repo contains Debian-focused dotfiles for WSL2 (also works on native Linux). Bootstrap a full dev environment from a clean machine with `make`.

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
├── scripts/        **Non-sourced** scripts — standalone executables, use shebang + set -euo pipefail
├── wsl/            WSL-specific scripts and config
├── .vscode/        VS Code settings and extension list
├── Makefile        Entry point for all install/bootstrap commands
└── .pre-commit-config.yaml
```

## Key Conventions

- **Install scripts** live in `install/`, are self-contained and idempotent, and register themselves as `Makefile` targets by carrying a `## @make <order> <Section> | <description>` header. The filename is the target name (`install/spotify.sh` → `make spotify`). The Makefile derives the target list, `.PHONY`, and `make help` from those headers via `scripts/make-help.sh` — nothing is listed by hand, and a script without a header is not a target. See the `add-dotfiles-tooling` skill.
- **Shell utilities** in `bin/` are **sourced** by `.bashrc`. They can call other functions and use dynamic shell state. No shebang needed.
- **Standalone scripts** in `scripts/` are **non-sourced** executables. Use `#!/usr/bin/env bash` and `set -euo pipefail`.
- **Config files** in `config/` are symlinked to `~` by the bash install script. Edit them here, not in `~`.
- **Secrets** are never committed. Use `password-store` (`pass`) and the `make insert-*`/`pull-*` targets.

## Pre-commit

Managed via `.pre-commit-config.yaml`. Active hooks:

- **shfmt** — shell formatting (4-space indent)
- **shellcheck** — shell linting, a `language: system` local hook against the apt-installed binary (upstream's hook is docker-only). Deliberate disables live in `.shellcheckrc`; keep the repo at zero findings.
- **ruff check + format** — Python linting and formatting
- **embed-command** (git-a-grip) — keeps README install options in sync with `make help` output, which is itself generated from the `## @make` headers
- Standard pre-commit-hooks (EOF fixer, shebangs, JSON/YAML/TOML checks, symlinks)

## Shell Startup Performance

**Lazy-load anything that isn't needed in every shell.** This is the single most important rule for keeping startup fast.

- **Pattern:** wrap the expensive source/eval in a stub function that replaces itself on first call:
  ```bash
  mytool() {
      unset -f mytool
      source /path/to/mytool/init.sh   # or: eval "$(mytool init bash)"
      mytool "$@"
  }
  ```
- **When to lazy-load:** any `eval "$(tool init bash)"`, large sourced files, language version managers (nvm, rbenv, pyenv), or anything that calls an external binary at source time.
- **When to eager-load:** tools used in every session that are already fast (<5ms) — e.g. starship, atuin, zoxide.
- **Glob over find:** for single-level directory listing, use `for dir in path/*/;` (bash builtin, no fork) instead of `find -maxdepth 1`.
- **Guard repeated env setup:** use `[[ -z "${VAR:-}" ]]` before any subprocess that sets an env var, so sourcing the same file twice (e.g. via `.secrets` → work aliases) doesn't repeat expensive calls.
- **Measure:** `hyperfine --warmup 3 'bash -i -c exit'` for startup; uncomment the `_bt_show` lines at the bottom of `.bashrc` for prompt lag.

- Config files use relative symlinks — don't move them without updating the bash install script.
