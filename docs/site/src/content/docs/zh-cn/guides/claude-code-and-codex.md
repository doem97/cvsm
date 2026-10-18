---
title: Claude Code 和 Codex
description: Claude Code 和 Codex 怎样读到同一套规则和 skill，各自怎样被禁止直接合并，又各自怎样发起全新会话审查。
sidebar:
  order: 5
---

rh 用一套文件同时支持 Claude Code 和 Codex：两者都读 `AGENTS.md` 和同样的四个 skill，各自有一份禁止 `gh pr merge` 的配置。两种工具的会话可以同时开，各做各的任务。

## 各自读什么

| | Claude Code | Codex |
|---|---|---|
| 规则 | `AGENTS.md` | `AGENTS.md` |
| skill | `.claude/skills`，指向 `../.agents/skills` 的软链 | `.agents/skills` |
| 禁止合并 | `.claude/settings.json`：`permissions.deny` 里的 `Bash(gh pr merge:*)` | `.codex/rules/harness.rules`：`gh pr merge` 设为 `forbidden` |
| 机器账号（可选） | `.claude/settings.local.json` 设 `GH_CONFIG_DIR` | `.codex/config.toml` 设 `GH_CONFIG_DIR` |

`AGENTS.md` 是唯一的指令文件。不要加 `CLAUDE.md`：guard 会拒收放在允许位置之外的 `.md`，harness 也只认 `AGENTS.md`。

## 确认规则已加载

1. **Codex：信任项目。** 项目要先被 Codex 信任，它才会读项目里的 `.codex/`。在仓库根目录交互式运行一次 `codex`，接受信任提示（`codex exec -s danger-full-access` 不提示就会把项目记为信任）。
2. **Codex：检查规则文件。** `codex execpolicy check --rules .codex/rules/harness.rules gh pr merge 1` 应输出 `forbidden`。这只检查文件本身。
3. **Codex：检查真实会话。** 在仓库里开一个 Codex 会话，让它运行 `gh pr merge --help`，应该被规则拦下（这条命令即使放行也不会合并任何东西）。确认四个 skill（`plan`、`implement`、`review`、`run`）都列出来了。
4. **Claude Code：检查真实会话。** 在仓库里开一个会话，确认四个 skill 都列出来了。

:::caution[只有 merge.py 能合并]
agent 只能通过 `.github/scripts/merge.py` 合并。Codex 在选择沙箱之前就按规则拒绝命令，所以即使是 full permission 的会话，这条禁令也生效；Claude Code 用 `permissions.deny` 做同一件事。
:::

## 发起全新会话审查

实现者从不审查自己的 PR。它按 `review` skill 第 4 节，另起一个只拿到 PR 编号的审查者：

- **Claude Code：** 一个新的 subagent，提示词是 “Follow `.agents/skills/review/SKILL.md` for PR #&lt;PR&gt;.”
- **Codex：** `codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #<PR>."`。`codex exec` 默认在没有网络的沙箱里运行，而 `gh` 需要网络，所以要加 `-s danger-full-access`。
- **Codex 内置审查：** 在 PR head 的 checkout 里运行 `codex exec review "<指令>"`。Codex 0.163 里 `--base` 不能和指令同时用，所以由指令写明基线（`git diff origin/main...HEAD`），并带上 issue 正文、issue 及其父 issue 上的 Decision、父 issue 是研究时它的规格，以及审查清单。它的输出给每条意见标 `[P0]` 到 `[P3]`：有 `[P0]` 或 `[P1]` 就记 `changes`，否则记 `pass`。由运行它的会话把输出原样贴在 Verdict 行下面，前提是 PR head 仍然等于审查过的 SHA。

开 PR 之前的内循环里，实现者只把 issue 编号和 diff 交给一个新的 subagent，或在 worktree 里交给 `codex exec -s danger-full-access`。这种 PR 前审查不往 GitHub 贴任何东西。

:::tip
审查者用哪种工具都行，和实现者用的是哪种无关。要紧的是它只从 PR 编号出发，从不看实现者的会话或总结。
:::

## 两种工具共用机器账号

如果 agent 用机器账号，两种工具都要把 `GH_CONFIG_DIR` 指向它的 gh 登录目录。用的是两个本地文件，路径都写进 `.git/info/exclude`：

- `.claude/settings.local.json`：`{"env": {"GH_CONFIG_DIR": "<dir>"}}`
- `.codex/config.toml`：

  ```toml
  [shell_environment_policy]
  set = { GH_CONFIG_DIR = "<dir>" }
  ```

这两个文件只在主 clone 里。从主 clone 启动的会话会把这个设置传给它派出的 agent；直接在 worktree 里开会话，就要先在那里也放一份。完整设置见[接入 rh](/research-harness/zh-cn/guides/adopt/#可选给-agent-一个机器账号)。

## 相关页面

- [审查](/research-harness/zh-cn/concepts/review/)
- [说话，不点页面](/research-harness/zh-cn/start/talk-dont-click/)
- [skill](/research-harness/zh-cn/reference/skills/)
- [AGENTS.md](/research-harness/zh-cn/reference/agents-md/)
- [merge.py](/research-harness/zh-cn/reference/merge-py/)
