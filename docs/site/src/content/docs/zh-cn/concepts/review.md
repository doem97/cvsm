---
title: 审查
description: 每个改动怎样由新会话审查，Verdict 行又怎样决定能不能合并。
sidebar:
  order: 3
---

每个 PR 都由一个新会话审查：它只拿到 PR 编号，从不看实现者的会话。它贴的唯一一条评论以针对某个 head SHA 的 `Verdict:` 行开头，PR 能不能算待合并就看这一行。

## 为什么要新会话

实现者的会话里满是它自己的推理，审查者读了就会带上同样的盲点。所以审查者是一个新会话，读的是实现者本来就要满足的那些材料：

- PR 和它的 diff；
- 它关闭的 issue（`Closes #N`）及其评论；
- 这个 issue 的父 issue 上的 Decision；
- 父 issue 是研究时，它的规格：Arms（各组）、Controlled（受控）、Adaptable（可调整）。

此外它还读 AGENTS.md、项目的设计文档和 diff 周围的代码。审查者从不拿到实现者的总结或推理。它不改代码，唯一的写操作是一条 PR 评论。

## 两层循环

**内层循环，开 PR 之前。** 实现者跑完每条 Acceptance 命令和项目测试，再请一个新会话对照 issue 审 diff。这次审查不往 GitHub 贴任何东西。实现者修掉值得修的问题，再换一个新的审查者开始下一轮，直到 Acceptance 全部通过、没有阻断问题。质量主要来自这一层。

**外层循环，PR 上。** PR 开出来后，一次新会话的 PR 审查是最后一道独立检查。给出 `changes` 时，实现者修掉问题、重跑 Acceptance，再请新会话审查新的 head。连续 3 次 `changes` 是卡点。

## 审查清单

1. **合同**：diff 满足 issue 的 Goal 和 Acceptance，不超出 Scope，遵守相关的 Decision。父 issue 是研究时，规格里的每个键都经配置设置并写进 `$RUN_DIR/config.json`，改动不改 Controlled 设置，也不让各组的差异超出 Arms。
2. **正确性**：在真实输入和出错路径上都对。
3. **一致性**：与 AGENTS.md、设计文档和现有代码一致。
4. **测试**：测试锁住合同，回归时会失败。
5. **简洁**：合同用不到的东西一概不加。

违反第 1 到 4 项的是阻断问题，其余都是 minor。至少有一个阻断问题才给 `changes`。审查者假定 agent 是能干且配合的，不要求防御格式错乱、伪造或外人，除非 issue 要求。

## Verdict 评论

```text
Verdict: pass @ <完整的 head SHA>

<审查工具自己格式和语言的意见>
```

- 第一行恰好是 `Verdict: pass @ <SHA>` 或 `Verdict: changes @ <SHA>`，SHA 是贴之前刚取的完整 head SHA。head 变了，就先审新的 head。
- 下面原样贴审查工具的意见，不改写、不翻译，每条指向文件和行号。这是项目面向人的语言规定里唯一的例外。
- `merge.py` 读第一行以 `Verdict:` 开头的最新一条评论，要求它是 pass，且 SHA 是当前 head 的前缀，至少 7 位。

## 怎么发起审查

- **Claude Code**：开一个新 subagent，提示词是 “Follow `.agents/skills/review/SKILL.md` for PR #13.”
- **Codex**：`codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #13."`。要加这个参数，因为 `gh` 需要联网。
- **Codex 内置审查**：在 PR head 的 checkout 里运行 `codex exec review`，把 issue、它的 Decision、父 issue 的规格和审查清单交给它。有 `[P0]` 或 `[P1]` 的问题就记 `changes`，否则记 `pass`；由运行它的会话把输出原样贴在 Verdict 行下面。

## pass 之后的 minor 意见

pass 就结束循环。实现者把 Scope 内的 minor 意见当场修掉；推了修复的，再请一次新会话审查。然后在 PR 上贴一条评论，对剩下的每条 minor 提出处理办法：开新 issue、并进已有 issue，或不处理，各附一行理由。你说合并就是批准这些提议，由执行合并的 agent 照办。

:::tip
即使项目面向人的文字是中文，审查意见也可能是英文。你不必去 GitHub 上读：审查者会把结论和评论链接报给发起审查的会话，由那个会话讲给你听。
:::

## 相关页面

- [合并](/cvsm/zh-cn/concepts/merging/)
- [关口与卡点](/cvsm/zh-cn/concepts/gates-and-blockers/)
- [skill](/cvsm/zh-cn/reference/skills/)
- [Claude Code 和 Codex](/cvsm/zh-cn/guides/claude-code-and-codex/)
