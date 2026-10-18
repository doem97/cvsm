---
title: 合并
description: 为什么 merge.py 是 agent 唯一的合并入口，以及它合并前检查什么。
sidebar:
  order: 4
---

agent 只通过 `.github/scripts/merge.py` 合并，默认还要等你说合并。任务可以写 `Merge: agent` 交给 agent 合并，这时 merge.py 先核对三项事实，再 squash 合并。

## 谁来合并

每个 `code` issue 都有一节 `### Merge`：

- **`human`**（默认）：PR 待合并时，agent 停在[关口 02](/research-harness/zh-cn/concepts/gates-and-blockers/)。待合并的 PR 本身就是请求，不打 label，也不贴卡点评论。你说“合并”，agent 运行 `merge.py <PR> --human`，并在 issue 上记下 `Decision:`。
- **`agent`**：用于 Scope 不碰任何受保护路径的低风险任务。PR 待合并后，agent 自己运行 `merge.py <PR>`。

## merge.py 检查什么

`python .github/scripts/merge.py <PR>` 只在三项都满足时合并：

1. PR 关闭的 issue 写了 `Merge: agent`。
2. 改动的路径（含重命名前的旧路径）都不匹配 PR 目标分支上 `guard.toml` 的 `protected`。
3. 第一行以 `Verdict:` 开头的最新一条评论是 `Verdict: pass @ <SHA>`，且 SHA 是当前 head 的前缀，至少 7 位。

否则它列出原因，以退出码 2 拒绝，PR 等你来合并。

`python .github/scripts/merge.py <PR> --human` 跳过这三项检查，因为你已经决定了。

## 怎么合并

两种方式都对当前 head 运行同一条命令：

```sh
gh pr merge <PR> --squash --match-head-commit <SHA> --subject "<PR 标题> (#<PR>)" --body ""
```

`--match-head-commit` 保证检查之后 head 若有变动就不合并。分支保护照常要求 `guard` 和 `test` 通过。退出码 1 表示 merge.py 读不到 PR，或者合并本身失败了；agent 读报错、排除原因后重试，同一个失败连续 3 次就是卡点。

## 为什么只留一个入口

两种 agent 命令行工具都禁止直接运行 `gh pr merge`：`.claude/settings.json` 的 `permissions.deny` 写了 `Bash(gh pr merge:*)`，`.codex/rules/harness.rules` 把 `gh pr merge` 设为 `forbidden`。AGENTS.md 也用文字写了同一条。只有一个入口，上面的检查就不会被无意绕过。

:::caution[受保护路径一律由你合并]
AGENTS.md、`.agents/`、`.codex/`、`.claude/`、`.github/`，以及你的评测和数据路径，都是受保护路径。只有任务的 Scope 明确列出时，guard 才允许 PR 改它们；不带 `--human` 的 merge.py 拒绝任何碰了它们的 PR。所以这样的 PR 不管 Merge 字段写什么，都要等你说合并。
:::

## main 允许什么

`scripts/setup.sh` 把仓库设成只能通过 squash 合并进 main：

- 只允许 squash 合并，PR 标题作提交标题，正文留空；
- 合并后自动删分支；
- main 只能通过 PR 改动，`guard` 和 `test` 必过，0 个批准，管理员也不能绕过，禁止强推和删除。

GitHub 上不要求批准：你在会话里说的合并就是批准。

## 合并之后

`code` issue 通过 `Closes #N` 自动关闭。执行合并的 agent 照办审查后已获批准的 minor 提议，再删掉这个任务的 worktree 和分支。

## 相关页面

- [审查](/research-harness/zh-cn/concepts/review/)
- [关口与卡点](/research-harness/zh-cn/concepts/gates-and-blockers/)
- [merge.py](/research-harness/zh-cn/reference/merge-py/)
- [guard](/research-harness/zh-cn/reference/guard/)
