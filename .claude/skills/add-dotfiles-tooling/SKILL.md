---
name: add-dotfiles-tooling
description: "Invoke when adding a new tool, install script, or shell command to this dotfiles repo."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Dotfiles Repo

For repo layout and general conventions, see `.claude/references/dotfiles-repo.md`.

## Adding a New Tool

1. Create `install/<tool>.sh` — idempotent, sources cleanly.
2. Add a Make target in `Makefile` wired to that script.
3. If the tool needs shell aliases/functions, add them to `config/.bash_aliases` or a new file in `bin/`.
4. Update the `.PHONY` list in `Makefile`.
5. Add a passthrough stub to `bin/stubs.sh` so the tool appears in `cmds` with documentation (see below).
6. **Add the tool to `scripts/dotfiles_audit.sh`** — every installed dependency must have a corresponding check so the audit stays the source of truth for what's installed and why.

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
