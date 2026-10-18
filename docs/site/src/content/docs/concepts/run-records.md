---
title: Run records
description: How each run becomes an MLflow run with provenance and its resolved config, and how results comments come from those records.
sidebar:
  order: 5
---

Each run is one MLflow run that records where it came from, the config it actually resolved, and its outputs. Results comments are generated from these records, so what you read about a run is what the run recorded, not what an agent wrote.

## What a record holds

The reference Run command, `scripts/run.py`, creates the record before launching the command. Its docstring is the reference for every field.

- **`rh.*` params**, which MLflow never lets change once written:
  - at creation: `rh.issue`, `rh.command`, `rh.seed`, `rh.host`;
  - right before launch: `rh.commit`, `rh.dirty`, `rh.env_lock_sha`, `rh.env_lock_missing`, `rh.data_manifest_sha`, `rh.gpus`;
  - at the end: `rh.exit_code`.
- **`cfg.*` params**: the resolved config the command writes to `$RUN_DIR/config.json`, flattened to dotted keys such as `cfg.optim.lr`. They are logged once, as soon as the file parses as a JSON object, so a running run can already be checked against its spec.
- **Artifacts**: `log.txt` (the command's output), every file the command writes to `$RUN_DIR` including `config.json`, and `diff.patch` and `untracked.txt` when the tree is dirty.
- **Metrics**: a flat `{name: number}` in `$RUN_DIR/metrics.json`, or MLflow's standard API, which `MLFLOW_RUN_ID` attaches to the same run.
- **Final status**: `FINISHED` for exit code 0, `KILLED` when a signal stopped the command, `FAILED` otherwise.

Missing values are empty strings and lists are comma-joined. The commit, environment lock and data manifest hashes are the fingerprints that the results table compares.

## The resolved config

Your training code writes its full resolved config as one JSON object to `$RUN_DIR/config.json` at start, from one process only (for example rank 0). It includes every setting that can affect results, derived ones too, such as the effective batch. It leaves out values that differ per run without affecting results, such as output directories, run names and timestamps; otherwise every results comment lists them as undeclared differences.

:::note
Keys used in a study spec must stay within MLflow's characters for param names: letters, digits, `_ - . / :` and spaces. run.py skips other keys and lists them on stderr.
:::

## Where records live

The backend is whatever `MLFLOW_TRACKING_URI` names. When it is unset, it is `mlflow.db` at the main clone root, shared by every worktree, with artifacts beside it in `mlartifacts/`. MLflow's web UI is optional. Records are never edited or deleted, and `mlflow gc` is never run.

## How runs are launched

The `run` skill claims the run issue, makes a clean worktree on a branch from `main`, and launches every line of the issue's Runs from there, so each record names merged code. A run issue has no commits and no PR.

```sh
python scripts/run.py --issue 12 -- python train.py arm=lora seed=1
python scripts/run.py --issue 12 --gpus 4 -- python train.py arm=lora seed=2
```

- Right after launch, once configs are recorded, it checks the runs against the spec and stops any that break it. Stopped runs stay recorded.
- A failed run stays and is counted. A line is rerun only after an infra failure, such as a lost node, preemption or a full disk, never because a result looks wrong.
- A failure caused by the code is a result: the agent keeps it, opens a `code` issue for the bug, and continues with the other lines.

## The results comment

When every line has a finished or failed record, the agent posts one comment on the run issue: a short note on what ran, failures, reruns and Adaptable changes, followed by the results command's output, pasted unchanged. Then it closes the issue.

The table groups runs by command with the seed removed. Each group shows:

- `n`, the runs that exited 0, and the number of failures;
- the mean and sample standard deviation of each metric;
- the commit, environment lock and data fingerprints;
- with a spec, the arm the group belongs to.

It flags groups that differ in commit, environment or data (with `git diff --stat` when commits differ), successful runs without metrics, unfinished runs and deleted runs. A `规格核对` (spec check) section follows; see [The study spec](/research-harness/concepts/study-spec/).

When all run issues of a study are closed, the agent posts the same table and spec check over all of them on the study itself: the study table.

:::caution
The results comment states facts. Whether runs are still comparable, and whether to rerun, is your decision.
:::

## Related

- [The study spec](/research-harness/concepts/study-spec/)
- [Run experiments](/research-harness/guides/run-experiments/)
- [run.py](/research-harness/reference/run-py/)
- [results.py](/research-harness/reference/results-py/)
