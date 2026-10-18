---
title: 关口与卡点
description: 由你拍板的四个计划内停点，以及让 agent 计划外停下的卡点。
sidebar:
  order: 2
---

agent 只在到达目标、碰到四个关口之一或遇到卡点时停下，其余时候一直推进。关口是计划内的停点，一切顺利也要停；卡点是 agent 自己解决不了的问题。

## 四个关口

| 关口 | 什么时候 | 你说什么 |
|---|---|---|
| **01 发布** | 新增或改变已批准的工作：发布计划；改任务的 Goal、Scope、Acceptance 或 Merge，或研究的 Arms（各组）、Controlled（受控）、Adaptable（可调整）；改受保护路径 | “发布”，或批准这处改动 |
| **02 合并** | PR 待合并时，除非任务写了 `Merge: agent` | “合并”，或“合并 #13” |
| **03 预算** | 下一步会超出预算：token、时间或 GPU 小时 | “继续”，也可以给个新预算 |
| **04 下结论** | 研究的子 issue 全部关闭，进入待分析 | 你的结论，例如“`#10` 下结论：……” |

:::caution[关口由你把守]
你明确下的指令就是对它所说之事的批准，agent 会在 issue 上记成 `Decision: <选项> — <一行理由>`。没有这样的指令，agent 不发布、不改规格、不合并需要你合并的任务、不超预算、不关闭研究。机械上能拦住的只有两件事：禁用规则不让 agent 直接运行 `gh pr merge`；不带 `--human` 的 `merge.py` 拒绝碰了受保护路径或没有审查通过的 head。只在你指示时才用 `--human`，和其他关口一样，靠的是 AGENTS.md。
:::

### 关口 02 的细节

任务写了 `Merge: agent` 时，agent 在 PR 待合并后自己用 `python .github/scripts/merge.py <PR>` 合并；碰了受保护路径、或当前 head 没有审查通过的，merge.py 会拒绝。其他情况，或 merge.py 拒绝时，待合并的 PR 本身就是请求：agent 不打 label，也不贴卡点评论，等你说“合并”。见[合并](/research-harness/zh-cn/concepts/merging/)。

### 关口 03 的细节

对运行任务来说，已用 GPU 小时 = 本 issue 所有 run（失败的也算）的墙钟时间 × GPU 数，逐个相加。启动某个 run 会让总数超出 Budget 时，agent 先汇报已用小时数、剩余部分的估计和还没启动的 run，然后等你。

## 卡点

遇到以下情况，agent 也会停下：

- 同一个失败连续 3 次；
- 审查连续 3 次给出 `changes`；
- 目标有歧义，而且会影响交付物；
- 研究的某个 Controlled 设置不改变对比就满足不了。

最后一种的写法是 `Blocked: 这个对比按规格做不了，因为 <X>`，给三个选项：改实现、放宽规格（这属于关口 01），或放弃这个对比。

## agent 怎么问

同一个卡点只问一次，带上证据、最多 3 个选项和推荐。

- **你在会话里**：当场问。
- **你不在**：给 issue 打上 `needs-decision`，贴一条四行的卡点评论，然后转去做别的就绪任务。你答复后，它去掉这个 label。

```text
Blocked: <一行>
Evidence: <链接>
Options: <最多 3 个>
Recommend: <选项>
```

## agent 自己处理的事

下面这些不算卡点，agent 不来问：

- 测试或 CI 失败、合并冲突、infra 失败重试；
- 任务 Scope 内的 bug；
- 审查给出 `changes`：修掉它指出的问题，再请新会话审查新的 head；
- 在规则内调整 Adaptable 设置，并在结果评论里写明。

Scope 外的 bug 另开一个 issue；agent 照常推进，修复不塞进当前 PR。

:::tip
离开一阵回来，问一句“看看等我的”，所有 `needs-decision` 的 issue 和待合并的 PR 一次列全，是清队列最快的办法。
:::

## 相关页面

- [说话，不点页面](/research-harness/zh-cn/start/talk-dont-click/)
- [合并](/research-harness/zh-cn/concepts/merging/)
- [审查](/research-harness/zh-cn/concepts/review/)
- [研究规格](/research-harness/zh-cn/concepts/study-spec/)
