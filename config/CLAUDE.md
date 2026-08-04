# LLM Instructions

Global defaults. A project's own `CLAUDE.md` overrides anything here.

## General Approach

- Prefer a TDD approach, with tests written before code.
- We'll be doing Human-in-the-Loop AI-assisted coding.
  - Unless specifically requested to build end to end, you should implement code in discrete, testable steps, then wait for human feedback before continuing.
  - You should always write tests for your code, and provide commands to run them to the user.
  - You should not be adding, committing, or pushing code, the user will do that manually.

## Communication Style

- When reporting information to me, be as concise as possible. Sacrifice grammar for the sake of concision.
- Very few to no comments in generated code unless explicitly requested. Comments should be "why", not "what". i.e., if a comment is needed to explain what the code does, the code should be rewritten to be more readable instead.
- Don't restate questions. Don't apologize. Match my mood.
- Admit when you don't know. Cite sources if uncertain.
- If multiple approaches exist, briefly state which and why to choose, then list alternatives.
- Cite sources. Provide links to visualizations that can't be displayed in a TUI.
- Don't ask bait questions. Only ask if you genuinely need more information.
- Always show the diff as you make changes to my code.

## Model Delegation

- For a sub-task that's mechanical and fully specified (rename across files, run-and-report, known-pattern lookup, template-driven boilerplate), delegate it to a cheap/fast subagent instead of doing it inline.
- Keep judgment calls, multi-file architectural reasoning, and anything the user is actively iterating on in the main session.
- This is a difficulty-based heuristic, not a task-type one.

## Multi-Agent & Agentic Patterns

- Default to inline execution. Delegate to a fresh `Agent` only for genuinely independent work (research, a second opinion, a specialized agent); use `fork` when the sub-task shares current context but its raw tool output (large greps, file dumps) isn't worth keeping around.
- Batch independent tool calls (e.g. `git status`/`diff`/`log` at review start) in one message; keep dependent calls sequential.
- For long-running or async work, prefer `run_in_background` + `Monitor` over sleep-polling, and don't fabricate a fork/background result before its notification actually arrives.

## Code Review

- Never hand a lint error or failing test to the user. If a repo has `pre-commit`, run it against changed files before ending a turn and fix what it reports.
- Before pushing, run `/code-review` (and `/security-review` if the change touches auth, secrets, external input, or dependencies).
- For an active red-team pass (construct a real failing case, not checklist verification) on important/large changes, suggest the user run an adversarial review — never spawn one automatically, it's expensive and user-triggered only.

## CI (GitHub Actions)

- Never write an action version from memory — it's usually a major behind and lands a Node deprecation warning. Check the current major first (`gh api repos/<owner>/<repo>/releases/latest -q .tag_name`) and pin to it.

## Code Style (General)

- Always use type hints for function parameters (all languages where available).
- Write tests using `test.each` (JS/TS) or `pytest.mark.parametrize` (Python) for DRY reusable test code.
- You have read-only access to git. Don't write with git unless permission is explicitly given.

## Documentation

- When making architectural changes (API framework, storage backend, TUI restructure, major dependencies), update the relevant `SKILL.md` / `CLAUDE.md` / `README.md` to match. Look for outdated framework names, dependency lists, API signatures, and file structure.

## Security

- Keep a privacy-first mindset.
- Never hardcode secrets, tokens, or credentials. Use environment variables or a secrets manager.
- Never `eval` or dynamically execute user-supplied input.
- Validate and sanitize all external input at system boundaries (API inputs, CLI args, file reads).
- Use parameterized queries; never string-interpolate SQL.
- Pin dependency versions. Audit before adding new dependencies.
- Prefer the principle of least privilege; request minimal permissions, expose minimal surface area.
