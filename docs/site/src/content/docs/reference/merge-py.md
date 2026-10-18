---
title: merge.py
description: The only way an agent merges, with its three checks, the --human mode and its exit codes.
sidebar:
  order: 5
---

`merge.py` squash-merges one PR at its current head. Without `--human` it merges only a pre-approved, reviewed task that touches no protected path; with `--human` it carries out a merge the human has decided.

Source: [`.github/scripts/merge.py`](https://github.com/doem97/cvsm/blob/main/.github/scripts/merge.py).

## Usage

```sh
python .github/scripts/merge.py <PR>           # an agent merging a `Merge: agent` task
python .github/scripts/merge.py <PR> --human   # on the human's explicit instruction
```

`<PR>` is the PR number. It needs `gh` logged in with write access, and Python 3.11 or later; it uses only the standard library and imports its parsing helpers from `guard.py`.

## Checks without `--human`

It merges only when all three hold:

| Check | Passes when | Read from |
|---|---|---|
| Merge mode | the PR body closes exactly one issue, that issue can be read, and its `### Merge` section is `agent` (case-insensitive) | PR body; the issue |
| Protected paths | no changed path, including the old path of a rename, matches `protected` in `guard.toml` | PR files; `.github/guard.toml` on the PR's **base branch** |
| Review | the newest PR comment whose first line starts with `Verdict:` is exactly `Verdict: pass @ <SHA>`, where `<SHA>` is 7 to 40 hex characters and a prefix of the current head (case-insensitive) | PR conversation comments |

Notes:

- Closing references are parsed as in [guard](/cvsm/reference/guard/#1-closing-reference).
- `protected` is matched as plain globs here: unlike guard, a Scope entry that names a protected path doesn't unlock it. A PR that touches a protected path is always merged by the human.
- A newer `Verdict: changes`, or a pass for an older head, blocks the merge. Comments whose first line doesn't start with `Verdict:` are ignored, so the comment listing remaining minors must not start with it.

If any check fails, it lists every reason and waits for the human.

## `--human`

`--human` skips the three checks, because the human has decided. The agent runs it only on an explicit instruction in a session, and records `Decision: 合并 PR #<PR> — <the human's instruction>` on the issue.

## The merge

Both modes run:

```sh
gh pr merge <PR> --squash --match-head-commit <head SHA> --subject "<PR title> (#<PR>)" --body ""
```

- `--match-head-commit` pins the merge to the head that was read, so a push in between makes it fail rather than merge unreviewed code.
- The commit title is `<PR title> (#<PR>)` with an empty body.
- Branch protection still applies: `guard` and `test` must pass.

## Exit codes

| Code | Meaning | What the agent does |
|---|---|---|
| `0` | Merged. | Carry out the approved minor proposals; clean up the worktree and branches. |
| `2` | Refused: a check failed (only without `--human`). | Stop. The merge-ready PR is the request; add no label or blocker comment. |
| `1` | Usage error; the PR, its files, its comments or the base branch's `guard.toml` couldn't be read; or `gh pr merge` failed. | Read the message, fix the cause (checks not green yet, head moved, ...) and retry. The same failure 3 times in a row is a blocker. |

Messages are printed in Chinese, e.g. `不合并 PR #15：` followed by one `- <reason>` line per failed check and `等人合并`.

## Why agents can't bypass it

`gh pr merge` is forbidden for agents: `AGENTS.md` says so, `.claude/settings.json` denies `Bash(gh pr merge:*)`, and `.codex/rules/cvsm.rules` marks it `forbidden`. Calling `python .github/scripts/merge.py` stays allowed.

## Related

- [Merging](/cvsm/concepts/merging/)
- [Review](/cvsm/concepts/review/)
- [guard](/cvsm/reference/guard/)
- [AGENTS.md: Gates](/cvsm/reference/agents-md/#gates)
- [Interfaces that stay fixed](/cvsm/reference/interfaces/)
