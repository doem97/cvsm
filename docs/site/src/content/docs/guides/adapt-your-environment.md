---
title: Adapt CVSM to your environment
description: Fit CVSM to your cluster, scheduler, storage and tracking backend through your own issues, while keeping the interfaces the skills depend on.
sidebar:
  order: 4
---

CVSM ships a single-machine reference for runs and no adapters for clusters, schedulers, storage or tracking services. Each adopter fits its own environment through its own issues, and changes implementations, not the shapes the skills, guard, `merge.py` and the results comment depend on.

## What is yours to change

Everything below is your project's to decide, through its own issues:

| Area | Examples |
|---|---|
| Scheduler | a Run command that submits to SLURM and still writes run records |
| Cluster and GPU allocation | how many GPUs a line gets, which hosts it runs on |
| Data and artifact storage | where datasets and run artifacts live |
| Tracking backend | `MLFLOW_TRACKING_URI` pointing at a team MLflow server |
| guard | the allow-list (`layout`) and `protected` paths in `.github/guard.toml` |
| CI | the dependencies installed in `.github/workflows/test.yml` |
| Results language | the reference `results.py` writes Chinese text; change `results.py` for another language |

## What stays fixed

Keep these shapes. They are listed in full in [Interfaces that stay fixed](/cvsm/reference/interfaces/).

- The Run command: `<run> --issue N [options] -- <cmd>`.
- The results command: `<results> --issue N [N ...] [--metric M ...] [--spec FILE]`, with FILE `-` reading stdin.
- Run records: one MLflow run per run, with the `cvsm.*` and `cfg.*` params, artifacts and final statuses that `run.py` writes.
- The results comment, ending with the `规格核对` section.
- The `### ` headings of the issue forms, the PR template, the review comment and `merge.py`'s rules.

## How to adapt

1. **Open a `code` issue for the change.** Adapting is ordinary work under a `plan` parent: discuss it, publish it (gate 01) and let an agent implement it. Changes to protected paths need their Scope to name them, and a human merge.
2. **Change the implementation behind the interface.** For example, a SLURM Run command still takes `--issue N [options] -- <cmd>`, still creates one MLflow run with the same `cvsm.*` params, and still logs `$RUN_DIR/config.json` as `cfg.*` params, so the `run` skill and the results command work unchanged.
3. **Update the `Run` and `Run records` lines** in the Project section of `AGENTS.md` to the new commands and backend. The skills call exactly what is written there.

:::tip
A Runs line may carry Run-command options before `--`, such as `--gpus 4 -- python train.py seed=1`. If your launcher needs other options (a partition, a time limit), accept them the same way and the run form needs no change.
:::

## Common adaptations

### A shared or remote tracking backend

Set `MLFLOW_TRACKING_URI` in the environment of the sessions and runs. When it is unset, `run.py` and `results.py` use `mlflow.db` at the main clone root, with artifacts beside it in `mlartifacts/`. The experiment name comes from `MLFLOW_EXPERIMENT_NAME`, else from `experiment` in `scripts/run.toml`. Run records are never edited or deleted, and `mlflow gc` is never run, whatever the backend.

### Several users on one machine

`run.py` leases GPUs through lock files in `<lock_dir>/<host>/`. By default `lock_dir` is `cvsm-gpu-locks` in the system temp directory, shared only by users who share `TMPDIR`. If `TMPDIR` is per user, set `lock_dir` in `scripts/run.toml` to one local directory they can all write to.

### Runs in fresh worktrees

Runs launch in a fresh worktree (`../worktrees/N-<slug>`) with no ignored `.venv` or data directories. Make the Run command work there as written: for example with uv, put `mlflow-skinny`, `sqlalchemy` and `alembic` in the dev group and write `uv run python scripts/run.py --issue N -- <cmd>`. Find data through absolute paths, environment variables or tracked symlinks.

### Data fingerprints

Data directories are usually ignored by git. Keep a tracked data manifest, e.g. `sha256sum` output saved as `data.sha256`, set its path in `data_manifest` in `run.toml`, and add it to both `layout` and `protected` in `guard.toml`.

### CI without GPUs

CI runners have no GPU. If your lock file pins a CUDA build of torch, install the CPU build first in `test.yml` (`pip install torch --index-url https://download.pytorch.org/whl/cpu`), then the project's dependencies. Keep the job names `guard` and `test`.

## Related

- [Adopt CVSM](/cvsm/guides/adopt/)
- [Interfaces that stay fixed](/cvsm/reference/interfaces/)
- [run.py reference](/cvsm/reference/run-py/)
- [results.py reference](/cvsm/reference/results-py/)
- [Principles](/cvsm/concepts/principles/)
