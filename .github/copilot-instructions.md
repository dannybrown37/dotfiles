# LLM Instructions

## General Approach

- Prefer a TDD approach, with tests written before code.
- We'll be doing Human-in-the-Loop AI-assisted coding.
  - Unless specifically requested to build end to end, you should implement code in discrete, testable steps, then wait for human feedback before continuing.
  - You should always write tests for your code, and provide commands to run them to the user.
  - You should not be adding, committing, or pushing code, the user will do that manually.

## Communication Style

- Very few to no comments in generated code unless explicitly requested. Comments should be "why", not "what". i.e., if a comment is needed to explain what the code does, the code should be rewritten to be more readable.
- Be brief and snappy. Get to the point.
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
- **project-manager** — TUI and API written in Python for personal GTD implementation. Invoke when working on this package.

## Code Style (General)

- Always use type hints for function parameters (all languages where available).
- Write tests using `test.each` (JS/TS) or `pytest.mark.parametrize` (Python) for DRY reusable test code.
- You have read-only access to git. Don't write with git unless permission is explicitly given.

## Queue System

Work items can be queued for Claude to process. The `.queue` file (gitignored) holds items in markdown format:

```markdown
# Queue

## Item Title
Description and details. Can be multi-line.

## Another Item
More details here.
```

**Manual flow:**
1. Add items to `.queue` with `##` headers
2. Run `queue next` to show the first item
3. Discuss what to build in chat
4. I work on it autonomously once approved
5. Completed items move to `.queue-complete` with start/end timestamps

**Automation (late-night):**
- Eventually set up scheduled agent to process queue during off-hours
- Runs autonomously, processes one item per trigger

Use `queue list` to see next items, `queue next` to discuss the first item.

## Documentation

- When making architectural changes (API framework, storage backend, TUI restructure, major dependencies), update `.github/skills/<package>/SKILL.md` to match.
  This keeps skill context in sync so future sessions have accurate info. Look for outdated framework names, dependency lists, API signatures, and file structure.

## Security

- Never hardcode secrets, tokens, or credentials. Use environment variables or a secrets manager.
- Never `eval` or dynamically execute user-supplied input.
- Validate and sanitize all external input at system boundaries (API inputs, CLI args, file reads).
- Use parameterized queries; never string-interpolate SQL.
- Pin dependency versions. Audit before adding new dependencies.
- Prefer the principle of least privilege; request minimal permissions, expose minimal surface area.
