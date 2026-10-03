# Dotfiles Repo

This repo contains Debian-focused dotfiles for WSL2 (also works on native Linux). Bootstrap a full dev environment from a clean machine with `just bootstrap`.

## Repo Layout

```
├── ahk/            AutoHotKey scripts for Windows (hotstrings, secrets)
├── aws/            AWS helper scripts
├── bin/            **Sourced** scripts — loaded into the current shell session, no shebang
├── config/         Dotfiles symlinked to ~ (.bashrc, .gitconfig, .tmux.conf, .ruff.toml, etc.)
│   └── .secrets    Untracked secrets file managed via password-store
├── docs/           Long-form documentation (secrets, GitHub accounts) linked from README
├── githooks/       Tracked git hooks (core.hooksPath) -- pre-commit, commit-msg and pre-push forward to prek
├── install/        Per-tool bootstrap scripts invoked by justfile recipes
├── nvim/           Neovim config (lazy.nvim, Lua)
├── references/     Personal reference material (mental models, media, vim notes)
├── scripts/        **Non-sourced** scripts — standalone executables, use shebang + set -euo pipefail
├── windows/        PowerShell network-rescue verbs + offline cheat sheet, copied to C: by `just windows net-rescue`
├── wsl/            WSL-specific scripts and config
├── .vscode/        VS Code settings and extension list
├── justfile        Entry point for all install/bootstrap commands
└── .pre-commit-config.yaml
```

## Key Conventions

- **Install scripts** live in `install/`, are self-contained and idempotent, and register themselves as recipes by carrying a `## @just <order> <Section> | <description>` header. The filename is the recipe name (`install/gnome.sh` → `just gnome`). The help script `scripts/just-help.sh` renders the target list from those headers — nothing is listed by hand, and a script without a header is not discoverable. Opt-in tools live in `install/extras/` with a `## @extra <binary> | <desc>` header instead; `just extras` (`scripts/extras.sh`) shows them in an fzf menu with ✓ for installed, so it doubles as an at-a-glance audit. Language runtimes are extras too; a `## @runtime` line makes them install before the rest. Names are colored by source (`## @mine` for my own projects, runtime, cargo, gh, apt). See the `add-dotfiles-tooling` skill.
- **Shell utilities** in `bin/` are **sourced** by `.bashrc`. They can call other functions and use dynamic shell state. No shebang needed.
- **Standalone scripts** in `scripts/` are **non-sourced** executables. Use `#!/usr/bin/env bash` and `set -euo pipefail`.
- **Config files** in `config/` are symlinked to `~` by `install/symlinks.sh` (run by `just bootstrap`). Edit them here, not in `~`.
- **Secrets** are never committed. Use `password-store` (`pass`) and the `just secrets-save`/`secrets-load` recipes (see `docs/secrets.md`).

## Prek

Managed via `.pre-commit-config.yaml` (prek reads this natively). Active hooks:

- **shfmt** — shell formatting (4-space indent)
- **shellcheck** — shell linting, a `language: system` local hook against the apt-installed binary (upstream's hook is docker-only). Deliberate disables live in `.shellcheckrc`; keep the repo at zero findings.
- **ruff check + format** — Python linting and formatting
- **commitizen-early** (git-a-grip) + **commitizen** — conventional commit messages. `-early` rejects a bad `-m` message before the slow hooks run; the commit-msg stage (via `githooks/commit-msg`) catches editor/rebase messages. `pr-title.yml` applies the same hook to PR titles, which become the squash-merge commit on `main`.
- **pytest** (git-a-grip) — pre-push stage only (via `githooks/pre-push`), since the suite is slow and CI's `test` job gates merges. The Claude `Stop` hook runs pre-commit hooks, so it skips this too: run `uv run pytest scripts/` after touching `scripts/`.
- **actionlint** — workflow linting (correctness; zizmor covers security). Upstream golang hook, so prek builds it once and caches it
- **typos** — spell check, report-only (no auto-rewrite). Exceptions live in `_typos.toml`
- **embed-command** (git-a-grip) — keeps README install options in sync with `just` help output, which is itself generated from the `## @just` headers
- Standard pre-commit-hooks repo (EOF fixer, shebangs, JSON/YAML/TOML checks, symlinks)

## CI

- `.github/workflows/ci.yml` runs `lint`, `test` and `bootstrap`, all required checks on `main`.
- `bootstrap` also fails if `scripts/bench-shell.sh` measures a median shell startup over `SHELL_BUDGET_MS` (250ms).
- `extras.yml` installs every non-cargo extra in a `debian:bookworm` container, weekly and on PRs touching `install/extras/`, `release_binary.sh` or `versions.sh`. Not a required check.
- `bootstrap` (~5 min cold) runs only when `scripts/ci_needs_bootstrap.sh` sees a bootstrap path change (`install/`, `ci.yml`, or a file added/removed/renamed under `config/` -- edits there cannot break a symlink), plus a weekly cold run and on `workflow_dispatch`. Otherwise it is skipped, which counts as passing. The `justfile` is left out on purpose: lint's `embed-command` hook already runs `just`, and the weekly run catches a broken `_ci` recipe. Add a path there if a new file changes what `just _ci` does.

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
