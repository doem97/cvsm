---
title: skill
description: plan、implement、review、run 四个 skill：各读什么、写什么、停在哪里。
sidebar:
  order: 2
---

一个 skill 写清一个角色从头到尾怎么做，最多 120 行。一共四个，Claude Code 和 Codex 读的是同一套文件。

源文件：[`.agents/skills/`](https://github.com/doem97/cvsm/tree/main/.agents/skills)。

## 共同的形状

| 项 | 值 |
|---|---|
| 位置 | `.agents/skills/<name>/SKILL.md`；`.claude/skills` 是指向 `../.agents/skills` 的软链 |
| frontmatter | `name`（与目录同名）和 `description`（什么时候用） |
| 长度 | 最多 120 行，由 `tests/skills/test_skills.py` 检查 |
| 命令 | `<run>` 和 `<results>` 指 `AGENTS.md` Project 里 `Run` 一行给出的 Run 命令和结果命令，即 `--issue N` 之前的部分 |
| 汇报 | plan、implement、run 每次停下都用 `AGENTS.md` Report 的三行汇报；review 以 Verdict 评论结束，并把链接和结论报给请它审查的会话 |
| 语言 | 原样的 skill 规定讨论、草稿、PR 正文、汇报和评论模板用中文；`Language` 一行设了别的语言的项目，要相应改这些地方 |

| skill | 输入 | 从 | 到 | 写什么 |
|---|---|---|---|---|
| `plan` | 一次讨论 | 新工作 | 发布父 issue 和子 issue（关口 1） | issue、一条 Decision |
| `implement` | 一个 `code` issue | 就绪 | 待合并；`Merge: agent` 时到合并完成 | Scope 内的文件、PR、卡点评论 |
| `review` | 一个 PR 编号 | 新会话 | 一条 Verdict 评论 | 一条 PR 评论 |
| `run` | 一个 `run` issue | 就绪 | 贴出结果评论并关闭 | 运行记录、结果评论 |

## plan

*人想讨论新工作，并把它变成一个已发布的 `study`（研究）或 `plan`（开发）父 issue 及其 `code` 和 `run` 子 issue 时使用。*

1. **读状态和背景。** 开着的 `study`、`plan`、`needs-decision` issue；打开的 PR；以往的研究或任务及其评论；用 `<results> --issue <N>` 看以往的运行记录；这次要动的代码，以及人指给它的论文和记录。讨论期间什么都不写。
2. **讨论**，直到草稿完整：问题或目标、什么结果算回答了它、预算，研究还要有规格。Controlled 要把常见混杂因素过一遍（数据与划分；预处理与增强；模型与初始化；优化器与调度；有效 batch 与训练长度；精度；调参预算；评测协议与 checkpoint 选择；seed），每项都有取值和有出处的理由。seed 和调参网格写成 `in` 行。键从代码里取；代码还不能通过配置设置的项，需要一个 `code` 子 issue。
3. **起草 issue**，用表单里确切的 `### ` 各节。`plan` 父 issue 有 `### Goal` 和 `### Context`。Scope 的 glob 不以通配符开头；Acceptance 各行当且仅当任务完成时全部以 0 退出；只有低风险、Scope 不匹配任何受保护路径的任务，Merge 才写 `agent`。
4. **把子 issue 排成波次。** 同一波的 Scope 互不重叠，重叠的用 blocked-by 串起来。把整份草稿和依赖图给人看，改到人批准为止。
5. **发布（关口 1）**，只在明确指示时：先建父 issue，再按波次用 `gh issue create --label ... --parent P --blocked-by ...` 建子 issue，正文经带引号的 heredoc 传入。检查父 issue 列出了所有子 issue。
6. **记录并停下：** 在父 issue 上记 `Decision: 发布 ...`，汇报，停下。改已发布任务的 Goal、Scope、Acceptance 或 Merge，或研究的规格，同样是关口 1。

## implement

*做一个 `code` issue 时使用：从认领、经过全新会话审查，到 PR 待合并；Merge 字段为 `agent` 时一直到合并完成。*

1. **认领并建 worktree。** `gh issue develop N --name t/N-<slug> --base main`，再 `gh issue develop --list N`；还有别的分支关联时，删掉自己的，转去做别的。只在 `../worktrees/N-<slug>` 里工作。
2. **读** issue 和它的 Decision、父 issue 和它的 Decision（研究还有规格）、`AGENTS.md`、Scope 内的代码和它用到的接口。
3. **实现。** 合适时用 TDD。只改 Scope 内的路径（`git diff --name-only origin/main...`）。研究底下，规格里的每个键都经配置设置，解析后的配置由一个进程写进 `$RUN_DIR/config.json`，绝不改 Controlled 设置，也不让各组的差异超出 Arms。Scope 外的 bug 开成新的 `code` issue。提交写成 `<type>(#N): <summary>`，勤推送。
4. **PR 前的内循环。** 跑每一行 Acceptance 和 `Test` 命令；请一个新会话对照 issue 审 diff；修；换新的审查者再来，直到没有阻断问题。
5. **开 PR**，按模板写：英文标题，中文正文。用 `gh pr checks <PR> --watch` 盯检查，guard 或 test 失败自己修，不来问。
6. **外循环。** 发起全新会话的 PR 审查，确认最新的 `Verdict:` 针对的是 PR head。`changes`：修、重跑 Acceptance、推送、再审（连续三次是卡点）。带 minor 的 `pass`：修掉 Scope 内的，推了修复就再请一次新审查，然后贴一条评论，逐条提出剩余 minor 的处理办法。这条评论的第一行不能以 `Verdict:` 开头。
7. **待合并。** `Merge: agent` 时运行 `python .github/scripts/merge.py <PR>`。否则，或它以 2 退出时，停下：待合并的 PR 本身就是请求。以 1 退出（读不到 PR，或合并本身失败）时，修掉原因后重试；同一失败连续 3 次是卡点。人说合并时，运行 `merge.py <PR> --human`，并记 `Decision: 合并 PR #<PR> — ...`。两种合并之后，都要执行已批准的 minor 处理办法，并删掉 worktree 和分支。

## review

*在一个只拿到 PR 编号的新会话里使用：对照 PR 的 issue 审查它，贴一条第一行是 Verdict 的评论。*

1. **读** PR 和它的 diff、它关闭的 issue 及评论、父 issue 上的 `Decision:` 评论，父 issue 是研究时还有它的规格；`AGENTS.md`、`docs/` 里的设计文档（如果有），以及 diff 周围的代码。从不看实现者的会话或总结。要跑 Acceptance 时，在临时 worktree `../worktrees/review-<PR>` 里 checkout head SHA（不用 `FETCH_HEAD`）。
2. **清单：**
   1. 合同：满足 Goal 和 Acceptance，不超出 Scope，遵守各条 Decision；研究底下，规格的每个键都经配置设置并写进 `config.json`，任何改动都不改 Controlled 设置、不让各组的差异超出 Arms。
   2. 在真实输入和出错路径上的正确性，假定 agent 和用户都有能力、且配合。
   3. 与 `AGENTS.md`、设计文档和已有代码一致。
   4. 有锁定合同的测试。
   5. 简洁：合同不需要的东西一概不要。

   第 1 到 4 项是阻断的，其余都是 minor。除非 issue 要求，不要求防御格式错乱、伪造、外人或恶意输入。至少有一条阻断问题才给 `changes`。
3. **贴一条评论。** 贴之前再取一次完整的 head SHA；变了就先审新的 head。第一行严格是 `Verdict: pass @ <full head SHA>` 或 `Verdict: changes @ <full head SHA>`；下面是审查工具自己格式和语言的意见，原样不改，每条指向文件和行。不批准、不打 label、不推送、不改任何东西。删掉临时 worktree。
4. **发起审查**（给实现者看）：一个新的 Claude Code subagent、`codex exec -s danger-full-access`，或 Codex 内置的 `codex exec review`（有 `[P0]` 或 `[P1]` 就记 `changes`）。PR 前审查只拿到 issue 编号和 diff，不贴任何东西。见 [Claude Code 和 Codex](/cvsm/zh-cn/guides/claude-code-and-codex/#发起全新会话审查)。

## run

*做一个 `run` issue 时使用：从认领、在 Budget 内启动它的 Runs，到贴出结果评论并关闭 issue。*

1. **认领并建 worktree**，同 `implement`。所有 run 都从这个干净的 worktree 启动，让每条记录对应已合并的代码。不提交任何东西；run issue 没有 PR。
2. **读** issue（Runs、Budget、Report）和它的 Decision、研究及其规格和 Decision，用 `<results> --issue N` 看已经记录的 run。已有记录的行不再启动，除非之前那次以 infra 失败结束。
3. **在 Budget 内启动。** 确认每行 Runs 只跑一组，本 issue 跑到的每一组都跑遍每个 `in` 值，否则是卡点。启动 `<run> --issue N [options] -- <cmd>`。启动后马上运行 `gh issue view P --json body -q .body | <results> --issue N --spec -`，停掉 `规格核对` 列出的违反 Controlled `key=value`、没记录该键、或不属于任何一组或属于多组的 run。`未声明的差异` 下的键是卡点。Adaptable 调整不出规则，并记下来。GPU 小时 = 运行时长 × GPU 数，对所有 run（含失败的）求和；超出 Budget 之前停在关口 3。
4. **失败。** 失败的 run 保留并计数。只在 infra 失败后重跑，从不因为结果看起来不对而重跑。代码导致的失败是一个结果：开一个 `code` issue，接着做。同一失败连续 3 次是卡点。
5. **结果评论并关闭。** 每一行都有结束或失败的记录后，贴一段说明加上 `<results> --issue N --metric <Report> --spec -` 的输出，原样不改、不筛；关闭 issue。研究的 run issue 全部关闭后，把覆盖所有 run issue 的研究级总表贴到研究上。删掉 worktree 和分支。
6. **汇报**，带上结果评论和研究的链接。研究下结论是关口 4。

## 相关页面

- [AGENTS.md](/cvsm/zh-cn/reference/agents-md/)
- [审查](/cvsm/zh-cn/concepts/review/)
- [计划一个研究](/cvsm/zh-cn/guides/plan-a-study/)
- [运行实验](/cvsm/zh-cn/guides/run-experiments/)
- [Claude Code 和 Codex](/cvsm/zh-cn/guides/claude-code-and-codex/)
