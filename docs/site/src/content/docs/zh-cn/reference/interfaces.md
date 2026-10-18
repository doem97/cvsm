---
title: 保持不变的接口
description: skill、guard、merge.py 和结果评论依赖的形状；接入方适配 rh 时要守住它们。
sidebar:
  order: 8
---

skill、guard、`merge.py` 和结果评论都依赖下面这些接口。适配自己的环境时，只换实现，不改它们的形状。

其他的都由你的项目自己决定，并通过自己的 issue 去改：调度器（例如让 Run 命令把任务提交到 SLURM，同时照样写运行记录）、集群和 GPU 分配、数据和产物的存储位置、跟踪后端（例如把 `MLFLOW_TRACKING_URI` 指向团队的 MLflow 服务器）、`guard.toml` 的白名单和受保护路径、CI 的依赖。见[适配你的环境](/research-harness/zh-cn/guides/adapt-your-environment/)。

## Run 命令和结果命令

Run 命令的形状：

```
<run> --issue N [options] -- <cmd>
```

run issue 的每行 Runs 是 `<cmd>` 或 `<options> -- <cmd>`：`run` skill 把选项（如 `--gpus 4`）放在 `--` 之前，命令原样放在 `--` 之后。

结果命令的形状：

```
<results> --issue N [N ...] [--metric M ...] [--spec FILE]
```

`--spec` 读研究 issue 的正文，FILE 为 `-` 时从标准输入读，例如 `gh issue view P --json body -q .body | <results> --issue N --spec -`。

两者的实际命令写在 `AGENTS.md` 的 `Run` 一行。

## 运行记录

每次运行是一个 MLflow run，字段以 `scripts/run.py` 开头的说明为准，细节见 [run.py](/research-harness/zh-cn/reference/run-py/)。

- **`rh.*` 参数**，写入后不能改：
  - 创建时写 `rh.issue`、`rh.command`、`rh.seed`、`rh.host`；
  - 启动前写 `rh.commit`、`rh.dirty`、`rh.env_lock_sha`、`rh.env_lock_missing`、`rh.data_manifest_sha`、`rh.gpus`；
  - 结束时写 `rh.exit_code`。

  没有的值写空字符串，列表用逗号连接。
- **`cfg.*` 参数**：命令写的 `$RUN_DIR/config.json` 一能解析成 JSON 对象就记一次。
  - 命令还在跑时就记，所以运行中的 run 也能核对；文件到结束时才出现的，在结束时记。
  - 嵌套对象展开成点号键 `cfg.<键>`，字符串原样记，其他值记成 JSON。
  - 超过 MLflow 长度上限的键和值截断到上限，完整内容看产物 `config.json`。
- **`cfg.*` 的键**只能由字母、数字、`_ - . / :` 和空格组成，这是 MLflow 对参数名的要求。
  - 含其他字符的键（例如 `label2id` 里的 `tench, Tinca tinca`）和截断后重复的键不记成参数，run.py 在 stderr 列出它们。
  - 研究规格里用到的键要在这个范围内。
- **tag**：`mlflow.source.git.commit`。
- **产物**：
  - 工作区不干净时有 `diff.patch`（`git diff HEAD`）和 `untracked.txt`；
  - 命令的输出 `log.txt`；
  - 命令写进 `$RUN_DIR` 的所有文件，包括 `config.json`。

  `$RUN_DIR/metrics.json`（扁平的 `{名字: 数值}`）记成指标；训练代码也可以用 MLflow 的标准 API 记指标，`MLFLOW_RUN_ID` 让它接到同一个 run。
- **最终状态**：退出码 0 为 `FINISHED`，被信号停止为 `KILLED`，其他为 `FAILED`。
- **后端**由 `MLFLOW_TRACKING_URI` 决定；不设时用主 clone 根目录下的 `mlflow.db`，产物放在旁边的 `mlartifacts/`。实验名取 `MLFLOW_EXPERIMENT_NAME`，否则取 `scripts/run.toml` 的 `experiment`。
- 记录不改不删，不运行 `mlflow gc`。

## 结果评论

run issue 结束时贴一条评论：一段说明，加上结果命令生成的输出，原样粘贴。

表按去掉 seed 的命令分组，每组给出：

- n、失败数、每个指标的均值和标准差；
- commit、环境锁和数据的指纹；
- 给了规格时，每组所属的 arm。

它还会标出：

- 所选 run 之间 commit、环境或数据的不同，commit 不同时附 `git diff --stat`；
- 成功但没有指标、未完成和已删除的 run。

之后是 `规格核对` 一节，按规格的原话列出所选 run（含还在跑的）的事实：

- Controlled 不成立或没记录该键（`未记录`）的 run；
- 不属于任何 arm 或属于多个 arm 的 run；
- 缺 `in` 行某些取值的 arm（只算还在跑或成功退出、没删除的 run）；
- 不在任何一节、取值却不同的键（`未声明的差异`）；
- 没有 run 的 arm；
- 读不懂的规格行；
- 各 Adaptable 键在每个 arm 的取值。

没给规格或没有偏差时，也会写明。研究的 run issue 全部关闭后，覆盖所有 run issue 的同一张表和核对会贴到研究 issue 上。每一行的样子见 [results.py](/research-harness/zh-cn/reference/results-py/)。

## issue 表单的各节

guard、`merge.py` 和 skill 按 `### ` 标题读正文，标题名不能改：

- **`study`**：Question、Arms、Controlled、Adaptable、Criteria、Budget、Context。
  - 结果命令按行读规格三节，每行一项，行尾可加 `  # <注释>`。
  - Arms 每行 `<arm>: <键>=<值> ...`。
  - Controlled 每行 `<键>=<值>  # <理由>` 或 `<键> in <值1>,<值2>,...  # <理由>`，理由必填。
  - Adaptable 每行 `<键>  # <规则>`，可以留空。
  - 值能解析成 JSON 时按 JSON 比较，否则按字符串比较。
- **`code`**：Goal、Scope、Acceptance、Budget、Merge（`human` 或 `agent`，默认 `human`）。
- **`run`**：Runs、Budget、Report。

见 [issue 表单](/research-harness/zh-cn/reference/issue-forms/)。

## PR 模板、审查评论和 merge.py

**PR 模板**：第一行 `Closes #N`，然后 `## Changes`（最多 5 条）、`## Acceptance`、`## Out of scope`。

**审查评论**：第一行是 `Verdict: pass @ <head SHA>` 或 `Verdict: changes @ <head SHA>`，下面原样贴审查工具的意见。

**merge.py**：

- `python .github/scripts/merge.py <PR>`：以下三项都满足才合并，否则拒绝，等人合并。
  - PR 关闭的 issue 写了 `Merge: agent`。
  - 改动（含重命名前的路径）不碰 PR 目标分支上 `guard.toml` 列出的受保护路径。
  - 最新一条 `Verdict:` 评论是对当前 head 的 pass（SHA 至少 7 位前缀）。
- `python .github/scripts/merge.py <PR> --human`：人已经决定，跳过这三项检查。
- 两种方式都用 `gh pr merge --squash --match-head-commit <SHA>` 合并当前 head，提交标题是 `<PR 标题> (#<PR>)`，正文为空；分支保护照常要求检查通过。

见 [merge.py](/research-harness/zh-cn/reference/merge-py/)。

## 评论格式

这几种格式来自 `AGENTS.md`，关键字保持英文。

| 格式 | 形状 |
|---|---|
| 决定记录（issue 评论） | `Decision: <选项> — <一行理由>` |
| 卡点评论 | 四行：`Blocked: <一行>`、`Evidence: <链接>`、`Options: <最多 3 个>`、`Recommend: <选项>` |
| 每次停下的汇报 | 三行：`Done:`、`Waiting for you:`、`Next:` |

## 相关页面

- [适配你的环境](/research-harness/zh-cn/guides/adapt-your-environment/)
- [run.py](/research-harness/zh-cn/reference/run-py/)
- [results.py](/research-harness/zh-cn/reference/results-py/)
- [merge.py](/research-harness/zh-cn/reference/merge-py/)
- [issue 表单](/research-harness/zh-cn/reference/issue-forms/)
