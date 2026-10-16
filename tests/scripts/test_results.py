import json
import os
import shlex
import signal
import sys
import time

from run_record_helpers import Repo


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
    for method in "ab":
        for seed in (1, 2, 3):
            assert repo.run(f"method={method}", f"seed={seed}").returncode == 0
    out = repo.results()
    rows = table(out)
    assert set(rows) == {group("method=a"), group("method=b")}
    a, b = rows[group("method=a")], rows[group("method=b")]
    assert (a["n"], a["n_failed"], a["acc mean"], a["acc std"]) == ("3", "0", "2", "1")
    assert (b["n"], b["acc mean"], b["acc std"]) == ("3", "20", "10")
    assert a["loss mean"] == "0.5" and a["loss std"] == "0"
    head = repo.git("rev-parse", "HEAD")
    assert a["commit"] == head[:7]
    assert "commits differ" not in out and "env differs" not in out


def test_metric_selection(repo):
    repo.run("seed=1")
    out = repo.results("--metric", "acc")
    row = table(out)[group()]
    assert "acc mean" in row and "loss mean" not in row


def test_single_seed_shows_dash_for_std(repo):
    repo.run("method=a", "seed=4")
    row = table(repo.results())[group("method=a")]
    assert (row["n"], row["acc mean"], row["acc std"]) == ("1", "4", "—")


def test_different_commits_are_flagged_with_diff_stat(repo):
    first = repo.git("rev-parse", "HEAD")
    repo.run("seed=1")
    (repo.root / "shared.py").write_text("def f():\n    return 1\n")
    second = repo.commit("change shared code")
    repo.run("seed=2")
    out = repo.results()
    row = table(out)[group()]
    assert row["commit"] == f"{first[:7]}, {second[:7]}"  # ordered by run start
    assert "commits differ" in out
    assert f"git diff --stat {first[:7]} {second[:7]}" in out
    assert "shared.py" in out and "1 file changed" in out


def test_different_env_is_flagged(make_repo):
    repo = make_repo()
    (repo.root / "uv.lock").write_text("v1\n")
    repo.commit("lock v1")
    repo.run("seed=1")
    (repo.root / "uv.lock").write_text("v2\n")
    repo.commit("lock v2")
    repo.run("seed=2")
    out = repo.results()
    assert "env differs" in out
    assert "data differs" not in out


def test_failed_and_incomplete_runs_are_counted(repo):
    repo.run("seed=1", "fail_seed=2")
    repo.run("seed=2", "fail_seed=2")
    # An interrupted run (SIGKILL): start.json without run.json.
    d = repo.storage / "runs" / "20260101-000000-abcdef"
    d.mkdir(parents=True)
    (d / "start.json").write_text(json.dumps({"run_id": d.name, "issue": 5, "command": ["x"],
                                              "start": "2026-01-01T00:00:00+00:00"}))
    out = repo.results()
    row = table(out)[group("fail_seed=2")]
    assert (row["n"], row["n_failed"], row["acc mean"]) == ("1", "1", "1")
    assert "incomplete runs (1" in out and d.name in out


def test_sigkilled_run_is_incomplete(repo):
    p = repo.start("hold=" + str(repo.root.parent / "never"))
    while not any((d / "started").exists() for d in repo.run_dirs()):
        time.sleep(0.02)
    p.kill()
    p.communicate(timeout=30)
    d = repo.run_dirs()[0]
    os.kill(int((d / "started").read_text()), signal.SIGKILL)
    out = repo.results()
    assert "incomplete runs (1" in out and d.name in out


def test_missing_env_lock_is_flagged(repo):
    repo.run()
    out = repo.results()
    assert "env lock missing" in out and "uv.lock" in out


def test_dirty_runs_are_flagged(repo):
    (repo.root / "scratch.py").write_text("1\n")
    repo.run()
    run_id = repo.run_dirs()[0].name
    out = repo.results()
    assert "dirty runs (1" in out and run_id in out


def test_other_issues_are_ignored(repo):
    repo.run("seed=1", issue=5)
    repo.run("method=b", "seed=1", issue=6)
    repo.run("method=b", "seed=1", issue=None)
    assert set(table(repo.results(issue=5))) == {group()}
    assert set(table(repo.results(issue=6))) == {group("method=b")}


def test_no_runs_still_prints_a_table(repo):
    out = repo.results(issue=99)
    assert "| command |" in out and table(out) == {}


def test_results_from_a_worktree_read_the_shared_storage(tmp_path):
    repo = Repo(tmp_path, storage="../storage")
    wt = tmp_path / "worktrees" / "9-x"
    repo.git("worktree", "add", "-q", "-b", "t/9-x", str(wt))
    repo.run("seed=1")
    repo.run("seed=2", cwd=wt)
    for cwd in (repo.root, wt):
        assert table(repo.results(cwd=cwd))[group()]["n"] == "2"


def test_bad_metrics_file_is_flagged_not_fatal(repo):
    repo.run("seed=1")
    d = repo.run_dirs()[0]
    (d / "metrics.json").write_text("[1, 2]")
    out = repo.results()
    assert "no metrics (1 run(s)" in out and d.name in out
