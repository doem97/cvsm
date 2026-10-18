---
title: 运行记录
description: 每次运行怎样记成带出处和解析后配置的 MLflow run，结果评论又怎样从这些记录生成。
sidebar:
  order: 5
---

每次运行是一个 MLflow run，记下它从哪来、实际解析出的配置和它的输出。结果评论由这些记录生成，所以你读到的是 run 自己记下的东西，而不是 agent 写的说法。

## 记录里有什么

Run 命令的参考实现 `scripts/run.py` 在启动命令之前就建好记录。各字段以它开头的说明为准。

- **`rh.*` 参数**，MLflow 不允许写入后再改：
  - 创建时：`rh.issue`、`rh.command`、`rh.seed`、`rh.host`；
  - 启动前：`rh.commit`、`rh.dirty`、`rh.env_lock_sha`、`rh.env_lock_missing`、`rh.data_manifest_sha`、`rh.gpus`；
  - 结束时：`rh.exit_code`。
- **`cfg.*` 参数**：命令写到 `$RUN_DIR/config.json` 的解析后配置，展开成点号键，例如 `cfg.optim.lr`。文件一能解析成 JSON 对象就记一次，所以还在跑的 run 也能对照规格核对。
- **产物**：`log.txt`（命令的输出）；命令写进 `$RUN_DIR` 的所有文件，包括 `config.json`；工作区不干净时还有 `diff.patch` 和 `untracked.txt`。
- **指标**：`$RUN_DIR/metrics.json` 里扁平的 `{名字: 数值}`，或者用 MLflow 的标准 API 记，`MLFLOW_RUN_ID` 让它接到同一个 run。
- **最终状态**：退出码 0 为 `FINISHED`，被信号停止为 `KILLED`，其他为 `FAILED`。

没有的值写空字符串，列表用逗号连接。commit、环境锁和数据清单的哈希就是结果表比较的指纹。

## 解析后的配置

训练代码在启动时把解析后的完整配置写成一个 JSON 对象，存到 `$RUN_DIR/config.json`，只由一个进程写（例如 rank 0）。所有可能影响结果的设置都要在里面，包括推导出来的，例如有效 batch。输出目录、run 名、时间戳这类每个 run 都不同、又不影响结果的值不要写进去，否则每条结果评论都会把它们列为未声明的差异。

:::note
研究规格里用到的键，只能用 MLflow 参数名允许的字符：字母、数字、`_ - . / :` 和空格。其他键 run.py 不记成参数，并在 stderr 列出来。
:::

## 记录存在哪里

后端由 `MLFLOW_TRACKING_URI` 决定。不设时用主 clone 根目录下的 `mlflow.db`，所有 worktree 共用，产物放在旁边的 `mlartifacts/`。MLflow 的网页可以用来浏览，但不是必需的。记录不改不删，也不运行 `mlflow gc`。

## run 怎么启动

`run` skill 认领运行 issue，在从 `main` 拉出的分支上建一个干净的 worktree，从那里启动 Runs 的每一行，这样每条记录对应的都是已合并的代码。运行任务不提交代码，也没有 PR。

```sh
python scripts/run.py --issue 12 -- python train.py arm=lora seed=1
python scripts/run.py --issue 12 --gpus 4 -- python train.py arm=lora seed=2
```

- 启动后，配置一记录下来就对照规格核对，停掉违反规格的 run。被停掉的 run 照样留在记录里。
- 失败的 run 保留并计数。只有 infra 失败（丢节点、被抢占、磁盘满等）才重跑那一行，从不因为结果看着不对而重跑。
- 代码导致的失败也是结果：agent 保留它，为这个 bug 开一个 `code` issue，接着跑其他行。

## 结果评论

每一行都有了完成或失败的记录后，agent 在运行 issue 上贴一条评论：先是一段说明，写跑了什么、失败和重跑、Adaptable（可调整）设置的调整，后面原样粘贴结果命令的输出。然后关闭 issue。

结果表按去掉 seed 的命令分组，每组给出：

- `n`（退出码为 0 的 run 数）和失败数；
- 每个指标的均值和样本标准差；
- commit、环境锁和数据的指纹；
- 给了规格时，该组所属的 arm。

它还会标出：组间 commit、环境或数据的不同（commit 不同时附 `git diff --stat`），成功但没有指标的 run，未完成的 run 和已删除的 run。之后是一节 `规格核对`，见[研究规格](/research-harness/zh-cn/concepts/study-spec/)。

研究的 run issue 全部关闭后，agent 把覆盖全部 run 的同一张表和规格核对贴到研究 issue 上，也就是研究总表。

:::caution
结果评论只陈述事实。这些 run 还能不能比、要不要重跑，由你决定。
:::

## 相关页面

- [研究规格](/research-harness/zh-cn/concepts/study-spec/)
- [跑实验](/research-harness/zh-cn/guides/run-experiments/)
- [run.py](/research-harness/zh-cn/reference/run-py/)
- [results.py](/research-harness/zh-cn/reference/results-py/)
