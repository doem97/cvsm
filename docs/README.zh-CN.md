<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-zh-dark.svg">
  <img alt="research-harness：agent 干活，你来把关。agent 的轨迹穿过四道人的关口（发布、合并、预算、下结论），汇成一张按研究规格核对过的结果表。" src="assets/hero-zh-light.svg" width="100%">
</picture>

**让编码 agent 推进你的机器学习研究，同时让每个对比都公平。**

rh 是一套模板，复制进研究仓库就能用，不是一个服务。状态放在 GitHub issue 里，步骤写在一个规则文件（`AGENTS.md`）和四个 skill 里，Claude Code 和 Codex 都能用。你在会话里只在四个关口做决定：发布、合并、预算、下结论。每个 run 都按它自己的记录，对照你批准的研究规格核对。

![状态：预发布](https://img.shields.io/badge/%E7%8A%B6%E6%80%81-%E9%A2%84%E5%8F%91%E5%B8%83-5C616B?style=flat-square&labelColor=0B0C0F) ![agent：Claude Code 和 Codex](https://img.shields.io/badge/agent-Claude_Code_%C2%B7_Codex-5C616B?style=flat-square&labelColor=0B0C0F) ![安装：无需服务](https://img.shields.io/badge/%E5%AE%89%E8%A3%85-%E6%97%A0%E9%9C%80%E6%9C%8D%E5%8A%A1-5C616B?style=flat-square&labelColor=0B0C0F) ![人的关口：4](https://img.shields.io/badge/%E4%BA%BA%E7%9A%84%E5%85%B3%E5%8F%A3-4-F04A0E?style=flat-square&labelColor=0B0C0F) ![run：按规格核对](https://img.shields.io/badge/run-%E6%8C%89%E8%A7%84%E6%A0%BC%E6%A0%B8%E5%AF%B9-2F6FE0?style=flat-square&labelColor=0B0C0F) ![许可证：Apache-2.0](https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF%E8%AF%81-Apache--2.0-5C616B?style=flat-square&labelColor=0B0C0F)

[English](../README.md) · [文档](https://doem97.github.io/research-harness/zh-cn/) · [快速开始](https://doem97.github.io/research-harness/zh-cn/start/quick-start/)

## 规格就是合同

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/contract-zh-dark.svg">
  <img alt="一张研究规格卡片，你能读懂，在关口 01 批准。下面是越来越密的 agent 工作层：代码、配置、启动和运行。一支蓝色箭头从六条运行记录指回规格，旁边是这些记录得出的规格核对。" src="assets/contract-zh-light.svg" width="100%">
</picture>

规格写明各组（arm）之间的不同、固定不变的设置（各带理由），以及可以调整的设置。它是你能真正读懂的那一层。规格以下的事都由 agent 去做，rh 按每个 run 自己的记录对照规格核对：启动后马上核对一次，每条结果评论里再核对一次。

## 开始

1. **复制模板文件**进你的仓库：

   ```
   git -C <rh clone> archive HEAD \
     AGENTS.md .agents .claude .codex .github scripts tests \
     ':!.github/workflows/pages.yml' | tar -x -C <你的仓库>
   ```

2. **填写 `AGENTS.md` 的 Project 一节**，每个字段一行：目录结构、测试命令、语言、受保护路径、Run 命令和运行记录。
3. **推到 `main`，再以仓库管理员身份运行 `bash scripts/setup.sh`**。它会建好 label，只允许 squash 合并，并给 main 加分支保护。

然后在仓库里打开 Claude Code 或 Codex，说"我们计划一下这个研究"。[接入指南](https://doem97.github.io/research-harness/zh-cn/guides/adopt/)讲了 `guard.toml`、`run.toml`、CI 和可选的机器账号。

## 了解更多

- **入门**：[概览](https://doem97.github.io/research-harness/zh-cn/start/overview/) · [快速开始](https://doem97.github.io/research-harness/zh-cn/start/quick-start/) · [说话，不点页面](https://doem97.github.io/research-harness/zh-cn/start/talk-dont-click/)
- **概念**：[状态](https://doem97.github.io/research-harness/zh-cn/concepts/state/) · [关口与卡点](https://doem97.github.io/research-harness/zh-cn/concepts/gates-and-blockers/) · [审查](https://doem97.github.io/research-harness/zh-cn/concepts/review/) · [合并](https://doem97.github.io/research-harness/zh-cn/concepts/merging/) · [运行记录](https://doem97.github.io/research-harness/zh-cn/concepts/run-records/) · [研究规格](https://doem97.github.io/research-harness/zh-cn/concepts/study-spec/) · [原则](https://doem97.github.io/research-harness/zh-cn/concepts/principles/)
- **指南**：[接入](https://doem97.github.io/research-harness/zh-cn/guides/adopt/) · [计划一个研究](https://doem97.github.io/research-harness/zh-cn/guides/plan-a-study/) · [跑实验](https://doem97.github.io/research-harness/zh-cn/guides/run-experiments/) · [适配自己的环境](https://doem97.github.io/research-harness/zh-cn/guides/adapt-your-environment/) · [Claude Code 和 Codex](https://doem97.github.io/research-harness/zh-cn/guides/claude-code-and-codex/)
- **参考**：[AGENTS.md](https://doem97.github.io/research-harness/zh-cn/reference/agents-md/) · [skill](https://doem97.github.io/research-harness/zh-cn/reference/skills/) · [issue 表单](https://doem97.github.io/research-harness/zh-cn/reference/issue-forms/) · [guard](https://doem97.github.io/research-harness/zh-cn/reference/guard/) · [merge.py](https://doem97.github.io/research-harness/zh-cn/reference/merge-py/) · [run.py](https://doem97.github.io/research-harness/zh-cn/reference/run-py/) · [results.py](https://doem97.github.io/research-harness/zh-cn/reference/results-py/) · [接口](https://doem97.github.io/research-harness/zh-cn/reference/interfaces/)
- **项目**：[状态](https://doem97.github.io/research-harness/zh-cn/project/status/) · [用 rh 开发 rh](https://doem97.github.io/research-harness/zh-cn/project/built-with-rh/) · [许可证](https://doem97.github.io/research-harness/zh-cn/project/license/)

rh 处于预发布阶段，接口仍可能变化。文档站点随第一个正式版上线。

## 许可证

[Apache-2.0](../LICENSE)。
