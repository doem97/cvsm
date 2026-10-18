---
title: 适配你的环境
description: 通过自己的 issue，把 CVSM 适配到你的集群、调度器、存储和跟踪后端，同时守住 skill 依赖的接口。
sidebar:
  order: 4
---

CVSM 只带一个单机的运行参考实现，不带集群、调度器、存储或跟踪服务的适配器。每个接入方通过自己的 issue 适配自己的环境：换的是实现，不改 skill、guard、`merge.py` 和结果评论所依赖的形状。

## 哪些由你决定

下面这些都由你的项目自己决定，并通过自己的 issue 去改：

| 方面 | 例子 |
|---|---|
| 调度器 | 让 Run 命令把任务提交到 SLURM，同时照样写运行记录 |
| 集群和 GPU 分配 | 每行分几张卡、跑在哪些机器上 |
| 数据和产物的存储 | 数据集和运行产物放在哪里 |
| 跟踪后端 | 把 `MLFLOW_TRACKING_URI` 指向团队的 MLflow 服务器 |
| guard | `.github/guard.toml` 的白名单（`layout`）和 `protected` 路径 |
| CI | `.github/workflows/test.yml` 里装的依赖 |
| 结果的语言 | 参考实现 `results.py` 输出中文；要用别的语言就改 `results.py` |

## 哪些保持不变

这些形状要守住，完整列表见[保持不变的接口](/cvsm/zh-cn/reference/interfaces/)。

- Run 命令：`<run> --issue N [options] -- <cmd>`。
- 结果命令：`<results> --issue N [N ...] [--metric M ...] [--spec FILE]`，FILE 为 `-` 时从标准输入读。
- 运行记录：每次运行是一个 MLflow run，带 `run.py` 写的 `cvsm.*` 和 `cfg.*` 参数、产物和最终状态。
- 结果评论，最后是 `规格核对` 一节。
- issue 表单的 `### ` 标题、PR 模板、审查评论，以及 `merge.py` 的规则。

## 怎么适配

1. **为改动开一个 `code` issue。** 适配就是 `plan` 父 issue 下的普通工作：讨论、发布（关口 01），再交给 agent 实现。改受保护路径，需要 Scope 明确列出它，并由人合并。
2. **只换接口背后的实现。** 例如提交到 SLURM 的 Run 命令，仍然接受 `--issue N [options] -- <cmd>`，仍然建一个带同样 `cvsm.*` 参数的 MLflow run，仍然把 `$RUN_DIR/config.json` 记成 `cfg.*` 参数。这样 `run` skill 和结果命令不用改就能用。
3. **更新 `AGENTS.md` Project 一节的 `Run` 和 `Run records` 两行**，写成新的命令和后端。skill 调用的就是那里写的命令。

:::tip
Runs 行可以在 `--` 前带 Run 命令的选项，例如 `--gpus 4 -- python train.py seed=1`。你的启动器要别的选项（分区、时限）时，用同样的方式接收，运行表单就不用改。
:::

## 常见的适配

### 共享或远程的跟踪后端

在会话和 run 的环境里设 `MLFLOW_TRACKING_URI`。不设时，`run.py` 和 `results.py` 用主 clone 根目录下的 `mlflow.db`，产物放在旁边的 `mlartifacts/`。实验名取 `MLFLOW_EXPERIMENT_NAME`，否则取 `scripts/run.toml` 的 `experiment`。不论用什么后端，记录都不改不删，也不运行 `mlflow gc`。

### 几个用户共用一台机器

`run.py` 通过 `<lock_dir>/<host>/` 下的锁文件租用 GPU。`lock_dir` 默认是系统临时目录下的 `cvsm-gpu-locks`，只有共用 `TMPDIR` 的用户才能互相看见。`TMPDIR` 按用户区分时，把 `scripts/run.toml` 的 `lock_dir` 设成他们都能写的同一个本机目录。

### 在新 worktree 里运行

run 在新建的 worktree（`../worktrees/N-<slug>`）里启动，那里没有被忽略的 `.venv` 和数据目录。让 Run 命令照写的样子就能在那里运行：例如用 uv 时，把 `mlflow-skinny`、`sqlalchemy`、`alembic` 放进 dev 组，写成 `uv run python scripts/run.py --issue N -- <cmd>`。数据用绝对路径、环境变量或被跟踪的软链找到。

### 数据指纹

数据目录通常被 git 忽略。维护一个被跟踪的数据清单，例如 `sha256sum` 的输出存成 `data.sha256`，把路径写进 `run.toml` 的 `data_manifest`，并加进 `guard.toml` 的 `layout` 和 `protected`。

### 没有 GPU 的 CI

CI 的 runner 没有 GPU。锁文件固定了 CUDA 版 torch 时，在 `test.yml` 里先装 CPU 版（`pip install torch --index-url https://download.pytorch.org/whl/cpu`），再装项目依赖。job 名 `guard` 和 `test` 保持不变。

## 相关页面

- [接入 CVSM](/cvsm/zh-cn/guides/adopt/)
- [保持不变的接口](/cvsm/zh-cn/reference/interfaces/)
- [run.py 参考](/cvsm/zh-cn/reference/run-py/)
- [results.py 参考](/cvsm/zh-cn/reference/results-py/)
- [原则](/cvsm/zh-cn/concepts/principles/)
