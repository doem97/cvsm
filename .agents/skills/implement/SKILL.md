---
name: implement
description: Use when doing a `code` issue, from claiming it through fresh reviews to a merge-ready PR, or to merged when its Merge field is agent.
---

# implement

Take one `code` issue N from ready to merge-ready, or to merged under `Merge: agent`, following
AGENTS.md. Most quality comes from the inner loop (step 4); the PR review is the final check.

## 1. Claim and set up the worktree

Read state as AGENTS.md State says. N must be ready, or in progress and named by the
instruction or claimed by this session (then reuse its branch and worktree).

```
gh issue develop N --name t/N-<slug> --base main
gh issue develop --list N
```

If `--list` shows another branch besides yours, run `git push origin --delete t/N-<slug>` and
pick other work. Otherwise work only in a worktree, made from the main clone root (AGENTS.md Git):

```
git fetch origin
git worktree add ../worktrees/N-<slug> t/N-<slug>
```

## 2. Read

```
gh issue view N             # body: Goal, Scope, Acceptance, Merge; parent P
gh issue view N --comments  # Decisions
gh issue view P && gh issue view P --comments  # parent: body (a study's spec), Decisions
```

Read AGENTS.md, the code in Scope and the interfaces that code uses.

## 3. Implement

- Use TDD where it fits: first a failing test that pins the contract, then the code.
- Change only paths that Scope matches; check with `git diff --name-only origin/main...`.
- If P is a `study`, its spec (Arms, Controlled, Adaptable) binds the code: set every key it
  names through config; write the resolved config (every setting that can affect results,
  derived ones included) to `$RUN_DIR/config.json` from one process; never alter a Controlled
  setting or make the arms differ beyond Arms.
- A bug outside Scope: open a new `code` issue with `--parent P` (AGENTS.md Blockers), keep it
  out of this branch, and list it under Out of scope in the PR.
- A Scope that is too small, an ambiguity that changes the deliverable, or a Controlled line the
  code cannot meet without changing the comparison is a blocker (AGENTS.md Blockers).
- Commit as `<type>(#N): <summary>` and push often: `git push -u origin t/N-<slug>`.

## 4. Inner loop, before the PR

Repeat until every Acceptance command passes and a fresh reviewer finds nothing blocking:
1. Run each Acceptance line from the worktree root, plus the Test command in AGENTS.md Project.
2. Get a fresh pre-PR review of the diff against the issue, started as section 4 of
   `.agents/skills/review/SKILL.md` says. Never pass it your summary or reasoning.
3. Fix the findings worth fixing, commit, push, and start the next round with a new reviewer.

## 5. Open the PR

Follow `.github/pull_request_template.md` and AGENTS.md Git: an English title, a Chinese body.

```
gh pr create --base main --head t/N-<slug> --title "<type>(#N): <summary>" --body "$(cat <<'EOF'
Closes #N
## Changes
- <至多 5 条>
## Acceptance
- `<命令>`：<结果>
## Out of scope
none
EOF
)"
gh pr checks <PR> --watch   # fix guard or test failures without asking
```

## 6. Outer loop: fresh review of the PR

Start a fresh PR review (section 4 of `.agents/skills/review/SKILL.md`). Then check that the
newest `Verdict:` comment names the PR head (`gh pr view <PR> --json headRefOid -q .headRefOid`).
- `changes`: fix its findings, rerun Acceptance, push, and get a fresh review of the new head.
  Three `changes` in a row is a blocker (AGENTS.md Blockers).
- `pass` with minor findings: fix the ones inside Scope. If you pushed fixes, get ONE more
  fresh review (a `changes` there returns to the line above); otherwise go straight on. Then
  post one PR comment listing every remaining minor with a proposal: a new issue, an existing
  issue #M, or no action, each with a one-line reason. Its first line must not start with `Verdict:`.

```
gh pr comment <PR> --body "$(cat <<'EOF'
剩余的 minor 意见与处理建议（合并的指示即批准，由执行合并的 agent 照办）：
1. <意见>（<审查评论链接>）— 建议：开新 issue「<标题>」；理由：<一行>
2. <意见> — 建议：并进 #M；理由：<一行>
3. <意见> — 建议：不处理；理由：<一行>
EOF
)"
```

## 7. Merge-ready

Once the PR is merge-ready (AGENTS.md State), under `Merge: agent` run
`python .github/scripts/merge.py <PR>`. Otherwise, or if it refuses (exit 2), stop and report:
the merge-ready PR is the request; add no label or blocker comment. If `merge.py` exits 1 (it
could not read the PR, or the merge itself failed), read its message, fix the cause (checks not
green yet, head moved, ...) and retry; the same failure 3 times in a row is a blocker.

When the human explicitly says to merge, run `python .github/scripts/merge.py <PR> --human`
and record `Decision: 合并 PR #<PR> — <人的指示>` on issue N. That instruction, or under
`Merge: agent` the one naming the task, approves the minor proposals. After either merge:
1. Carry out the minor proposals (`gh issue create --label code --parent P ...`, `gh issue comment M`).
2. Clean up from the main clone; the origin branch is gone if the repo deletes merged branches:

```
git worktree remove ../worktrees/N-<slug>
git branch -D t/N-<slug>
git ls-remote --exit-code --heads origin t/N-<slug> && git push origin --delete t/N-<slug>
```

At every stop, report the three lines of AGENTS.md Report in Chinese, with links.
