import fcntl
import hashlib
import importlib.util
import os
import shlex
import signal
import socket
import subprocess
import sys
import time

import pytest

from run_record_helpers import RUN, closed_port, wait_for

_spec = importlib.util.spec_from_file_location("run_script", RUN)
run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run)

PARAMS = {"rh.issue", "rh.command", "rh.seed", "rh.host", "rh.commit", "rh.dirty", "rh.env_lock_sha",
          "rh.env_lock_missing", "rh.data_manifest_sha", "rh.gpus", "rh.exit_code"}


def rh(run_):
    return {k: v for k, v in run_.data.params.items() if k.startswith("rh.")}


def test_record_has_every_param_and_the_commit_tag(repo):
    head = repo.git("rev-parse", "HEAD")
    p = repo.run("method=a", "seed=2")
    assert p.returncode == 0, p.stderr
    r = repo.only_run()
    params = rh(r)
    assert set(params) == PARAMS
    assert params["rh.commit"] == head
    assert r.data.tags["mlflow.source.git.commit"] == head
    assert params["rh.issue"] == "5" and params["rh.seed"] == "2" and params["rh.dirty"] == "false"
    assert shlex.split(params["rh.command"])[-3:] == ["fake.py", "method=a", "seed=2"]
    assert params["rh.host"] == socket.gethostname()
    assert params["rh.gpus"] == "" and params["rh.exit_code"] == "0"
    assert r.info.status == "FINISHED"
    assert r.info.experiment_id == repo.exp_id
    log = repo.artifact(r, "log.txt").read_text()
    assert "hello stdout" in log and "hello stderr" in log
    assert repo.artifact(r, "cuda.txt").read_text() == "<unset>"  # leasing off: untouched
    assert not repo.artifact(r, "diff.patch").exists()
    assert list(repo.tmpdir.iterdir()) == []  # RUN_DIR removed after the upload


def test_params_are_immutable(repo):
    repo.run()
    r = repo.only_run()
    with pytest.raises(Exception, match="(?i)chang"):
        repo.client.log_param(r.info.run_id, "rh.commit", "0" * 40)


def test_experiment_from_env_is_created_and_overrides_config(repo):
    p = repo.run(env={"MLFLOW_EXPERIMENT_NAME": "from-env"})
    assert p.returncode == 0, p.stderr
    exp = repo.client.get_experiment_by_name("from-env")
    assert exp is not None and repo.runs() == []
    assert len(repo.runs([exp.experiment_id])) == 1


def test_files_in_run_dir_become_artifacts(repo):
    repo.run("config=1")
    r = repo.only_run()
    assert repo.artifact(r, "config.json").is_file()
    assert repo.artifact(r, "metrics.json").is_file()
    assert r.data.metrics == {"acc": 1, "loss": 0.5}  # the metrics.json fallback


def test_command_attaching_with_mlflow_logs_into_the_same_run(repo):
    p = repo.run("attach=1", "exit=2")
    assert p.returncode == 2
    r = repo.only_run()
    assert r.data.metrics["attached"] == 7.0 and r.data.params["lr"] == "0.1"
    # The command's own end_run() said FINISHED; run.py sets the final status last.
    assert r.info.status == "FAILED"


def test_bad_metrics_file_is_not_fatal(repo):
    assert repo.run("metrics=list").returncode == 0
    r = repo.only_run()
    assert r.info.status == "FINISHED" and r.data.metrics == {}
    assert repo.artifact(r, "metrics.json").read_text() == "[1, 2]"


def test_failed_upload_keeps_run_dir(repo):
    if os.geteuid() == 0:
        pytest.skip("root ignores permissions")
    (repo.tmp / "artifacts").mkdir()
    (repo.tmp / "artifacts").chmod(0o500)
    try:
        p = repo.run()
    finally:
        (repo.tmp / "artifacts").chmod(0o700)
    assert p.returncode == 0
    [kept] = list(repo.tmpdir.iterdir())
    assert str(kept) in p.stderr and (kept / "log.txt").is_file()
    assert repo.only_run().info.status == "FINISHED"


def test_dirty_tree_with_untracked_file(repo):
    (repo.root / "fake.py").write_text((repo.root / "fake.py").read_text() + "\n# local edit\n")
    (repo.root / "new_module.py").write_text("x = 1\n")
    repo.run()
    r = repo.only_run()
    assert r.data.params["rh.dirty"] == "true"
    assert "# local edit" in repo.artifact(r, "diff.patch").read_text()
    assert repo.artifact(r, "untracked.txt").read_text().split() == ["new_module.py"]


def test_untracked_only_is_dirty(repo):
    (repo.root / "data").mkdir()
    (repo.root / "data" / "x.csv").write_text("1\n")
    repo.run()
    r = repo.only_run()
    assert r.data.params["rh.dirty"] == "true"
    assert repo.artifact(r, "untracked.txt").read_text().split() == ["data/x.csv"]


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


@pytest.mark.parametrize("args, seed", [(["seed=3"], "3"), (["--seed", "3"], "3"), (["--seed=3"], "3"), ([], "")])
def test_seed_recorded(repo, args, seed):
    repo.run(*args)
    assert repo.only_run().data.params["rh.seed"] == seed


def test_nonzero_exit_is_failed_and_returned(repo):
    p = repo.run("exit=3")
    assert p.returncode == 3
    r = repo.only_run()
    assert r.info.status == "FAILED" and r.data.params["rh.exit_code"] == "3"


def test_missing_command_is_a_failed_run(repo):
    p = repo.run(issue=None, cmd=["no-such-binary-xyz"])
    assert p.returncode == 127
    r = repo.only_run()
    assert r.info.status == "FAILED"
    assert r.data.params["rh.exit_code"] == "127" and r.data.params["rh.issue"] == ""
    assert "no-such-binary-xyz" in repo.artifact(r, "log.txt").read_text()


def test_unreachable_backend_fails_before_the_command(repo):
    marker = repo.tmp / "ran"
    p = repo.run(cmd=["touch", str(marker)], env={
        "MLFLOW_TRACKING_URI": f"http://127.0.0.1:{closed_port()}",
        "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "0", "MLFLOW_HTTP_REQUEST_TIMEOUT": "2"})
    assert p.returncode != 0 and "run.py:" in p.stderr
    assert not marker.exists()


def test_missing_mlflow_is_a_clear_error(repo):
    p = subprocess.run([sys.executable, "-S", str(RUN), "--", "true"], cwd=repo.root,
                       capture_output=True, text=True, env=repo.env, timeout=30)
    assert p.returncode != 0 and "mlflow is not installed" in p.stderr


def test_env_lock_and_data_manifest_hashes(make_repo):
    repo = make_repo(env_lock=["uv.lock", "requirements.txt"], data_manifest="data.sha256")
    (repo.root / "uv.lock").write_text("lock v1\n")
    (repo.root / "data.sha256").write_text("abc  train.bin\n")
    repo.commit("add lock and manifest")
    repo.run()
    params = repo.only_run().data.params
    assert params["rh.env_lock_sha"] == hashlib.sha256(b"lock v1\n").hexdigest()  # = sha256sum uv.lock
    assert params["rh.env_lock_missing"] == "requirements.txt"
    assert params["rh.data_manifest_sha"] == hashlib.sha256(b"abc  train.bin\n").hexdigest()


def test_missing_env_lock_is_recorded(repo):
    repo.run()
    params = repo.only_run().data.params
    assert params["rh.env_lock_sha"] == "" and params["rh.env_lock_missing"] == "uv.lock"
    assert params["rh.data_manifest_sha"] == ""


def test_more_gpus_than_configured_is_an_immediate_error(make_repo):
    repo = make_repo(gpus=[0, 1])
    p = repo.run(gpus=3)
    assert p.returncode != 0 and "--gpus" in p.stderr
    assert repo.runs() == []
    assert repo.run().returncode == 0  # without --gpus, one GPU is leased
    assert repo.only_run().data.params["rh.gpus"] == "0"


def test_gpus_with_leasing_off_is_an_error(repo):
    p = repo.run(gpus=1)
    assert p.returncode != 0 and repo.runs() == []


def test_concurrent_runs_lease_different_gpus(make_repo):
    repo = make_repo(gpus=[0, 1])
    hold = repo.tmp / "release"
    first = repo.start("hold=" + str(hold), gpus=1)
    try:
        wait_for(hold.with_suffix(".pid"))
        second = repo.run(gpus=1)
        assert second.returncode == 0, second.stderr
    finally:
        hold.write_text("go")
        first.communicate(timeout=30)
    runs = [repo.client.get_run(r.info.run_id) for r in repo.runs()]
    gpus = sorted(r.data.params["rh.gpus"] for r in runs)
    assert gpus == ["0", "1"]
    for r in runs:
        assert repo.artifact(r, "cuda.txt").read_text() == r.data.params["rh.gpus"]


def test_default_lock_dir_is_under_the_temp_dir(make_repo):
    repo = make_repo(gpus=[0], lock_dir="")
    assert repo.run().returncode == 0
    assert (repo.tmpdir / "rh-gpu-locks" / socket.gethostname() / "gpu0.lock").is_file()


def lock_is_free(path):
    with open(path, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def test_sigterm_is_killed_and_releases_lease(make_repo):
    repo = make_repo(gpus=[0])
    hold = repo.tmp / "never"
    p = repo.start("hold=" + str(hold))
    wait_for(hold.with_suffix(".pid"))
    lock = repo.locks / socket.gethostname() / "gpu0.lock"
    assert not lock_is_free(lock)
    p.send_signal(signal.SIGTERM)
    p.communicate(timeout=30)
    assert p.returncode == 128 + signal.SIGTERM
    r = repo.only_run()
    assert r.info.status == "KILLED"
    assert r.data.params["rh.exit_code"] == str(-signal.SIGTERM) and r.data.params["rh.gpus"] == "0"
    assert lock_is_free(lock)


def test_sigterm_while_waiting_for_gpus_is_killed_without_running(make_repo):
    repo = make_repo(gpus=[0])
    lock = repo.locks / socket.gethostname() / "gpu0.lock"
    lock.parent.mkdir(parents=True)
    with open(lock, "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        p = repo.start(cmd=["touch", str(repo.tmp / "ran")])
        while "waiting" not in (line := p.stderr.readline()):
            assert line, "run.py exited before waiting for the GPU"
        p.send_signal(signal.SIGTERM)
        p.communicate(timeout=30)
    assert p.returncode == 128 + signal.SIGTERM
    assert repo.only_run().info.status == "KILLED"
    assert not (repo.tmp / "ran").exists()


SIGINT_CHILD = r"""
import os, signal, sys, time
hits = []
signal.signal(signal.SIGINT, lambda *_: hits.append(1))
open(sys.argv[1], "w").close()
deadline = time.time() + 20
while not hits and time.time() < deadline:
    time.sleep(0.02)
time.sleep(0.5)  # a forwarded second SIGINT would land in this window
with open(os.path.join(os.environ["RUN_DIR"], "sigints"), "w") as f:
    f.write(str(len(hits)))
"""


def test_ctrl_c_reaches_the_command_once(repo):
    (repo.root / "sigint.py").write_text(SIGINT_CHILD)
    started = repo.tmp / "started"
    p = repo.start(cmd=[sys.executable, "sigint.py", str(started)], start_new_session=True)
    wait_for(started)
    os.killpg(p.pid, signal.SIGINT)  # what the terminal does on Ctrl-C
    p.communicate(timeout=30)
    r = repo.only_run()
    assert repo.artifact(r, "sigints").read_text() == "1"
    assert r.data.params["rh.exit_code"] == "0" and r.info.status == "FINISHED"


def kill_run_py(repo, p, hold):
    """SIGKILL run.py once its command runs; return the orphaned command's pid."""
    wait_for(hold.with_suffix(".pid"))
    p.kill()
    p.communicate(timeout=30)
    return int(hold.with_suffix(".pid").read_text())


def test_sigkill_leaves_the_run_running(repo):
    hold = repo.tmp / "never"
    child = kill_run_py(repo, repo.start("hold=" + str(hold)), hold)
    os.kill(child, signal.SIGKILL)
    r = repo.only_run()
    assert r.info.status == "RUNNING" and "rh.exit_code" not in r.data.params
    assert r.data.params["rh.commit"] == repo.git("rev-parse", "HEAD")


def test_lease_outlives_a_killed_run_py(make_repo):
    repo = make_repo(gpus=[0])
    hold = repo.tmp / "never"
    child = kill_run_py(repo, repo.start("hold=" + str(hold)), hold)
    lock = repo.locks / socket.gethostname() / "gpu0.lock"
    assert not lock_is_free(lock)  # the orphaned command still holds its GPU
    os.kill(child, signal.SIGKILL)
    deadline = time.time() + 10
    while not lock_is_free(lock):
        assert time.time() < deadline, "lease not released after the command died"
        time.sleep(0.02)

