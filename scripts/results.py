#!/usr/bin/env python3
"""Print a Markdown results table for the run records of one issue.

    python scripts/results.py --issue N [--metric M ...] [--config scripts/run.toml]

Runs are grouped by command with the seed tokens removed. Per group: n (runs that exited
0, which the statistics use), n_failed, and the mean and sample std of each metric from
metrics.json. Provenance differences (commit, env lock, data manifest), dirty trees and
incomplete runs (start.json without run.json) are flagged; whether runs are comparable
is for the reader to decide.
"""
import argparse
import json
import shlex
import statistics
import subprocess
from datetime import datetime

from run import load_config, split_seed, storage_root


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def fmt(x):
    return f"{x:.4g}"


def short(values, n):
    return ", ".join(dict.fromkeys(v[:n] if v else "none" for v in values))


def main():
    ap = argparse.ArgumentParser(prog="results.py")
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--metric", nargs="+", action="extend", help="metrics to show (default all)")
    ap.add_argument("--config", default="scripts/run.toml")
    a = ap.parse_args()
    cfg = load_config(a.config)

    runs, incomplete = [], []
    for d in sorted((storage_root(cfg) / "runs").glob("*/")):
        rec = load(d / "run.json")
        if rec is None:
            if (load(d / "start.json") or {}).get("issue") == a.issue:
                incomplete.append(d.name)
        elif rec.get("issue") == a.issue:
            rec["metrics"] = load(d / "metrics.json") or {}
            runs.append(rec)
    runs.sort(key=lambda r: datetime.fromisoformat(r["start"]))
    groups = {}
    for r in runs:
        groups.setdefault(shlex.join(split_seed(r["command"], cfg["seed_key"])[1]), []).append(r)
    metrics = a.metric or sorted({m for r in runs for m, v in r["metrics"].items() if num(v)})

    head = ["command", "n", "n_failed", *(f"{m} {s}" for m in metrics for s in ("mean", "std")),
            "commit", "env_lock", "data"]
    out = [f"Results for #{a.issue}: {len(runs)} run(s) in {len(groups)} group(s), "
           "grouped by command without the seed.", "",
           "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for cmd, rs in groups.items():
        ok = [r for r in rs if r["exit_code"] == 0]
        row = ["`" + cmd.replace("|", "\\|") + "`", str(len(ok)), str(len(rs) - len(ok))]
        for m in metrics:
            v = [r["metrics"][m] for r in ok if num(r["metrics"].get(m))]
            row += [fmt(statistics.mean(v)) if v else "—", fmt(statistics.stdev(v)) if len(v) > 1 else "—"]
        row += [short((r["commit"] for r in rs), 7), short((r["env_lock_sha"] for r in rs), 8),
                short((r["data_manifest_sha"] for r in rs), 8)]
        out.append("| " + " | ".join(row) + " |")

    flags = []
    commits = list(dict.fromkeys(r["commit"] for r in runs))  # in order of run start
    if len(commits) > 1:
        first, last = commits[0], commits[-1]
        p = subprocess.run(["git", "diff", "--stat", first, last], capture_output=True, text=True)
        flags += [f"- commits differ: {short(commits, 7)}; `git diff --stat {first[:7]} {last[:7]}`:",
                  "", "```", (p.stdout or p.stderr).rstrip(), "```"]
    for key, name in (("env_lock_sha", "env"), ("data_manifest_sha", "data")):
        if len({r[key] for r in runs}) > 1:
            flags.append(f"- {name} differs: {short((r[key] for r in runs), 8)}")
    missing = [r for r in runs if r["env_lock_missing"]]
    if missing:
        files = sorted({f for r in missing for f in r["env_lock_missing"]})
        flags.append(f"- env lock missing in {len(missing)} run(s): {', '.join(files)}")
    dirty = [r["run_id"] for r in runs if r["dirty"]]
    if dirty:
        flags.append(f"- dirty runs ({len(dirty)}, see diff.patch): {', '.join(dirty)}")
    if incomplete:
        flags.append(f"- incomplete runs ({len(incomplete)}, no run.json: still running or killed): {', '.join(incomplete)}")
    print("\n".join(out + ["", "Flags:", *(flags or ["- none"])]))


if __name__ == "__main__":
    main()
