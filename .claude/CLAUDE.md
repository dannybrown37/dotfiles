# LLM Instructions

General defaults live in `~/.claude/CLAUDE.md` (symlinked from `config/CLAUDE.md` in this
repo). Only `dotfiles`-specific instructions belong here.

## Skills

Invoke the relevant skill before writing or debugging code in that language/domain:

- **add-dotfiles-tooling** — Adding a new third-party dependency, tool, install script, or shell command to this repo. Invoke when performing one of those procedures.

## References

Read these references before writing code in the following domains:

- Read directly when writing Bash code: `.claude/references/bash-style.md`
- Read directly when writing TypeScript/JavaScript/Node code: `.claude/references/node-style.md`
- Read directly when writing Python code: `.claude/references/python-style.md`
- Read directly for this repo's (`dotfiles`) layout, conventions, pre-commit hooks, or shell startup performance: `.claude/references/dotfiles-repo.md`

## Model Delegation

- The cheap/fast subagent for mechanical, fully-specified sub-tasks is `quick-task` (`.claude/agents/quick-task.md`, pinned to Haiku).
- Full decision framework: `.claude/references/model-strategy.md`.

## Multi-Agent & Agentic Patterns

- Full patterns and examples: `.claude/references/agentic-patterns.md`.

## Code Review

- A `Stop` hook (`scripts/verify_changes.py`, wired in `.claude/settings.json`) runs `pre-commit` against every changed file before a turn can end, and blocks the turn with the output if it fails. Fix what it reports. Hooks that `git add` are skipped, so formatting is still settled at commit time. `VERIFY_CHANGES_SKIP=1` disables it.
- A `pre-push` git hook prints a reminder to run `/code-review` — it does not block the push or call any AI review itself.
- Full checklist: `.claude/references/code-review-checklist.md`.
- The adversarial red-team pass is the `adversarial-review` subagent — `.claude/agents/adversarial-review.md`. User-triggered only, like `/code-review ultra`. Especially useful for `password-store` operations and other auth/secrets. (`backlog_cli.py` moved to `skill-tree`, which carries the same recommendation in its own `CLAUDE.md`.)

## Documentation

- Architectural changes should be reflected in `.claude/skills/<package>/SKILL.md` (or the package's own `CLAUDE.md`, if it has one) and in `README.md`.
