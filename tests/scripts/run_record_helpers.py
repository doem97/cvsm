"""Helpers for the scripts/run.py and scripts/results.py tests (a temp repo plus storage)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "scripts" / "run.py"
RESULTS = ROOT / "scripts" / "results.py"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}

# A fake training command. key=value args; writes metrics.json (and config.json on config=1)
# into $RUN_DIR; hold=<path> waits for that file to appear; exit=<n> sets the exit code;
# fail_seed=<s> exits 1 when seed=<s> (same group key, so a failure inside one group).
FAKE = r'''
import json, os, sys, time
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
run_dir = os.environ["RUN_DIR"]
seed = int(args.get("seed", 1))
scale = {"a": 1, "b": 10}[args.get("method", "a")]
with open(os.path.join(run_dir, "metrics.json"), "w") as f:
    json.dump({"acc": scale * seed, "loss": 0.5}, f)
if args.get("config"):
    with open(os.path.join(run_dir, "config.json"), "w") as f:
        json.dump(args, f)
with open(os.path.join(run_dir, "cuda.txt"), "w") as f:
    f.write(os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"))
print("hello stdout")
print("hello stderr", file=sys.stderr)
if "hold" in args:
    with open(os.path.join(run_dir, "started"), "w") as f:
        f.write(str(os.getpid()))
    deadline = time.time() + 20
    while not os.path.exists(args["hold"]) and time.time() < deadline:
        time.sleep(0.02)
sys.exit(1 if args.get("fail_seed") == str(seed) else int(args.get("exit", 0)))
'''


class Repo:
    """A temporary git repo with scripts/run.toml and fake.py committed, plus a storage dir."""

    def __init__(self, tmp, storage=None, **cfg):
        self.root = tmp / "repo"
        self.storage = tmp / "storage"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.root / "fake.py").write_text(FAKE)
        self.configure(storage=storage or str(self.storage), **cfg)
        self.commit("init")

    def configure(self, storage, env_lock=("uv.lock",), data_manifest="", gpus=()):
        (self.root / "scripts").mkdir(exist_ok=True)
        (self.root / "scripts" / "run.toml").write_text(
            f"storage = {json.dumps(storage)}\nenv_lock = {json.dumps(list(env_lock))}\n"
            f"data_manifest = {json.dumps(data_manifest)}\nseed_key = \"seed\"\n"
            f"gpus = {json.dumps(list(gpus))}\n")

    def git(self, *args, cwd=None):
        out = subprocess.run(["git", *args], cwd=cwd or self.root, check=True, text=True,
                             capture_output=True, env={**os.environ, **GIT_ENV})
        return out.stdout.strip()

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def start(self, *args, issue=5, gpus=None, cwd=None):
        """Launch run.py without waiting. args are the fake command's key=value args."""
        opts = ["--issue", str(issue)] if issue is not None else []
        opts += ["--gpus", str(gpus)] if gpus is not None else []
        return subprocess.Popen([sys.executable, str(RUN), *opts, "--", sys.executable, "fake.py", *args],
                                cwd=cwd or self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def run(self, *args, **kw):
        p = self.start(*args, **kw)
        out, err = p.communicate(timeout=30)
        return subprocess.CompletedProcess(p.args, p.returncode, out, err)

    def run_dirs(self):
        return sorted((self.storage / "runs").iterdir()) if (self.storage / "runs").exists() else []

    def record(self, run_dir):
        return json.loads((run_dir / "run.json").read_text())

    def results(self, *args, issue=5, cwd=None):
        out = subprocess.run([sys.executable, str(RESULTS), "--issue", str(issue), *args],
                             cwd=cwd or self.root, capture_output=True, text=True, timeout=30)
        assert out.returncode == 0, out.stderr
        return out.stdout

