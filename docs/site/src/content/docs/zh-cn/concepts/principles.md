---
title: 原则
description: CVSM 背后的设计原则，以及每条原则让什么进来、把什么挡在外面。
sidebar:
  order: 7
---

CVSM 有意做得很小：规则不多，每条对应 agent 推进研究时的一种主要失败。这些原则解释它为什么长成这样，以及它有意留给你的是什么。

## CVSM 运行在 GitHub 和你自己的机器上

流程状态都在 issue、PR、检查和分支保护里，运行记录在 MLflow 里。没有 CVSM 服务器、数据库或命令行工具。所有东西都能在 GitHub 自己的界面里看到，接入 CVSM 就是复制文件。

## 状态在 GitHub 上，会话什么都不存

仓库里没有状态、计划或进度文件，会话也从来不是记录。每次状态变化都当场写回 GitHub 或 git，会话随时可以断，不会丢东西；新会话读一遍就知道进展到哪里。见[状态](/cvsm/zh-cn/concepts/state/)。

## CVSM 记录事实，判断留给你

CVSM 只记录事实、展示差异。它不定 seed 数，不设计实验，不决定何时重跑，也不判断 run 能不能比，这些由你在[研究规格](/cvsm/zh-cn/concepts/study-spec/)和指令里定。分析、可视化，以及 agent 在任务内部怎么实现，它也都不管。

## 关口少而固定

agent 一直推进，直到到达目标、碰到[四个关口](/cvsm/zh-cn/concepts/gates-and-blockers/)之一或遇到卡点。关口对每个项目都一样，也是仅有的计划内停点。人只在会话里做决定，GitHub 上的每个操作都由 agent 执行并记录。见[在会话里工作](/cvsm/zh-cn/start/talk-dont-click/)。

## 能机械检查的，就机械检查

每条规则放在最能保证它的地方。脚本查得了的，交给 `guard` 和 `merge.py`；脚本查不了的，在 AGENTS.md 里写一行，由新会话[审查](/cvsm/zh-cn/concepts/review/)把关。需要人合并的改动，你在合并时再看一遍。

## 按高能力模型来写

规则短而具体：AGENTS.md 最多 80 行，每个 skill 最多 120 行。它们假定 agent 能遵守写清楚的规则。脚本固化流程，但不防御格式错乱、冒充或外人；除非任务要求，审查也不要求这类防御。

## CVSM 是你仓库里的一组文件

CVSM 不带集群、调度器、存储或跟踪服务的适配器。`run.py` 和 `results.py` 只是单机参考实现。每个接入方通过自己的 issue，把集群、调度器（例如 SLURM）和跟踪后端适配到自己的环境，同时守住[保持不变的接口](/cvsm/zh-cn/reference/interfaces/)。

:::tip
CVSM 的每条规则都针对 agent 推进研究时的一种失败。给自己的项目加规则也用同一个标准：往 AGENTS.md 加一行之前，先说出它防的是哪种失败。
:::

## 相关页面

- [概览](/cvsm/zh-cn/start/overview/)
- [保持不变的接口](/cvsm/zh-cn/reference/interfaces/)
- [适配自己的环境](/cvsm/zh-cn/guides/adapt-your-environment/)
- [设计文档](https://github.com/doem97/cvsm/blob/main/docs/design/2026-10-16-harness-v1.md)
