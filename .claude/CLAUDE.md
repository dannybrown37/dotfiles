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

- **bash** — Shell scripts, `bin/` utilities, bash config. Invoke when writing/debugging shell code.
- **node** — TypeScript/JavaScript, Node.js tooling, ESLint/Prettier config. Invoke when writing/debugging TS/JS.
- **python** — Python code, pytest, ruff/linting. Invoke when writing/debugging Python.
- **dotfiles** — Repo layout, tools, install scripts, config files. Invoke when adding tools, modifying structure, or updating dotfile config.
- **gtd** — TUI and API written in Python for personal GTD implementation. Invoke when working on this package.
- **queue** — Workflow rather than a language: the `.queue` work-item file and its CLI. Invoke when pulling work from the queue. See "Queue System" below.

## Model Delegation

- For a sub-task that's mechanical and fully specified (rename across files, run-and-report, known-pattern lookup, template-driven boilerplate), delegate it to the `quick-task` subagent (`.claude/agents/quick-task.md`, pinned to Haiku) instead of doing it inline.
- Keep judgment calls, multi-file architectural reasoning, and anything the user is actively iterating on in the main session.
- Full decision framework: `.claude/references/model-strategy.md`. This is a difficulty-based delegation heuristic.

## Code Style (General)

- Always use type hints for function parameters (all languages where available).
- Write tests using `test.each` (JS/TS) or `pytest.mark.parametrize` (Python) for DRY reusable test code.
- You have read-only access to git. Don't write with git unless permission is explicitly given.

## Documentation

- When making architectural changes (API framework, storage backend, TUI restructure, major dependencies), update `.claude/skills/<package>/SKILL.md` to match.
  This keeps skill context in sync so future sessions have accurate info. Look for outdated framework names, dependency lists, API signatures, and file structure.

## Security

- Never hardcode secrets, tokens, or credentials. Use environment variables or a secrets manager.
- Never `eval` or dynamically execute user-supplied input.
- Validate and sanitize all external input at system boundaries (API inputs, CLI args, file reads).
- Use parameterized queries; never string-interpolate SQL.
- Pin dependency versions. Audit before adding new dependencies.
- Prefer the principle of least privilege; request minimal permissions, expose minimal surface area.
