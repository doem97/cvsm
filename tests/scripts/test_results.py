import os
import shlex
import signal
import subprocess
import sys

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
    assert (a["n"], a["n_failed"], a["acc mean"], a["acc std"]) == ("3", "0", "2", "1")
    assert (b["n"], b["acc mean"], b["acc std"]) == ("3", "20", "10")
    assert a["loss mean"] == "0.5" and a["loss std"] == "0"
    assert a["commit"] == repo.git("rev-parse", "HEAD")[:7]
    assert "commits differ" not in out and "env differs" not in out


def test_metric_selection(repo):
    repo.run("seed=1")
    row = table(repo.results("--metric", "acc"))[group()]
    assert "acc mean" in row and "loss mean" not in row


def test_single_seed_shows_dash_for_std(repo):
    repo.run("method=a", "seed=4")
    row = table(repo.results())[group("method=a")]
    assert (row["n"], row["acc mean"], row["acc std"]) == ("1", "4", "—")


def finished(repo, start, **rh):
    """A successful run of `python t.py` recorded directly; rh overrides its rh.* params."""
    params = {"issue": "5", "command": "python t.py", "seed": str(start), "host": "h", "commit": "0" * 40,
              "dirty": "false", "env_lock_sha": "e" * 64, "env_lock_missing": "",
              "data_manifest_sha": "", "gpus": "", "exit_code": "0"}
    return repo.record(start, metrics={"acc": 1.0}, **(params | rh))


def test_different_commits_are_flagged_with_diff_stat(repo):
    first = repo.git("rev-parse", "HEAD")
    (repo.root / "shared.py").write_text("def f():\n    return 1\n")
    second = repo.commit("change shared code")
    finished(repo, 2000, commit=second)
    finished(repo, 1000, commit=first)
    out = repo.results()
    assert table(out)["python t.py"]["commit"] == f"{first[:7]}, {second[:7]}"  # ordered by run start
    assert "commits differ" in out
    assert f"git diff --stat {first[:7]} {second[:7]}" in out
    assert "shared.py" in out and "1 file changed" in out


def test_different_env_and_data_are_flagged(repo):
    finished(repo, 1000, env_lock_sha="a" * 64, data_manifest_sha="c" * 64)
    finished(repo, 2000, env_lock_sha="b" * 64, data_manifest_sha="c" * 64)
    out = repo.results()
    assert "env differs: aaaaaaaa, bbbbbbbb" in out and "data differs" not in out
    finished(repo, 3000, env_lock_sha="b" * 64, data_manifest_sha="d" * 64)
    assert "data differs: cccccccc, dddddddd" in repo.results()


def test_failed_and_incomplete_runs_are_counted(repo):
    assert sorted(repo.run_many(["seed=1", "fail_seed=2"], ["seed=2", "fail_seed=2"])) == [0, 1]
    # A run whose run.py was killed while it waited for GPUs: params from creation only.
    stuck = repo.record(3000, status="RUNNING", issue="5", command="python other.py", seed="", host="h")
    out = repo.results()
    row = table(out)[group("fail_seed=2")]
    assert (row["n"], row["n_failed"], row["acc mean"]) == ("1", "1", "1")
    assert "incomplete runs (1" in out and stuck in out
    other = table(out)["python other.py"]
    assert (other["n"], other["n_failed"], other["commit"]) == ("0", "0", "none")


def test_sigkilled_run_is_incomplete(repo):
    hold = repo.tmp / "never"
    p = repo.start("hold=" + str(hold))
    wait_for(hold.with_suffix(".pid"))
    p.kill()
    p.communicate(timeout=30)
    os.kill(int(hold.with_suffix(".pid").read_text()), signal.SIGKILL)
    out = repo.results()
    assert "incomplete runs (1" in out and repo.only_run().info.run_id in out


def test_deleted_runs_are_flagged(repo):
    assert repo.run_many(["seed=1"], ["seed=2"]) == [0, 0]
    gone = repo.runs()[0].info.run_id
    repo.client.delete_run(gone)
    out = repo.results()
    assert table(out)[group()]["n"] == "2"
    assert "deleted runs (1" in out and gone in out


def test_missing_env_lock_is_flagged(repo):
    repo.run()
    out = repo.results()
    assert "env lock missing" in out and "uv.lock" in out


def test_dirty_runs_are_flagged(repo):
    (repo.root / "scratch.py").write_text("1\n")
    repo.run()
    out = repo.results()
    assert "dirty runs (1" in out and repo.only_run().info.run_id in out


def test_bad_metrics_file_is_flagged_not_fatal(repo):
    repo.run("metrics=list")
    out = repo.results()
    assert "no metrics (1 run(s)" in out and repo.only_run().info.run_id in out


def test_other_issues_are_ignored(repo):
    procs = [repo.start("seed=1"), repo.start("method=b", "seed=1", issue=15),
             repo.start("method=b", "seed=2", issue=None)]
    assert [p.communicate(timeout=30) and p.returncode for p in procs] == [0, 0, 0]
    assert set(table(repo.results(issue=5))) == {group()}
    assert set(table(repo.results(issue=15))) == {group("method=b")}


def test_no_runs_still_prints_a_table(repo):
    out = repo.results(issue=99)
    assert "| command |" in out and table(out) == {}
    out = repo.results(env={"MLFLOW_EXPERIMENT_NAME": "no-such-experiment"})
    assert "| command |" in out and table(out) == {}


def test_missing_mlflow_is_a_clear_error(repo):
    p = subprocess.run([sys.executable, "-S", str(RESULTS), "--issue", "5"], cwd=repo.root,
                       capture_output=True, text=True, env=repo.env, timeout=30)
    assert p.returncode != 0 and "mlflow is not installed" in p.stderr
