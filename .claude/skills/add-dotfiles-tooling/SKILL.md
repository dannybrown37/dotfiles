---
name: add-dotfiles-tooling
description: "Invoke when adding a new tool, install script, or shell command to this dotfiles repo."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Dotfiles Repo

For repo layout and general conventions, see `.claude/references/dotfiles-repo.md`.

## Adding a New Tool

1. Create `install/<tool>.sh` — idempotent, sources cleanly. Copy `install/lazygit.sh`
   as the reference implementation: version check, skip-if-current, `mktemp -d` + `trap`
   cleanup, install, confirm, optional config symlink.
2. Add a Make target in `Makefile` wired to that script.
3. Add a `@echo` line for it under the right heading in the `help` target — this is what
   `sync-readme-make.sh` copies into the README, so a target without one is invisible.
4. If the tool needs shell aliases/functions, add them to `config/.bash_aliases` or a new file in `bin/`.
5. Update the `.PHONY` list in `Makefile`.
6. Add a passthrough stub to `bin/stubs.sh` so the tool appears in `cmds` with documentation (see below).
7. **Add the tool to `scripts/dotfiles_audit.sh`** — every installed dependency must have a corresponding check so the audit stays the source of truth for what's installed and why.
8. **Verify the wiring** — don't eyeball the list above, run it:

   ```bash
   ./scripts/check-tool-wiring.sh <tool>
   ```

## Verifying Wiring

`scripts/check-tool-wiring.sh <tool>` checks every step above and exits non-zero on the
first thing you missed. It detects how the tool is installed and only demands the wiring
that applies:

| Mode | Detected by | Needs a Make target? |
|---|---|---|
| `dedicated` | `install/<tool>.sh` exists | yes |
| `apt` | listed in `install/apt_packages.sh` | no |
| `bundled` | another install script builds it (eza via `install/bash.sh`) | no |

All three still need a `bin/stubs.sh` stub and audit coverage. apt packages get audit
coverage for free — `dotfiles_audit.sh` iterates `apt_packages.sh`.

Two flags for the cases that would otherwise false-alarm:

- `--apt-package <pkg>` when the package name differs from the command (`fd-find` → `fd`,
  `ripgrep` → `rg`). Without it the tool looks uninstalled.
- `--no-stub` for language runtimes (`python`, `node`, `rust`) and action-only targets
  (`secrets-save`, `wsl-fonts`) that deliberately have no passthrough stub.

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

## Tools

- `scripts/check-tool-wiring.sh` — mechanical verification of every wiring step above.
  Run it before declaring a tool done.

There is deliberately no install-script template. `install/` ranges from 3 lines
(`deno.sh`, a `curl | sh`) to 252 (`bash.sh`), and the install method differs per tool —
apt, cargo, GitHub release, language version manager. Copy whichever existing script
matches the method you need; `lazygit.sh` is the closest thing to a canonical
GitHub-release example.
