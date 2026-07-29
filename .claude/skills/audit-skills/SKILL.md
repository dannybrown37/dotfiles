---
name: audit-skills
description: "Invoke when reviewing this repo's .claude/skills or .claude/references for structural drift — e.g. \"review my skills\", \"audit skills/references\", \"is this a skill or a reference\", \"are my skills bloated/stale\", or after adding/renaming a skill."
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash
---

# Audit Skills

Read-only analysis. Report findings, don't apply fixes — the user picks what to act on
(same human-in-the-loop rule as `/code-review`).

The classification rules this checks against live in `.claude/CLAUDE.md`'s **Skill
Structure** section — read that first, don't re-derive it here.

## Steps

1. **Mechanical layer first**: run `uv run python scripts/check_skill_structure.py`.
   Frontmatter and bundled-script errors it reports are non-negotiable — fix those before
   doing any judgment-call analysis below.
2. **Inventory sync**: list `.claude/skills/*` and `.claude/references/*` on disk, compare
   against the "Skills" and "References" lists in `.claude/CLAUDE.md`. Flag anything on
   disk but unlisted, or listed but missing.
3. **Skill vs. reference shape**: read each SKILL.md body. Playbook (imperative steps,
   "do X then Y") belongs as a skill. Background/theory/exhaustive listing belongs in
   `.claude/references/` with the skill (if any) shrunk to a thin trigger + pointer. Flag
   misclassified ones.
4. **Bundled-file anti-patterns**: for anything under a skill dir besides SKILL.md, check
   the two named anti-patterns in CLAUDE.md — (a) a file a human would plausibly read/run
   directly outside the skill context (→ belongs in `scripts/` or `.claude/references/`),
   (b) a synthetic template duplicating a real file (→ point at the real file instead).
5. **Staleness**: grep each skill/reference for file paths, function/flag names,
   dependency or framework names it references. Verify each skill matches current repo
   state. Flag anything renamed, removed, or never true.
6. **Report**: group findings by skill/reference, each tagged with one recommendation —
   keep / demote-to-reference / promote-to-skill / trim-fluff / fix-staleness /
   relocate-bundled-file. No fixes applied automatically.
