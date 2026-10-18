---
title: Run experiments
description: Take a published study through its code and run issues to results comments checked against the spec, and on to your conclusion.
sidebar:
  order: 3
---

After you publish a study, agents implement its code tasks, launch its runs within budget, and post results comments generated from the run records. You step in at the merge, budget and conclude gates, and at blockers.

## 1. Get the code merged

Say "do `#12`" for a code task, or "take `#10` to analysis" to have the agent work through the whole study. Under a study, the spec binds the code: every key it names is set through config, the resolved config is written to `$RUN_DIR/config.json` from one process, and nothing changes a Controlled setting or makes the arms differ beyond Arms. The fresh-context reviewer checks the same, and a violation blocks the PR.

:::caution[Gate 02: merge]
A code task stops at merge-ready: `guard` and `test` green and a `Verdict: pass` for the current head. Say "merge" or "merge `#15`". A task marked `Merge: agent` is merged by the agent itself through `merge.py`, which refuses protected paths and heads without a passing review.
:::

## 2. Launch the runs

A run issue becomes ready once the code issues it is blocked by are closed. The agent claims it, makes a clean worktree from main and launches every Runs line from there, so each record names merged code. A run issue has no PR.

Before launching, it checks that each Runs line runs exactly one arm and that each arm the issue runs gets every value of each Controlled `in` line. Each line goes through the Run command on the `Run` line of `AGENTS.md`:

```sh
<run> --issue N -- <cmd>
<run> --issue N --gpus 4 -- <cmd>   # for the Runs line `--gpus 4 -- <cmd>`
```

The reference Run command, `scripts/run.py`, records each run as an MLflow run and waits for free GPUs, so several lines can be launched at once. Runs already recorded for the issue count, so a resumed session launches only the lines with no record yet.

## 3. Check right after launch

As soon as the runs have logged their configs as `cfg.*` params, the agent runs the results command with the study's spec:

```sh
gh issue view P --json body -q .body | <results> --issue N --spec -
```

:::note
The agent stops every running run that `规格核对` lists as breaking a Controlled `key=value` line, not recording one, or matching no arm or several. A key listed under `未声明的差异` (undeclared difference) is a blocker; if it can affect results, the runs are stopped first. Stopped runs stay recorded.
:::

An Adaptable setting may change within its rule, for example a smaller per-device batch after an out-of-memory error. The agent notes each change, its run and the reason for the results comment.

## 4. Budget and failures

GPU hours used is the sum, over the issue's runs (failed ones included), of wall time times the number of GPUs. The agent estimates the rest from the first finished run.

:::caution[Gate 03: budget]
Before launching a run that would take the total past Budget, the agent stops and reports the hours used, the estimate for the rest, and the runs not yet launched. Say "continue", with a new budget if you like. Your instruction is recorded as a Decision on the issue.
:::

- A failed run stays recorded and is counted (`失败数` in the table).
- A line is rerun only after an infra failure: a lost node or GPU, preemption, a full disk, a lost connection to the tracking backend. Never because a result looks wrong.
- A failure caused by the code is a result, not infra. The agent keeps it, opens a `code` issue for the bug and goes on with the other lines. Whether to run again after the fix is your call.
- The same failure 3 times in a row is a blocker.

## 5. Results comments

When every line has a finished or failed record, the agent posts one comment on the run issue: a short note (what ran, failures and reruns with their causes, every Adaptable change, and whether the budget was exceeded), followed by the output of the results command with `--metric` and `--spec`, pasted unedited. No run is dropped, filtered or reordered. Then it closes the run issue.

When all run issues of the study are closed, it posts the same table and spec check over all of them on the study issue: the study table. The study now awaits analysis.

## 6. Conclude

:::caution[Gate 04: conclude]
Read the study table and its `规格核对`. rh reports what the records show; whether the runs are still comparable is your call. Give your conclusion, e.g. "conclude `#10`: …". The agent records it and closes the study only on your explicit instruction.
:::

## Related

- [Run records](/research-harness/concepts/run-records/)
- [Gates and blockers](/research-harness/concepts/gates-and-blockers/)
- [Skills: run](/research-harness/reference/skills/#run)
- [run.py reference](/research-harness/reference/run-py/)
- [results.py reference](/research-harness/reference/results-py/)
