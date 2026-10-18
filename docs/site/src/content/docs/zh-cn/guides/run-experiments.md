---
title: 运行实验
description: 把一个已发布的研究，经过它的代码和运行任务，推进到按规格核对过的结果评论，再交给你下结论。
sidebar:
  order: 3
---

研究发布后，agent 实现它的代码任务，在预算内启动它的 run，并从运行记录生成结果评论。你只在合并、预算、下结论三个关口和卡点处出面。

## 1. 把代码合并进去

对一个代码任务说“做 `#12`”，或者说“把 `#10` 推到待分析”，让 agent 把整个研究推完。研究底下，规格约束着代码：规格里的每个键都经配置设置，解析后的配置由一个进程写进 `$RUN_DIR/config.json`，任何改动都不能改 Controlled 设置，也不能让各组的差异超出 Arms。全新会话审查也按这些检查，违反就阻断 PR。

:::caution[关口 02：合并]
代码任务停在待合并：`guard` 和 `test` 全绿，当前 head 有一条 `Verdict: pass`。你说“合并”或“合并 `#15`”。标了 `Merge: agent` 的任务由 agent 自己通过 `merge.py` 合并；碰了受保护路径、或 head 没有审查通过的，`merge.py` 会拒绝。
:::

## 2. 启动 run

挡住 run issue 的代码 issue 都关闭后，它就就绪了。agent 认领它，从 main 建一个干净的 worktree，所有 Runs 行都从那里启动，这样每条记录对应的都是已合并的代码。run issue 没有 PR。

启动前，它确认每行 Runs 只跑一组，而且本 issue 跑到的每一组都跑遍每条 Controlled `in` 行的每个值。每行都通过 `AGENTS.md` 里 `Run` 一行给出的 Run 命令启动：

```sh
<run> --issue N -- <cmd>
<run> --issue N --gpus 4 -- <cmd>   # 对应 Runs 行 `--gpus 4 -- <cmd>`
```

参考实现 `scripts/run.py` 把每次运行记成一个 MLflow run，并会等空闲的 GPU，所以几行可以同时启动。已经为本 issue 记录过的 run 都算数，会话中断后接着做时，只启动还没有记录的行。

## 3. 启动后马上核对

run 一把配置记成 `cfg.*` 参数，agent 就拿研究的规格运行结果命令：

```sh
gh issue view P --json body -q .body | <results> --issue N --spec -
```

:::note
`规格核对` 列出的、违反某条 Controlled `key=value`、没记录该键、或不属于任何一组或属于多组的 run，agent 都会停掉。列在 `未声明的差异` 下的键是卡点；如果它可能影响结果，先停掉 run。停掉的 run 照样留在记录里。
:::

Adaptable 设置可以按它的规则调整，例如显存不够时调小每卡 batch。agent 会记下每一处调整、对应的 run 和原因，写进结果评论。

## 4. 预算与失败

已用 GPU 小时 = 本 issue 所有 run（含失败的）的运行时长乘以 GPU 数之和。剩余部分按第一个跑完的 run 估算。

:::caution[关口 03：预算]
如果下一个 run 会让总量超出 Budget，agent 在启动前停下，报告已用的小时数、剩余部分的估计和还没启动的 run。你说“继续”，也可以给个新预算。你的指示会作为 Decision 记在 issue 上。
:::

- 失败的 run 留在记录里，也计入表中的 `失败数`。
- 只有 infra 失败才重跑：节点或 GPU 丢失、被抢占、磁盘满、和跟踪后端断开连接。结果看起来不对，不是重跑的理由。
- 代码导致的失败是一个结果，不是 infra 问题。agent 保留它，为这个 bug 开一个 `code` issue，接着跑其他行。修好之后要不要再跑，由你决定。
- 同一个失败连续 3 次，就是卡点。

## 5. 结果评论

每一行都有了结束或失败的记录后，agent 在 run issue 上贴一条评论：一段简短说明（跑了什么、失败与重跑及原因、每一处 Adaptable 调整、有没有超出预算），后面是带 `--metric` 和 `--spec` 的结果命令输出，原样粘贴。不删、不筛、不调整 run 的顺序。然后关闭这个 run issue。

研究的 run issue 全部关闭后，它把覆盖所有 run issue 的同一张表和规格核对贴到研究 issue 上，这就是研究总表。研究随即进入待分析。

## 6. 下结论

:::caution[关口 04：下结论]
读研究总表和它的 `规格核对`。CVSM 只报告记录里有什么，这些 run 还能不能比，由你判断。给出你的结论，例如“`#10` 下结论：……”。agent 记下它；只有你明确指示，才关闭研究。
:::

## 相关页面

- [运行记录](/cvsm/zh-cn/concepts/run-records/)
- [关口与卡点](/cvsm/zh-cn/concepts/gates-and-blockers/)
- [skill：run](/cvsm/zh-cn/reference/skills/#run)
- [run.py 参考](/cvsm/zh-cn/reference/run-py/)
- [results.py 参考](/cvsm/zh-cn/reference/results-py/)
