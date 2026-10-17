import os
import shlex
import signal
import subprocess
import sys
import time

from run_record_helpers import RESULTS, wait_for


def table(out):
    """Parse the Markdown table into {command: {column: cell}}."""
    lines = [l for l in out.splitlines() if l.startswith("|")]
    head = [c.strip() for c in lines[0].strip("|").split(" | ")]
    rows = {}
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split(" | ")]
        rows[cells[0].strip("`")] = dict(zip(head, cells))
    return rows


def group(*args):
    return shlex.join([sys.executable, "fake.py", *args])


def test_groups_by_command_without_seed(repo):
    assert repo.run_many(*([f"method={m}", f"seed={s}"] for m in "ab" for s in (1, 2, 3))) == [0] * 6
    out = repo.results()
    rows = table(out)
    assert set(rows) == {group("method=a"), group("method=b")}
    a, b = rows[group("method=a")], rows[group("method=b")]
    assert (a["n"], a["失败数"], a["acc 均值"], a["acc 标准差"]) == ("3", "0", "2", "1")
    assert (b["n"], b["acc 均值"], b["acc 标准差"]) == ("3", "20", "10")
    assert a["loss 均值"] == "0.5" and a["loss 标准差"] == "0"
    assert a["commit"] == repo.git("rev-parse", "HEAD")[:7]
    assert out.startswith("#5 的结果：6 个 run，2 组，按去掉 seed 的命令分组。")
    assert "commit 不同" not in out and "环境不同" not in out


def test_metric_selection(repo):
    repo.run("seed=1")
    row = table(repo.results("--metric", "acc"))[group()]
    assert "acc 均值" in row and "loss 均值" not in row


def test_single_seed_shows_dash_for_std(repo):
    repo.run("method=a", "seed=4")
    row = table(repo.results())[group("method=a")]
    assert (row["n"], row["acc 均值"], row["acc 标准差"]) == ("1", "4", "—")


def finished(repo, start, cfg=None, **rh):
    """A successful run of `python t.py` recorded directly; rh overrides its rh.* params and cfg
    gives its cfg.* params."""
    params = {"issue": "5", "command": "python t.py", "seed": str(start), "host": "h", "commit": "0" * 40,
              "dirty": "false", "env_lock_sha": "e" * 64, "env_lock_missing": "",
              "data_manifest_sha": "", "gpus": "", "exit_code": "0"}
    return repo.record(start, metrics={"acc": 1.0}, cfg=cfg, **(params | rh))


def spec_check(out):
    return out.split("\n规格核对：\n", 1)[1]


SPEC = """### Question

Does b beat a?

### Arms

base: method=a
ours: method=b  # the change under study
deep: method=b depth=2
c: method=c
broken line

### Controlled

lr=0.1  # paper X, table 3
seed in 1,2  # two seeds, as in #12
optim.name="adamw"  # a JSON string equals the plain value
wd=0

### Adaptable

batch  # per-device; the effective batch is fixed

### Criteria

b > a by 1 point
"""


def test_spec_check_lists_each_deviation(repo, tmp_path):
    common = {"lr": "0.1", "optim.name": "adamw", "batch": "32", "warmup": "100"}
    r1 = finished(repo, 1000, cfg=common | {"method": "a", "seed": "1"})
    r2 = finished(repo, 2000, cfg=common | {"method": "a", "seed": "2.0", "lr": "0.10", "batch": "64"})
    r3 = finished(repo, 3000, cfg=common | {"method": "b", "seed": "1", "lr": "0.2"})
    r4 = finished(repo, 4000, cfg=common | {"method": "b", "depth": "2", "seed": "1", "warmup": "200"})
    r5 = finished(repo, 5000, cfg={"method": "d", "lr": "0.1", "seed": "3", "batch": "16", "warmup": "100"})
    (tmp_path / "spec.md").write_text(SPEC)
    out = repo.results("--spec", str(tmp_path / "spec.md"))
    assert table(out)["python t.py"]["arm"] == "base、ours、deep、无"
    assert "\n标注：\n- 无\n" in out  # the flags are unchanged
    assert spec_check(out) == f"""- 读不懂的规格行：Arms：broken line
- 读不懂的规格行：Controlled：wd=0
- `lr=0.1` 不成立：1 个 run，{r3}（0.2）
- `seed in 1,2` 不成立：1 个 run，{r5}（3）
- `optim.name="adamw"`：1 个 run 未记录 `optim.name`：{r5}
- 1 个 run 不属于任何 arm：{r5}
- 1 个 run 属于多个 arm：{r4}（ours、deep）
- arm ours 缺 `seed in 1,2` 的取值：2
- arm deep 缺 `seed in 1,2` 的取值：2
- 未声明的差异 `warmup`：100（4 个 run）、200（1 个 run）
- 没有 run 的 arm：c
- Adaptable `batch`：base 取 32（1 个 run）、64（1 个 run）；ours 取 32（2 个 run）；deep 取 32（1 个 run）
"""
    assert r1 not in spec_check(out) and r2 not in spec_check(out)


def test_spec_from_stdin_without_deviations(repo):
    spec = SPEC.replace("deep: method=b depth=2\nc: method=c\nbroken line\n", "").replace("wd=0\n", "")
    spec = spec.replace("batch  # per-device; the effective batch is fixed", "_No response_")
    for start, (method, seed) in enumerate([("a", 1), ("a", 2), ("b", 1), ("b", 2)]):
        finished(repo, start, cfg={"method": method, "seed": str(seed), "lr": "0.1", "optim.name": "adamw"})
    out = repo.results("--spec", "-", input=spec)
    assert spec_check(out) == "- 没有偏差\n"
    assert table(out)["python t.py"]["arm"] == "base、ours"


def test_no_spec_is_said(repo):
    finished(repo, 1000, cfg={"method": "a"})
    out = repo.results()
    assert spec_check(out) == "- 没有给出规格（--spec）\n" and "arm" not in table(out)["python t.py"]


def recorded_config(repo, timeout=10):
    deadline = time.time() + timeout
    while not (cfg := {k: v for k, v in repo.only_run().data.params.items() if k.startswith("cfg.")}):
        assert time.time() < deadline, "config.json was not logged"
        time.sleep(0.05)
    return cfg


def test_a_running_run_is_checked_once_its_config_is_recorded(repo):
    hold = repo.tmp / "release"
    p = repo.start("config=1", "method=b", "seed=1", "hold=" + str(hold))
    try:
        wait_for(hold.with_suffix(".pid"))
        assert recorded_config(repo)["cfg.method"] == "b"
        run_id = repo.only_run().info.run_id
        out = repo.results("--spec", "-", input="### Arms\n\nbase: method=a\n\n### Controlled\n\n"
                                                "seed in 1,2  # two seeds\n")
        assert spec_check(out) == f"- 1 个 run 不属于任何 arm：{run_id}\n- 没有 run 的 arm：base\n"
        assert p.poll() is None and repo.only_run().info.status == "RUNNING"
    finally:
        hold.write_text("go")
        p.communicate(timeout=30)
    assert p.returncode == 0


def test_different_commits_are_flagged_with_diff_stat(repo):
    first = repo.git("rev-parse", "HEAD")
    (repo.root / "shared.py").write_text("def f():\n    return 1\n")
    second = repo.commit("change shared code")
    finished(repo, 2000, commit=second)
    finished(repo, 1000, commit=first)
    out = repo.results()
    assert table(out)["python t.py"]["commit"] == f"{first[:7]}, {second[:7]}"  # ordered by run start
    assert f"- commit 不同：{first[:7]}, {second[:7]}；`git diff --stat {first[:7]} {second[:7]}`：" in out
    assert "shared.py" in out and "1 file changed" in out


def test_different_env_and_data_are_flagged(repo):
    finished(repo, 1000, env_lock_sha="a" * 64, data_manifest_sha="c" * 64)
    finished(repo, 2000, env_lock_sha="b" * 64, data_manifest_sha="c" * 64)
    out = repo.results()
    assert "- 环境不同：aaaaaaaa, bbbbbbbb" in out and "数据不同" not in out
    finished(repo, 3000, env_lock_sha="b" * 64, data_manifest_sha="d" * 64)
    assert "- 数据不同：cccccccc, dddddddd" in repo.results()


def test_failed_and_incomplete_runs_are_counted(repo):
    assert sorted(repo.run_many(["seed=1", "fail_seed=2"], ["seed=2", "fail_seed=2"])) == [0, 1]
    # A run whose run.py was killed while it waited for GPUs: params from creation only.
    stuck = repo.record(3000, status="RUNNING", issue="5", command="python other.py", seed="", host="h")
    out = repo.results()
    row = table(out)[group("fail_seed=2")]
    assert (row["n"], row["失败数"], row["acc 均值"]) == ("1", "1", "1")
    assert f"- 1 个 run 未完成（还在跑或已被杀）：{stuck}" in out
    other = table(out)["python other.py"]
    assert (other["n"], other["失败数"], other["commit"]) == ("0", "0", "无")


def test_sigkilled_run_is_incomplete(repo):
    hold = repo.tmp / "never"
    p = repo.start("hold=" + str(hold))
    wait_for(hold.with_suffix(".pid"))
    p.kill()
    p.communicate(timeout=30)
    os.kill(int(hold.with_suffix(".pid").read_text()), signal.SIGKILL)
    out = repo.results()
    assert f"- 1 个 run 未完成（还在跑或已被杀）：{repo.only_run().info.run_id}" in out


def test_deleted_runs_are_flagged(repo):
    assert repo.run_many(["seed=1"], ["seed=2"]) == [0, 0]
    gone = repo.runs()[0].info.run_id
    repo.client.delete_run(gone)
    out = repo.results()
    assert table(out)[group()]["n"] == "2"
    assert f"- 1 个 run 已在 MLflow 中删除，但仍计入上表：{gone}" in out


def test_missing_env_lock_is_flagged(repo):
    repo.run()
    out = repo.results()
    assert "- 1 个 run 缺环境锁文件：uv.lock" in out


def test_dirty_runs_are_flagged(repo):
    (repo.root / "scratch.py").write_text("1\n")
    repo.run()
    out = repo.results()
    assert f"- 1 个 run 的工作区不干净（见产物 diff.patch 和 untracked.txt）：{repo.only_run().info.run_id}" in out


def test_bad_metrics_file_is_flagged_not_fatal(repo):
    repo.run("metrics=list")
    out = repo.results()
    assert f"- 1 个 run 成功退出但没有指标：{repo.only_run().info.run_id}" in out


def test_other_issues_are_ignored(repo):
    procs = [repo.start("seed=1"), repo.start("method=b", "seed=1", issue=15),
             repo.start("method=b", "seed=2", issue=None)]
    assert [p.communicate(timeout=30) and p.returncode for p in procs] == [0, 0, 0]
    assert set(table(repo.results(issue=5))) == {group()}
    assert set(table(repo.results(issue=15))) == {group("method=b")}
    out = repo.results(issue=[5, 15])
    assert set(table(out)) == {group(), group("method=b")} and out.startswith("#5、#15 的结果：2 个 run")


def test_no_runs_still_prints_a_table(repo):
    out = repo.results(issue=99)
    assert "| 命令 |" in out and table(out) == {}
    assert out.endswith("标注：\n- 无\n\n规格核对：\n- 没有给出规格（--spec）\n")
    out = repo.results(env={"MLFLOW_EXPERIMENT_NAME": "no-such-experiment"})
    assert "| 命令 |" in out and table(out) == {}


def test_missing_mlflow_is_a_clear_error(repo):
    p = subprocess.run([sys.executable, "-S", str(RESULTS), "--issue", "5"], cwd=repo.root,
                       capture_output=True, text=True, env=repo.env, timeout=30)
    assert p.returncode != 0 and "mlflow is not installed" in p.stderr
