<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="research-harness. Agents do the work. You hold the gates. Agent trajectories pass four human gates (publish, merge, budget, conclude) and resolve into a results table checked against the study spec." src="docs/assets/hero-light.svg" width="100%">
</picture>

**Let coding agents run your ML research, and keep every comparison fair.**

rh is a template you copy into a research repo. GitHub issues hold the state, one rules file and four skills hold the procedure, and every run is checked against the study spec you approved, from its own record. There is no service to install or host.

![status: pre-release](https://img.shields.io/badge/status-pre--release-5C616B?style=flat-square&labelColor=0B0C0F) ![agents: Claude Code and Codex](https://img.shields.io/badge/agents-Claude_Code_%C2%B7_Codex-5C616B?style=flat-square&labelColor=0B0C0F) ![install: no service](https://img.shields.io/badge/install-no_service-5C616B?style=flat-square&labelColor=0B0C0F) ![human gates: 4](https://img.shields.io/badge/human_gates-4-F04A0E?style=flat-square&labelColor=0B0C0F) ![runs: checked against the spec](https://img.shields.io/badge/runs-checked_against_the_spec-2F6FE0?style=flat-square&labelColor=0B0C0F)

[中文](docs/README.zh-CN.md) · [Adopt rh](#adopt-rh) · [Design (中文)](docs/design/2026-10-16-harness-v1.md)

## Why rh

Coding agents can now write the code, launch the runs and post the results of an ML study faster than you can read them. The risk is below the plan. A learning rate gets changed to fix a crash. An effective batch gets halved to fit memory. Each change is reasonable on its own, and together they turn a comparison into a guess. Usually all you see is the agent's summary.

rh keeps you where a human is needed and makes the rest checkable. You approve a study spec: the arms, the settings held fixed (each with a reason), and what may adapt. Agents do everything below it through issues and pull requests. They stop only at four gates, or at a blocker they can't resolve alone. Every run records its resolved config, and the results command checks those records against the spec. So deviations reach you as facts, not as an agent's account.

It is a convention around git and GitHub, not a service. You copy in a rules file, four skills, issue forms, a PR check, a merge script and two reference scripts for runs. Nothing runs outside GitHub, git and your own machines.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/stats-dark.svg">
  <img alt="0 services to install. 80 lines of rules, capped by a test. 4 skills of at most 120 lines each. 4 human gates, the only planned stops. 1 merge path for agents, merge.py. 2 agent CLIs, Claude Code and Codex, with one set of skills." src="docs/assets/stats-light.svg" width="100%">
</picture>

rh is built with rh. Since the initial commit, every change to its `main` has been a squash-merged PR that closes one task issue under a `plan` parent.

## How it works

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/loop-dark.svg">
  <img alt="Swimlanes for the six phases plan, implement, review, merge, run and analyze. Human: four orange gates and blocker answers. Agents: the plan, implement, review (fresh session) and run skills, merge.py and the three-line report. Record: issues, the pull request, the Verdict comment, the squash merge, MLflow runs, and the results with the spec check and the study table." src="docs/assets/loop-light.svg" width="100%">
</picture>

- **State is GitHub issues.** A `study` parent holds a research question and a `plan` parent holds development work. Under each sit `code` and `run` sub-issues. Dependencies, linked branches, PRs, checks and closed states are native GitHub fields. The only extra label is `needs-decision`. The repo holds no plan, progress or notes files.
- **Rules are AGENTS.md**, at most 80 lines. It covers how to read state, when to stop, how to ask, and how to use git and files.
- **Procedures are skills.** `plan`, `implement`, `review` and `run` each take one role from start to finish, in at most 120 lines. Claude Code and Codex read the same files.
- **Checks are mechanical where they can be.** `guard` checks each PR's format, file locations and scope. `test` runs the project's tests. `merge.py` is the only way an agent merges.
- **Every PR gets a fresh-context review.** The reviewer starts from the PR number alone and reads the PR, its issue, the Decisions and, under a study, the spec. It never sees the implementer's session. It posts one comment whose first line is `Verdict: pass @ <sha>` or `Verdict: changes @ <sha>`.
- **Runs are MLflow runs** with provenance (issue, command, commit, environment and data fingerprints) and the resolved config. Results comments are generated from those records. MLflow's web UI is optional.

Each instruction names a target state. The agent keeps going until it reaches the target, a gate or a blocker. It stops at the four gates even when everything works:

| Gate | When | What you say |
|---|---|---|
| **01&nbsp;Publish** | New or changed approved work: publishing a plan; changing a task's Goal, Scope, Acceptance or Merge, or a study's Arms, Controlled or Adaptable; changing a protected path | "publish", or approve the change |
| **02&nbsp;Merge** | A PR is merge-ready, unless its task says `Merge: agent`. Then the agent merges it itself with `merge.py`, which refuses protected paths and heads without a passing review | "merge", or "merge `#15`" |
| **03&nbsp;Budget** | The next step would exceed the budget in tokens, time or GPU hours | "continue", with a new budget if you like |
| **04&nbsp;Conclude** | All of a study's sub-issues are closed and it awaits analysis | your conclusion, e.g. "conclude `#10`: …" |

**Blockers.** The agent also stops at a blocker:
- the same failure 3 times in a row;
- 3 `changes` verdicts in a row;
- an ambiguity that would change the deliverable;
- a Controlled setting that can't be met without changing the comparison.

It asks once, with evidence, at most 3 options and a recommendation. If you are in the session, it asks there. Otherwise it adds `needs-decision` to the issue, posts a four-line comment (`Blocked:`, `Evidence:`, `Options:`, `Recommend:`) and moves on to other ready work. It handles test failures, merge conflicts and bugs inside Scope itself.

## The spec is the contract

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/contract-dark.svg">
  <img alt="A study spec card, readable by you and approved at gate 01. Below it, denser layers of agent work: code, config, launches and runs. A blue arrow runs from six run records back up to the spec, with the spec check those records produced." src="docs/assets/contract-light.svg" width="100%">
</picture>

When you approve a study, you read its spec: a fair-comparison table with a few variables. Below it, code, configs and launches multiply faster than anyone can read, and that is where setting differences creep in. The spec is the one layer you can truly check. So rh checks every run against it from the run's record, not from an agent's account.

The spec is three sections of the study issue, one item per line:

```
### Arms
full: model.adapter=none
lora: model.adapter=lora model.lora.rank=8

### Controlled
data.split=val  # held-out split from data.sha256
model.backbone=vit_b16  # paper X, Table 2
optim.lr=3e-4  # paper X, Table 2
train.epochs=30  # paper X, Table 2
train.effective_batch=256  # paper X, Table 2
seed in 1,2,3  # three seeds, as in paper X

### Adaptable
train.per_device_batch  # fit to GPU memory; effective batch stays 256
train.accum  # follows per_device_batch
```

- **Arms**: the only settings in which the arms differ.
- **Controlled**: `key=value  # reason` holds for every run. `key in v1,v2,...  # reason` lists values every arm must run, such as seeds and tuning grids. The reason is required: a paper, a record or an earlier result.
- **Adaptable**: engineering settings that may differ between runs, each with the rule that keeps the comparison intact.
- **Keys** are the dotted keys of each run's resolved config. The training code writes that config to `$RUN_DIR/config.json`, and `run.py` logs it as `cfg.*` params as soon as it parses, so a running run can already be checked.

The `run` skill checks right after launch and stops runs that break the spec. Every results comment ends with a `规格核对` (spec check) section. It lists, as facts:
- runs where a Controlled line does not hold, or that never recorded its key;
- runs that match no arm, or several;
- arms missing a value of an `in` line;
- keys in no section whose values differ (`未声明的差异`, undeclared difference);
- arms with no run;
- the values each Adaptable key took per arm.

When all of a study's run issues close, the same table and check for the whole study is posted on the study.

This is the output of `scripts/results.py` for six toy runs of the spec above. One lora run was launched with a smaller per-device batch and fp16. The runs were started with `run.py` directly, not through the `run` skill, which would have stopped that run right after launch. The reference `results.py` writes its text in Chinese; a project that wants another language changes `results.py`.

> 规格核对：
> - `train.effective_batch=256` 不成立：1 个 run，0330bc8a46094e03a875e72c6dfd0872（128）
> - 未声明的差异 `train.precision`：bf16（5 个 run）、fp16（1 个 run）
> - Adaptable `train.per_device_batch`：full 取 64（3 个 run）；lora 取 64（2 个 run）、32（1 个 run）
> - Adaptable `train.accum`：full 取 4（3 个 run）；lora 取 4（3 个 run）

In English, that reads:
- The effective batch line fails for one run, which took 128.
- `train.precision` differs between runs although no section declares it.
- These are the values each Adaptable key took.

<details>
<summary>The whole output of <code>results.py</code></summary>

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

</details>

rh reports what the records show. Whether the runs are still comparable is your call.

## Talk, don't click

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/session-dark.svg">
  <img alt="A session: you plan a study, say publish (gate 01), do #11, merge (gate 02), take the study to analysis and ask what is waiting; the agent answers each stop with Done, Waiting for you and Next." src="docs/assets/session-light.svg" width="100%">
</picture>

You make decisions only in an agent session (Claude Code or Codex) and never click around GitHub. Agents create issues, open PRs, review, merge and close on your instruction. They record each of your decisions on the issue as `Decision: <choice> — <one-line reason>`. An explicit instruction approves what it names, so the agent won't ask again.

| You say | The agent |
|---|---|
| "let's plan this study", "I want to study X" | Discusses it with you through the `plan` skill. It drafts the study, its spec and its sub-issues, and creates nothing until you say "publish". |
| "publish" | Creates the parent and its sub-issues, wave by wave, and records the Decision |
| "do `#12`" | Takes the code task to merge-ready: checks green and a `Verdict: pass` on the current head. If the task says `Merge: agent`, it goes on to merged. |
| "merge", or "merge `#15`" | Squash-merges the current head with `python .github/scripts/merge.py <PR> --human` |
| "take `#10` to analysis" | Works until every sub-issue of study `#10` is closed |
| "continue" | Goes on to the next gate |
| "what's waiting for me?" | Reads GitHub and lists `needs-decision` issues and merge-ready PRs |

Every stop ends with three lines, with links: `Done:`, `Waiting for you:` and `Next:`. You can run several sessions at once, each on its own task. Claiming a task creates a linked branch, and other sessions leave a claimed task alone unless an instruction names it.

## What's in the box

| File or directory | Purpose |
|---|---|
| `AGENTS.md` | All of the agents' rules. Each project fills in the final Project section. |
| `.agents/skills/{plan,implement,review,run}/SKILL.md` | The four roles' procedures. Codex reads skills from here. |
| `.claude/skills` | Symlink to `../.agents/skills`, so Claude Code reads the same skills |
| `.claude/settings.json` | Claude Code `permissions.deny`: no direct `gh pr merge` |
| `.codex/rules/harness.rules` | Codex rule: `gh pr merge` is forbidden |
| `.github/ISSUE_TEMPLATE/` | Three issue forms: `study.yml`, `code.yml`, `run.yml` |
| `.github/pull_request_template.md` | PR body template |
| `.github/guard.toml` | guard's config: directory allow-list, `.md` locations, forbidden file names, protected paths, PR title types, body line limit |
| `.github/scripts/guard.py` | Checks a PR: it closes exactly one task issue, its files are in allowed places and inside Scope, and its title and body follow the format |
| `.github/scripts/merge.py` | The only way an agent merges (rules [below](#interfaces-that-stay-fixed)) |
| `.github/workflows/guard.yml` | Runs guard on `pull_request_target`, with code from main; never runs code from the PR |
| `.github/workflows/test.yml` | Runs the project's tests on PRs and on pushes to main |
| `scripts/run.py` | Reference Run command: runs one command and records it as an MLflow run, optionally queueing for GPUs |
| `scripts/results.py` | Builds the results table from one or more issues' run records and checks each run against the study spec |
| `scripts/run.toml` | run.py's config: MLflow experiment name, environment lock, data manifest, seed parameter name, GPU list, GPU lock directory |
| `scripts/setup.sh` | One-time repo setup: labels, merge settings, branch protection of main |
| `tests/` | Tests for the scripts and rule files above |
| `docs/` | Design documents written by people, the Chinese README (`README.zh-CN.md`), and the README figures with their generator (`assets/`) |
| `.gitignore` | Ignores the local MLflow store (`mlflow.db*`, `mlartifacts/`, `mlruns/`) |

## Principles

- **GitHub-native, no service to install.** Workflow state lives in issues, PRs, checks and branch protection, and run records live in MLflow. Sessions keep nothing, so a session can end at any moment without losing anything.
- **Mechanism, not policy.** rh records facts and shows differences. It doesn't choose seeds, design experiments, decide when to rerun, or judge whether runs are comparable. You set those in the spec and your instructions. It also leaves analysis, visualization and how an agent works inside a task to you.
- **Written for capable models.** Rules are short and concrete. They assume an agent that follows clearly written rules. Scripts fix the process, but they don't defend against malformed input, forgery or outsiders.
- **A template, not a framework.** rh ships no adapters for clusters, schedulers, storage or tracking services. `run.py` and `results.py` are a single-machine reference. Each adopter fits its own cluster, scheduler (e.g. SLURM) and tracking backend through its own issues, and keeps the [interfaces that stay fixed](#interfaces-that-stay-fixed).

## Adopt rh

An agent in your session can do all of this. You decide, and you provide an admin account where one is needed. There are five steps, plus an optional machine account.

<details>
<summary><b>1. Copy the template files</b>, then adapt <code>guard.toml</code>, <code>run.toml</code> and your training code's config output</summary>

Copy only tracked files. That way untracked local files in the template clone (tool configs, `__pycache__`) stay behind, and the `.claude/skills` symlink survives:

```
git -C <rh clone> archive HEAD AGENTS.md .agents .claude .codex .github scripts tests | tar -x -C <your repo>
```

Then merge the lines of `.gitignore` into yours. You can delete tests in `tests/` that you won't use. Note which rh commit you copied (`git -C <rh clone> rev-parse HEAD`) in the message of the adoption commit, so you can compare later rh improvements against it.
- Edit `.github/guard.toml`:
  - Add your directories to `layout` (e.g. `src/**`, `configs/**`). Also add the root files the project changes, such as `pyproject.toml`, lock files like `uv.lock`, and `.python-version`. If you miss one, guard rejects PRs that change dependencies.
  - Add your eval and data paths to `protected`.
  - Adjust `markdown` as needed.
- Edit `scripts/run.toml`: `experiment`, `env_lock` (your lock files) and `gpus`.
  - Data directories are usually ignored by git, so the data fingerprint comes from a tracked data manifest: a file listing each data file's checksum, e.g. the output of `sha256sum` saved as `data.sha256`.
  - Put its path, relative to the repo root, in `data_manifest`, and add it to both `layout` and `protected` in guard.toml.
- Make your training code write its full resolved config as a JSON object to `$RUN_DIR/config.json` at start, from one process only (e.g. rank 0).
  - Include every setting that can affect results, derived ones too, such as the effective batch.
  - The keys in a study spec are this config's flattened dotted keys (e.g. `optim.lr`). The results command uses them to check each run against the spec.
  - Leave out values that differ per run without affecting results, such as output directories, run names and timestamps. Otherwise every results comment lists them as `未声明的差异` (undeclared differences). If you must include one, declare it Adaptable in the spec.
- If several users share one machine and `TMPDIR` is per user, each user's default GPU lock directory sits in their own `TMPDIR`, and they can't see each other's locks. Set `lock_dir` in run.toml to one local directory they can all write to.
- If you have a CLAUDE.md, condense the project facts into the Project section of AGENTS.md (one line per field). Move the rest into `docs/` or code comments, then delete CLAUDE.md. The harness reads only AGENTS.md, and guard rejects `.md` files elsewhere.

</details>

<details>
<summary><b>2. Fill in the Project section of AGENTS.md</b>, one line per field</summary>

Leave the other sections as they are. AGENTS.md is at most 80 lines (a test checks this), and each field is one line:
- `Layout`: how the code directories divide, and where the shared code and the method modules live.
- `Test`: the test command, the same one CI runs.
- `Language`: the language of human-facing text (see [Language](#language)).
- `Protected eval/data paths`: eval and data paths agents may not change at will. These match `protected` in guard.toml.
- `Run`: the Run command and the results-comment command.
  - Runs launch in a fresh worktree (`../worktrees/N-<slug>`) that has no ignored `.venv` or data directories. So the commands must work as they are in a new worktree, in an environment with both the project's dependencies and MLflow.
  - With uv, put `mlflow-skinny`, `sqlalchemy` and `alembic` in the dev dependency group (`uv add --dev`; `uv run` includes the dev group by default).
  - Then write `uv run python scripts/run.py --issue N -- <cmd>`, and the results command as `uv run python scripts/results.py --issue N` (results.py needs MLflow too).
  - Find data through absolute paths, environment variables or tracked symlinks.
- `Run records`: which MLflow backend run records go to.

</details>

<details>
<summary><b>3. Install your CI dependencies</b> in <code>.github/workflows/test.yml</code></summary>

Edit the `pip install` line in `.github/workflows/test.yml` to install your project's dependencies and test tools, and keep the test command the same as `Test` in AGENTS.md. If the project uses uv, CI can still install dependencies with pip and run the same tests.
- The copied rule, skill and guard tests need `pyyaml`.
- If you keep the tests of `scripts/run.py`, install MLflow too. The template installs `mlflow-skinny`, plus `sqlalchemy` and `alembic` for SQLite.
- CI runners have no GPU. If your lock file has a CUDA build of torch, install the CPU build in CI instead (`pip install torch --index-url https://download.pytorch.org/whl/cpu`). Install it *before* the project's dependencies, because a CUDA build that is already installed won't be replaced by one installed later.
- Don't rename the jobs `guard` and `test`. Branch protection finds the checks by these names.

</details>

<details>
<summary><b>4. Push to main, then run <code>scripts/setup.sh</code> as an admin</b></summary>

The default branch must be called `main`; setup.sh, guard and the skills all assume it. If an older repo uses `master`, rename it on GitHub first.

Push the changes above to main directly, as one adoption commit. Two things make this necessary:
- guard runs on `pull_request_target`, so it uses the version on main.
- Until main has both the `guard` and `test` workflows, the required checks would block every PR.

This is the only exception to "never push to main" in AGENTS.md, and you do it once, before protection is on. After the push, the `test` workflow runs once on main; confirm on the Actions page that CI passes.

Then, from the repo root and logged in to gh as the human admin (not the machine account), run:

```
bash scripts/setup.sh            # defaults to the repo of the current directory
bash scripts/setup.sh owner/repo
```

It does the following:
- Creates five labels: `study`, `plan`, `code`, `run` and `needs-decision`.
- Allows only squash merges, with the PR title as the commit title and an empty body, and deletes branches after merge.
- Protects main: changes go through PRs, `guard` and `test` must pass, 0 approvals, no bypass even for admins, and no force pushes or deletion.

Running it again is safe, and it keeps other labels you already have. Branch protection, though, is overwritten as a whole: protection settings the project added later (e.g. required approvals) are reverted on a rerun. Branch protection on a private repo needs a paid GitHub plan (e.g. Pro or Team); public repos don't.

</details>

<details>
<summary><b>5. Check that both agents load the rules</b>: Codex and Claude Code</summary>

- **Codex** reads `AGENTS.md`, skills from `.agents/skills` and rules from `.codex/rules`.
  - Codex reads the project's `.codex/` only once it trusts the project. Run `codex` interactively once at the repo root and accept the trust prompt. (`codex exec -s danger-full-access` marks the project trusted without a prompt.)
  - `codex execpolicy check --rules .codex/rules/harness.rules gh pr merge 1` checks only the rules file itself, and should print `forbidden`.
  - To confirm a session really loaded the rules, open a Codex session in the repo and ask it to run `gh pr merge --help`. The rule should block it; even if allowed, this command merges nothing. Also confirm that all four skills are listed.
- **Claude Code** reads `AGENTS.md`, reads skills through the `.claude/skills` symlink, and `.claude/settings.json` denies `gh pr merge`. Open a session in the repo and confirm that all four skills are listed.

</details>

<details>
<summary><b>Optional: a machine account for the agents</b>, so GitHub separates their actions from yours</summary>

If you want GitHub to separate your actions from the agents', let all agents share one machine account:
- Add it as a repo collaborator with write access, not admin.
- Create a classic token for it with the scopes `repo`, `workflow` and `read:org`. A fine-grained token can't act as a collaborator on a repo someone else owns.
- Log it in to a separate directory with `GH_CONFIG_DIR=<dir> gh auth login`, and have agents use it in this repo only.
  - Two local files point `GH_CONFIG_DIR` at `<dir>`. List both paths in `.git/info/exclude` so they stay out of the repo.
  - Both files live only in the main clone, not in worktrees. A session started from the main clone passes the setting to the agents it starts. If you open a session directly in a worktree, put copies there first.
  - `.claude/settings.local.json`: `{"env": {"GH_CONFIG_DIR": "<dir>"}}`
  - `.codex/config.toml`:

    ```toml
    [shell_environment_policy]
    set = { GH_CONFIG_DIR = "<dir>" }
    ```
- Commit as that account too.
  - In the repo, run `git config user.name <account>` and `git config user.email <id>+<account>@users.noreply.github.com`. Look up `<id>` with `gh api users/<account> -q .id`.
  - Use an HTTPS remote and run `gh auth setup-git` once, so pushes go through gh's login. It writes the global git config, so the account it uses depends on the `GH_CONFIG_DIR` set at the time.
- If an agent runs on another machine, log in with this token there too.
- Admin tasks (running setup.sh, changing branch protection) still use your own account.

</details>

## Interfaces that stay fixed

The skills, guard, merge.py and the results comment depend on the interfaces below. When you adapt rh to your environment, change the implementations, not these shapes. Everything else is your project's to decide, through its own issues. That covers the scheduler (e.g. a Run command that submits to SLURM and still writes run records), cluster and GPU allocation, data and artifact storage, the tracking backend (e.g. `MLFLOW_TRACKING_URI` pointing at a team MLflow server), the allow-list and protected paths in `guard.toml`, and CI dependencies.

<details>
<summary><b>Run and results commands</b></summary>

The Run command has the shape `<run> --issue N [options] -- <cmd>`. Each line in a run issue's Runs is either `<cmd>` or `<options> -- <cmd>`. The `run` skill puts the options (e.g. `--gpus 4`) before `--` and the command, unchanged, after it.

The results command has the shape `<results> --issue N [N ...] [--metric M ...] [--spec FILE]`. `--spec` reads the study issue's body, and FILE `-` reads stdin, e.g. `gh issue view P --json body -q .body | <results> --issue N --spec -`.

The actual commands for both go on the `Run` line of AGENTS.md.

</details>

<details>
<summary><b>Run records</b></summary>

Each run is one MLflow run. The docstring at the top of `scripts/run.py` is the reference for its fields.
- **`rh.*` params**, which can't change once written:
  - at creation: `rh.issue`, `rh.command`, `rh.seed` and `rh.host`;
  - before launch: `rh.commit`, `rh.dirty`, `rh.env_lock_sha`, `rh.env_lock_missing`, `rh.data_manifest_sha` and `rh.gpus`;
  - at the end: `rh.exit_code`.

  Missing values are empty strings, and lists are comma-joined.
- **`cfg.*` params**: logged once, as soon as the `$RUN_DIR/config.json` the command writes parses as a JSON object.
  - It is logged while the command is still running, so a running run can be checked. A file that only appears by the end is logged at the end.
  - Nested objects flatten to dotted keys `cfg.<key>`. Strings are logged as they are, other values as JSON.
  - Keys and values longer than MLflow's limits are truncated to them. The full content is in the `config.json` artifact.
- **Allowed `cfg.*` keys**: only letters, digits, `_ - . / :` and spaces, which is MLflow's rule for param names.
  - Keys with other characters (e.g. `tench, Tinca tinca` inside a `label2id`) are not logged as params, and neither are keys that repeat after truncation. run.py lists them on stderr.
  - Keys used in a study spec must stay within this set.
- **Tag**: `mlflow.source.git.commit`.
- **Artifacts**:
  - `diff.patch` (`git diff HEAD`) and `untracked.txt` when the tree is dirty;
  - the command's output, `log.txt`;
  - every file the command writes to `$RUN_DIR`, including `config.json`.

  `$RUN_DIR/metrics.json` (a flat `{name: number}`) is logged as metrics. Training code can also log metrics with MLflow's standard API; `MLFLOW_RUN_ID` attaches it to the same run.
- **Final status**: `FINISHED` for exit code 0, `KILLED` when a signal stopped the command, and `FAILED` otherwise.
- **Backend**: set by `MLFLOW_TRACKING_URI`. When unset, it is `mlflow.db` at the main clone root, with artifacts beside it in `mlartifacts/`. The experiment name comes from `MLFLOW_EXPERIMENT_NAME`, else from `experiment` in `scripts/run.toml`.
- Records are never edited or deleted, and `mlflow gc` is never run.

</details>

<details>
<summary><b>Results comment</b></summary>

When a run issue finishes, the agent posts one comment: a note, followed by the output of the results command pasted unchanged.

The table groups runs by command with the seed removed. Each group shows:
- n, the number of failures, and the mean and standard deviation of each metric;
- fingerprints of the commit, environment lock and data;
- with a spec, the arm each group belongs to.

It also flags:
- groups that differ in commit, environment or data, with `git diff --stat` attached when commits differ;
- runs that succeeded without metrics, unfinished runs and deleted runs.

A `规格核对` section follows, quoting the spec. It lists facts about the selected runs, running ones included:
- runs where a Controlled line does not hold or whose key was not recorded (`未记录`);
- runs in no arm or in several;
- arms missing values of an `in` line (counting only running or successful, undeleted runs);
- keys in no section whose values differ (`未声明的差异`);
- arms with no run;
- spec lines it can't read;
- each Adaptable key's values per arm.

When there is no spec or no deviation, the section says so.

</details>

<details>
<summary><b>Issue form sections</b></summary>

guard, merge.py and the skills read bodies by their `### ` headings, so the heading names can't change:
- **`study`**: Question, Arms, Controlled, Adaptable, Criteria, Budget, Context.
  - The results command reads the three spec sections line by line, one item per line; any line may end with `  # <comment>`.
  - Arms lines are `<arm>: <key>=<value> ...`.
  - Controlled lines are `<key>=<value>  # <reason>` or `<key> in <v1>,<v2>,...  # <reason>`, and the reason is required.
  - Adaptable lines are `<key>  # <rule>`, and the section may be empty.
  - Values that parse as JSON compare as JSON; others compare as strings.
- **`code`**: Goal, Scope, Acceptance, Budget, Merge (`human` or `agent`; default `human`).
- **`run`**: Runs, Budget, Report.

</details>

<details>
<summary><b>PR template, review comment and merge.py</b></summary>

**PR template**: the first line is `Closes #N`, followed by `## Changes` (at most 5 items), `## Acceptance` and `## Out of scope`.

**Review comment**: the first line is `Verdict: pass @ <head SHA>` or `Verdict: changes @ <head SHA>`. The review tool's findings follow, unedited.

**merge.py**:
- `python .github/scripts/merge.py <PR>` merges only when all three of these hold. Otherwise it refuses and waits for the human.
  - The issue the PR closes says `Merge: agent`.
  - The changes, including pre-rename paths, touch no path that guard.toml on the PR's base branch lists as protected.
  - The newest `Verdict:` comment is a pass for the current head (an SHA prefix of at least 7 characters).
- `python .github/scripts/merge.py <PR> --human` skips the three checks, because the human has decided.
- Both run `gh pr merge --squash --match-head-commit <SHA>` on the current head. The commit title is `<PR title> (#<PR>)` with an empty body, and branch protection still requires the checks to pass.

</details>

## Language

This README is in English, and a complete [Chinese version](docs/README.zh-CN.md) sits in `docs/`. The two are kept in sync.

In this repo, all other human-facing text is Chinese: PR bodies, issue and PR comments, reports, issue-form descriptions and results comments. The one exception is review comments, which keep the review tool's own text below the Verdict line.

Agent instructions (AGENTS.md, skills), code, PR titles and format keywords (`Closes`, `Decision:`, `Blocked:`, `Verdict:` and so on) stay in English, because models follow English instructions more precisely. An adopting project sets its own language on the `Language` line of AGENTS.md's Project section.

## Status

rh is a pre-release. It runs its own development, and its interfaces may still change before the first release.
