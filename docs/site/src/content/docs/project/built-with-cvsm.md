---
title: Built with CVSM
description: How CVSM is developed with its own workflow, and where to see the record on GitHub.
sidebar:
  order: 2
---

CVSM is developed with its own workflow. Since the initial commit, every change to its `main` has been a squash-merged PR that closes one task issue under a `plan` parent.

## Plans

Development work sits under `plan` parent issues, each with `code` sub-issues:

| Plan | Issue | What it covers |
|---|---|---|
| p001 bootstrap | [#1](https://github.com/doem97/cvsm/issues/1) | the first version: guard, rules, skills, run records, setup script, merge tiers, and follow-ups from reviews and the adoption pilot |
| p002 fair comparison | [#29](https://github.com/doem97/cvsm/issues/29) | the study spec: Arms, Controlled and Adaptable; agents held to it; run configs recorded and checked |
| p003 pre-release | [#38](https://github.com/doem97/cvsm/issues/38) | this docs site, lean READMEs and the Apache-2.0 licence |
| p004 rename to CVSM | [#43](https://github.com/doem97/cvsm/issues/43) | the new name in the code, the READMEs and their figures, and this site |

Project-level Decisions live on [#1](https://github.com/doem97/cvsm/issues/1): branch protection, the scope of the project, the language of each interface, tiered merging, the machine account and more. The design document, [`docs/design/2026-10-16-harness-v1.md`](https://github.com/doem97/cvsm/blob/main/docs/design/2026-10-16-harness-v1.md) (Chinese), is kept in sync with them.

## How a change lands

1. **Plan.** The human and an agent discuss the work in a session. The agent drafts a `plan` parent with a Goal, the design in its Context, and `code` sub-issues ordered into waves with disjoint Scopes. On "publish" it creates them and records the Decision.
2. **Implement.** An agent claims a task with a linked branch `t/<N>-<slug>`, works in its own worktree, and loops with fresh pre-PR reviewers until Acceptance passes.
3. **Review.** A fresh session that sees only the PR number posts the `Verdict:` comment. A PR often goes through several reviews before its final pass; remaining minor findings are proposed as follow-up issues in one comment.
4. **Merge.** CVSM's changes almost always touch protected paths (`AGENTS.md`, `.agents/`, `.github/` and so on), so its tasks say `Merge: human`. The human says "merge" in the session. Since PR #15, the machine account `doem1997-claude-bot` then runs `merge.py --human` and records `Decision: 合并 PR #<PR> — ...` on the task, with the human's words and the reviewed SHA.
5. **Follow up.** Approved minor proposals become new tasks under the same plan, e.g. [#16](https://github.com/doem97/cvsm/issues/16) from the review of PR #15.

## Where to look

- `git log --oneline main`: one commit per PR, titled `<type>(#N): <summary> (#PR)`.
- Merged PRs from #14 on: the `Verdict:` comments, the last a pass for a named head SHA, and the minor proposals.
- Closed tasks from [#13](https://github.com/doem97/cvsm/issues/13) on: the merge Decision with the human's instruction. The merge of PRs #9, #10 and #12 is recorded on #1.
- [#7](https://github.com/doem97/cvsm/issues/7), the pilot: adoption into a fresh repo (scenario 0) passed, its README findings became [#23](https://github.com/doem97/cvsm/issues/23) and [#24](https://github.com/doem97/cvsm/issues/24), and the human closed the rest as not planned in favour of adopting CVSM in real projects.

## Related

- [Status](/cvsm/project/status/)
- [Work in a session](/cvsm/start/talk-dont-click/)
- [Review](/cvsm/concepts/review/)
- [Merging](/cvsm/concepts/merging/)
