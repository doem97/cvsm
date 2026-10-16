import fcntl
import hashlib
import importlib.util
import json
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import time

import pytest

from run_record_helpers import RUN, Repo

_spec = importlib.util.spec_from_file_location("run_script", RUN)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

FIELDS = {"run_id", "issue", "commit", "dirty", "untracked", "command", "seed", "config",
          "env_lock_sha", "env_lock_missing", "data_manifest_sha", "host", "gpus", "start",
          "end", "exit_code"}


def wait_for(path, timeout=10):
    deadline = time.time() + timeout
    while not path.exists():
        assert time.time() < deadline, f"timed out waiting for {path}"
        time.sleep(0.02)


def only_run(repo):
    dirs = repo.run_dirs()
    assert len(dirs) == 1, dirs
    return dirs[0]


def test_record_has_every_field_and_is_read_only(repo):
    head = repo.git("rev-parse", "HEAD")
    p = repo.run("method=a", "seed=2")
    assert p.returncode == 0, p.stderr
    d = only_run(repo)
    rec = repo.record(d)
    assert set(rec) == FIELDS
    assert rec["commit"] == head
    assert rec["run_id"] == d.name
    assert rec["issue"] == 5
    assert rec["dirty"] is False and rec["untracked"] == []
    assert rec["command"][-2:] == ["method=a", "seed=2"]
    assert rec["exit_code"] == 0 and rec["gpus"] == [] and rec["config"] is None
    assert rec["start"] <= rec["end"]
    assert stat.S_IMODE((d / "run.json").stat().st_mode) == 0o444
    assert not (d / "diff.patch").exists()
    log = (d / "log.txt").read_text()
    assert "hello stdout" in log and "hello stderr" in log
    assert (d / "cuda.txt").read_text() == "<unset>"  # leasing off: CUDA_VISIBLE_DEVICES untouched
    start = json.loads((d / "start.json").read_text())
    assert start == {"run_id": d.name, "issue": 5, "command": rec["command"], "start": rec["start"]}
    assert (d / "run.json").read_text().endswith("\n")
    assert json.loads((d / "run.json").read_text()) == rec


def test_run_id_format(repo):
    repo.run()
    assert re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", only_run(repo).name)


def test_config_written_by_command_is_recorded(repo):
    repo.run("config=1")
    d = only_run(repo)
    cfg = repo.record(d)["config"]
    assert cfg == {"path": "config.json",
                   "sha256": hashlib.sha256((d / "config.json").read_bytes()).hexdigest()}


def test_dirty_tree_with_untracked_file(repo):
    (repo.root / "fake.py").write_text((repo.root / "fake.py").read_text() + "\n# local edit\n")
    (repo.root / "new_module.py").write_text("x = 1\n")
    repo.run()
    d = only_run(repo)
    rec = repo.record(d)
    assert rec["dirty"] is True
    assert rec["untracked"] == ["new_module.py"]
    assert "# local edit" in (d / "diff.patch").read_text()


def test_untracked_only_is_dirty(repo):
    (repo.root / "data").mkdir()
    (repo.root / "data" / "x.csv").write_text("1\n")
    repo.run()
    rec = repo.record(only_run(repo))
    assert rec["dirty"] is True and rec["untracked"] == ["data/x.csv"]


@pytest.mark.parametrize("cmd, seed, rest", [
    (["python", "train.py", "seed=3", "lr=0.1"], 3, ["python", "train.py", "lr=0.1"]),
    (["python", "train.py", "--seed", "3", "--lr", "0.1"], 3, ["python", "train.py", "--lr", "0.1"]),
    (["python", "train.py", "--seed=3"], 3, ["python", "train.py"]),
    (["python", "train.py", "lr=0.1"], None, ["python", "train.py", "lr=0.1"]),
])
def test_split_seed(cmd, seed, rest):
    assert run.split_seed(cmd, "seed") == (seed, rest)


def test_split_seed_custom_key():
    assert run.split_seed(["t.py", "train.seed=7", "seed=1"], "train.seed") == (7, ["t.py", "seed=1"])


@pytest.mark.parametrize("args, seed", [(["seed=3"], 3), (["--seed", "3"], 3), ([], None)])
def test_seed_recorded(repo, args, seed):
    repo.run(*args)
    assert repo.record(only_run(repo))["seed"] == seed


def test_nonzero_exit_is_recorded_and_returned(repo):
    p = repo.run("exit=3")
    assert p.returncode == 3
    assert repo.record(only_run(repo))["exit_code"] == 3


def test_missing_command_is_a_failed_run(repo):
    p = subprocess.run([sys.executable, str(RUN), "--", "no-such-binary-xyz"],
                       cwd=repo.root, capture_output=True, text=True, timeout=30)
    assert p.returncode == 127
    rec = repo.record(only_run(repo))
    assert rec["exit_code"] == 127 and rec["issue"] is None


def test_env_lock_and_data_manifest_hashes(make_repo):
    repo = make_repo(env_lock=["uv.lock", "requirements.txt"], data_manifest="data.sha256")
    (repo.root / "uv.lock").write_text("lock v1\n")
    (repo.root / "data.sha256").write_text("abc  train.bin\n")
    repo.commit("add lock and manifest")
    repo.run()
    rec = repo.record(only_run(repo))
    assert rec["env_lock_sha"] == hashlib.sha256(b"lock v1\n").hexdigest()  # same as sha256sum uv.lock
    assert rec["env_lock_missing"] == ["requirements.txt"]
    assert rec["data_manifest_sha"] == hashlib.sha256(b"abc  train.bin\n").hexdigest()


def test_missing_env_lock_is_recorded(repo):
    repo.run()
    rec = repo.record(only_run(repo))
    assert rec["env_lock_sha"] is None and rec["env_lock_missing"] == ["uv.lock"]
    assert rec["data_manifest_sha"] is None


def test_more_gpus_than_configured_is_an_immediate_error(make_repo):
    repo = make_repo(gpus=[0, 1])
    p = repo.run(gpus=3)
    assert p.returncode != 0 and "--gpus" in p.stderr
    assert repo.run_dirs() == []
    assert repo.run().returncode == 0  # without --gpus, one GPU is leased
    assert repo.record(repo.run_dirs()[0])["gpus"] == [0]


def test_gpus_with_leasing_off_is_an_error(repo):
    p = repo.run(gpus=1)
    assert p.returncode != 0 and repo.run_dirs() == []


def test_concurrent_runs_lease_different_gpus(make_repo):
    repo = make_repo(gpus=[0, 1])
    release = repo.root.parent / "release"
    first = repo.start("hold=" + str(release), gpus=1)
    try:
        wait_for(repo.storage / "runs")
        d1 = repo.run_dirs()[0]
        wait_for(d1 / "started")
        second = repo.run(gpus=1)
        assert second.returncode == 0, second.stderr
    finally:
        release.write_text("go")
        first.communicate(timeout=30)
    d2 = [d for d in repo.run_dirs() if d != d1][0]
    r1, r2 = repo.record(d1), repo.record(d2)
    assert len(r1["gpus"]) == len(r2["gpus"]) == 1
    assert r1["gpus"] != r2["gpus"]
    assert (d1 / "cuda.txt").read_text() == str(r1["gpus"][0])
    assert (d2 / "cuda.txt").read_text() == str(r2["gpus"][0])


def lock_is_free(path):
    with open(path, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def test_sigterm_records_negative_exit_and_releases_lease(make_repo):
    repo = make_repo(gpus=[0])
    p = repo.start("hold=" + str(repo.root.parent / "never"))
    wait_for(repo.storage / "runs")
    d = repo.run_dirs()[0]
    wait_for(d / "started")
    assert not lock_is_free(repo.storage / "locks" / socket.gethostname() / "gpu0.lock")
    p.send_signal(signal.SIGTERM)
    p.communicate(timeout=30)
    rec = repo.record(d)
    assert rec["exit_code"] == -signal.SIGTERM
    assert p.returncode == 128 + signal.SIGTERM
    assert rec["gpus"] == [0]
    assert lock_is_free(repo.storage / "locks" / socket.gethostname() / "gpu0.lock")


SIGINT_CHILD = r"""
import os, signal, time
hits = []
signal.signal(signal.SIGINT, lambda *_: hits.append(1))
open(os.path.join(os.environ["RUN_DIR"], "started"), "w").close()
deadline = time.time() + 20
while not hits and time.time() < deadline:
    time.sleep(0.02)
time.sleep(0.5)  # a forwarded second SIGINT would land in this window
with open(os.path.join(os.environ["RUN_DIR"], "sigints"), "w") as f:
    f.write(str(len(hits)))
"""


def test_ctrl_c_reaches_the_command_once(repo):
    (repo.root / "sigint.py").write_text(SIGINT_CHILD)
    p = subprocess.Popen([sys.executable, str(RUN), "--issue", "5", "--", sys.executable, "sigint.py"],
                         cwd=repo.root, start_new_session=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wait_for(repo.storage / "runs")
    d = repo.run_dirs()[0]
    wait_for(d / "started")
    os.killpg(p.pid, signal.SIGINT)  # what the terminal does on Ctrl-C
    p.communicate(timeout=30)
    assert (d / "sigints").read_text() == "1"
    assert repo.record(d)["exit_code"] == 0

def test_sigkill_leaves_start_json_without_run_json(repo):
    p = repo.start("hold=" + str(repo.root.parent / "never"))
    wait_for(repo.storage / "runs")
    d = repo.run_dirs()[0]
    wait_for(d / "started")
    p.kill()
    p.communicate(timeout=30)
    os.kill(int((d / "started").read_text()), signal.SIGKILL)  # the orphaned child
    assert (d / "start.json").exists() and not (d / "run.json").exists()


def test_lease_outlives_a_killed_run_py(make_repo):
    repo = make_repo(gpus=[0])
    p = repo.start("hold=" + str(repo.root.parent / "never"))
    wait_for(repo.storage / "runs")
    d = repo.run_dirs()[0]
    wait_for(d / "started")
    lock = repo.storage / "locks" / socket.gethostname() / "gpu0.lock"
    p.kill()
    p.communicate(timeout=30)
    assert not lock_is_free(lock)  # the orphaned command still holds its GPU
    os.kill(int((d / "started").read_text()), signal.SIGKILL)
    deadline = time.time() + 10
    while not lock_is_free(lock):
        assert time.time() < deadline, "lease not released after the command died"
        time.sleep(0.02)


def test_linked_worktree_shares_main_checkout_storage(tmp_path):
    repo = Repo(tmp_path, storage="../storage")
    wt = tmp_path / "worktrees" / "9-x"
    repo.git("worktree", "add", "-q", "-b", "t/9-x", str(wt))
    assert repo.run(cwd=repo.root).returncode == 0
    p = repo.run(cwd=wt)
    assert p.returncode == 0, p.stderr
    dirs = repo.run_dirs()
    assert len(dirs) == 2  # both under tmp/storage, the sibling of the main checkout
    assert not (tmp_path / "worktrees" / "storage").exists()
    assert {repo.record(d)["commit"] for d in dirs} == {repo.git("rev-parse", "HEAD")}
