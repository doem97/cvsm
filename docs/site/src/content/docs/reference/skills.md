---
title: Skills
description: The four skills, plan, implement, review and run, with what each reads, writes and where it stops.
sidebar:
  order: 2
---

A skill is the procedure for one role, from start to finish, in at most 120 lines. There are four, and Claude Code and Codex read the same files.

Sources: [`.agents/skills/`](https://github.com/doem97/research-harness/tree/main/.agents/skills).

## Common shape

| Item | Value |
|---|---|
| Location | `.agents/skills/<name>/SKILL.md`; `.claude/skills` is a symlink to `../.agents/skills` |
| Frontmatter | `name` (the directory name) and `description` (when to use it) |
| Length | at most 120 lines, checked by `tests/skills/test_skills.py` |
| Commands | `<run>` and `<results>` stand for the Run and results commands on the `Run` line of `AGENTS.md` Project, the part before `--issue N` |
| Reports | each skill ends its stops with the three lines of `AGENTS.md` Report |
| Language | as shipped, the skills name Chinese for the discussion, drafts, PR bodies, reports and comment templates; a project whose `Language` line names another language changes them |

| Skill | Takes | From | To | Writes |
|---|---|---|---|---|
| `plan` | a discussion | new work | published parent and sub-issues (gate 1) | issues, one Decision |
| `implement` | one `code` issue | ready | merge-ready, or merged under `Merge: agent` | files in Scope, the PR, blocker comments |
| `review` | one PR number | fresh session | one Verdict comment | one PR comment |
| `run` | one `run` issue | ready | closed with a results comment | run records, the results comment |

## plan

*Use when the human wants to discuss new work and turn it into a published `study` (research) or `plan` (development) parent issue with its `code` and `run` sub-issues.*

1. **Read state and context.** Open `study`, `plan` and `needs-decision` issues; open PRs; earlier studies or tasks with their comments; `<results> --issue <N>` for earlier run records; the code the work will touch and the papers and records the human points to. Nothing is written while discussing.
2. **Discuss** with the human until the draft is complete: the question or goal, the result that answers it, the budget and, for a study, the spec. For Controlled, walk the usual confounders (data and split; preprocessing and augmentation; model and init; optimizer and schedule; effective batch and training length; precision; tuning budget; evaluation protocol and checkpoint selection; seeds), each with a value and a sourced reason. Seeds and tuning grids are `in` lines. Keys come from the code; a setting the code can't take through config needs a `code` sub-issue.
3. **Draft the issues** with the forms' exact `### ` sections. A `plan` parent has `### Goal` and `### Context`. Scope globs never start with a wildcard; Acceptance lines all exit 0 if and only if the task is done; Merge is `agent` only for a low-risk task whose Scope matches no protected path.
4. **Order sub-issues into waves.** Issues in one wave have disjoint Scopes; overlapping ones are chained with blocked-by. Show the whole draft and the graph to the human and revise until they approve.
5. **Publish (gate 1)** only on explicit instruction: the parent first, then sub-issues wave by wave with `gh issue create --label ... --parent P --blocked-by ...`, bodies through a quoted heredoc. Check the parent lists every sub-issue.
6. **Record and stop:** `Decision: 发布 ...` on the parent, report, stop. Editing a published task's Goal, Scope, Acceptance or Merge, or a study's spec, is gate 1 too.

## implement

*Use when doing a `code` issue, from claiming it through fresh reviews to a merge-ready PR, or to merged when its Merge field is `agent`.*

1. **Claim and set up.** `gh issue develop N --name t/N-<slug> --base main`, then `gh issue develop --list N`; if another branch is linked, delete yours and pick other work. Work only in `../worktrees/N-<slug>`.
2. **Read** the issue and its Decisions, the parent and its Decisions (and a study's spec), `AGENTS.md`, the code in Scope and its interfaces.
3. **Implement.** TDD where it fits. Change only paths in Scope (`git diff --name-only origin/main...`). Under a study, set every spec key through config, write the resolved config to `$RUN_DIR/config.json` from one process, and never alter a Controlled setting or make arms differ beyond Arms. Bugs outside Scope become new `code` issues. Commit as `<type>(#N): <summary>` and push often.
4. **Inner loop before the PR.** Run every Acceptance line and the `Test` command; get a fresh pre-PR review of the diff against the issue; fix; repeat with a new reviewer until nothing blocking remains.
5. **Open the PR** from the template: English title, Chinese body. Watch `gh pr checks <PR> --watch` and fix guard or test failures without asking.
6. **Outer loop.** Start a fresh PR review and check the newest `Verdict:` names the PR head. `changes`: fix, rerun Acceptance, push, review again (three in a row is a blocker). `pass` with minors: fix those inside Scope, get one more fresh review if you pushed, then post one comment proposing an action for each remaining minor. Its first line must not start with `Verdict:`.
7. **Merge-ready.** Under `Merge: agent`, run `python .github/scripts/merge.py <PR>`. Otherwise, or if it exits 2, stop: the merge-ready PR is the request. Exit 1 (couldn't read the PR, or the merge failed): fix the cause and retry; the same failure 3 times is a blocker. On the human's merge instruction, run `merge.py <PR> --human` and record `Decision: 合并 PR #<PR> — ...`. After either merge, carry out the minor proposals and remove the worktree and branches.

## review

*Use in a fresh session whose only input is a PR number, to review that PR against its issue and post one comment whose first line is the Verdict.*

1. **Read** the PR and its diff, the issue it closes with its comments, the parent's `Decision:` comments and, for a study, its spec; `AGENTS.md`, the design doc in `docs/` if there is one, and the code around the diff. Never the implementer's session or summaries. To run Acceptance, check out the head SHA in a scratch worktree `../worktrees/review-<PR>` (not `FETCH_HEAD`).
2. **Checklist:**
   1. Contract: meets Goal and Acceptance, stays in Scope, follows the Decisions; under a study, every spec key is set through config and written to `config.json`, and nothing alters a Controlled setting or makes arms differ beyond Arms.
   2. Correctness on realistic inputs and error paths, assuming capable, cooperative agents and users.
   3. Consistency with `AGENTS.md`, the design doc and existing code.
   4. Tests that pin the contract.
   5. Simplicity: nothing the contract doesn't need.

   Items 1 to 4 are blocking; everything else is minor. No requests for defenses against malformed formats, forgery, outsiders or adversarial input unless the issue requires them. The verdict is `changes` only with at least one blocking finding.
3. **Post one comment.** Re-read the full head SHA right before posting; if it moved, review the new head first. First line exactly `Verdict: pass @ <full head SHA>` or `Verdict: changes @ <full head SHA>`; below it, the findings in the tool's own format and language, unedited, each pointed at a file and line. Don't approve, label, push or edit anything. Remove the scratch worktree.
4. **Starting a review** (for the implementer): a fresh Claude Code subagent, `codex exec -s danger-full-access`, or the built-in `codex exec review`, whose `[P0]` or `[P1]` findings mean `changes`. A pre-PR review gets only the issue number and the diff and posts nothing. See [Claude Code and Codex](/research-harness/guides/claude-code-and-codex/#start-a-fresh-context-review).

## run

*Use when doing a `run` issue, from claiming it and launching its Runs within Budget to the results comment and closing the issue.*

1. **Claim and set up** as in `implement`. Launch every run from the clean worktree, so each record names merged code. Commit nothing; a run issue has no PR.
2. **Read** the issue (Runs, Budget, Report) and its Decisions, the study and its spec and Decisions, and `<results> --issue N` for runs already recorded. Recorded lines aren't launched again, unless an earlier attempt ended in an infra failure.
3. **Launch within Budget.** Check that each Runs line runs exactly one arm and that each arm this issue runs gets every `in` value; otherwise it's a blocker. Launch `<run> --issue N [options] -- <cmd>`. Right after launch, run `gh issue view P --json body -q .body | <results> --issue N --spec -` and stop every running run that `规格核对` lists as breaking a Controlled `key=value` line, not recording one, or matching no arm or several. A key under `未声明的差异` is a blocker. Adaptable changes stay within their rule and are noted. GPU hours = wall time times GPUs, summed over all runs including failed ones; before exceeding Budget, stop at gate 3.
4. **Failures.** Failed runs stay and count. Rerun only after an infra failure, never because a result looks wrong. A code failure is a result: open a `code` issue and continue. Same failure 3 times is a blocker.
5. **Results comment and close.** When every line has a finished or failed record, post a note plus `<results> --issue N --metric <Report> --spec -` output, unedited and unfiltered; close the issue. If all run issues of the study are closed, post the study-level table over all of them on the study. Clean up the worktree and branches.
6. **Report** with links to the results comment and the study. Concluding the study is gate 4.

## Related

- [AGENTS.md](/research-harness/reference/agents-md/)
- [Review](/research-harness/concepts/review/)
- [Plan a study](/research-harness/guides/plan-a-study/)
- [Run experiments](/research-harness/guides/run-experiments/)
- [Claude Code and Codex](/research-harness/guides/claude-code-and-codex/)
