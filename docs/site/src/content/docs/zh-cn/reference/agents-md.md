---
title: AGENTS.md
description: 规则文件的每一节、每条规则的含义，以及卡住它们的测试。
sidebar:
  order: 1
---

`AGENTS.md` 用最多 80 行装下 agent 的全部规则。前八节在每个项目里都一样；最后的 Project 一节由各接入方填写自己的值。

源文件：[`AGENTS.md`](https://github.com/doem97/cvsm/blob/main/AGENTS.md)。

## 形状

| 约束 | 由谁检查 |
|---|---|
| 最多 80 行 | `tests/rules/test_rules.py` |
| 各节依次为 State、Gates、Blockers、Report、Git、Files、Context、Skills、Project | `tests/rules/test_rules.py` |
| 出现 `Decision:`、`Blocked:`、`Evidence:`、`Options:`、`Recommend:`、`Done:`、`Waiting for you:`、`Next:` 这些格式 | `tests/rules/test_rules.py` |
| `guard.toml` 的每一项 `protected`、`markdown`、`forbidden_names`，PR 标题类型和正文行数上限都出现在文中 | `tests/rules/test_rules.py` |
| Project 一节有 `Layout`、`Test`、`Language`、`Protected eval/data paths`、`Run`、`Run records` 这几个字段 | `tests/rules/test_rules.py` |

给 agent 的指令用英文，因为模型对英文指令的理解更准确。`AGENTS.md` 是唯一的指令文件，没有 `CLAUDE.md`。

## State

agent 怎么判断当前状态。每条指令开始时都从 GitHub 读状态，从不依赖聊天记忆。

| 规则 | 含义 |
|---|---|
| 先读状态 | 开着的 `study` 和 `plan` issue 及其子 issue 概况，打开的 PR 及其检查，带 `needs-decision` 的 issue。 |
| 父 issue 与子 issue | `study`（研究）或 `plan`（开发）父 issue 下挂 `code` 或 `run` 子 issue；子 issue 全部关闭后，父 issue 进入待分析。只用这五个 label。 |
| 关系用原生字段 | 父子关系和依赖用 `gh issue create --parent P --blocked-by M` 设置，不写进正文。 |
| 正文按表单写 | issue 正文用 `.github/ISSUE_TEMPLATE/` 里对应表单的 `### ` 各节。 |
| 等依赖 | 被一个还开着的 issue 挡住。 |
| 就绪 | 开着、没被挡住、没有关联分支。 |
| 进行中 | 有关联分支。用 `gh issue develop` 认领，再查 `gh issue develop --list N`；如果还有别的分支也关联上了，删掉自己的，转去做别的。 |
| 谁接着做 | 进行中的 issue，只有指令点名或本会话认领的才接着做。所以并行开几个会话是安全的。 |
| 等你决定 | label `needs-decision` 加一条卡点评论；人答复后去掉 label。 |
| 审查中 | PR 已打开，检查或审查还没完成。 |
| 待合并 | `guard` 和 `test` 全绿，最新的审查是针对当前 head 的 `Verdict: pass @ <head SHA>`。 |
| 完成 | `code` issue 在 PR 合并时关闭（`Closes #N`）；`run` issue 由 agent 贴出结果评论后自己关闭。 |
| 放弃任务、关闭父 issue | 只在人明确指示时做。 |
| 边做边写 | 每次状态变化都当场写到 GitHub 或 git；会话随时可能结束。 |

## Gates

每条指令就是一个目标状态，agent 一直推进，到达目标、关口或卡点才停。

- “做 `#12`”：任务写了 `Merge: agent` 就是合并完成，否则是待合并。“把 `#10` 推到待分析”：它的子 issue 全部关闭。“继续”：推进到下一个关口。
- 四个关口，一切顺利也要停：
  1. **新增或改变已批准的工作：** 发布计划；改任务的 Goal、Scope、Acceptance 或 Merge，或研究的 Arms、Controlled、Adaptable；改受保护路径。
  2. **合并**，除非任务写了 `Merge: agent`。那时 agent 在待合并后用 `python .github/scripts/merge.py <PR>` 合并；碰了受保护路径或 head 没审查通过的，它会拒绝。其他情况，或被拒绝时，待合并的 PR 本身就是请求：不打 label，也不贴卡点评论。只有人明确说合并，agent 才用 `python .github/scripts/merge.py <PR> --human` 合并。
  3. **超出预算：** token、时间或 GPU 小时。
  4. **研究下结论并关闭。**
- 人明确下的指令本身就批准了它点名的事，agent 不再问一遍。
- 每个决定记成一条 issue 评论：`Decision: <choice> — <one-line reason>`。

## Blockers

什么时候停下来问，什么事自己处理。

- **停下来问：** 到了关口；同一个失败连续 3 次；连续 3 次 `changes` 结论；会改变交付物的歧义；研究的某条 Controlled 不改变对比就满足不了。最后一种写成 `Blocked: 这个对比按规格做不了，因为 <X>`，选项是：改实现、放宽规格（关口 1）、或放弃这个对比。
- **不问，自己处理：** 测试或 CI 失败、合并冲突、infra 重试、Scope 内的 bug、在规则内调整 Adaptable 设置（写进结果评论），以及 `changes` 结论（修掉它指出的问题，再请新的审查看新的 head）。
- **pass 之后：** Scope 内的 minor 意见当场修掉；推了修复就再请一次新的审查。然后在 PR 上贴一条评论，对剩下的每条 minor 提出处理办法：开新 issue、并进已有 issue、或不处理。人说合并即批准这些提议（`Merge: agent` 的任务，点名该任务的指令即批准），由执行合并的 agent 照办。
- **Scope 外的 bug：** 开一个新 issue，当前工作照常继续，修复不放进当前 PR。
- **怎么问：** 每个卡点只问一次，带证据、最多 3 个选项和推荐。人在会话里就当场问；不在时打上 `needs-decision`、贴卡点评论，转去做别的就绪任务。
- **卡点评论**四行：`Blocked: <one line>`、`Evidence: <links>`、`Options: <at most 3>`、`Recommend: <option>`。

## Report

每次停下，agent 只汇报三行，带链接：`Done: <完成了什么>`、`Waiting for you: <人要做什么，或没有>`、`Next: <接下来做什么>`。

## Git

- 一个任务 = 一个 issue = 一个分支 `t/<N>-<slug>` = 一个 worktree `../worktrees/<N>-<slug>`（相对主 clone）= 一个 PR。
- PR 标题 `<type>(#N): <summary>`，type 取 `feat`、`fix`、`refactor`、`test`、`exp`、`docs`、`chore` 之一；N 是 PR 关闭的 issue。
- PR 正文用 `.github/pull_request_template.md`：第一行 `Closes #N`，然后 `## Changes`（最多 5 条）、`## Acceptance`（命令和结果）、`## Out of scope`（新开的 issue，没有就写 none）；最多 40 行。
- 不直接运行 `gh pr merge`，只通过 `.github/scripts/merge.py` 合并。不往 main 推，不强推，不打 tag，不碰别的任务的分支。

## Files

- 只在 `.github/guard.toml` 的 `layout` 允许的地方加文件。
- `.md` 只能是 `README.md`、`AGENTS.md`，或在 `docs/`、`.agents/skills/`、`.github/` 里。不加 `CLAUDE.md`。
- 不建名为 `TODO`、`NOTES`、`PLAN`、`PROGRESS` 的文件，大小写和扩展名不限。
- 只改 issue 的 Scope 匹配的路径。
- 受保护：`AGENTS.md`、`.agents/`、`.codex/`、`.claude/`、`.github/`，以及 Project 里的评测和数据路径。只有 Scope 明确列出时才能改。
- 方法任务只改自己的模块、配置和测试；改共享代码要单独开一个任务。
- `docs/` 属于人，只有 Scope 列出时才改。
- 不改、不删运行记录（MLflow run），不运行 `mlflow gc`。

## Context

- 动手之前，读自己的 issue、Scope 内的代码，以及这些代码用到的接口；其余要读的由 skill 列出。
- 只写 GitHub（issue、评论、PR）、Scope 内的文件和运行记录。不留记忆、笔记、文档或讨论记录。
- 决定和结论记在 GitHub 上。
- 每次审查都由按 `review` skill 工作的新会话来做。PR 前审查只拿到 issue 和 diff，PR 审查只拿到 PR 编号（Codex 内置审查另外拿到 issue、它的 Decision，以及研究底下的规格）。绝不把自己的总结或推理交给它。

## Skills

skill 放在 `.agents/skills/<name>/SKILL.md`，每个角色一个：`plan`、`implement`、`review`、`run`。见 [skill](/cvsm/zh-cn/reference/skills/)。

## Project

接入方唯一要改的一节，每个字段一行。表中附 CVSM 自己的值作参考。

| 字段 | 含义 | CVSM 自己的值 |
|---|---|---|
| `Layout` | 代码目录怎么分，共享代码和方法模块各在哪里 | 就是本仓库；没有 `src/`；`scripts/` 放运行和结果的参考脚本 |
| `Test` | 测试命令，和 CI 里跑的一致 | `python -m pytest -q` |
| `Language` | 面向人的文字用什么语言 | 见下文 |
| `Protected eval/data paths` | 不许 agent 随意改的评测和数据路径，与 `guard.toml` 的 `protected` 一致 | 无 |
| `Run` | Run 命令和结果评论命令 | `python scripts/run.py --issue N -- <cmd>`；`python scripts/results.py --issue N` |
| `Run records` | 运行记录写到哪个 MLflow 后端 | `MLFLOW_TRACKING_URI` 指定的后端；不设时用主 clone 根目录下的 `mlflow.db`；实验在 `scripts/run.toml` 里设 |

CVSM 的 `Language` 一行：`README.md` 用英文，中文版在 `docs/README.zh-CN.md`，两者保持同步。其他面向人的文字用中文：PR 正文、issue 和 PR 评论、汇报、表单说明、结果评论。审查评论例外，Verdict 行下面保留审查工具的原文。给 agent 的指令（`AGENTS.md`、skill）、代码、PR 标题和格式关键字（`Closes`、`Decision:`、`Blocked:`、`Verdict:` 等）用英文。接入方在这一行设自己的语言。

## 相关页面

- [关口与卡点](/cvsm/zh-cn/concepts/gates-and-blockers/)
- [状态](/cvsm/zh-cn/concepts/state/)
- [skill](/cvsm/zh-cn/reference/skills/)
- [guard](/cvsm/zh-cn/reference/guard/)
- [接入 CVSM](/cvsm/zh-cn/guides/adopt/)
