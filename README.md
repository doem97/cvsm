# research-harness

一套围绕 git 和 GitHub 的研究开发约定，给"人 + 编码 agent"一起做机器学习研究用。没有要安装的程序，也不存任何状态。完整设计见 [docs/design/2026-10-16-harness-v1.md](docs/design/2026-10-16-harness-v1.md)。

## 是什么

- **状态机是 GitHub issue**：研究（`study`）和开发计划（`plan`）是父 issue，下面挂 `code` 和 `run` 子 issue。依赖、关联分支、PR、检查和关闭状态都用 GitHub 原生字段表达，另外只加一个 `needs-decision` label。仓库里没有计划、进度或笔记文件。
- **规则是 AGENTS.md**：状态怎么判断、什么时候必须停、怎么提问、Git 和文件怎么用，都写在里面。
- **步骤是 skill**：`plan`、`implement`、`review`、`run` 四个 skill 分别写清一个角色从头到尾怎么做。
- **检查是 guard、CI 和 merge.py**：guard 检查 PR 的格式、目录白名单和改动范围；`test` 跑项目自己的测试；merge.py 是 agent 唯一的合并入口。
- **运行记录是 MLflow run**：每次运行由 Run 命令记成一个 MLflow run，带 issue、命令、commit、环境和数据指纹；结果评论由脚本从这些记录生成。MLflow 的网页可以用来浏览记录，但不是必需的。

harness 刻意不做的事：
- **不预置任何环境**：不带集群、调度器、存储或跟踪服务的适配器。`scripts/` 里的 run.py 和 results.py 只是一个单机参考实现。
- 不管研究方法（seed 数、实验设计、何时重跑）、分析与可视化，也不管 agent 在任务内部怎么实现。

每个接入的项目通过自己的 issue，把集群、调度器（例如 SLURM）和跟踪后端适配到自己的环境。适配时哪些接口要保持不变，见下文。

## 人怎么参与

人只在 agent 会话（Codex 或 Claude Code）里做决定，不直接操作 GitHub 页面。建 issue、开 PR、审查、合并、关闭都由 agent 按人的指示执行；人做的每个决定，agent 都在相应 issue 上记成一条 `Decision: <选项> — <一行理由>` 评论。

每条指令就是一个目标状态。agent 一直推进，只在三种时候停下：到达目标、碰到关口、遇到卡点。

**四个关口**（一切顺利也要停）：
1. 新增或改变已批准的工作：发布计划；改任务的 Goal、Scope、Acceptance 或 Merge；改受保护路径。
2. 合并，除非任务写了 `Merge: agent`。这时 agent 在 PR 待合并后用 `python .github/scripts/merge.py <PR>` 自己合并；否则待合并的 PR 本身就是请求，等人说合并。
3. 超出预算：token、时间或 GPU 小时。
4. 研究下结论并关闭。

**卡点**：同一个失败连续 3 次、审查连续 3 次给出 changes、或者目标有歧义且会影响交付物。agent 只问一次，带上证据、最多 3 个选项和推荐。人在会话里就当场问；不在时给 issue 打上 `needs-decision`，贴一条四行的卡点评论（`Blocked:`、`Evidence:`、`Options:`、`Recommend:`），然后转去做别的就绪任务。测试失败、合并冲突、范围内的 bug 这类事，agent 自己处理，不来问。

人明确下的指令本身就算批准，agent 不会再问一遍。每次停下，agent 汇报三行：`Done:`、`Waiting for you:`、`Next:`，带链接。

指令示例：

| 说法 | agent 做到哪 |
|---|---|
| "做 #12" | 把代码任务推进到待合并（检查全绿、当前 head 有审查 pass）；任务写了 `Merge: agent` 就推进到合并完成 |
| "把 #10 推到待分析" | 研究 #10 的子 issue 全部关闭 |
| "继续" | 推进到下一个关口 |
| "看看等我的" | 读 GitHub 上的状态，列出带 `needs-decision` 的 issue 和待合并的 PR |
| "合并"（或"合并 #15"） | 用 `python .github/scripts/merge.py <PR> --human` squash 合并当前 head |

讨论新工作时说"我想研究 X"之类，agent 按 `plan` skill 和你讨论，起草研究和子任务，等你说发布才建 issue。

可以同时开几个会话，各做一件事：每个任务认领时会建一个关联分支，已经认领的任务，除非指令点名，别的会话不会接手。

## 文件一览

| 文件或目录 | 作用 |
|---|---|
| `AGENTS.md` | agent 的全部规则；最后的 Project 一节由各项目填写 |
| `.agents/skills/{plan,implement,review,run}/SKILL.md` | 四个角色的步骤；Codex 从这里读 skill |
| `.claude/skills` | 指向 `../.agents/skills` 的软链，让 Claude Code 读到同一套 skill |
| `.claude/settings.json` | Claude Code 的 `permissions.deny`：禁止直接运行 `gh pr merge` |
| `.codex/rules/harness.rules` | Codex 的规则：`gh pr merge` 设为 forbidden |
| `.github/ISSUE_TEMPLATE/` | 三种 issue 表单：`study.yml`、`code.yml`、`run.yml` |
| `.github/pull_request_template.md` | PR 正文模板 |
| `.github/guard.toml` | guard 的配置：目录白名单、`.md` 位置、禁用文件名、受保护路径、PR 标题类型、正文行数上限 |
| `.github/scripts/guard.py` | 检查 PR：关闭恰好一个任务 issue、文件位置、不超出 Scope、标题和正文格式 |
| `.github/scripts/merge.py` | agent 唯一的合并入口（规则见下文） |
| `.github/workflows/guard.yml` | 用 `pull_request_target` 跑 guard，代码取自 main，不执行 PR 里的代码 |
| `.github/workflows/test.yml` | 用 `pull_request` 跑项目测试 |
| `scripts/run.py` | Run 命令的参考实现：跑一条命令，记成一个 MLflow run，可选按 GPU 排队 |
| `scripts/results.py` | 从一个 issue 的运行记录生成结果表 |
| `scripts/run.toml` | run.py 的配置：MLflow 实验名、环境锁、数据清单、seed 参数名、GPU 列表 |
| `scripts/setup.sh` | 一次性设置仓库：label、合并方式、main 的分支保护 |
| `tests/` | 以上脚本和规则文件的测试 |
| `docs/` | 人写的设计文档 |
| `.gitignore` | 忽略本地的 MLflow 存储（`mlflow.db*`、`mlartifacts/`、`mlruns/`） |

## 接入已有代码库

下面的事都可以交给会话里的 agent 去做，人只需要拍板和提供管理员账号。

**1. 复制模板文件。** 把 `AGENTS.md`、`.agents/`、`.claude/`、`.codex/`、`.github/`、`scripts/` 下的四个文件复制到你的仓库根目录，再把 `.gitignore` 的几行并进去；需要的话也复制 `tests/` 里对应的测试。复制时保留软链，例如 `cp -a`。
- 改 `.github/guard.toml`：`layout` 加上你的目录（如 `src/**`、`configs/**`），`protected` 加上评测和数据路径，`markdown` 按需调整。
- 已有的 CLAUDE.md 并进 AGENTS.md 后删掉：harness 只认 AGENTS.md，guard 会拒收别处的 `.md`。

**2. 填写 AGENTS.md 的 Project 一节。** 其他各节不用改。逐行填：
- `Layout`：代码目录怎么分，共享代码和方法模块各在哪里；
- `Test`：测试命令，和 CI 里跑的一致；
- `Language`：面向人的文字用什么语言（见下文"语言"）；
- `Protected eval/data paths`：不许 agent 随意改的评测和数据路径，与 guard.toml 的 `protected` 一致；
- `Run`：Run 命令和结果评论命令；
- `Run records`：运行记录写到哪个 MLflow 后端。

**3. 安装 CI 依赖。** 改 `.github/workflows/test.yml` 里的 `pip install` 一行，装上你项目的依赖和测试工具，测试命令与 AGENTS.md 的 `Test` 一致。如果保留 `scripts/run.py` 的测试，还要装 MLflow（模板里装的是 `mlflow-skinny`，加上 SQLite 需要的 `sqlalchemy` 和 `alembic`）。job 名 `guard` 和 `test` 不要改，分支保护按这两个名字认检查。本机跑实验的环境同样需要 MLflow。

**4. 以管理员身份运行 `scripts/setup.sh`。** 默认分支需要叫 `main`（老仓库是 `master` 的，先在 GitHub 上改名），setup.sh、guard 和各个 skill 都按 main 写。先把以上改动合进 main：guard 用 `pull_request_target`，跑的是 main 上的版本；main 上还没有 `guard` 和 `test` 两个 workflow 时，必过检查会卡住所有 PR。然后在仓库根目录、用有管理员权限的 gh 登录运行：

```
bash scripts/setup.sh            # 默认是当前目录所在的仓库
bash scripts/setup.sh owner/repo
```

它建五个 label（`study`、`plan`、`code`、`run`、`needs-decision`），只允许 squash 合并（PR 标题作提交标题，正文留空），合并后自动删分支；给 main 加分支保护：必须走 PR，`guard` 和 `test` 必过，0 个批准，管理员也不能绕过，禁止强推和删除。可以重复运行，不会删除已有的其他 label；但分支保护是整体覆盖的，项目后来自己加的保护设置（例如要求批准）重跑时会被还原。私有仓库的分支保护需要 GitHub 付费套餐（例如 Pro 或 Team），公开仓库不需要。

**5. 确认两种 agent 都读到了规则。**
- Codex：读 `AGENTS.md`，从 `.agents/skills` 读 skill，从 `.codex/rules` 读规则；项目要先被 Codex 信任，它才会读项目里的 `.codex/`。`codex execpolicy check --rules .codex/rules/harness.rules gh pr merge 1` 只检查规则文件本身，结果应为 `forbidden`；要确认会话真的加载了规则，就在仓库里开一个 Codex 会话，让它运行 `gh pr merge --help`，应该被规则拦下（这条命令即使放行也不会合并任何东西），并确认四个 skill 都列出来了。
- Claude Code：读 `AGENTS.md`，通过 `.claude/skills` 软链读 skill，`.claude/settings.json` 禁止 `gh pr merge`。在仓库里开一个会话，确认四个 skill 都列出来了。

**可选：给 agent 一个机器账号。** 想在 GitHub 上分清人和 agent 的操作时，可以让所有 agent 共用一个机器账号：
- 把它加为仓库协作者，给写权限，不给管理员权限；
- 给它建一个 classic token，勾选 `repo`、`workflow` 和 `read:org`（fine-grained token 不能以协作者身份操作别人名下的仓库）；
- 只在研究工作区里用它，例如在本地、不进仓库的工具配置里用 `GH_CONFIG_DIR` 指向机器账号的 gh 登录目录；
- 管理员的事（运行 setup.sh、改分支保护）仍然用人的账号。

## 适配自己的环境时保持不变的接口

skill、guard、merge.py 和结果评论都依赖下面这些接口。适配时只换实现，不改它们的形状：

**Run 命令的形状**：`<run> --issue N [options] -- <cmd>`。run issue 的每行 Runs 是 `<cmd>` 或 `<选项> -- <cmd>`：`run` skill 把选项（如 `--gpus 4`）放在 `--` 之前，命令原样放在 `--` 之后。结果命令的形状是 `<results> --issue N [--metric M ...]`。两者的实际命令写在 AGENTS.md 的 `Run` 一行。

**运行记录**：每次运行是一个 MLflow run（字段以 `scripts/run.py` 开头的说明为准）：
- `rh.*` 参数（写入后不能改）：创建时写 `rh.issue`、`rh.command`、`rh.seed`、`rh.host`；启动前写 `rh.commit`、`rh.dirty`、`rh.env_lock_sha`、`rh.env_lock_missing`、`rh.data_manifest_sha`、`rh.gpus`；结束时写 `rh.exit_code`。没有的值写空字符串，列表用逗号连接。
- tag `mlflow.source.git.commit`。
- 产物：工作区不干净时有 `diff.patch`（`git diff HEAD`）和 `untracked.txt`；命令的输出 `log.txt`；命令写进 `$RUN_DIR` 的所有文件。`$RUN_DIR/metrics.json`（扁平的 `{名字: 数值}`）记成指标；训练代码也可以用 MLflow 的标准 API 记指标，`MLFLOW_RUN_ID` 让它接到同一个 run。
- 最终状态：退出码 0 为 `FINISHED`，被信号停止为 `KILLED`，其他为 `FAILED`。
- 后端由 `MLFLOW_TRACKING_URI` 决定；不设时用主 clone 根目录下的 `mlflow.db`，产物放在旁边的 `mlartifacts/`。实验名取 `MLFLOW_EXPERIMENT_NAME`，否则取 `scripts/run.toml` 的 `experiment`。
- 记录不改不删，不运行 `mlflow gc`。

**结果评论**：run issue 结束时贴一条评论：一段说明加结果命令生成的表，表原样粘贴。表按去掉 seed 的命令分组，给出 n、失败数、每个指标的均值和标准差，以及 commit、环境锁和数据的指纹；组间 commit、环境或数据不同要标出来，commit 不同时附 `git diff --stat`；成功但没有指标、未完成和已删除的 run 也列出来。

**issue 表单的各节**：guard、merge.py 和 skill 按 `### ` 标题读正文，标题名不能改：
- `study`：Question、Comparison、Criteria、Budget、Context；
- `code`：Goal、Scope、Acceptance、Budget、Merge（human 或 agent，默认 human）；
- `run`：Runs、Budget、Report。

**PR 模板**：第一行 `Closes #N`，然后 `## Changes`（最多 5 条）、`## Acceptance`、`## Out of scope`。

**审查评论**：第一行是 `Verdict: pass @ <head SHA>` 或 `Verdict: changes @ <head SHA>`，下面原样贴审查工具的意见。

**merge.py 的行为**：
- `python .github/scripts/merge.py <PR>`：只有三项都满足才合并：PR 关闭的 issue 写了 `Merge: agent`；改动（含重命名前的路径）不碰 PR 目标分支上 guard.toml 列出的受保护路径；最新一条 `Verdict:` 评论是对当前 head 的 pass（SHA 至少 7 位前缀）。否则拒绝，等人合并。
- `python .github/scripts/merge.py <PR> --human`：人已经决定，跳过这三项检查。
- 两种方式都用 `gh pr merge --squash --match-head-commit <SHA>` 合并当前 head，提交标题是 `<PR 标题> (#<PR>)`，正文为空；分支保护照常要求检查通过。

其他的都由你的项目自己决定，并通过自己的 issue 去改：调度器（例如让 Run 命令把任务提交到 SLURM，同时照样写运行记录）、集群和 GPU 分配、数据和产物的存储位置、跟踪后端（例如把 `MLFLOW_TRACKING_URI` 指向团队的 MLflow 服务器）、`guard.toml` 的白名单和受保护路径、CI 的依赖。

## 语言

面向人的文字用中文：PR 正文、issue 和 PR 评论、汇报、表单说明、README、结果评论。审查评论例外，Verdict 行下面保留审查工具的原文。给 agent 的指令（AGENTS.md、skill）、代码、PR 标题和格式关键字（`Closes`、`Decision:`、`Blocked:`、`Verdict:` 等）用英文，因为 LLM 对英文指令的理解更准确。接入的项目可以改 AGENTS.md Project 一节的 `Language` 一行，换成自己的语言。
