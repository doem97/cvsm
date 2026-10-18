---
title: Claude Code and Codex
description: How Claude Code and Codex load the same rules and skills, how each is kept from merging directly, and how each starts a fresh review.
sidebar:
  order: 5
---

CVSM works with Claude Code and Codex from one set of files: both read `AGENTS.md` and the same four skills, and each has its own config that forbids `gh pr merge`. You can run sessions of either tool side by side, each on its own task.

## What each tool reads

| | Claude Code | Codex |
|---|---|---|
| Rules | `AGENTS.md` | `AGENTS.md` |
| Skills | `.claude/skills`, a symlink to `../.agents/skills` | `.agents/skills` |
| Merge ban | `.claude/settings.json`: `permissions.deny` with `Bash(gh pr merge:*)` | `.codex/rules/cvsm.rules`: `gh pr merge` is `forbidden` |
| Machine account (optional) | `.claude/settings.local.json` sets `GH_CONFIG_DIR` | `.codex/config.toml` sets `GH_CONFIG_DIR` |

`AGENTS.md` is the only instruction file. Don't add a `CLAUDE.md`: guard rejects `.md` files outside the allowed places, and CVSM reads only `AGENTS.md`.

## Check that the rules are loaded

1. **Codex: trust the project.** Codex reads the project's `.codex/` only once it trusts the project. Run `codex` interactively once at the repo root and accept the trust prompt. (`codex exec -s danger-full-access` marks the project trusted without a prompt.)
2. **Codex: check the rules file.** `codex execpolicy check --rules .codex/rules/cvsm.rules gh pr merge 1` should print `forbidden`. This checks only the file itself.
3. **Codex: check a live session.** Open a Codex session in the repo and ask it to run `gh pr merge --help`. The rule should block it; even if allowed, this command merges nothing. Confirm that all four skills (`plan`, `implement`, `review`, `run`) are listed.
4. **Claude Code: check a live session.** Open a session in the repo and confirm that all four skills are listed.

:::caution[Only merge.py merges]
Agents merge only through `.github/scripts/merge.py`. Codex applies its rules before it chooses a sandbox, so the ban holds even in a full-permission session; Claude Code does the same job with `permissions.deny`.
:::

## Start a fresh-context review

The implementer never reviews its own PR. It starts a fresh reviewer that gets only the PR number, following section 4 of the `review` skill:

- **Claude Code:** a fresh subagent with the prompt "Follow `.agents/skills/review/SKILL.md` for PR #&lt;PR&gt;."
- **Codex:** `codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #<PR>."` `codex exec` is sandboxed without network by default, and `gh` needs it, hence `-s danger-full-access`.
- **Codex built-in review,** run in a checkout of the PR head with `codex exec review "<instructions>"`. In Codex 0.163, `--base` can't be combined with instructions, so the instructions name the base (`git diff origin/main...HEAD`) and carry the issue body, the Decisions on the issue and its parent, the parent's spec if it is a study, and the review checklist. Its output tags findings `[P0]` to `[P3]`: any `[P0]` or `[P1]` means `changes`, otherwise `pass`. The session that ran it posts the output verbatim under the Verdict line, only if the PR head still equals the reviewed SHA.

For the inner loop before a PR, the implementer gives a fresh subagent, or `codex exec -s danger-full-access` in the worktree, only the issue number and the diff. That pre-PR review posts nothing.

:::tip
The reviewer can run in either tool, whichever ran the implementer. What matters is that it starts from the PR number alone and never sees the implementer's session or summary.
:::

## Use a machine account with both

If agents use a machine account, both tools need `GH_CONFIG_DIR` pointed at its gh login, through two local files listed in `.git/info/exclude`:

- `.claude/settings.local.json`: `{"env": {"GH_CONFIG_DIR": "<dir>"}}`
- `.codex/config.toml`:

  ```toml
  [shell_environment_policy]
  set = { GH_CONFIG_DIR = "<dir>" }
  ```

Both files live only in the main clone. A session started from the main clone passes the setting to the agents it starts; if you open a session directly in a worktree, put copies there first. The full setup is in [Adopt CVSM](/cvsm/guides/adopt/#optional-a-machine-account-for-the-agents).

## Related

- [Review](/cvsm/concepts/review/)
- [Work in a session](/cvsm/start/talk-dont-click/)
- [Skills](/cvsm/reference/skills/)
- [AGENTS.md](/cvsm/reference/agents-md/)
- [merge.py](/cvsm/reference/merge-py/)
