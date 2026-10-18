---
title: merge.py
description: agent 唯一的合并入口：三项检查、--human 模式和退出码。
sidebar:
  order: 5
---

`merge.py` 在 PR 的当前 head 上做一次 squash 合并。不带 `--human` 时，它只合并预先批准、审查通过、且不碰受保护路径的任务；带 `--human` 时，它执行人已经做出的合并决定。

源文件：[`.github/scripts/merge.py`](https://github.com/doem97/cvsm/blob/main/.github/scripts/merge.py)。

## 用法

```sh
python .github/scripts/merge.py <PR>           # agent 合并 `Merge: agent` 的任务
python .github/scripts/merge.py <PR> --human   # 按人的明确指示
```

`<PR>` 是 PR 编号。需要有写权限的 `gh` 登录，以及 Python 3.11 或更高版本；只用标准库，解析函数从 `guard.py` 导入。

## 不带 `--human` 时的检查

三项都满足才合并：

| 检查 | 通过的条件 | 读自 |
|---|---|---|
| 合并方式 | PR 正文恰好关闭一个 issue，这个 issue 读得到，且它的 `### Merge` 一节是 `agent`（不分大小写） | PR 正文；issue |
| 受保护路径 | 改动的路径（包括重命名前的旧路径）都不匹配 `guard.toml` 的 `protected` | PR 的文件；PR **目标分支**上的 `.github/guard.toml` |
| 审查 | 第一行以 `Verdict:` 开头的最新一条 PR 评论，严格是 `Verdict: pass @ <SHA>`，`<SHA>` 为 7 到 40 位十六进制，且是当前 head 的前缀（不分大小写） | PR 对话里的评论 |

说明：

- 关闭引用的解析方式同 [guard](/cvsm/zh-cn/reference/guard/#1-关闭引用)。
- 这里的 `protected` 按普通 glob 匹配：和 guard 不同，Scope 列出受保护路径也解锁不了它。碰了受保护路径的 PR 一律由人合并。
- 更新的一条 `Verdict: changes`，或针对旧 head 的 pass，都会挡住合并。第一行不以 `Verdict:` 开头的评论不算，所以列出剩余 minor 的那条评论不能以它开头。

任何一项不满足，它列出所有原因，等人合并。

## `--human`

`--human` 跳过这三项检查，因为人已经决定了。agent 只在会话里收到明确指示时才这样运行，并在 issue 上记 `Decision: 合并 PR #<PR> — <人的指示>`。

## 合并本身

两种方式运行的都是：

```sh
gh pr merge <PR> --squash --match-head-commit <head SHA> --subject "<PR title> (#<PR>)" --body ""
```

- `--match-head-commit` 把合并钉在读到的那个 head 上；中间有人推送，合并就会失败，而不是合进没审查过的代码。
- 提交标题是 `<PR 标题> (#<PR>)`，正文为空。
- 分支保护照常生效：`guard` 和 `test` 必须通过。

## 退出码

| 退出码 | 含义 | agent 怎么做 |
|---|---|---|
| `0` | 已合并。 | 执行已批准的 minor 处理办法；删掉 worktree 和分支。 |
| `2` | 拒绝：有检查没通过（只在不带 `--human` 时）。 | 停下。待合并的 PR 本身就是请求，不打 label，也不贴卡点评论。 |
| `1` | 用法错误；读不到 PR、它的文件、评论或目标分支上的 `guard.toml`；或 `gh pr merge` 失败。 | 读输出，修掉原因（检查还没全绿、head 变了等）后重试。同一失败连续 3 次是卡点。 |

输出是中文，例如 `不合并 PR #15：`，后面每个没通过的检查一行 `- <原因>`，最后是 `等人合并`。

## agent 为什么绕不过它

agent 不能运行 `gh pr merge`：`AGENTS.md` 这样规定，`.claude/settings.json` 用 `Bash(gh pr merge:*)` 拒绝它，`.codex/rules/cvsm.rules` 把它设为 `forbidden`。运行 `python .github/scripts/merge.py` 仍然是允许的。

## 相关页面

- [合并](/cvsm/zh-cn/concepts/merging/)
- [审查](/cvsm/zh-cn/concepts/review/)
- [guard](/cvsm/zh-cn/reference/guard/)
- [AGENTS.md：Gates](/cvsm/zh-cn/reference/agents-md/#gates)
- [保持不变的接口](/cvsm/zh-cn/reference/interfaces/)
