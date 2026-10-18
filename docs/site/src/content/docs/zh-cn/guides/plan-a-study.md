---
title: 计划一个研究
description: 把一个研究问题变成一个已发布的研究 issue，带完整的规格，以及它的代码和运行子 issue。
sidebar:
  order: 2
---

计划研究的方式，是和按 `plan` skill 工作的 agent 把它谈清楚。你说“发布”之前，GitHub 上什么都不会建；“发布”就是关口 01。

## 1. 开始讨论

说出你想研究什么，例如“我们计划一下这个研究”或“我想研究 X”，再告诉 agent 要参考哪些论文、记录和之前的结果。

agent 先读状态：开着的 `study`、`plan` 和 `needs-decision` issue，打开的 PR，你提到的以往研究和任务，以及它们的结果评论和 Decision。它也会读这次要动的代码。讨论期间，它不往 GitHub 或文件里写任何东西。

## 2. 定下公平对比

agent 和你一直讨论到草稿完整：问题是什么、什么样的结果算回答了它、预算多少，研究还要有规格。会影响交付物的歧义，都在这时提出来，不留到以后。

规格有三节，逐节定下来：

1. **Arms**（各组）：各组之间仅有的不同。每组一行，`<arm>: <key>=<value> ...`。
2. **Controlled**（受控）：把常见的混杂因素过一遍，适用的都固定下来：
   - 数据与划分；
   - 预处理与增强；
   - 模型与初始化；
   - 优化器与调度；
   - 有效 batch 与训练长度；
   - 精度；
   - 调参预算；
   - 评测协议与 checkpoint 选择；
   - seed。

   每行都要有取值和理由：一篇论文、你的记录或之前的一个结果。agent 找不到出处的理由，会来问你。seed 和调参网格写成 `in` 行（`seed in 1,2,3  # ...`），这样每组都会跑遍每个值。
3. **Adaptable**（可调整）：可以因 run 而不同的工程设置，例如每卡 batch，各带一条保证对比不被破坏的规则。这一节可以留空。

键是 run 解析后配置（`config.json`）的点号键，由 agent 从代码里取名。代码还不能通过配置设置的项，需要一个 `code` 子 issue。

:::note
每个 run 都会按它自己的记录对照这份规格核对。为什么你批准的是这一层，见[研究规格](/cvsm/zh-cn/concepts/study-spec/)；各行的确切格式见 [issue 表单](/cvsm/zh-cn/reference/issue-forms/#study)。
:::

一份规格示例：

```
### Arms
full: model.adapter=none
lora: model.adapter=lora model.lora.rank=8

### Controlled
data.split=val  # 留出的划分，来自 data.sha256
model.backbone=vit_b16  # 论文 X 表 2
optim.lr=3e-4  # 论文 X 表 2
train.epochs=30  # 论文 X 表 2
train.effective_batch=256  # 论文 X 表 2
seed in 1,2,3  # 同论文 X，用 3 个 seed

### Adaptable
train.per_device_batch  # 按显存调整，有效 batch 固定为 256
train.accum  # 跟随 per_device_batch
```

## 3. 审阅 issue 草稿

agent 按表单里确切的 `### ` 各节起草父 issue 和子 issue：

- **研究**父 issue：依次是 Question、Arms、Controlled、Adaptable、Criteria、Budget、Context。（开发工作用 `plan` 父 issue，只有 `### Goal` 和 `### Context`，没有表单。）
- **`code`** 子 issue：Goal（最多 3 句，写结果而不是步骤）、Scope（路径 glob，不能以通配符开头，取能覆盖工作的最小集合）、Acceptance（从仓库根目录运行的命令，当且仅当任务完成时全部以 0 退出）、Budget（时间，例如 `2h`）和 Merge（默认 `human`；只有低风险、Scope 不匹配任何受保护路径的任务才写 `agent`）。
- **`run`** 子 issue，被它需要的代码 issue 挡住：Runs（每行一条命令，带配置覆盖和 seed；每行只跑一组；一个 issue 跑到的每一组都要跑遍每个 `in` 值；研究的所有 run issue 合起来跑遍每一组）、Budget（GPU 小时）和 Report（指标名，空格分隔）。

agent 把子 issue 排成波次。第 1 波没有依赖；第 k 波只被更早的波次挡住。同一波的 issue 可以并行推进，所以它们的 Scope 必须互不重叠：有重叠时，用 blocked-by 把一个排到另一个后面。这样并行的 PR 就不会冲突。

它用中文把整份草稿和依赖图给你看：

```
Wave 1: A code <title> (Scope: src/pkg/core/**)  |  B code <title> (Scope: src/pkg/methods/foo/**)
Wave 2: C run <title>  blocked by A, B
```

改到你满意为止。

## 4. 发布

:::caution[关口 01：发布]
规格和每个子 issue 都是你想要的，再说“发布”。发布就是批准：之后的每个 run 都要按它核对。
:::

你说“发布”后，agent 先建父 issue，再按波次建子 issue，保证每个依赖在被引用时已经存在。父子关系和依赖用 `gh issue create --parent P --blocked-by M` 设置，不写进正文。它检查父 issue 列出了所有子 issue、每个 blocked-by 都已设好，在父 issue 上记一条 `Decision: 发布 ... — <理由>`，汇报三行（`Done:`、`Waiting for you:`、`Next:`）后停下。除非你的指令给了发布之后的目标，它不会认领或开始任何子 issue。

## 修改已发布的研究

改研究的 Arms、Controlled 或 Adaptable，或者改任务的 Goal、Scope、Acceptance 或 Merge，同样属于关口 01。明确告诉 agent 要改什么，它会改 issue 并在上面记一条 Decision。

## 相关页面

- [研究规格](/cvsm/zh-cn/concepts/study-spec/)
- [关口与卡点](/cvsm/zh-cn/concepts/gates-and-blockers/)
- [运行实验](/cvsm/zh-cn/guides/run-experiments/)
- [issue 表单](/cvsm/zh-cn/reference/issue-forms/)
- [skill：plan](/cvsm/zh-cn/reference/skills/#plan)
