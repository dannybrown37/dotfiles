root_dir := justfile_directory()

default:
    @bash "{{root_dir}}/scripts/just-help.sh"

# ── Install scripts ──────────────────────────────────────────────────────────
# Each recipe sources the matching install/ script. The script carries a
# `## @just` header that registers it in `just help` and the README.

_apt:
    bash -c ". {{root_dir}}/install/apt.sh"

_bash:
    bash -c ". {{root_dir}}/install/bash.sh"

symlinks:
    bash -c ". {{root_dir}}/install/symlinks.sh"

_cli-tools:
    bash -c ". {{root_dir}}/install/cli-tools.sh"

_chrome:
    bash -c ". {{root_dir}}/install/chrome.sh"

_password-store:
    bash -c ". {{root_dir}}/install/password-store.sh"

python:
    bash -c ". {{root_dir}}/install/python.sh"

node:
    bash -c ". {{root_dir}}/install/node.sh"

deno:
    bash -c ". {{root_dir}}/install/deno.sh"

golang:
    bash -c ". {{root_dir}}/install/golang.sh"

rust:
    bash -c ". {{root_dir}}/install/rust.sh"

nvim:
    bash -c ". {{root_dir}}/install/nvim.sh"

_lazygit:
    bash -c ". {{root_dir}}/install/lazygit.sh"

_cartoon:
    bash -c ". {{root_dir}}/install/cartoon.sh"

spotify:
    bash -c ". {{root_dir}}/install/spotify.sh"

terraform:
    bash -c ". {{root_dir}}/install/terraform.sh"

rust-tools:
    bash -c ". {{root_dir}}/install/rust-tools.sh"

gnome:
    bash -c ". {{root_dir}}/install/gnome.sh"

_select-nerdfont:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/select-nerdfont.ps1"

_wsl-fonts:
    bash -c ". {{root_dir}}/install/wsl-fonts.sh"

_komo:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/komo.ps1"

_win-dev:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/win-dev.ps1"

_win32yank:
    bash -c ". {{root_dir}}/install/win32yank.sh"

_skill-tree:
    bash -c ". {{root_dir}}/install/skill-tree.sh"

_gtd:
    bash -c ". {{root_dir}}/install/gtd.sh"

_git-a-grip:
    bash -c ". {{root_dir}}/install/git-a-grip.sh"

## @just 30 Developer Tools | Install git workflow tools (lazygit, ghstack, git-absorb, git-branchless, gh-dash)
git-tools: _lazygit
    bash -c ". {{root_dir}}/install/ghstack.sh"
    bash -c ". {{root_dir}}/install/git-absorb.sh"
    bash -c ". {{root_dir}}/install/git-branchless.sh"
    bash -c ". {{root_dir}}/install/gh-dash.sh"

# ── Composite targets ────────────────────────────────────────────────────────
# Order is important: apt delivers curl/wget/jq/git/gh that everything else
# assumes, and rust delivers the cargo that cli-tools needs for eza.

## @just 10 Start Here | Full machine setup (apt, rust, bash, cli-tools, chrome, git-tools, password-store)
bootstrap: _apt rust _bash _cli-tools _chrome git-tools _password-store

## @just 32 Developer Tools | Install VS Code extensions and settings
vscode:
    bash -c ". {{root_dir}}/.vscode/vsc_extensions.sh"
    bash -c ". {{root_dir}}/.vscode/sync_vsc_settings.sh"

## @just 33 Developer Tools | Install AI coding tools (cartoon)
ai: _cartoon

## @just 50 Secrets (requires GPG keys) | Save local secrets to password-store, push to private repo
secrets-save:
    bash -c "{{root_dir}}/scripts/secrets.sh save"

## @just 51 Secrets (requires GPG keys) | Pull private repo, load secrets from password-store to local files
secrets-load:
    bash -c "{{root_dir}}/scripts/secrets.sh load"

## @just 40 Environment-Specific | Install Windows-side tooling (win-dev, win32yank, komo)
windows: _win-dev _win32yank _komo

## @just 60 My Dev Tooling | Clone and install skill-tree, gtd, and git-a-grip
my-dev-tools: _skill-tree _gtd _git-a-grip

## @just 74 Verification | Benchmark interactive shell startup time (10 runs default, pass N to override)
bench-shell runs='10':
    bash "{{root_dir}}/scripts/bench-shell.sh" "{{runs}}"

## @just 70 Verification | Run every prek hook over the whole repo
check:
    prek run --all-files

## @just 71 Verification | Run all tests (pytest + shell syntax check)
test:
    uv run --with pytest --with pytest-cov --with pytest-xdist pytest --cov=scripts --cov-report=term-missing "{{root_dir}}/scripts/"
    bash "{{root_dir}}/scripts/test_shell_syntax.sh"

## @just 72 Verification | Audit this machine against every dotfiles dependency (read-only)
audit:
    bash "{{root_dir}}/scripts/dotfiles_audit.sh"

## @just 73 Verification | Diagnose a refused git push -- credentials, remotes, transport (read-only)
doctor:
    bash "{{root_dir}}/scripts/git_auth_doctor.sh"
