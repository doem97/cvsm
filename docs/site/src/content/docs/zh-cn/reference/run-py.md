---
title: run.py
description: Run 命令的参考实现：在可选的 GPU 租约下运行一条命令，并把它记成一个 MLflow run。
sidebar:
  order: 6
---

`scripts/run.py` 运行一条命令，把它记成一个 MLflow run，带上出处、解析后的配置、输出、产物和指标。它是单机参考实现：项目可以替换它，只要替换后的实现守住 [Run 命令和运行记录的接口](/research-harness/zh-cn/reference/interfaces/)。

源文件：[`scripts/run.py`](https://github.com/doem97/research-harness/blob/main/scripts/run.py)。记录的字段以它开头的模块说明为准。

## 用法

```sh
python scripts/run.py [--issue N] [--gpus K] [--config scripts/run.toml] -- <cmd...>
```

| 选项 | 默认 | 含义 |
|---|---|---|
| `--issue N` | 无 | 所属的 run issue，记成 `rh.issue`。`run` skill 总会传它。 |
| `--gpus K` | 配了 `gpus` 时为 1，否则为 0 | 要租用的 GPU 数，必须在 0 到已配置的 GPU 数之间。 |
| `--config FILE` | `scripts/run.toml` | 配置文件。 |
| `-- <cmd...>` | 必填 | 要运行的命令，原样不动。`--` 之后的全部属于它。 |

需要 Python 3.11 或更高版本，以及 MLflow（`mlflow`，或 `mlflow-skinny` 加上 SQLite 需要的 `sqlalchemy` 和 `alembic`）。在命令所用代码的那个 git checkout 里运行它。

## run.toml

| 键 | 模板里的值 | 缺省时 | 含义 |
|---|---|---|---|
| `experiment` | `"research-harness"` | `"Default"` | MLflow 实验；`MLFLOW_EXPERIMENT_NAME` 优先。不存在时自动创建。 |
| `env_lock` | `["uv.lock"]` | `[]` | 哈希进 `rh.env_lock_sha` 的锁文件；缺失的列进 `rh.env_lock_missing`。 |
| `data_manifest` | `""` | `""` | 哈希进 `rh.data_manifest_sha` 的被跟踪数据清单；空表示没有。 |
| `seed_key` | `"seed"` | `"seed"` | 匹配命令里的 `seed=N`、`--seed=N` 或 `--seed N`。 |
| `gpus` | `[]` | `[]` | 可租用的 GPU 编号；空表示不租用。 |
| `lock_dir` | `""` | `""` | GPU 锁文件放在 `<lock_dir>/<host>/`；空表示系统临时目录。 |

`env_lock` 和 `data_manifest` 的路径相对 checkout 根目录解析。

## 执行过程

1. **建记录。** 连上存储，创建 run，记下 `rh.issue`、`rh.command`、`rh.seed` 和 `rh.host`。后端连不上时，什么都不启动。
2. **租 GPU。** K > 0 时，等到有 K 个 GPU 锁空闲。run 已经建好，所以等待中的 run 显示为 `RUNNING`。
3. **记下代码状态**，在启动前、等完 GPU 之后：记 `rh.commit`、`rh.dirty`、`rh.env_lock_sha`、`rh.env_lock_missing`、`rh.data_manifest_sha`、`rh.gpus` 和 tag `mlflow.source.git.commit`。工作区不干净时，另存产物 `diff.patch` 和 `untracked.txt`。
4. **启动**命令，输出写到 `$RUN_DIR/log.txt`。
5. **记配置。** 命令运行期间每 0.5 秒找一次 `$RUN_DIR/config.json`，一能解析成 JSON 对象就记一次。
6. **收尾。** 还没记配置就补记，上传指标和 `$RUN_DIR`，记 `rh.exit_code`，设最终状态。

## 存储

| 项 | 值 |
|---|---|
| 后端 | `MLFLOW_TRACKING_URI`；不设时为 `sqlite:///<主 clone>/mlflow.db` |
| 主 clone | git 公共目录的上一级，所以同一个 clone 的所有 worktree 共用一个存储，worktree 删了它还在 |
| 新实验的产物 | SQLite 文件旁边的 `mlartifacts/`；PostgreSQL、MySQL、MSSQL 用 `<主 clone>/mlartifacts`；跟踪服务器由 MLflow 自己决定 |
| 首次初始化 | SQLite 存储在 `<db>.lock` 文件锁下初始化，因为几个进程同时迁移一个新数据库时 MLflow 会失败 |

tracking URI 会传给命令，但从不打印，因为里面可能带凭据。

## 命令的环境变量

| 变量 | 值 |
|---|---|
| `MLFLOW_RUN_ID` | 这个 run 的 id，命令里的 `mlflow.start_run()` 会接到同一个 run |
| `MLFLOW_TRACKING_URI` | run.py 写入的存储 |
| `RUN_DIR` | 一个新建的临时目录 |
| `CUDA_VISIBLE_DEVICES` | 租到的 GPU 编号，逗号连接；只在配了 `gpus` 时设置 |

## 参数

`rh.*` 参数写入后不能改。没有的值写空字符串，布尔值写 `true` 或 `false`，列表用逗号连接。

| 参数 | 何时写 | 值 |
|---|---|---|
| `rh.issue` | 创建时 | `--issue` |
| `rh.command` | 创建时 | 命令，按 shell 规则拼接 |
| `rh.seed` | 创建时 | 按 `seed_key` 找到的 seed |
| `rh.host` | 创建时 | 主机名 |
| `rh.commit` | 启动前 | `git rev-parse HEAD` |
| `rh.dirty` | 启动前 | `git status` 是否有改动或未跟踪文件 |
| `rh.env_lock_sha` | 启动前 | 存在的 `env_lock` 文件按路径排序后的 sha256 |
| `rh.env_lock_missing` | 启动前 | 没找到的 `env_lock` 文件 |
| `rh.data_manifest_sha` | 启动前 | `data_manifest` 的 sha256 |
| `rh.gpus` | 启动前 | 租到的 GPU 编号 |
| `rh.exit_code` | 结束时 | 命令的退出码；被信号 S 停止时为 `-S` |

`cfg.*` 参数来自 `$RUN_DIR/config.json`，即命令启动时由一个进程（例如 rank 0）写下的解析后配置：

- 文件一能解析成 JSON 对象就记一次，所以还在跑的 run 也能核对。到结束时才出现的文件，在结束时、上传之前记。记录失败的，结束时再试一次。
- 嵌套对象展开成点号键 `cfg.<键>`，空对象的值是 `{}`。字符串原样记，其他值记成 JSON。
- 超过 MLflow 长度上限（MLflow 3 里键 250、值 6000 个字符）的键和值截断到上限，完整内容看产物 `config.json`。
- 键只能由字母、数字、`_ - . / :` 和空格组成。含其他字符的键，以及展开或截断后与前面重复的键，会被跳过，并在 stderr 列出。研究规格里用到的键要在这个范围内。

## 产物和指标

| 产物 | 何时有 |
|---|---|
| `diff.patch`（`git diff HEAD`，按字节保存） | 工作区不干净时 |
| `untracked.txt`（每行一个路径） | 工作区不干净时 |
| `log.txt`（命令的 stdout 和 stderr） | 总有 |
| 命令写进 `$RUN_DIR` 的所有文件，包括 `config.json` | 总有 |

`$RUN_DIR/metrics.json` 里扁平的 `{名字: 数值}` 记成指标，所以训练代码不必 import MLflow。也可以用 MLflow 的标准 API 记指标，`MLFLOW_RUN_ID` 让它接到同一个 run。上传后删掉 `$RUN_DIR`；上传失败时保留它并打印路径。

## 状态和退出码

| 最终状态 | 何时 |
|---|---|
| `FINISHED` | 退出码 0 |
| `KILLED` | 命令被信号停止，或在启动前收到停止信号 |
| `FAILED` | 其他退出码；命令无法启动时为 127 |

run.py 的退出码就是命令自己的；命令被信号 S 停止时为 128 + S。最终状态最后才设，所以会覆盖命令里用 `mlflow.end_run()` 自己结束 run 时设的状态。

## GPU 锁

- 锁文件是 `<lock_dir>/<host>/gpu<i>.lock`，用 `flock` 持有。`lock_dir` 默认是系统临时目录下的 `rh-gpu-locks`。
- run.py 尝试同时持有 K 个已配置的 GPU；拿不齐就全部释放，打印 `run.py: waiting for K free GPU(s) of [...]`，每 30 秒重试一次。
- 命令继承这些锁，所以租约和命令一样长，即使 run.py 自己被杀掉也一样。
- 默认目录只有共用 `TMPDIR` 的用户才能共享。`TMPDIR` 按用户区分时，把 `lock_dir` 设成大家都能写的目录。run.py 在那里新建的按主机子目录会设成可共享（sticky、所有人可写）；已经存在的目录保持原有权限。

## 信号

| 信号 | 启动前（含等 GPU 时） | 启动后 |
|---|---|---|
| `SIGTERM` | run 以 `KILLED` 结束，不启动命令 | 转发给命令 |
| `SIGHUP` | 同上，除非被忽略（`nohup`） | 转发，除非被忽略 |
| `SIGINT`（Ctrl-C） | 同上 | 不转发：它已经通过终端到达命令 |

停后台的 run 用 `SIGTERM`。启动时就被忽略的信号保持忽略。

## 相关页面

- [运行记录](/research-harness/zh-cn/concepts/run-records/)
- [results.py](/research-harness/zh-cn/reference/results-py/)
- [保持不变的接口](/research-harness/zh-cn/reference/interfaces/#运行记录)
- [运行实验](/research-harness/zh-cn/guides/run-experiments/)
- [适配你的环境](/research-harness/zh-cn/guides/adapt-your-environment/)
