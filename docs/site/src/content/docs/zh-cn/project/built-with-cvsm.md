---
title: 用 CVSM 开发 CVSM
description: CVSM 怎样按它自己的流程开发，以及在 GitHub 上去哪里看记录。
sidebar:
  order: 2
---

CVSM 用它自己的流程开发。从第一个提交之后，`main` 上的每次改动都是一个 squash 合并的 PR，关闭 `plan` 父 issue 下的一个任务 issue。

## 计划

开发工作挂在 `plan` 父 issue 下，每个计划有若干 `code` 子 issue：

| 计划 | issue | 内容 |
|---|---|---|
| p001 bootstrap | [#1](https://github.com/doem97/cvsm/issues/1) | 第一版：guard、规则、skill、运行记录、setup 脚本、合并分级，以及来自审查和接入试点的后续修改 |
| p002 fair comparison | [#29](https://github.com/doem97/cvsm/issues/29) | 研究规格：Arms、Controlled 和 Adaptable；让 agent 守住规格；记录 run 的配置并核对 |
| p003 pre-release | [#38](https://github.com/doem97/cvsm/issues/38) | 本文档站、精简的 README 和 Apache-2.0 许可证 |
| p004 rename to CVSM | [#43](https://github.com/doem97/cvsm/issues/43) | 在代码、README 及其配图和本站里改用新名字 |

项目级的 Decision 都在 [#1](https://github.com/doem97/cvsm/issues/1) 上：分支保护、项目的边界、各接口的语言、合并分级、机器账号等。设计文档 [`docs/design/2026-10-16-harness-v1.md`](https://github.com/doem97/cvsm/blob/main/docs/design/2026-10-16-harness-v1.md)（中文）与这些决定保持同步。

## 一次改动怎么落地

1. **计划。** 人和 agent 在会话里讨论这项工作。agent 起草一个 `plan` 父 issue：写明 Goal，把设计写进 Context，下面的 `code` 子 issue 排成 Scope 互不重叠的波次。人说“发布”后，agent 建好这些 issue 并记下 Decision。
2. **实现。** agent 用关联分支 `t/<N>-<slug>` 认领任务，在自己的 worktree 里工作，反复请新的 PR 前审查者，直到 Acceptance 通过。
3. **审查。** 一个只拿到 PR 编号的新会话贴出 `Verdict:` 评论。一个 PR 常常要经过几轮审查才拿到最终的 pass；剩下的 minor 意见在一条评论里逐条提出后续 issue 的建议。
4. **合并。** CVSM 的改动几乎都碰受保护路径（`AGENTS.md`、`.agents/`、`.github/` 等），所以它的任务都写 `Merge: human`。人在会话里说“合并”。从 PR #15 起，由机器账号 `doem1997-claude-bot` 运行 `merge.py --human`，并在任务上记 `Decision: 合并 PR #<PR> — ...`，写明人的原话和审查过的 SHA。
5. **后续。** 批准的 minor 处理建议成为同一计划下的新任务，例如来自 PR #15 审查的 [#16](https://github.com/doem97/cvsm/issues/16)。

## 去哪里看

- `git log --oneline main`：每个 PR 一个提交，标题是 `<type>(#N): <summary> (#PR)`。
- 从 #14 起合并的 PR：上面的 `Verdict:` 评论（最后一条是针对具体 head SHA 的 pass），以及 minor 处理建议。
- 从 [#13](https://github.com/doem97/cvsm/issues/13) 起关闭的任务：带人的指示的合并 Decision。PR #9、#10、#12 的合并记在 #1 上。
- 试点 [#7](https://github.com/doem97/cvsm/issues/7)：在新仓库接入（场景 0）通过，发现的 README 问题开成了 [#23](https://github.com/doem97/cvsm/issues/23) 和 [#24](https://github.com/doem97/cvsm/issues/24)；其余部分由人决定以 not planned 关闭，改为直接在真实项目里接入 CVSM。

## 相关页面

- [状态](/cvsm/zh-cn/project/status/)
- [在会话里工作](/cvsm/zh-cn/start/talk-dont-click/)
- [审查](/cvsm/zh-cn/concepts/review/)
- [合并](/cvsm/zh-cn/concepts/merging/)
