# LLM Instructions

General defaults live in `~/.claude/CLAUDE.md` (symlinked from `config/CLAUDE.md` in this
repo). Only `dotfiles`-specific instructions belong here.

## Skills

Invoke the relevant skill before writing or debugging code in that language/domain:

- **add-dotfiles-tooling** — Adding a new third-party dependency, tool, install script, or shell command to this repo. Invoke when performing one of those procedures.
- **skill-tree:bash-style** — Invoke before writing Bash code
- **skill-tree:python-style** — Invoke before writing Python code
- **skill-tree:node-style** — Invoke before writing Node/TS/JS code

## References

- Read directly for this repo's (`dotfiles`) layout, conventions, prek hooks, or shell startup performance: `.claude/references/dotfiles-repo.md`

## Code Review

- A `Stop` hook (`scripts/verify_changes.py`, wired in `.claude/settings.json`) runs `prek` against every changed file before a turn can end, and blocks the turn with the output if it fails. Fix what it reports. Hooks that `git add` are skipped, so formatting is still settled at commit time. `VERIFY_CHANGES_SKIP=1` disables it.
- `/code-review` (and `/security-review` for auth/secrets/external input/dependency changes) is opt-in — run it yourself before pushing. Nothing prompts for it.
- The adversarial red-team pass is `skill-tree:adversarial-review`. User-triggered only, like `/code-review ultra`. Especially useful for `password-store` operations and other auth/secrets.

## Documentation

- Architectural changes should be reflected in `.claude/skills/<package>/SKILL.md` (or the package's own `CLAUDE.md`, if it has one) and in `README.md`.
