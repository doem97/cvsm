---
title: issue 表单
description: 研究、代码和运行三种 issue 表单，它们生成的每个 `### ` 节，以及哪个工具读哪一节。
sidebar:
  order: 3
---

`.github/ISSUE_TEMPLATE/` 里的三种 issue 表单，固定了每个任务和研究正文的各节。guard、`merge.py`、结果命令和各个 skill 都按 `### ` 标题读正文，所以标题名不能改。

源文件：[`study.yml`](https://github.com/doem97/cvsm/blob/main/.github/ISSUE_TEMPLATE/study.yml)、[`code.yml`](https://github.com/doem97/cvsm/blob/main/.github/ISSUE_TEMPLATE/code.yml)、[`run.yml`](https://github.com/doem97/cvsm/blob/main/.github/ISSUE_TEMPLATE/run.yml)。

## 总览

| 表单 | 表单名 | label | 各节，按顺序 |
|---|---|---|---|
| `study.yml` | 研究 | `study` | Question、Arms、Controlled、Adaptable、Criteria、Budget、Context |
| `code.yml` | 代码任务 | `code` | Goal、Scope、Acceptance、Budget、Merge |
| `run.yml` | 运行任务 | `run` | Runs、Budget、Report |

开发用的父 issue（label `plan`）没有表单，正文是 `### Goal` 和 `### Context`。agent 严格按这些节写正文，父子关系和依赖用 `gh issue create --parent P --blocked-by M` 设置，不写进正文。表单说明用中文，也就是 CVSM 自己面向人的语言。

## study

一个研究问题，由 `code` 和 `run` 子 issue 来回答。Arms、Controlled、Adaptable 是每个 run 都要对照的规格。

| 节 | 字段 | 必填 | 格式 |
|---|---|---|---|
| `### Question` | textarea | 是 | 这个研究要回答的问题。 |
| `### Arms` | textarea | 是 | 每行一组：`<arm>: <key>=<value> [<key>=<value> ...]`。只写各组之间不同的设置，例如 `lora: model.adapter=lora model.lora.rank=8`。 |
| `### Controlled` | textarea | 是 | 每行一个设置，理由必填：`<key>=<value>  # <理由>`（每个 run 都取这个值），或 `<key> in <v1>,<v2>,...  # <理由>`（每组都要跑遍这些值，如 seed 和调参网格）。 |
| `### Adaptable` | textarea | 否 | 每行一个：`<key>  # <规则>`。可以因 run 而不同、执行中可以按规则调整的工程设置，例如 `train.per_device_batch`。可以留空。 |
| `### Criteria` | textarea | 是 | 什么样的结果算回答了这个问题。 |
| `### Budget` | input | 否 | GPU 小时和时间，例如 4 GPU 小时、1 天。 |
| `### Context` | textarea | 否 | 相关研究、结果评论和论文的链接。 |

`results.py` 读规格行的规则：

- 每行一项；行尾可加 `  # <注释>`（`#` 前要有空白）。
- 键是 run 的 `config.json` 里的点号键。一个键最多出现在一节里。
- 值能按 JSON 解析（数字、`true`/`false`/`null`、列表）就按 JSON 比较，所以 `1` 和 `1.0` 相等；否则按字符串比较。
- `in` 的取值按括号外的逗号切分，所以一个取值可以是 JSON 列表。
- Controlled 的表单说明列出了要逐项覆盖的常见混杂因素：数据与划分、预处理与增强、模型与初始化、优化器与调度、有效 batch 与训练长度、精度、调参预算、评测协议与 checkpoint 选择、seed。

## code

一次代码或文件改动，限定在固定的 Scope 内。

| 节 | 字段 | 必填 | 格式 | 谁读 |
|---|---|---|---|---|
| `### Goal` | textarea | 是 | 最多 3 句；写结果，不写步骤。 | implement、review |
| `### Scope` | textarea | 是 | 路径 glob，每行一个，不能以通配符开头。 | guard |
| `### Acceptance` | textarea | 是 | 命令，每行一个，从仓库根目录运行。 | implement、review |
| `### Budget` | input | 否 | 时间，例如 `2h`。 | implement |
| `### Merge` | dropdown | 默认 `human` | `human`：由人合并。`agent`：审查通过后由 agent 用 `merge.py` 合并。碰了受保护路径的 PR 一律由人合并。 | `merge.py` |

guard 读 Scope 时，会去掉行首的 `- ` 或 `* ` 和反引号，并忽略 `_No response_`。glob 里 `**` 可以跨 `/`，`*` 和 `?` 不跨；其他字符都按字面匹配。

## run

一组实验运行，结果以一条评论贴出。

| 节 | 字段 | 必填 | 格式 |
|---|---|---|---|
| `### Runs` | textarea | 是 | 每行一条命令，包含配置覆盖和 seed。带 Run 命令的选项时写成 `<options> -- <cmd>`，例如 `--gpus 4 -- python train.py seed=1`。 |
| `### Budget` | input | 否 | GPU 小时，例如 2。 |
| `### Report` | input | 否 | 指标名，空格分隔；作为 `--metric` 传给结果命令。 |

每行 Runs 只跑一组。一个 issue 跑到的每一组，都要跑遍每条 Controlled `in` 行的每个值；研究的所有 run issue 合起来要跑遍每一组。

## 相关页面

- [研究规格](/cvsm/zh-cn/concepts/study-spec/)
- [计划一个研究](/cvsm/zh-cn/guides/plan-a-study/)
- [guard](/cvsm/zh-cn/reference/guard/)
- [results.py](/cvsm/zh-cn/reference/results-py/)
- [保持不变的接口](/cvsm/zh-cn/reference/interfaces/)
