---
title: Interfaces that stay fixed
description: The shapes the skills, guard, merge.py and the results comment depend on, which adopters keep when they adapt rh.
sidebar:
  order: 8
---

The skills, guard, `merge.py` and the results comment depend on the interfaces below. When you adapt rh to your environment, change the implementations, not these shapes.

Everything else is your project's to decide, through its own issues: the scheduler (e.g. a Run command that submits to SLURM and still writes run records), cluster and GPU allocation, data and artifact storage, the tracking backend (e.g. `MLFLOW_TRACKING_URI` pointing at a team MLflow server), the allow-list and protected paths in `guard.toml`, and CI dependencies. See [Adapt rh to your environment](/research-harness/guides/adapt-your-environment/).

## Run and results commands

The Run command has the shape:

```
<run> --issue N [options] -- <cmd>
```

Each line in a run issue's Runs is either `<cmd>` or `<options> -- <cmd>`. The `run` skill puts the options (e.g. `--gpus 4`) before `--` and the command, unchanged, after it.

The results command has the shape:

```
<results> --issue N [N ...] [--metric M ...] [--spec FILE]
```

`--spec` reads the study issue's body, and FILE `-` reads stdin, e.g. `gh issue view P --json body -q .body | <results> --issue N --spec -`.

The actual commands for both go on the `Run` line of `AGENTS.md`.

## Run records

Each run is one MLflow run. The docstring at the top of `scripts/run.py` is the reference for its fields; see [run.py](/research-harness/reference/run-py/) for the details.

- **`rh.*` params**, which can't change once written:
  - at creation: `rh.issue`, `rh.command`, `rh.seed` and `rh.host`;
  - before launch: `rh.commit`, `rh.dirty`, `rh.env_lock_sha`, `rh.env_lock_missing`, `rh.data_manifest_sha` and `rh.gpus`;
  - at the end: `rh.exit_code`.

  Missing values are empty strings, and lists are comma-joined.
- **`cfg.*` params**: logged once, as soon as the `$RUN_DIR/config.json` the command writes parses as a JSON object.
  - It is logged while the command is still running, so a running run can be checked. A file that only appears by the end is logged at the end.
  - Nested objects flatten to dotted keys `cfg.<key>`. Strings are logged as they are, other values as JSON.
  - Keys and values longer than MLflow's limits are truncated to them. The full content is in the `config.json` artifact.
- **Allowed `cfg.*` keys**: only letters, digits, `_ - . / :` and spaces, which is MLflow's rule for param names.
  - Keys with other characters (e.g. `tench, Tinca tinca` inside a `label2id`) are not logged as params, and neither are keys that repeat after truncation. run.py lists them on stderr.
  - Keys used in a study spec must stay within this set.
- **Tag**: `mlflow.source.git.commit`.
- **Artifacts**:
  - `diff.patch` (`git diff HEAD`) and `untracked.txt` when the tree is dirty;
  - the command's output, `log.txt`;
  - every file the command writes to `$RUN_DIR`, including `config.json`.

  `$RUN_DIR/metrics.json` (a flat `{name: number}`) is logged as metrics. Training code can also log metrics with MLflow's standard API; `MLFLOW_RUN_ID` attaches it to the same run.
- **Final status**: `FINISHED` for exit code 0, `KILLED` when a signal stopped the command, and `FAILED` otherwise.
- **Backend**: set by `MLFLOW_TRACKING_URI`. When unset, it is `mlflow.db` at the main clone root, with artifacts beside it in `mlartifacts/`. The experiment name comes from `MLFLOW_EXPERIMENT_NAME`, else from `experiment` in `scripts/run.toml`.
- Records are never edited or deleted, and `mlflow gc` is never run.

## Results comment

When a run issue finishes, the agent posts one comment: a note, followed by the output of the results command pasted unchanged.

The table groups runs by command with the seed removed. Each group shows:

- n, the number of failures, and the mean and standard deviation of each metric;
- fingerprints of the commit, environment lock and data;
- with a spec, the arm each group belongs to.

It also flags:

- groups that differ in commit, environment or data, with `git diff --stat` attached when commits differ;
- runs that succeeded without metrics, unfinished runs and deleted runs.

A `规格核对` section follows, quoting the spec. It lists facts about the selected runs, running ones included:

- runs where a Controlled line does not hold or whose key was not recorded (`未记录`);
- runs in no arm or in several;
- arms missing values of an `in` line (counting only running or successful, undeleted runs);
- keys in no section whose values differ (`未声明的差异`);
- arms with no run;
- spec lines it can't read;
- each Adaptable key's values per arm.

When there is no spec or no deviation, the section says so. When all of a study's run issues close, the same table and check over all of them is posted on the study. See [results.py](/research-harness/reference/results-py/) for every line.

## Issue form sections

guard, `merge.py` and the skills read bodies by their `### ` headings, so the heading names can't change:

- **`study`**: Question, Arms, Controlled, Adaptable, Criteria, Budget, Context.
  - The results command reads the three spec sections line by line, one item per line; any line may end with `  # <comment>`.
  - Arms lines are `<arm>: <key>=<value> ...`.
  - Controlled lines are `<key>=<value>  # <reason>` or `<key> in <v1>,<v2>,...  # <reason>`, and the reason is required.
  - Adaptable lines are `<key>  # <rule>`, and the section may be empty.
  - Values that parse as JSON compare as JSON; others compare as strings.
- **`code`**: Goal, Scope, Acceptance, Budget, Merge (`human` or `agent`; default `human`).
- **`run`**: Runs, Budget, Report.

See [Issue forms](/research-harness/reference/issue-forms/).

## PR template, review comment and merge.py

**PR template**: the first line is `Closes #N`, followed by `## Changes` (at most 5 items), `## Acceptance` and `## Out of scope`.

**Review comment**: the first line is `Verdict: pass @ <head SHA>` or `Verdict: changes @ <head SHA>`. The review tool's findings follow, unedited.

**merge.py**:

- `python .github/scripts/merge.py <PR>` merges only when all three of these hold. Otherwise it refuses and waits for the human.
  - The issue the PR closes says `Merge: agent`.
  - The changes, including pre-rename paths, touch no path that `guard.toml` on the PR's base branch lists as protected.
  - The newest `Verdict:` comment is a pass for the current head (an SHA prefix of at least 7 characters).
- `python .github/scripts/merge.py <PR> --human` skips the three checks, because the human has decided.
- Both run `gh pr merge --squash --match-head-commit <SHA>` on the current head. The commit title is `<PR title> (#<PR>)` with an empty body, and branch protection still requires the checks to pass.

See [merge.py](/research-harness/reference/merge-py/).

## Comment formats

These lines come from `AGENTS.md`; their keywords stay in English.

| Format | Shape |
|---|---|
| Decision (issue comment) | `Decision: <choice> — <one-line reason>` |
| Blocker comment | four lines: `Blocked: <one line>`, `Evidence: <links>`, `Options: <at most 3>`, `Recommend: <option>` |
| Report at every stop | three lines: `Done:`, `Waiting for you:`, `Next:` |

## Related

- [Adapt rh to your environment](/research-harness/guides/adapt-your-environment/)
- [run.py](/research-harness/reference/run-py/)
- [results.py](/research-harness/reference/results-py/)
- [merge.py](/research-harness/reference/merge-py/)
- [Issue forms](/research-harness/reference/issue-forms/)
