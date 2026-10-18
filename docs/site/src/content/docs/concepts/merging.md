---
title: Merging
description: Why merge.py is an agent's only way to merge, and what it checks before it does.
sidebar:
  order: 4
---

Agents merge only through `.github/scripts/merge.py`, and by default only when you say so. A task can opt into agent merging with `Merge: agent`, and then merge.py checks three facts before it squash-merges.

## Who merges

Every `code` issue has a `### Merge` field:

- **`human`** (the default): when the PR is merge-ready, the agent stops at [gate 02](/cvsm/concepts/gates-and-blockers/). The merge-ready PR is the request; there is no label or blocker comment. When you say "merge", the agent runs `merge.py <PR> --human` and records `Decision:` on the issue.
- **`agent`**: for low-risk tasks whose Scope matches no protected path. The agent runs `merge.py <PR>` itself once the PR is merge-ready.

## What merge.py checks

`python .github/scripts/merge.py <PR>` merges only when all three hold:

1. The issue the PR closes says `Merge: agent`.
2. No changed path, including the old path of a rename, matches `protected` in `guard.toml` on the PR's base branch.
3. The newest comment whose first line starts with `Verdict:` is `Verdict: pass @ <SHA>`, and the SHA is a prefix, at least 7 characters, of the current head.

Otherwise it lists the reasons, refuses with exit code 2, and the PR waits for you.

`python .github/scripts/merge.py <PR> --human` skips the three checks, because you have decided.

## How it merges

Both forms run the same command on the current head:

```sh
gh pr merge <PR> --squash --match-head-commit <SHA> --subject "<PR title> (#<PR>)" --body ""
```

`--match-head-commit` means a head that moved after the check is not merged. Branch protection still requires `guard` and `test` to pass. Exit code 1 means merge.py could not read the PR or the merge itself failed; the agent reads the message, fixes the cause and retries, and the same failure 3 times in a row is a blocker.

## Why only one path

A direct `gh pr merge` is denied in both agent CLIs: `.claude/settings.json` has `permissions.deny` for `Bash(gh pr merge:*)`, and `.codex/rules/cvsm.rules` marks `gh pr merge` as `forbidden`. AGENTS.md says the same in words. With one path, the checks above cannot be skipped by accident.

:::caution[Protected paths always go to you]
AGENTS.md, `.agents/`, `.codex/`, `.claude/`, `.github/` and your eval and data paths are protected. guard lets a PR change them only when the task's Scope names them explicitly, and merge.py without `--human` refuses any PR that touches them. Such a PR always waits for your merge instruction, whatever its Merge field says.
:::

## What main allows

`scripts/setup.sh` sets the repo up so that the squash merge is the only way in:

- only squash merges, with the PR title as the commit title and an empty body;
- branches deleted after merge;
- main changes only through PRs, `guard` and `test` must pass, 0 approvals, no bypass even for admins, no force pushes or deletion.

No GitHub approval is required: your merge instruction in the session is the approval.

## After the merge

The `code` issue closes through `Closes #N`. The merging agent carries out the approved minor proposals from the review, then removes the task's worktree and branch.

## Related

- [Review](/cvsm/concepts/review/)
- [Gates and blockers](/cvsm/concepts/gates-and-blockers/)
- [merge.py](/cvsm/reference/merge-py/)
- [guard](/cvsm/reference/guard/)
