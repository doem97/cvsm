#!/usr/bin/env python3
"""Run one command with a GPU lease and write an immutable run record.

    python scripts/run.py [--issue N] [--gpus K] [--config scripts/run.toml] -- <cmd...>

Everything goes to <storage>/runs/<run_id>/: start.json at launch, log.txt (stdout and
stderr of the command), diff.patch when the tree is dirty, and run.json once at the end.
The command gets RUN_DIR (write metrics.json and config.* there) and, when leasing is on,
CUDA_VISIBLE_DEVICES. Records are never modified after they are written.

A relative `storage` resolves against the main checkout (the parent of git's common dir),
so runs from linked worktrees land in the same place. env_lock and data_manifest paths
resolve against the current checkout. The exit status is the command's own; a command
killed by signal S gives 128 + S, and run.json records -S.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

RETRY_SECONDS = 30


def git(*args):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout


def load_config(path):
    cfg = {"env_lock": [], "data_manifest": "", "seed_key": "seed", "gpus": []}
    return cfg | tomllib.loads(Path(path).read_text())


def storage_root(cfg):
    path = Path(cfg["storage"]).expanduser()
    if path.is_absolute():
        return path
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return (Path(common).parent / path).resolve()


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


def write_once(path, obj):
    with open(path, "x") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    path.chmod(0o444)


def now():
    return datetime.now().astimezone().isoformat(timespec="microseconds")


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

    storage, start = storage_root(cfg), now()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
    run_dir = storage / "runs" / run_id
    run_dir.mkdir(parents=True)
    write_once(run_dir / "start.json", {"run_id": run_id, "issue": a.issue, "command": cmd, "start": start})
    print(f"run.py: {run_dir}", file=sys.stderr, flush=True)
    held = lease(ids, k, storage / "locks") if k else []

    # Capture the code state right before launch, after any wait for GPUs.
    top = Path(git("rev-parse", "--show-toplevel").strip())
    commit = git("rev-parse", "HEAD").strip()
    status = git("status", "--porcelain", "-z", "--untracked-files=all")
    untracked = [e[3:] for e in status.split("\0") if e.startswith("?? ")]
    if status:
        (run_dir / "diff.patch").write_text(git("diff", "HEAD"))
    env_sha, env_missing = hash_files(cfg["env_lock"], top)
    data_sha = hash_files([cfg["data_manifest"]], top)[0] if cfg["data_manifest"] else None

    env = dict(os.environ, RUN_DIR=str(run_dir))
    if ids:
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i, _ in held)
    with open(run_dir / "log.txt", "wb") as log:
        try:
            child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
        except OSError as e:
            log.write(f"run.py: {e}\n".encode())
            code = 127
        else:
            for s in (signal.SIGTERM, signal.SIGINT):
                signal.signal(s, lambda sig, _: child.send_signal(sig))
            code = child.wait()
    for _, f in held:
        f.close()

    configs = sorted(p for p in run_dir.glob("config.*") if p.is_file())
    write_once(run_dir / "run.json", {
        "run_id": run_id, "issue": a.issue, "commit": commit, "dirty": bool(status),
        "untracked": untracked, "command": cmd, "seed": split_seed(cmd, cfg["seed_key"])[0],
        "config": {"path": configs[0].name, "sha256": hashlib.sha256(configs[0].read_bytes()).hexdigest()}
        if configs else None,
        "env_lock_sha": env_sha, "env_lock_missing": env_missing, "data_manifest_sha": data_sha,
        "host": socket.gethostname(), "gpus": [i for i, _ in held], "start": start, "end": now(),
        "exit_code": code,
    })
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
