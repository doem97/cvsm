---
title: results.py
description: The reference results command, which builds the results table from run records and checks every run against the study spec.
sidebar:
  order: 7
---

`scripts/results.py` prints a Markdown results table for the runs of one or more issues, with flags for provenance differences and a `规格核对` (spec check) section. Agents paste its output unchanged into results comments; it reports facts and leaves the judgment of comparability to you.

Source: [`scripts/results.py`](https://github.com/doem97/cvsm/blob/main/scripts/results.py).

## Usage

```sh
python scripts/results.py --issue N [N ...] [--metric M ...] [--spec FILE] [--config scripts/run.toml]
gh issue view P --json body -q .body | python scripts/results.py --issue N --spec -
```

| Option | Meaning |
|---|---|
| `--issue N [N ...]` | Required. The issues whose runs to read (`cvsm.issue` param). Repeats count once. |
| `--metric M [M ...]` | Metrics to show, in this order; may be given more than once. Default: every numeric metric of the runs, sorted. |
| `--spec FILE` | A study issue's body to check the runs against; `-` reads stdin. Without it, the check says no spec was given. |
| `--config FILE` | `run.toml` to read `experiment` and `seed_key` from. Default `scripts/run.toml`. |

It reads the same store and experiment that `run.py` writes to (`MLFLOW_TRACKING_URI`, else `<main clone>/mlflow.db`; `MLFLOW_EXPERIMENT_NAME`, else `experiment`). Deleted runs are read too. It imports `run.py`, so it needs MLflow and must sit next to it.

## Output

The output is in Chinese; metric names, hashes and keys stay as they are. A project that wants another language changes `results.py`. It has four parts.

### 1. Summary line

`#12 的结果：6 个 run，3 组，按去掉 seed 的命令分组。`: the issues, the number of runs and groups, and how runs are grouped.

### 2. The table

Runs are sorted by start time and grouped by command with the seed tokens (`seed_key`) removed. One row per group:

| Column | Content |
|---|---|
| `命令` | the command without the seed |
| `arm` | with a spec only: the arms the group's runs match, `无` for none |
| `n` | runs that exited 0; the statistics use only these |
| `失败数` | runs that ended any other way, not counting runs still `RUNNING` |
| `<metric> 均值` | mean of the metric's latest value over the `n` runs |
| `<metric> 标准差` | sample standard deviation; `—` with fewer than 2 values |
| `commit` | commit prefixes (7 characters) |
| `环境锁` | environment lock hash prefixes (8) |
| `数据` | data manifest hash prefixes (8) |

Each of the last three columns lists the distinct values in the group, `无` for a run without one. Numbers are printed with 4 significant digits.

### 3. Flags (`标注`)

| Flag | When |
|---|---|
| `commit 不同` | runs have more than one commit; `git diff --stat` between the first and the last is attached |
| `环境不同` | environment lock hashes differ |
| `数据不同` | data manifest hashes differ |
| `缺环境锁文件` | some runs miss `env_lock` files, which are listed |
| `工作区不干净` | runs launched from a dirty tree (see artifacts `diff.patch` and `untracked.txt`) |
| `成功退出但没有指标` | runs that exited 0 with no metrics |
| `未完成` | runs still `RUNNING`: running, or killed without finishing their record |
| `已在 MLflow 中删除` | deleted runs, still counted in the table |

With no flag, the section reads `- 无`.

### 4. `规格核对` (spec check)

The check covers every selected run, running ones included, using the `cfg.*` params `run.py` logs from `config.json`. It lists facts in this order, starting with problems of the spec itself:

| Fact | Line shape |
|---|---|
| A Controlled line has no reason | `Controlled 行没有写理由：<line>` |
| A spec line can't be read | `读不懂的规格行：<section>：<line>` |
| Arms or Controlled is missing | `规格里没有 <section> 一节` |
| A key is in several sections | `` `<key>` 出现在多节：<sections> `` |
| Runs that don't record a Controlled key | `` `<line>`：n 个 run 未记录 `<key>`：<run ids> `` |
| Runs where a Controlled line doesn't hold | `` `<line>` 不成立：n 个 run，<run id>（<value>） `` |
| Runs in no arm | `n 个 run 不属于任何 arm：<run ids>` |
| Runs in several arms | `n 个 run 属于多个 arm：<run id>（<arms>）` |
| An arm misses values of an `in` line | `` arm <arm> 缺 `<line>` 的取值：<values> `` |
| A key in no section differs between runs (undeclared difference) | `` 未声明的差异 `<key>`：<value>（n 个 run）、... `` |
| Arms with no run | `没有 run 的 arm：<arms>` |
| Nothing above | `没有偏差` |
| Each Adaptable key's values per arm (always listed) | `` Adaptable `<key>`：<arm> 取 <value>（n 个 run）；... `` |

Rules behind the check:

- A run belongs to an arm when it records every key of that arm's line with an equal value.
- Values that parse as JSON compare as JSON (`1` equals `1.0`); others compare as strings. A key a run didn't record shows as `未记录`.
- An `in` line is checked per arm that has runs, counting only runs that are running or exited 0 and aren't deleted; failed runs cover nothing.
- Undeclared differences are computed over runs that recorded a config.

Without `--spec`, the section reads `- 没有给出规格（--spec）`.

## Example

Six toy runs of the [example spec](/cvsm/guides/plan-a-study/#2-work-out-the-fair-comparison), one lora run launched with a smaller per-device batch and fp16:

```text
#12 的结果：6 个 run，3 组，按去掉 seed 的命令分组。

| 命令 | arm | n | 失败数 | top1 均值 | top1 标准差 | commit | 环境锁 | 数据 |
|---|---|---|---|---|---|---|---|---|
| `python train.py arm=full` | full | 3 | 0 | 0.8505 | 0.00358 | 7ac858e | 73cb3858 | 无 |
| `python train.py arm=lora` | lora | 2 | 0 | 0.8424 | 0.004648 | 7ac858e | 73cb3858 | 无 |
| `python train.py arm=lora batch=32 precision=fp16` | lora | 1 | 0 | 0.8399 | — | 7ac858e | 73cb3858 | 无 |

标注：
- 无

规格核对：
- `train.effective_batch=256` 不成立：1 个 run，0330bc8a46094e03a875e72c6dfd0872（128）
- 未声明的差异 `train.precision`：bf16（5 个 run）、fp16（1 个 run）
- Adaptable `train.per_device_batch`：full 取 64（3 个 run）；lora 取 64（2 个 run）、32（1 个 run）
- Adaptable `train.accum`：full 取 4（3 个 run）；lora 取 4（3 个 run）
```

In English: the effective batch line fails for one run, which took 128; `train.precision` differs between runs although no section declares it; and these are the values each Adaptable key took.

## Related

- [Study spec](/cvsm/concepts/study-spec/)
- [Run records](/cvsm/concepts/run-records/)
- [run.py](/cvsm/reference/run-py/)
- [Interfaces that stay fixed](/cvsm/reference/interfaces/#results-comment)
- [Run experiments](/cvsm/guides/run-experiments/)
