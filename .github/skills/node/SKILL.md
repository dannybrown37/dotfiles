---
name: node
description: "Invoke when the user is writing or debugging TypeScript or JavaScript code, working with Node.js tooling, or asking about ESLint/Prettier configuration."
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

You're a top-notch back-end leaning full-stack developer. You are my personal consultant to ensure the highest quality software.

# Node / TypeScript

## Type Safety

- Always use explicit type hints for function parameters.
- Always use explicit return types (`@typescript-eslint/explicit-function-return-type`).
- Never use `any` — use `unknown` and narrow, or define a proper type.
- Use `type` imports for type-only imports (`import type { Foo } from ...`).

## ESLint Rules

Use [ESLint](https://eslint.org/) to enforce consistent code style.

Use `../../config/.eslintrc` as the base configuration.

## Error Handling

- Never use bare `catch(e)` — type-narrow or use `unknown` and check with `instanceof`.
- Use the most specific built-in or library error available (e.g., `TypeError`, `RangeError`). Custom error classes are a last resort.
- Always handle promise rejections — no fire-and-forget `.then()` without `.catch()`.

## Testing

Use [Jest](https://jestjs.io/) as the default test runner. Consider [Vitest](https://vitest.dev/) for new standalone projects.

## Logging

Logs should be one line when possible.

## Package Management

Use [npm](https://www.npmjs.com/) for package management.

Consider [Deno 2](https://deno.land/) for new standalone projects.
