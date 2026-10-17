---
name: run
description: Use when doing a `run` issue, from claiming it and launching its Runs within Budget to the results comment and closing the issue.
---

# run

Take one `run` issue N from ready to closed: launch every Runs line within Budget, post the
results comment and close N. Below, `<run>` and `<results>` are the Run and results commands on
the `Run` line of AGENTS.md Project, the part before `--issue N`, used exactly as written there
(here `python scripts/run.py` and `python scripts/results.py`; elsewhere maybe a cluster launcher).

## 1. Claim and set up

Read state as AGENTS.md State says. N must be ready (its blockers, usually the code issues
it needs, are closed), or in progress and named by the instruction or claimed by this session.

```
gh issue develop N --name t/N-<slug> --base main
gh issue develop --list N
```

If `--list` shows another branch besides yours, run `git push origin --delete t/N-<slug>` and
pick other work. Otherwise, from the main clone root:

```
git fetch origin
git worktree add ../worktrees/N-<slug> t/N-<slug>
```

Launch every run from this clean worktree, so each record names merged code. Commit nothing
to the branch; a run issue has no PR.

## 2. Read

```
gh issue view N                 # body: Runs, Budget (GPU hours), Report; parent P
gh issue view N --comments      # Decisions
gh issue view P                 # the study and its spec: Arms, Controlled, Adaptable
gh issue view P --comments      # its Decisions
<results> --issue N             # runs already recorded for N, if any
```

Runs already recorded for N count: launch only the lines that have no record yet, unless an
earlier attempt ended in an infra failure (section 4).

## 3. Launch within Budget

Before launching, check that each Runs line runs exactly one arm and that each arm this issue
runs gets every value of each Controlled `in` line; otherwise it is a blocker (AGENTS.md
Blockers); whether every arm runs is checked for the whole study (section 5). Launch each Runs
line from the worktree root. A line is `<cmd>`, or `<options> -- <cmd>` when it carries options
of the Run command such as `--gpus 4`; pass those through before `--`:

```
<run> --issue N -- <cmd>
<run> --issue N --gpus 4 -- <cmd>   # for the line `--gpus 4 -- <cmd>`
```

- The Run command records every run as an MLflow run (AGENTS.md Project, Run records) and
  waits for the GPUs it needs, so several lines may be launched at once. Use your tool's
  background execution for long runs; stop one the way the Run command provides (here SIGTERM).
- Right after launch, once the runs have recorded their configs (`cfg.*` params), run
  `gh issue view P --json body -q .body | <results> --issue N --spec -`. Stop every running
  run that `规格核对` lists as breaking a Controlled `key=value` line, not recording one, or
  matching no arm or several. A key under `未声明的差异` is a blocker; if it can affect results,
  stop the runs first. Stopped runs stay recorded. Whether to relaunch a stopped line follows
  section 4, or the human's answer to the blocker; note every stopped or relaunched run for the
  results comment.
- Change an Adaptable setting only within its rule (e.g. a smaller per-device batch after an
  out-of-memory error); note each change, its run and reason for the results comment.
- GPU hours used = the sum over this issue's runs, failed ones included, of wall time times
  the number of GPUs. Estimate a run from the first finished one.
- Before launching a run that would take the total past Budget, stop at gate 3: report the
  hours used, the estimate for the rest, and the runs not yet launched. Continue only on the
  human's explicit instruction, and record it as a Decision on N.

## 4. Failures

- A failed run stays and is counted (`n_failed` in the results table).
- Rerun a line only after an infra failure: node or GPU lost, preemption, a full disk,
  a lost connection to the tracking backend. Never rerun because a result looks wrong.
  Note every rerun, with the failed run's id and the cause, for the results comment.
- The same failure 3 times in a row is a blocker.
- A failure caused by the code is a result, not infra: keep it, open a `code` issue for the
  bug with `--parent P` (AGENTS.md Blockers), and continue with the other lines. Whether
  to run again after the fix is the human's call.

## 5. Results comment and close

When every line has a finished or failed record:

```
table=$(gh issue view P --json body -q .body | <results> --issue N --metric <Report metrics> --spec -)
gh issue comment N --body "$(printf '%s\n\n%s\n' "<中文说明：跑了什么、失败与重跑及原因、每项 Adaptable 改动、超出预算与否>" "$table")"
gh issue close N --reason completed
```

- Paste the table unedited. Do not drop, filter or reorder runs.
- If all `run` sub-issues of P are now closed, post on P, the same way, the study-level table
  and check over all of them (P awaits analysis once all its sub-issues are closed):

```
runs=$(gh api --paginate 'repos/{owner}/{repo}/issues/P/sub_issues' --jq '[.[] | select(any(.labels[]; .name == "run")) | .number] | join(" ")')
table=$(gh issue view P --json body -q .body | <results> --issue $runs --metric <Report metrics> --spec -)
gh issue comment P --body "$(printf '%s\n\n%s\n' "<一行中文说明：本研究全部 run issue 的结果与规格核对>" "$table")"
```

Then clean up from the main clone:

```
git worktree remove ../worktrees/N-<slug>
git branch -D t/N-<slug>
git ls-remote --exit-code --heads origin t/N-<slug> && git push origin --delete t/N-<slug>
```

## 6. Report

Report the three lines of AGENTS.md Report in Chinese, with links to the results comment and to
P. Do not conclude or close the study; that is gate 4.
