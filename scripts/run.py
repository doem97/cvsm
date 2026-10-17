#!/usr/bin/env python3
"""Run one command with a GPU lease and record it as an MLflow run.

    python scripts/run.py [--issue N] [--gpus K] [--config scripts/run.toml] -- <cmd...>

The record goes where MLFLOW_TRACKING_URI points. When it is unset, the store is
<main clone>/mlflow.db (the main clone is the parent of git's common dir), so every worktree of
a clone shares one store that outlives the worktrees. The experiment is MLFLOW_EXPERIMENT_NAME,
else `experiment` in run.toml, created if missing; in a database store (no server) a new
experiment keeps its artifacts in mlartifacts/ next to the SQLite file, or in
<main clone>/mlartifacts for other databases. The run is created before any wait for GPUs, so
a waiting or killed run shows as RUNNING. If the backend is unreachable, nothing is launched.

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

The command writes its resolved config, every setting that can affect results, as a JSON
object to $RUN_DIR/config.json at start (from one process only, e.g. rank 0). run.py looks for
it every POLL_SECONDS while the command runs and logs it once, as soon as it parses as a JSON
object, so a running run can already be checked against its study's spec; a file that only
appears by the end is logged then, before the upload. Its settings become params
cfg.<dotted key>: nested objects flatten to dotted keys (an empty one is the value {}), strings
are logged as they are and other values as JSON. Keys and values longer than MLflow's limits
(250 and 6000 characters in MLflow 3) are truncated to them, as MLflow's autologging does; the
file itself is uploaded with the other RUN_DIR files.

The final status is FINISHED for exit 0, KILLED when a signal stopped the command, and FAILED
otherwise (127 when it cannot start). The exit status is the command's own; signal S gives
128 + S, and rh.exit_code records -S.

GPU locks are <lock_dir>/<host>/gpu<i>.lock and the command inherits them, so a lease lasts as
long as the command, even if run.py itself is killed. The default lock_dir, <tmp>/rh-gpu-locks,
is shared by all users of the host only if they share the temp dir (TMPDIR). When several users
share a machine and TMPDIR is per-user, set lock_dir in run.toml to a directory they can
all write to; run.py makes the per-host subdirectory it creates there shareable (sticky,
world-writable). Directories that already exist keep their permissions.

SIGTERM, and SIGHUP unless it is ignored (nohup), are forwarded to the command. Ctrl-C already
reaches it through the terminal, so SIGINT is not forwarded; stop a background run with
SIGTERM. Any of the three before launch, including during the GPU wait, ends the run as KILLED
without launching.
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
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # MLflow 3.17 logs a hint on every import
try:
    from mlflow import MlflowClient
    from mlflow.entities import Metric, Param, RunTag
    from mlflow.exceptions import MlflowException
    from mlflow.utils.validation import (MAX_ENTITY_KEY_LENGTH, MAX_PARAM_VAL_LENGTH,
                                         MAX_PARAMS_TAGS_PER_BATCH)
except ImportError:
    sys.exit(f"{Path(sys.argv[0]).name}: mlflow is not installed "
             "(pip install mlflow, or mlflow-skinny with sqlalchemy and alembic)")

RETRY_SECONDS = 30
POLL_SECONDS = 0.5  # how often a running command's RUN_DIR is checked for config.json


def git(*args, raw=False):
    """Output as bytes (raw) or decoded like file names: undecodable bytes survive as surrogates."""
    p = subprocess.run(["git", *args], capture_output=True)
    if p.returncode:
        sys.exit(f"git {' '.join(args)}: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout if raw else os.fsdecode(p.stdout)


def load_config(path):
    cfg = {"experiment": "Default", "env_lock": [], "data_manifest": "", "seed_key": "seed",
           "gpus": [], "lock_dir": ""}
    return cfg | tomllib.loads(Path(path).read_text())


def main_clone():
    return Path(git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent


def tracking_uri():
    """MLFLOW_TRACKING_URI, else a SQLite store in the main clone, shared by its worktrees."""
    return os.environ.get("MLFLOW_TRACKING_URI") or f"sqlite:///{main_clone() / 'mlflow.db'}"


def sqlite_path(uri):
    if uri.startswith("sqlite:") and ":///" in uri:
        return Path(unquote(uri.split(":///", 1)[1].split("?", 1)[0])).absolute()
    return None


def artifact_root(uri, clone):
    """Where a new experiment in a database store keeps artifacts; None leaves it to MLflow,
    whose default is relative to the cwd, i.e. inside a worktree that will be deleted."""
    if db := sqlite_path(uri):
        return db.parent / "mlartifacts"
    scheme = uri.split(":", 1)[0].split("+", 1)[0]
    return clone / "mlartifacts" if scheme in ("postgresql", "mysql", "mssql") else None


@contextmanager
def store_setup(uri):
    """Hold <db>.lock for a SQLite store: MLflow's first-time migration of a new database
    fails when several processes run it at once. Other stores need no lock."""
    if not (db := sqlite_path(uri)):
        yield
        return
    fd = os.open(f"{db}.lock", os.O_RDWR | os.O_CREAT, 0o666)  # writable, for flock on NFS
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


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


def lock_dir(configured):
    """<lock_dir>/<host>, shareable by every user who can reach it."""
    if configured:
        # Per host, as a configured lock_dir may be on storage that several machines share.
        path = Path(configured).expanduser() / socket.gethostname()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.mkdir()
        except FileExistsError:
            return path  # an existing one keeps its permissions
        path.chmod(0o1777)  # else another user's O_CREAT fails there, as with the default below
        return path
    base = Path(tempfile.gettempdir()) / "rh-gpu-locks"
    for path in (base, base / socket.gethostname()):
        path.mkdir(exist_ok=True)
        if path.stat().st_uid == os.getuid():
            path.chmod(0o1777)  # mkdir applies the umask; sticky, so no one deletes others' locks
    return base / socket.gethostname()


def lock_fd(path):
    # Another user's lock file is read-only to us, and a local flock needs no write access. On
    # NFS, though, an exclusive flock needs a writable fd, so read-only is only the fallback.
    try:
        return os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    except PermissionError:
        return os.open(path, os.O_RDONLY)


def lease(ids, k, locks, stopped):
    """Hold k of the GPU lock files; until then release all and retry. Returns [(id, fd)], or
    None once stopped() is true."""
    while True:
        held = []
        for i in ids:
            fd = lock_fd(locks / f"gpu{i}.lock")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append((i, fd))
            except BlockingIOError:
                os.close(fd)
            if len(held) == k:
                return held
        for _, fd in held:
            os.close(fd)
        print(f"run.py: waiting for {k} free GPU(s) of {ids}", file=sys.stderr, flush=True)
        deadline = time.monotonic() + RETRY_SECONDS
        while time.monotonic() < deadline:  # in slices: a stop signal does not interrupt sleep
            if stopped():
                return None
            time.sleep(min(0.1, RETRY_SECONDS))


def params(**kw):
    """rh.* params as strings: None is "", booleans are true or false, lists are comma-separated."""
    def enc(v):
        if isinstance(v, list):
            return ",".join(map(str, v))
        return "" if v is None else str(v).lower() if isinstance(v, bool) else str(v)
    return [Param(f"rh.{k}", enc(v)) for k, v in kw.items()]


def experiment_id(client, name, uri):
    exp = client.get_experiment_by_name(name)
    if exp:
        return exp.experiment_id
    root = artifact_root(uri, main_clone())
    try:
        return client.create_experiment(name, artifact_location=root and str(root))
    except MlflowException:  # another run.py may have created it meanwhile
        if exp := client.get_experiment_by_name(name):
            return exp.experiment_id
        raise


def flatten(cfg, prefix="cfg."):
    """(cfg.<dotted key>, value) pairs: strings as they are, other values as JSON."""
    for k, v in cfg.items():
        if isinstance(v, dict) and v:
            yield from flatten(v, f"{prefix}{k}.")
        else:
            yield prefix + k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def log_config(client, run_id, run_dir):
    """Log $RUN_DIR/config.json as cfg.* params once it is a JSON object; True once done."""
    try:
        cfg = json.loads((run_dir / "config.json").read_bytes())
    except (OSError, ValueError):
        return False
    if not isinstance(cfg, dict):
        return False
    ps = [Param(k[:MAX_ENTITY_KEY_LENGTH], v[:MAX_PARAM_VAL_LENGTH]) for k, v in flatten(cfg)]
    try:
        for i in range(0, len(ps), MAX_PARAMS_TAGS_PER_BATCH):
            client.log_batch(run_id, params=ps[i:i + MAX_PARAMS_TAGS_PER_BATCH])
    except Exception as e:
        print(f"run.py: cannot log config.json of run {run_id}: {e}", file=sys.stderr)
    return True


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

    # Stop signals before launch are kept in pending (the run then ends KILLED without
    # launching); afterwards SIGTERM and SIGHUP are forwarded to the command. Ctrl-C reaches
    # the command directly through the terminal's process group, so forwarding SIGINT would
    # interrupt its cleanup a second time. A signal ignored at startup (nohup, background jobs) stays ignored.
    child, pending = None, []

    def on_stop(sig, _):
        if child is None:
            pending.append(sig)
        elif sig != signal.SIGINT:
            child.send_signal(sig)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(sig) is not signal.SIG_IGN:  # keep what nohup or the shell ignored
            signal.signal(sig, on_stop)

    # The command gets this URI too, so it writes to the same store. It may carry
    # credentials, so it is never printed.
    uri, exp_name = tracking_uri(), experiment_name(cfg)
    try:
        with store_setup(uri):
            client = MlflowClient(uri)
            exp_id = experiment_id(client, exp_name, uri)
        run_id = client.create_run(exp_id).info.run_id
        client.log_batch(run_id, params=params(issue=a.issue, command=shlex.join(cmd),
                                               seed=split_seed(cmd, cfg["seed_key"])[0],
                                               host=socket.gethostname()))
    except Exception as e:
        sys.exit(f"run.py: cannot record the run, nothing was launched: {e}")
    print(f"run.py: MLflow run {run_id} in experiment {exp_name}", file=sys.stderr, flush=True)

    try:
        held = lease(ids, k, lock_dir(cfg["lock_dir"]), lambda: pending) if k else []
        if held is not None:
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
            if status:  # as bytes: a diff of non-UTF-8 files must stay byte-exact
                untracked = [e[3:] for e in status.split("\0") if e.startswith("?? ")]
                with tempfile.TemporaryDirectory() as d:
                    Path(d, "diff.patch").write_bytes(git("diff", "HEAD", raw=True))
                    paths = b"".join(os.fsencode(p) + b"\n" for p in untracked)
                    Path(d, "untracked.txt").write_bytes(paths)
                    client.log_artifacts(run_id, d)
            run_dir = Path(tempfile.mkdtemp(prefix="rh-run-"))
    except BaseException:
        client.set_terminated(run_id, "FAILED")
        raise
    if pending:  # a stop signal came before launch, possibly during the GPU wait
        if held is not None:
            os.rmdir(run_dir)
        client.set_terminated(run_id, "KILLED")
        return 128 + pending[0]

    env = dict(os.environ, MLFLOW_RUN_ID=run_id, MLFLOW_TRACKING_URI=uri, RUN_DIR=str(run_dir))
    if ids:
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i, _ in held)
    logged = False  # config.json
    with open(run_dir / "log.txt", "wb") as log:
        try:
            child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                     pass_fds=[fd for _, fd in held])
        except OSError as e:
            log.write(f"run.py: {e}\n".encode())
            code = 127
        else:
            for sig in pending:  # arrived while Popen ran, before the handler could see child
                if sig != signal.SIGINT:
                    child.send_signal(sig)
            while True:
                try:
                    code = child.wait(POLL_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    logged = logged or log_config(client, run_id, run_dir)
    for _, fd in held:
        os.close(fd)

    if not logged:
        log_config(client, run_id, run_dir)
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
