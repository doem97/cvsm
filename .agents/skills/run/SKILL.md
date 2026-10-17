---
name: run
description: Use when doing a `run` issue, from claiming it and launching its Runs within Budget to the results comment and closing the issue.
---

# run

Take one `run` issue N from ready to closed: launch every Runs line through the Run command,
stay within Budget, post the results comment and close N. AGENTS.md rules apply throughout;
this skill adds the procedure. Below, `<run>` and `<results>` are the Run and results
commands named on the `Run` line of AGENTS.md Project, the part before `--issue N`; use them
exactly as written there. In this repo, for example, they are `python scripts/run.py` and
`python scripts/results.py`; an adopting project may use `uv run ...` or a cluster launcher.

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
gh issue view P                 # the study
gh issue view P --comments      # its Decisions
<results> --issue N             # runs already recorded for N, if any
```

Runs already recorded for N count: launch only the lines that have no record yet, unless an
earlier attempt ended in an infra failure (section 4).

## 3. Launch within Budget

For each Runs line, from the worktree root. A line is `<cmd>`, or `<options> -- <cmd>` when it
carries options of the Run command such as `--gpus 4`; pass those through before `--`:

```
<run> --issue N -- <cmd>
<run> --issue N --gpus 4 -- <cmd>   # for the line `--gpus 4 -- <cmd>`
```

- The Run command records every run as an MLflow run (AGENTS.md Project, Run records) and
  waits for the GPUs it needs (this repo's Run command leases them from `scripts/run.toml`),
  so several lines may be launched at once. Use your tool's background execution for long
  runs; stop one with SIGTERM.
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
table=$(<results> --issue N --metric <Report metrics>)
gh issue comment N --body "$(printf '%s\n\n%s\n' "<中文说明：跑了什么、失败与重跑及原因、超出预算与否>" "$table")"
gh issue close N --reason completed
```

- Paste the table unedited. Do not drop, filter or reorder runs.
- If all sub-issues of P are now closed, P awaits analysis (AGENTS.md State).

Then clean up from the main clone:

```
git worktree remove ../worktrees/N-<slug>
git branch -D t/N-<slug>
git ls-remote --exit-code --heads origin t/N-<slug> && git push origin --delete t/N-<slug>
```

## 6. Report

Report the three lines of AGENTS.md Report in Chinese, with links to the results comment and to
P. Do not conclude or close the study; that is gate 4.
