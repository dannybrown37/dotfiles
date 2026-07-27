# LLM Instructions

## General Approach

- Prefer a TDD approach, with tests written before code.
- We'll be doing Human-in-the-Loop AI-assisted coding.
  - Unless specifically requested to build end to end, you should implement code in discrete, testable steps, then wait for human feedback before continuing.
  - You should always write tests for your code, and provide commands to run them to the user.
  - You should not be adding, committing, or pushing code, the user will do that manually.

## Communication Style

- Very few to no comments in generated code unless explicitly requested. Comments should be "why", not "what". i.e., if a comment is needed to explain what the code does, the code should be rewritten to be more readable.
- When reporting information to me, be as concise as possible. Sacrifice grammar for the sake of concision.
- Don't restate questions. Don't apologize. Match my mood.
- Admit when you don't know. Cite sources if uncertain.
- If multiple approaches exist, briefly state which and why to choose, then list alternatives. Cite sources.
- Don't ask bait questions. Only ask if you genuinely need more information.
- Always show the diff as you make changes to my code.

## Skills

Invoke the relevant skill before writing or debugging code in that language/domain:

- **add-dotfiles-tooling** — Adding a new third-party dependency, tool, install script, or shell command to this repo. Invoke when performing one of those procedures.
- **queue** — Workflow rather than a language: the `.queue` work-item file and its CLI. Invoke when pulling work from the queue. See "Queue System" below.

## References

Read these references before writing code in the following domains:

- Read directly when writing Bash code: `.claude/references/bash-style.md`
- Read directly when writing TypeScript/JavaScript/Node code: `.claude/references/node-style.md`
- Read directly when writing Python code: `.claude/references/python-style.md`
- Read directly for this repo's (`dotfiles`) layout, conventions, pre-commit hooks, or shell startup performance: `.claude/references/dotfiles-repo.md`
- `gtd/` is a standalone package with its own `gtd/CLAUDE.md` — no skill needed, it loads automatically when working in that directory.

## Model Delegation

- For a sub-task that's mechanical and fully specified (rename across files, run-and-report, known-pattern lookup, template-driven boilerplate), delegate it to the `quick-task` subagent (`.claude/agents/quick-task.md`, pinned to Haiku) instead of doing it inline.
- Keep judgment calls, multi-file architectural reasoning, and anything the user is actively iterating on in the main session.
- Full decision framework: `.claude/references/model-strategy.md`. This is a difficulty-based delegation heuristic.

## Multi-Agent & Agentic Patterns

- Default to inline execution. Delegate to a fresh `Agent` only for genuinely independent work (research, a second opinion, a specialized agent like `quick-task`/`Explore`); use `fork` when the sub-task shares current context but its raw tool output (large greps, file dumps) isn't worth keeping around.
- Batch independent tool calls (e.g. `git status`/`diff`/`log` at review start) in one message; keep dependent calls sequential.
- For long-running or async work, prefer `run_in_background` + `Monitor` over sleep-polling, and don't fabricate a fork/background result before its notification actually arrives.
- Full patterns and examples: `.claude/references/agentic-patterns.md`.

## Code Review

- Before pushing, run `/code-review` (and `/security-review` if the change touches auth, secrets, external input, or dependencies).
- A `pre-push` git hook prints a reminder of this — it does not block the push or call any AI review itself.
- Full checklist: `.claude/references/code-review-checklist.md`.

## Code Style (General)

- Always use type hints for function parameters (all languages where available).
- Write tests using `test.each` (JS/TS) or `pytest.mark.parametrize` (Python) for DRY reusable test code.
- You have read-only access to git. Don't write with git unless permission is explicitly given.

## Documentation

- When making architectural changes (API framework, storage backend, TUI restructure, major dependencies), update `.claude/skills/<package>/SKILL.md` (or the package's own `CLAUDE.md`, e.g. `gtd/CLAUDE.md`) to match.
  This keeps skill/package context in sync so future sessions have accurate info. Look for outdated framework names, dependency lists, API signatures, and file structure.
- `.claude/skills/<name>/` are mirrored into `.github/skills/<name>` via symlink (so Copilot sees the same skills). When adding or removing a skill directory, add or remove the matching symlink in `.github/skills/` too.

## Security

- Keep a privacy-first mindset
- Never hardcode secrets, tokens, or credentials. Use environment variables or a secrets manager.
- Never `eval` or dynamically execute user-supplied input.
- Validate and sanitize all external input at system boundaries (API inputs, CLI args, file reads).
- Use parameterized queries; never string-interpolate SQL.
- Pin dependency versions. Audit before adding new dependencies.
- Prefer the principle of least privilege; request minimal permissions, expose minimal surface area.
