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

_symlinks:
    bash -c ". {{root_dir}}/install/symlinks.sh"

_python:
    bash "{{root_dir}}/install/extras/python.sh"

_cli-tools:
    bash -c ". {{root_dir}}/install/cli-tools.sh"

_password-store:
    bash -c ". {{root_dir}}/install/password-store.sh"

gnome:
    bash -c ". {{root_dir}}/install/gnome.sh"

_select-nerdfont:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/select-nerdfont.ps1"

_wsl-fonts:
    bash -c ". {{root_dir}}/install/wsl-fonts.sh"

_komo:
    powershell.exe -ExecutionPolicy Bypass -File "{{root_dir}}/install/komo.ps1"

# ── Composite targets ────────────────────────────────────────────────────────
# Order is important: apt delivers curl/wget/jq/git/gh that everything else
# assumes.

## @just 10 Start Here | Full machine setup (apt, bash, cli-tools, python, password-store)
bootstrap: _apt _bash _cli-tools _python _password-store

## @just 11 Start Here | Languages, editors, and opt-in tools, with ✓ for installed
extras *names:
    @bash "{{root_dir}}/scripts/extras.sh" {{names}}

# CI-safe subset: no bash/chrome/password-store (needs GPG), no symlinks (needs $HOME layout)
_ci: _apt _symlinks _cli-tools

## @just 40 Environment-Specific | Link VS Code settings, then pick extensions (✓ = installed)
vscode *names:
    @case "{{names}}" in -h|--help|--list) ;; *) bash "{{root_dir}}/.vscode/sync_vsc_settings.sh" ;; esac
    @bash "{{root_dir}}/.vscode/vsc_extensions.sh" {{names}}

## @just 50 Secrets (requires GPG keys) | Save local secrets to password-store, push to private repo
secrets-save:
    bash -c "{{root_dir}}/scripts/secrets.sh save"

## @just 51 Secrets (requires GPG keys) | Pull private repo, load secrets from password-store to local files
secrets-load:
    bash -c "{{root_dir}}/scripts/secrets.sh load"

## @just 41 Environment-Specific | Windows-side tools (winget, npm, uv, win32yank, net-rescue), with ✓ for installed
windows *names:
    @bash "{{root_dir}}/scripts/windows.sh" {{names}}

## @just 75 Verification | Benchmark interactive shell startup time
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
git-doctor:
    bash "{{root_dir}}/scripts/git_auth_doctor.sh"

## @just 74 Verification | Diagnose a dead network -- link, IP, gateway, internet, DNS (read-only, works offline)
net-doctor:
    @DOTFILES_DIR="{{root_dir}}" ON_WINDOWS="${ON_WINDOWS:-${WSL_DISTRO_NAME:+true}}" bash -c 'source "{{root_dir}}/bin/net.sh"; net-doctor'
