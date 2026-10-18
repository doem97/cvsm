---
title: guard
description: 检查 PR 格式、文件位置、Scope 和受保护路径的必过检查，含 guard.toml 的每个键和 guard.py 的每项检查。
sidebar:
  order: 4
---

guard 是每个 PR 的必过检查。它通过 GitHub API 读 PR，对照 `.github/guard.toml` 和 PR 关闭的 issue 检查，从不 checkout 或执行 PR 里的代码。

源文件：[`.github/guard.toml`](https://github.com/doem97/research-harness/blob/main/.github/guard.toml)、[`.github/scripts/guard.py`](https://github.com/doem97/research-harness/blob/main/.github/scripts/guard.py)、[`.github/workflows/guard.yml`](https://github.com/doem97/research-harness/blob/main/.github/workflows/guard.yml)。

## workflow

| 项 | 值 |
|---|---|
| 触发 | `pull_request_target`，类型 `opened`、`edited`、`synchronize`、`reopened`、`ready_for_review` |
| 运行的代码 | 目标分支上的 workflow 和 `guard.py`，`guard.toml` 也取自那里；从不 checkout PR 的代码 |
| 权限 | `contents: read`、`pull-requests: read`、`issues: read` |
| job 名 | `guard`；分支保护按这个名字要求检查 |
| Python | `ubuntu-latest` 上的 3.12；只用标准库 |
| 环境变量 | `GH_TOKEN`、`PR_NUMBER`、`REPO` |
| 退出码 | 全部通过为 0；任何一项失败，或无法通过 API 读到 PR，为 1 |
| 输出 | 每个失败一行 `guard: <message>`，并在 job summary 里写一节 `## guard` |

:::tip
guard 从 main 运行，所以对 `guard.toml` 的改动要合并之后才生效。某个任务需要一个 `layout` 还不允许的路径时，先在单独的任务里把这条 layout 合并进去。
:::

## guard.toml

| 键 | 类型 | rh 的值 | 含义 |
|---|---|---|---|
| `layout` | glob 列表 | `README.md`、`AGENTS.md`、`.gitignore`、`.agents/**`、`.claude/**`、`.codex/**`、`.github/**`、`docs/**`、`scripts/**`、`tests/**` | 文件可以放在哪里。接入方加上自己的目录和根目录文件（`src/**`、`configs/**`、`pyproject.toml`、锁文件、数据清单）。 |
| `markdown` | glob 列表 | `README.md`、`AGENTS.md`、`docs/**`、`.agents/skills/**`、`.github/**` | `.md` 文件可以放在哪里。 |
| `forbidden_names` | 名字列表 | `TODO`、`NOTES`、`PLAN`、`PROGRESS` | 任何位置都拒收的文件名，大小写和扩展名不限。 |
| `protected` | glob 列表 | `AGENTS.md`、`.agents/**`、`.codex/**`、`.claude/**`、`.github/**` | 只有 issue 的 Scope 明确列出时，PR 才能改的路径。接入方加上评测和数据路径。`merge.py` 也读这个列表。 |
| `types` | 名字列表 | `feat`、`fix`、`refactor`、`test`、`exp`、`docs`、`chore` | 允许的 PR 标题类型。 |
| `max_body_lines` | 整数 | `40` | PR 正文的最大行数。 |
| `test_paths` | glob 列表 | `tests/**` | 不计入 `max_diff_lines` 的路径。 |
| `max_diff_lines` | 整数 | 未设（注释掉的示例为 `400`） | 可选。`test_paths` 之外改动行数（增加加删除）的上限。 |

任务 #39 把仓库根目录的 Apache-2.0 许可证 `LICENSE` 加进 rh 自己的 `layout`。

### glob 语法

| 记号 | 匹配 |
|---|---|
| `**/` | 零个或多个完整目录 |
| `**` | 任意内容，包括 `/` |
| `*` | 除 `/` 以外的任意内容 |
| `?` | 除 `/` 以外的一个字符 |
| 其他字符 | 按字面匹配（包括 `[`） |

glob 必须匹配整个路径。

## 各项检查

guard 跑完所有检查，报告所有失败，顺序如下。

### 1. 关闭引用

- PR 正文恰好关闭一个 issue。关闭关键字是 `close`、`closes`、`closed`、`fix`、`fixes`、`fixed`、`resolve`、`resolves`、`resolved`，大小写不限，后面可带冒号，再跟 `#N`、`owner/repo#N` 或 issue 的 URL。
- 指向别的仓库的引用不算，重复的引用只算一次。

### 2. issue

- 存在且读得到。
- 开着。
- 有 `code` label。
- `### Scope` 一节不为空。
- 没有以通配符（`*` 或 `?`）开头的 Scope 项。

### 3. 每个改动的文件

除删除的文件外，每个文件：

- 路径匹配 `layout`；
- 以 `.md` 结尾的，路径匹配 `markdown`；
- 文件名第一个点之前的部分转成大写后，不在 `forbidden_names` 里。

每个文件（包括删除的），以及重命名前的旧路径：

- 路径匹配某个 Scope 项；
- 如果匹配某个 `protected` glob，就必须有一个 Scope 项既匹配这个路径、又以该 glob 的字面前缀开头。所以 `src/**` 这样宽泛的项永远解锁不了 `.github/**`，Scope 必须自己写出 `.github/...`。

### 4. 标题

PR 标题匹配 `<type>(#N): <summary>`：`type` 取自 `types`，`N` 是关闭的 issue，summary 1 到 72 个字符，且以非空白字符开头。

### 5. 正文

- 正文里有 `## Changes`、`## Acceptance` 和 `## Out of scope` 这三行。
- 不超过 `max_body_lines` 行。

### 6. diff 大小（可选）

设了 `max_diff_lines` 时，`test_paths` 之外的改动行数不超过它。

:::note
guard 不数 `## Changes` 下有几条，最多 5 条是 `AGENTS.md` 里的规则。它也不判断改动的内容，那是全新会话审查的事。
:::

## 在本地运行

在仓库根目录、gh 已登录时：

```sh
REPO=owner/repo PR_NUMBER=15 python .github/scripts/guard.py
```

它从当前目录读 `.github/guard.toml`，所以要得到和 CI 一样的结果，就在 main 的 checkout 里运行。

## 相关页面

- [AGENTS.md：Files](/research-harness/zh-cn/reference/agents-md/#files)
- [merge.py](/research-harness/zh-cn/reference/merge-py/)
- [issue 表单](/research-harness/zh-cn/reference/issue-forms/)
- [接入 rh](/research-harness/zh-cn/guides/adopt/)
- [合并](/research-harness/zh-cn/concepts/merging/)
