root_dir := justfile_directory()

default:
    @bash "{{root_dir}}/scripts/just-help.sh"

# ── Install scripts ──────────────────────────────────────────────────────────
# Each recipe sources the matching install/ script. The script carries a
# `## @just` header that registers it in `just help` and the README.

apt:
    bash -c ". {{root_dir}}/install/apt.sh"

bash:
    bash -c ". {{root_dir}}/install/bash.sh"

symlinks:
    bash -c ". {{root_dir}}/install/symlinks.sh"

cli-tools:
    bash -c ". {{root_dir}}/install/cli-tools.sh"

chrome:
    bash -c ". {{root_dir}}/install/chrome.sh"

password-store:
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

lazygit:
    bash -c ". {{root_dir}}/install/lazygit.sh"

cartoon:
    bash -c ". {{root_dir}}/install/cartoon.sh"

spotify:
    bash -c ". {{root_dir}}/install/spotify.sh"

terraform:
    bash -c ". {{root_dir}}/install/terraform.sh"

rust-tools:
    bash -c ". {{root_dir}}/install/rust-tools.sh"

gnome:
    bash -c ". {{root_dir}}/install/gnome.sh"

select-nerdfont:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/select-nerdfont.ps1"

wsl-fonts:
    bash -c ". {{root_dir}}/install/wsl-fonts.sh"

komo:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/komo.ps1"

win32yank:
    bash -c ". {{root_dir}}/install/win32yank.sh"

skill-tree:
    bash -c ". {{root_dir}}/install/skill-tree.sh"

gtd:
    bash -c ". {{root_dir}}/install/gtd.sh"

git-a-grip:
    bash -c ". {{root_dir}}/install/git-a-grip.sh"

ghstack:
    bash -c ". {{root_dir}}/install/ghstack.sh"

# ── Composite targets ────────────────────────────────────────────────────────
# Order is important: apt delivers curl/wget/jq/git/gh that everything else
# assumes, and rust delivers the cargo that cli-tools needs for eza.

## @just 10 Start Here | Set up a new machine end to end (every target below it)
bootstrap: apt rust bash cli-tools chrome lazygit password-store

## @just 35 Developer Tools | Install VS Code extensions and settings
vscode:
    bash -c ". {{root_dir}}/.vscode/vsc_extensions.sh"
    bash -c ". {{root_dir}}/.vscode/sync_vsc_settings.sh"

## @just 50 Secrets (requires GPG keys) | Save local secrets to password-store, push to private repo
secrets-save:
    bash -c "{{root_dir}}/scripts/secrets.sh save"

## @just 51 Secrets (requires GPG keys) | Pull private repo, load secrets from password-store to local files
secrets-load:
    bash -c "{{root_dir}}/scripts/secrets.sh load"

## @just 60 My Dev Tooling | Clone and install skill-tree, gtd, and git-a-grip
projects: skill-tree gtd git-a-grip

## @just 70 Verification | Run every prek hook over the whole repo
check:
    prek run --all-files

## @just 71 Verification | Run the scripts/ test suite with coverage
test:
    uv run --with pytest --with pytest-cov pytest --cov=scripts --cov-report=term-missing "{{root_dir}}/scripts/"

## @just 72 Verification | Audit this machine against every dotfiles dependency (read-only)
audit:
    bash "{{root_dir}}/scripts/dotfiles_audit.sh"

## @just 73 Verification | Diagnose a refused git push -- credentials, remotes, transport (read-only)
doctor:
    bash "{{root_dir}}/scripts/git_auth_doctor.sh"
