#!/usr/bin/env python3
"""Run one command with a GPU lease and record it as an MLflow run.

    python scripts/run.py [--issue N] [--gpus K] [--config scripts/run.toml] -- <cmd...>

The record goes wherever MLflow's own configuration points: MLFLOW_TRACKING_URI, or MLflow's
default when it is unset (mlflow.db and mlruns/ in the current directory; add them to
.gitignore, or every run is recorded as dirty). The experiment is MLFLOW_EXPERIMENT_NAME, else
`experiment` in run.toml, created if missing. The run is created before any wait for GPUs, so a
waiting or killed run shows as RUNNING. If the backend is unreachable, nothing is launched.

Provenance is logged as rh.* params, which MLflow never lets change: rh.issue, rh.command
(shlex-joined), rh.seed and rh.host at creation; rh.commit, rh.dirty (true or false),
rh.env_lock_sha, rh.env_lock_missing, rh.data_manifest_sha and rh.gpus right before launch;
rh.exit_code at the end. Absent values are "" and lists are comma-separated. The tag
mlflow.source.git.commit is set too. A dirty tree gets the artifacts diff.patch (git diff
HEAD) and untracked.txt before launch. env_lock and data_manifest paths resolve against the
checkout root.

The command gets MLFLOW_RUN_ID and MLFLOW_TRACKING_URI, so mlflow.start_run() in it attaches to
this run; RUN_DIR, a fresh temporary directory; and CUDA_VISIBLE_DEVICES when leasing.
Everything the command writes into $RUN_DIR becomes the run's artifacts. Its stdout and stderr
go to $RUN_DIR/log.txt, and a flat {name: number} $RUN_DIR/metrics.json is logged as metrics,
so training code need not import mlflow. RUN_DIR is removed after the upload, or kept and
printed if the upload fails.

The final status is FINISHED for exit 0, KILLED when a signal stopped the command, and FAILED
otherwise (127 when it cannot start). The exit status is the command's own; signal S gives
128 + S, and rh.exit_code records -S.

GPU locks are <lock_dir>/<host>/gpu<i>.lock and the command inherits them, so a lease lasts as
long as the command, even if run.py itself is killed. SIGTERM is forwarded to the command.
Ctrl-C already reaches it through the terminal, so SIGINT is not forwarded; stop a background
run with SIGTERM.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

try:
    import mlflow
    from mlflow import MlflowClient
    from mlflow.entities import Metric, Param, RunTag
    from mlflow.exceptions import MlflowException
except ImportError:
    sys.exit(f"{Path(sys.argv[0]).name}: mlflow is not installed "
             "(pip install mlflow, or mlflow-skinny with sqlalchemy and alembic)")

RETRY_SECONDS = 30


def git(*args):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout


def load_config(path):
    cfg = {"experiment": "Default", "env_lock": [], "data_manifest": "", "seed_key": "seed",
           "gpus": [], "lock_dir": ""}
    return cfg | tomllib.loads(Path(path).read_text())


def experiment_name(cfg):
    return os.environ.get("MLFLOW_EXPERIMENT_NAME") or cfg["experiment"]


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def split_seed(cmd, key):
    """Return (seed, cmd without seed tokens); matches key=V, --key=V and --key V."""
    seed, rest, i = None, [], 0
    while i < len(cmd):
        m = re.fullmatch(rf"(?:--)?{re.escape(key)}=(.*)", cmd[i])
        if m:
            seed = m.group(1)
        elif cmd[i] == f"--{key}" and i + 1 < len(cmd):
            seed, i = cmd[i + 1], i + 1
        else:
            rest.append(cmd[i])
        i += 1
    return (int(seed) if seed and re.fullmatch(r"-?\d+", seed) else seed), rest


def hash_files(paths, base):
    """sha256 over the contents of the existing files, sorted by path; plus the missing ones."""
    h, found, missing = hashlib.sha256(), False, []
    for p in sorted(paths):
        if (base / p).is_file():
            h.update((base / p).read_bytes())
            found = True
        else:
            missing.append(p)
    return (h.hexdigest() if found else None), missing


def lease(ids, k, lock_dir):
    """Hold k of the GPU lock files; until then release all and retry. Returns [(id, file)]."""
    lock_dir.mkdir(parents=True, exist_ok=True)
    while True:
        held = []
        for i in ids:
            f = open(lock_dir / f"gpu{i}.lock", "a")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append((i, f))
            except BlockingIOError:
                f.close()
            if len(held) == k:
                return held
        for _, f in held:
            f.close()
        print(f"run.py: waiting for {k} free GPU(s) of {ids}", file=sys.stderr, flush=True)
        time.sleep(RETRY_SECONDS)


def params(**kw):
    """rh.* params as strings: None is "", booleans are true or false, lists are comma-separated."""
    def enc(v):
        if isinstance(v, list):
            return ",".join(map(str, v))
        return "" if v is None else str(v).lower() if isinstance(v, bool) else str(v)
    return [Param(f"rh.{k}", enc(v)) for k, v in kw.items()]


def experiment_id(client, name):
    exp = client.get_experiment_by_name(name)
    if exp:
        return exp.experiment_id
    try:
        return client.create_experiment(name)
    except MlflowException:  # another run.py may have created it meanwhile
        if exp := client.get_experiment_by_name(name):
            return exp.experiment_id
        raise


def upload(client, run_id, run_dir):
    """Log metrics.json and every file in run_dir; remove run_dir once all of it is stored."""
    try:
        m = json.loads((run_dir / "metrics.json").read_text())
    except (OSError, ValueError):
        m = None
    try:
        if isinstance(m, dict):
            now = int(time.time() * 1000)
            client.log_batch(run_id, metrics=[Metric(k, v, now, 0) for k, v in m.items() if num(v)])
        client.log_artifacts(run_id, str(run_dir))
        shutil.rmtree(run_dir)
    except Exception as e:
        print(f"run.py: upload failed, kept {run_dir}: {e}", file=sys.stderr)


def stop(sig, _):
    raise KeyboardInterrupt(sig)


def main(argv):
    cut = argv.index("--") if "--" in argv else len(argv)
    ap = argparse.ArgumentParser(prog="run.py", usage="%(prog)s [options] -- <cmd...>")
    ap.add_argument("--issue", type=int)
    ap.add_argument("--gpus", type=int, help="GPUs to lease (default 1 when gpus is configured)")
    ap.add_argument("--config", default="scripts/run.toml")
    a, cmd = ap.parse_args(argv[:cut]), argv[cut + 1:]
    if not cmd:
        ap.error("no command after --")
    cfg = load_config(a.config)
    ids = cfg["gpus"]
    k = a.gpus if a.gpus is not None else min(1, len(ids))
    if not 0 <= k <= len(ids):
        ap.error(f"--gpus {k}: {len(ids)} GPU(s) configured in {a.config}")

    # Resolve the URI once (MLflow's default is relative to the cwd) so the command writes to
    # the same place. It may carry credentials, so it is never printed.
    uri, exp_name = mlflow.get_tracking_uri(), experiment_name(cfg)
    client = MlflowClient(uri)
    try:
        run_id = client.create_run(experiment_id(client, exp_name)).info.run_id
        client.log_batch(run_id, params=params(issue=a.issue, command=shlex.join(cmd),
                                               seed=split_seed(cmd, cfg["seed_key"])[0],
                                               host=socket.gethostname()))
    except Exception as e:
        sys.exit(f"run.py: cannot record the run, nothing was launched: {e}")
    print(f"run.py: MLflow run {run_id} in experiment {exp_name}", file=sys.stderr, flush=True)

    # Until the command starts (a GPU wait can be long), SIGTERM and Ctrl-C mark the run KILLED.
    signal.signal(signal.SIGTERM, stop)
    try:
        locks = Path(cfg["lock_dir"] or Path(tempfile.gettempdir()) / "rh-gpu-locks").expanduser()
        held = lease(ids, k, locks / socket.gethostname()) if k else []
        # Capture the code state right before launch, after any wait for GPUs.
        top = Path(git("rev-parse", "--show-toplevel").strip())
        commit = git("rev-parse", "HEAD").strip()
        status = git("status", "--porcelain", "-z", "--untracked-files=all")
        env_sha, env_missing = hash_files(cfg["env_lock"], top)
        data_sha = hash_files([cfg["data_manifest"]], top)[0] if cfg["data_manifest"] else None
        client.log_batch(run_id, params=params(
            commit=commit, dirty=bool(status), env_lock_sha=env_sha, env_lock_missing=env_missing,
            data_manifest_sha=data_sha, gpus=[i for i, _ in held]),
            tags=[RunTag("mlflow.source.git.commit", commit)])
        if status:
            untracked = [e[3:] for e in status.split("\0") if e.startswith("?? ")]
            client.log_text(run_id, git("diff", "HEAD"), "diff.patch")
            client.log_text(run_id, "".join(f"{p}\n" for p in untracked), "untracked.txt")
        run_dir = Path(tempfile.mkdtemp(prefix="rh-run-"))
    except BaseException as e:
        client.set_terminated(run_id, "KILLED" if isinstance(e, KeyboardInterrupt) else "FAILED")
        if isinstance(e, KeyboardInterrupt):
            return 128 + (e.args[0] if e.args else signal.SIGINT)
        raise

    env = dict(os.environ, MLFLOW_RUN_ID=run_id, MLFLOW_TRACKING_URI=uri, RUN_DIR=str(run_dir))
    if ids:
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i, _ in held)
    with open(run_dir / "log.txt", "wb") as log:
        try:
            child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                     pass_fds=[f.fileno() for _, f in held])
        except OSError as e:
            log.write(f"run.py: {e}\n".encode())
            code = 127
        else:
            # Ctrl-C reaches the command directly through the terminal's process group;
            # forwarding SIGINT as well would interrupt its cleanup a second time.
            signal.signal(signal.SIGINT, lambda *_: None)
            signal.signal(signal.SIGTERM, lambda sig, _: child.send_signal(sig))
            code = child.wait()
    for _, f in held:
        f.close()

    upload(client, run_id, run_dir)
    try:
        client.log_batch(run_id, params=params(exit_code=code))
        # Set last: a command that called mlflow.end_run() has already marked the run FINISHED.
        client.set_terminated(run_id, "FINISHED" if code == 0 else "KILLED" if code < 0 else "FAILED")
    except Exception as e:
        print(f"run.py: cannot finish the record of run {run_id}: {e}", file=sys.stderr)
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
