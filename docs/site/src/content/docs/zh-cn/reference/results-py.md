---
title: results.py
description: 结果命令的参考实现：从运行记录生成结果表，并对照研究规格逐个核对 run。
sidebar:
  order: 7
---

`scripts/results.py` 为一个或几个 issue 的 run 打印一张 Markdown 结果表，标出出处上的差异，最后是一节 `规格核对`。agent 把它的输出原样贴进结果评论；它只报告事实，能不能比由你判断。

源文件：[`scripts/results.py`](https://github.com/doem97/cvsm/blob/main/scripts/results.py)。

## 用法

```sh
python scripts/results.py --issue N [N ...] [--metric M ...] [--spec FILE] [--config scripts/run.toml]
gh issue view P --json body -q .body | python scripts/results.py --issue N --spec -
```

| 选项 | 含义 |
|---|---|
| `--issue N [N ...]` | 必填。要读哪些 issue 的 run（按 `cvsm.issue` 参数）。重复的只算一次。 |
| `--metric M [M ...]` | 要显示的指标，按给出的顺序；可以给多次。默认是这些 run 的所有数值指标，按名字排序。 |
| `--spec FILE` | 用来核对 run 的研究 issue 正文；`-` 从标准输入读。不给时，核对一节会写明没有给规格。 |
| `--config FILE` | 从哪个 `run.toml` 读 `experiment` 和 `seed_key`。默认 `scripts/run.toml`。 |

它读的存储和实验与 `run.py` 写入的一致（`MLFLOW_TRACKING_URI`，否则 `<主 clone>/mlflow.db`；`MLFLOW_EXPERIMENT_NAME`，否则 `experiment`）。已删除的 run 也会读。它 import `run.py`，所以需要 MLflow，并且要和 `run.py` 放在同一目录。

## 输出

输出是中文；指标名、哈希和键保持原样。项目要用别的语言，就改 `results.py`。输出分四部分。

### 1. 概要行

`#12 的结果：6 个 run，3 组，按去掉 seed 的命令分组。`：哪些 issue、几个 run、几组，以及怎么分组。

### 2. 表

run 按开始时间排序，按去掉 seed（`seed_key`）后的命令分组。每组一行：

| 列 | 内容 |
|---|---|
| `命令` | 去掉 seed 的命令 |
| `arm` | 仅在给了规格时：这组 run 匹配到的 arm，匹配不到为 `无` |
| `n` | 以 0 退出的 run 数；统计量只用这些 run |
| `失败数` | 以其他方式结束的 run 数，不含还是 `RUNNING` 的 |
| `<指标> 均值` | 这 `n` 个 run 上该指标最新值的均值 |
| `<指标> 标准差` | 样本标准差；不足 2 个值时为 `—` |
| `commit` | commit 前缀（7 位） |
| `环境锁` | 环境锁哈希前缀（8 位） |
| `数据` | 数据清单哈希前缀（8 位） |

最后三列列出组内出现过的不同取值，没有值的 run 记为 `无`。数字保留 4 位有效数字。

### 3. 标注

| 标注 | 何时出现 |
|---|---|
| `commit 不同` | run 的 commit 不止一个；附上第一个和最后一个之间的 `git diff --stat` |
| `环境不同` | 环境锁哈希不同 |
| `数据不同` | 数据清单哈希不同 |
| `缺环境锁文件` | 有 run 缺 `env_lock` 里的文件，并列出这些文件 |
| `工作区不干净` | 从不干净的工作区启动的 run（见产物 `diff.patch` 和 `untracked.txt`） |
| `成功退出但没有指标` | 以 0 退出却没有指标的 run |
| `未完成` | 还是 `RUNNING` 的 run：还在跑，或被杀掉而没写完记录 |
| `已在 MLflow 中删除` | 已删除的 run，仍计入上表 |

没有任何标注时，这一节是 `- 无`。

### 4. `规格核对`

核对覆盖所有选中的 run（含还在跑的），用的是 `run.py` 从 `config.json` 记下的 `cfg.*` 参数。按以下顺序列出事实，先是规格本身的问题：

| 事实 | 行的样子 |
|---|---|
| Controlled 行没写理由 | `Controlled 行没有写理由：<行>` |
| 读不懂的规格行 | `读不懂的规格行：<节>：<行>` |
| 缺 Arms 或 Controlled 一节 | `规格里没有 <节> 一节` |
| 一个键出现在多节 | `` `<键>` 出现在多节：<各节> `` |
| 没记录某条 Controlled 键的 run | `` `<行>`：n 个 run 未记录 `<键>`：<run id> `` |
| 某条 Controlled 不成立的 run | `` `<行>` 不成立：n 个 run，<run id>（<取值>） `` |
| 不属于任何 arm 的 run | `n 个 run 不属于任何 arm：<run id>` |
| 属于多个 arm 的 run | `n 个 run 属于多个 arm：<run id>（<各 arm>）` |
| 某个 arm 缺 `in` 行的取值 | `` arm <arm> 缺 `<行>` 的取值：<取值> `` |
| 不在任何一节、取值却不同的键（未声明的差异） | `` 未声明的差异 `<键>`：<取值>（n 个 run）、... `` |
| 没有 run 的 arm | `没有 run 的 arm：<各 arm>` |
| 以上都没有 | `没有偏差` |
| 每个 Adaptable 键在各 arm 的取值（总会列出） | `` Adaptable `<键>`：<arm> 取 <取值>（n 个 run）；... `` |

核对的规则：

- 一个 run 记录了某个 arm 那一行的每个键、且取值都相等，它就属于这个 arm。
- 值能按 JSON 解析就按 JSON 比较（`1` 等于 `1.0`），否则按字符串比较。run 没记录的键显示为 `未记录`。
- `in` 行只对有 run 的 arm 检查，只算还在跑或以 0 退出、且没删除的 run；失败的 run 不算覆盖了任何取值。
- 未声明的差异只在记录了配置的 run 之间比较。

不给 `--spec` 时，这一节是 `- 没有给出规格（--spec）`。

## 示例

对[示例规格](/cvsm/zh-cn/guides/plan-a-study/#2-定下公平对比)跑的六个玩具 run，其中一个 lora run 用了更小的每卡 batch 和 fp16：

```text
#12 的结果：6 个 run，3 组，按去掉 seed 的命令分组。

| 命令 | arm | n | 失败数 | top1 均值 | top1 标准差 | commit | 环境锁 | 数据 |
|---|---|---|---|---|---|---|---|---|
| `python train.py arm=full` | full | 3 | 0 | 0.8505 | 0.00358 | 7ac858e | 73cb3858 | 无 |
| `python train.py arm=lora` | lora | 2 | 0 | 0.8424 | 0.004648 | 7ac858e | 73cb3858 | 无 |
| `python train.py arm=lora batch=32 precision=fp16` | lora | 1 | 0 | 0.8399 | — | 7ac858e | 73cb3858 | 无 |

标注：
- 无

规格核对：
- `train.effective_batch=256` 不成立：1 个 run，0330bc8a46094e03a875e72c6dfd0872（128）
- 未声明的差异 `train.precision`：bf16（5 个 run）、fp16（1 个 run）
- Adaptable `train.per_device_batch`：full 取 64（3 个 run）；lora 取 64（2 个 run）、32（1 个 run）
- Adaptable `train.accum`：full 取 4（3 个 run）；lora 取 4（3 个 run）
```

## 相关页面

- [研究规格](/cvsm/zh-cn/concepts/study-spec/)
- [运行记录](/cvsm/zh-cn/concepts/run-records/)
- [run.py](/cvsm/zh-cn/reference/run-py/)
- [保持不变的接口](/cvsm/zh-cn/reference/interfaces/#结果评论)
- [运行实验](/cvsm/zh-cn/guides/run-experiments/)
