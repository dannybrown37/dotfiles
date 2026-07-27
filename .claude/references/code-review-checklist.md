# Code Review Checklist

Guidelines for reviewing AI-assisted changes in this repo before they land in a PR.

## Which command to run

- **`/code-review`** — default. Reviews the pending diff on the current branch inline.
- **`/security-review`** — run whenever a change touches auth, secrets, external input parsing, or dependencies. See the Security section in `.claude/CLAUDE.md` for the specific things it checks for.
- **`/code-review ultra`** (alias `/ultrareview`) — multi-agent cloud review, user-triggered and billed. Reach for it on larger or higher-risk branches, not routine changes. Needs a git repo; the no-arg form bundles the local branch, `/code-review ultra <PR#>` reviews a GitHub PR.

## What to look for in AI-assisted code specifically

- **Over-engineering** — abstractions, config flags, or error handling for cases that can't happen. Per `.claude/CLAUDE.md`, three similar lines beats a premature abstraction.
- **Comments explaining "what"** — a sign the code itself should be clearer, not that the comment is needed.
- **Hallucinated APIs** — function signatures, flags, or library behavior that look plausible but weren't verified against the actual source/docs.
- **Untested edge cases** — happy-path tests only, especially around empty input, boundary values, and error branches.
- **Silent scope creep** — changes beyond what was asked (renames, reformatting, unrelated refactors bundled into the same diff).

## Performance checklist

- No obvious N+1 patterns (loops doing DB/API/subprocess calls that could be batched).
- No unnecessary full-file reads/writes where a targeted edit would do.
- Long-running or blocking operations (network calls, subprocess, large file I/O) aren't on a hot path without justification.

## Security checklist

Mirrors the Security section of `.claude/CLAUDE.md` — check the diff against each:

- No hardcoded secrets, tokens, or credentials.
- No `eval`/dynamic execution of user-supplied input.
- External input (API params, CLI args, file reads) validated at the boundary.
- SQL is parameterized, never string-interpolated.
- New dependencies are pinned and were actually audited, not just added.
- Principle of least privilege — minimal permissions/scope requested.
