# Multiple GitHub Accounts

More than one GitHub account shares these machines. Both the commit author and the push token
are chosen from the repo's **remote**, via `includeIf "hasconfig:remote.*.url:..."` — not from
its directory, so a repo cloned somewhere unexpected still gets the right account.

| Remote | Author | Token |
| --- | --- | --- |
| personal account | personal email | `$MY_GITHUB_TOKEN` |
| anything else | *none — commit refused* | `gh` / `$GITHUB_TOKEN` |

The global `[user]` block deliberately has **no email** and sets `useConfigOnly = true`, so a
repo matching no rule fails with *"Author identity unknown"* rather than quietly committing as
the wrong person.

Any **non-personal** identity — the addresses, and the remote patterns that select them — lives
in `~/.gitconfig-private`, which is gitignored and never enters this repo. It reaches other
machines through the password store, not through git. Machines without that file simply inherit
the fail-loud default, since git ignores a missing include.

Personal repos get their token from `scripts/git-credential-personal.sh`, which emits
`$MY_GITHUB_TOKEN` and falls back to `gh` when unset. No token is stored in the repo — the
helper only reads the environment. The dotfiles audit verifies the whole wiring.

When a push is refused, run `gitdoctor` in the offending repo. It walks the chain end to end —
git version, which includes resolved, helper order, whether the token is actually exported into
git's subprocess environment, what `git credential fill` hands back, and whether the account
that token resolves to can actually push to this repo — and names the first broken link. That
last check is the one the audit cannot do: a present-but-wrong or expired token passes every
config-level check and only fails at push time. Tokens are printed as a prefix plus digest, so
the output is safe to paste.

Which helper *should* win depends on who owns the remote, so the doctor checks against that
rather than demanding the personal helper everywhere. On an **SSH** remote it diagnoses SSH
instead — agent, loaded keys, whether GitHub accepts the key — then runs the HTTPS chain as a
preview and, if that chain is healthy, tells you to switch transport:

```bash
git remote set-url origin https://github.com/OWNER/REPO.git
```

This setup routes identity and tokens by *HTTPS remote URL*, so an SSH remote bypasses all of
it. Switching is usually the fix, and it survives WSL forgetting your ssh-agent.
