---
title: run.py
description: The reference Run command, which runs one command under an optional GPU lease and records it as an MLflow run.
sidebar:
  order: 6
---

`scripts/run.py` runs one command and records it as one MLflow run, with its provenance, resolved config, output, artifacts and metrics. It is a single-machine reference: a project may replace it, as long as the replacement keeps the [Run command and run record interfaces](/research-harness/reference/interfaces/).

Source: [`scripts/run.py`](https://github.com/doem97/research-harness/blob/main/scripts/run.py). Its module docstring is the reference for the record's fields.

## Usage

```sh
python scripts/run.py [--issue N] [--gpus K] [--config scripts/run.toml] -- <cmd...>
```

| Option | Default | Meaning |
|---|---|---|
| `--issue N` | none | The run issue; logged as `rh.issue`. The `run` skill always passes it. |
| `--gpus K` | 1 if `gpus` is configured, else 0 | GPUs to lease. Must be between 0 and the number of configured GPUs. |
| `--config FILE` | `scripts/run.toml` | The config file. |
| `-- <cmd...>` | required | The command, unchanged. Everything after `--` belongs to it. |

Requirements: Python 3.11 or later, and MLflow (`mlflow`, or `mlflow-skinny` with `sqlalchemy` and `alembic` for a SQLite store). Run it inside the git checkout whose code the command uses.

## run.toml

| Key | Template value | Default if absent | Meaning |
|---|---|---|---|
| `experiment` | `"research-harness"` | `"Default"` | MLflow experiment; `MLFLOW_EXPERIMENT_NAME` overrides it. Created if missing. |
| `env_lock` | `["uv.lock"]` | `[]` | Lock files hashed into `rh.env_lock_sha`; missing ones are listed in `rh.env_lock_missing`. |
| `data_manifest` | `""` | `""` | Tracked data manifest hashed into `rh.data_manifest_sha`; empty means none. |
| `seed_key` | `"seed"` | `"seed"` | Matches `seed=N`, `--seed=N` or `--seed N` in the command. |
| `gpus` | `[]` | `[]` | GPU ids to lease from; empty disables leasing. |
| `lock_dir` | `""` | `""` | GPU lock files go in `<lock_dir>/<host>/`; empty means the system temp directory. |

`env_lock` and `data_manifest` paths resolve against the checkout root.

## What happens

1. **Record.** Connect to the store, create the run and log `rh.issue`, `rh.command`, `rh.seed` and `rh.host`. If the backend is unreachable, nothing is launched.
2. **Lease.** With K > 0, wait until K GPU locks are free. The run already exists, so a waiting run shows as `RUNNING`.
3. **Capture code state,** right before launch, after any wait: log `rh.commit`, `rh.dirty`, `rh.env_lock_sha`, `rh.env_lock_missing`, `rh.data_manifest_sha`, `rh.gpus` and the tag `mlflow.source.git.commit`. A dirty tree also gets the artifacts `diff.patch` and `untracked.txt`.
4. **Launch** the command with its output going to `$RUN_DIR/log.txt`.
5. **Log the config.** Every 0.5 s while the command runs, look for `$RUN_DIR/config.json` and log it once, as soon as it parses as a JSON object.
6. **Finish.** Log the config if not yet done, upload metrics and `$RUN_DIR`, log `rh.exit_code`, and set the final status.

## Store

| Item | Value |
|---|---|
| Backend | `MLFLOW_TRACKING_URI`; when unset, `sqlite:///<main clone>/mlflow.db` |
| Main clone | the parent of git's common directory, so every worktree of a clone shares one store that outlives the worktrees |
| Artifacts of a new experiment | `mlartifacts/` next to the SQLite file; `<main clone>/mlartifacts` for PostgreSQL, MySQL or MSSQL; MLflow's own choice for a tracking server |
| First-time setup | a SQLite store is set up under a `<db>.lock` file lock, because MLflow's migration of a new database fails when several processes run it at once |

The tracking URI is passed to the command but never printed, since it may carry credentials.

## Command environment

| Variable | Value |
|---|---|
| `MLFLOW_RUN_ID` | the run's id, so `mlflow.start_run()` in the command attaches to this run |
| `MLFLOW_TRACKING_URI` | the store run.py writes to |
| `RUN_DIR` | a fresh temporary directory |
| `CUDA_VISIBLE_DEVICES` | the leased GPU ids, comma-joined; set only when `gpus` is configured |

## Params

`rh.*` params can't change once written. Absent values are empty strings, booleans are `true` or `false`, and lists are comma-joined.

| Param | Written | Value |
|---|---|---|
| `rh.issue` | at creation | `--issue` |
| `rh.command` | at creation | the command, shell-joined |
| `rh.seed` | at creation | the seed found with `seed_key` |
| `rh.host` | at creation | the host name |
| `rh.commit` | before launch | `git rev-parse HEAD` |
| `rh.dirty` | before launch | whether `git status` shows changes or untracked files |
| `rh.env_lock_sha` | before launch | sha256 over the existing `env_lock` files, sorted by path |
| `rh.env_lock_missing` | before launch | `env_lock` files not found |
| `rh.data_manifest_sha` | before launch | sha256 of `data_manifest` |
| `rh.gpus` | before launch | the leased GPU ids |
| `rh.exit_code` | at the end | the command's exit code; `-S` when signal S stopped it |

`cfg.*` params come from `$RUN_DIR/config.json`, the resolved config the command writes at start from one process (e.g. rank 0):

- Logged once, as soon as the file parses as a JSON object, so a running run can already be checked. A file that only appears by the end is logged then, before the upload. If logging fails, it is tried once more at the end.
- Nested objects flatten to dotted keys `cfg.<key>`; an empty object is the value `{}`. Strings are logged as they are, other values as JSON.
- Keys and values longer than MLflow's limits (250 and 6000 characters in MLflow 3) are truncated to them. The full content is in the `config.json` artifact.
- Only letters, digits, `_ - . / :` and spaces are allowed in keys. Keys with other characters, and keys that repeat an earlier one after flattening or truncation, are skipped and listed on stderr. Keys used in a study spec must stay within this set.

## Artifacts and metrics

| Artifact | When |
|---|---|
| `diff.patch` (`git diff HEAD`, byte-exact) | the tree is dirty |
| `untracked.txt` (one path per line) | the tree is dirty |
| `log.txt` (stdout and stderr of the command) | always |
| every file the command writes to `$RUN_DIR`, `config.json` included | always |

A flat `{name: number}` in `$RUN_DIR/metrics.json` is logged as metrics, so training code need not import MLflow. It can also log metrics with MLflow's standard API, attached to the same run through `MLFLOW_RUN_ID`. After the upload, `$RUN_DIR` is removed; if the upload fails, it is kept and its path printed.

## Status and exit code

| Final status | When |
|---|---|
| `FINISHED` | exit code 0 |
| `KILLED` | a signal stopped the command, or a stop signal came before launch |
| `FAILED` | any other exit code; 127 when the command can't start |

run.py exits with the command's own status; a command stopped by signal S gives 128 + S. The status is set last, so it overrides a command that ended the run itself with `mlflow.end_run()`.

## GPU locks

- Lock files are `<lock_dir>/<host>/gpu<i>.lock`, held with `flock`. The default `lock_dir` is `rh-gpu-locks` in the system temp directory.
- run.py tries to hold K of the configured GPUs at once; if it can't, it releases all, prints `run.py: waiting for K free GPU(s) of [...]` and retries every 30 s.
- The command inherits the locks, so a lease lasts as long as the command, even if run.py itself is killed.
- The default directory is shared by all users of a host only if they share `TMPDIR`. When `TMPDIR` is per user, set `lock_dir` to a directory they can all write to. The per-host subdirectory run.py creates there is made shareable (sticky and world-writable); directories that already exist keep their permissions.

## Signals

| Signal | Before launch (incl. GPU wait) | After launch |
|---|---|---|
| `SIGTERM` | run ends `KILLED`, nothing launched | forwarded to the command |
| `SIGHUP` | same, unless ignored (`nohup`) | forwarded, unless ignored |
| `SIGINT` (Ctrl-C) | same | not forwarded: it already reaches the command through the terminal |

Stop a background run with `SIGTERM`. Signals ignored at startup stay ignored.

## Related

- [Run records](/research-harness/concepts/run-records/)
- [results.py](/research-harness/reference/results-py/)
- [Interfaces that stay fixed](/research-harness/reference/interfaces/#run-records)
- [Run experiments](/research-harness/guides/run-experiments/)
- [Adapt rh to your environment](/research-harness/guides/adapt-your-environment/)
