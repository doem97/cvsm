"""Helpers for the scripts/run.py and scripts/results.py tests: a temp repo plus a temp MLflow backend."""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from mlflow import MlflowClient
from mlflow.entities import ViewType

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "scripts" / "run.py"
RESULTS = ROOT / "scripts" / "results.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
EXPERIMENT = "cvsm-test"
GITIGNORE = "mlflow.db*\nmlartifacts/\nmlruns/\n"  # MLflow's default files in the clone

# A fake training command. key=value args; writes metrics.json into $RUN_DIR (metrics=list writes a
# JSON list instead); config=1 also writes config.json; hold=<path> writes its pid to <path>.pid and
# waits for <path> to appear; exit=<n> sets the exit code; fail_seed=<s> exits 1 when seed=<s>;
# attach=1 logs through mlflow.start_run() as a training script would.
FAKE = r'''
import json, os, sys, time
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
run_dir = os.environ["RUN_DIR"]
seed = int(args.get("seed", args.get("--seed", 1)))
scale = {"a": 1, "b": 10}[args.get("method", "a")]
metrics = [1, 2] if args.get("metrics") == "list" else {"acc": scale * seed, "loss": 0.5}
with open(os.path.join(run_dir, "metrics.json"), "w") as f:
    json.dump(metrics, f)
if args.get("config"):
    with open(os.path.join(run_dir, "config.json"), "w") as f:
        json.dump(args, f)
with open(os.path.join(run_dir, "cuda.txt"), "w") as f:
    f.write(os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"))
if args.get("attach"):
    import mlflow
    with mlflow.start_run():
        mlflow.log_metric("attached", 7.0)
        mlflow.log_param("lr", "0.1")
print("hello stdout")
print("hello stderr", file=sys.stderr)
if "hold" in args:
    with open(args["hold"] + ".pid", "w") as f:
        f.write(str(os.getpid()))
    deadline = time.time() + 20
    while not os.path.exists(args["hold"]) and time.time() < deadline:
        time.sleep(0.02)
sys.exit(1 if args.get("fail_seed") == str(seed) else int(args.get("exit", 0)))
'''


def local_path(uri):
    return Path(unquote(urlparse(uri).path)) if uri.startswith("file:") else Path(uri)


def wait_for(path, timeout=10):
    deadline = time.time() + timeout
    while not path.exists():
        assert time.time() < deadline, f"timed out waiting for {path}"
        time.sleep(0.02)


def closed_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Repo:
    """A temporary git repo with scripts/run.toml and fake.py committed, a copy of a migrated
    SQLite backend, the test experiment (artifacts outside the repo) and a private TMPDIR.
    A .gitignore with just MLflow's default files is committed, so they keep the tree clean; the
    project's own .gitignore is not used, since adopters' ignore lines vary."""

    def __init__(self, tmp, template, **cfg):
        self.tmp = tmp
        self.root = tmp / "repo"
        self.locks = tmp / "locks"
        self.tmpdir = tmp / "tmp"
        self.tmpdir.mkdir()
        self.root.mkdir()
        self.template = template
        shutil.copy(template, tmp / "mlflow.db")
        self.uri = f"sqlite:///{tmp / 'mlflow.db'}"
        self.client = MlflowClient(self.uri)
        self.exp_id = self.client.create_experiment(EXPERIMENT, artifact_location=str(tmp / "artifacts"))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("MLFLOW_")}
        self.env.update(GIT_ENV, MLFLOW_TRACKING_URI=self.uri, TMPDIR=str(self.tmpdir))
        self.git("init", "-q", "-b", "main")
        (self.root / "fake.py").write_text(FAKE)
        (self.root / ".gitignore").write_text(GITIGNORE)
        self.configure(**cfg)
        self.commit("init")

    def configure(self, env_lock=("uv.lock",), data_manifest="", gpus=(), lock_dir=None):
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "scripts" / "run.toml").write_text(
            f"experiment = {json.dumps(EXPERIMENT)}\nenv_lock = {json.dumps(list(env_lock))}\n"
            f"data_manifest = {json.dumps(data_manifest)}\nseed_key = \"seed\"\n"
            f"gpus = {json.dumps(list(gpus))}\n"
            f"lock_dir = {json.dumps(str(self.locks) if lock_dir is None else lock_dir)}\n")

    def git(self, *args, cwd=None):
        out = subprocess.run(["git", *args], cwd=cwd or self.root, check=True, text=True,
                             capture_output=True, env={**os.environ, **GIT_ENV})
        return out.stdout.strip()

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def start(self, *args, issue=5, gpus=None, cmd=None, env=None, cwd=None, **popen):
        """Launch run.py without waiting. args are the fake command's key=value args."""
        opts = ["--issue", str(issue)] if issue is not None else []
        opts += ["--gpus", str(gpus)] if gpus is not None else []
        cmd = cmd or [sys.executable, "fake.py", *args]
        return subprocess.Popen([sys.executable, str(RUN), *opts, "--", *cmd], cwd=cwd or self.root,
                                env={**self.env, **(env or {})}, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, **popen)

    def run(self, *args, **kw):
        p = self.start(*args, **kw)
        out, err = p.communicate(timeout=30)
        return subprocess.CompletedProcess(p.args, p.returncode, out, err)

    def run_many(self, *arg_lists, **kw):
        """Run several commands concurrently (no GPUs configured, so nothing waits)."""
        procs = [self.start(*args, **kw) for args in arg_lists]
        return [p.communicate(timeout=30) and p.returncode for p in procs]

    def record(self, start, status="FINISHED", metrics=None, cfg=None, **cvsm):
        """Write a run as run.py would, without running it; cvsm are the cvsm.* params and cfg the
        cfg.* params, by dotted key."""
        run_id = self.client.create_run(self.exp_id, start_time=start).info.run_id
        for key, value in cvsm.items():
            self.client.log_param(run_id, f"cvsm.{key}", value)
        for key, value in (cfg or {}).items():
            self.client.log_param(run_id, f"cfg.{key}", value)
        for key, value in (metrics or {}).items():
            self.client.log_metric(run_id, key, value)
        if status != "RUNNING":
            self.client.set_terminated(run_id, status)
        return run_id

    def runs(self, experiment_ids=None):
        return self.client.search_runs(experiment_ids or [self.exp_id], run_view_type=ViewType.ALL)

    def only_run(self):
        runs = self.runs()
        assert len(runs) == 1, [r.info.run_id for r in runs]
        return self.client.get_run(runs[0].info.run_id)

    def artifact(self, run, name):
        return local_path(run.info.artifact_uri) / name

    def results(self, *args, issue=5, env=None, cwd=None, input=None):
        """results.py's output; issue is a number or a list of them, input goes to stdin."""
        issues = [str(i) for i in (issue if isinstance(issue, list) else [issue])]
        out = subprocess.run([sys.executable, str(RESULTS), "--issue", *issues, *args],
                             cwd=cwd or self.root, capture_output=True, text=True, timeout=30,
                             env={**self.env, **(env or {})}, input=input)
        assert out.returncode == 0, out.stderr
        assert "mlflow.agent.hint" not in out.stderr
        return out.stdout
