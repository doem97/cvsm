#!/usr/bin/env python3
"""Print a Markdown results table for the MLflow runs of one issue.

    python scripts/results.py --issue N [--metric M ...] [--config scripts/run.toml]

Reads the runs whose rh.issue param is N, deleted ones included, from the experiment run.py
writes to (MLFLOW_EXPERIMENT_NAME, else `experiment` in run.toml) in the store it writes to
(MLFLOW_TRACKING_URI, else <main clone>/mlflow.db). Runs are grouped by command with the seed
tokens removed. Per group: n (runs that exited 0, which the statistics use), n_failed (runs
that ended any other way), and the mean and sample std of each metric's latest value.
Provenance differences (commit, env lock, data manifest), dirty trees, successful runs without
metrics, incomplete runs (still RUNNING) and deleted runs are flagged; whether runs are
comparable is for the reader to decide.
"""
import argparse
import shlex
import statistics
import subprocess

from run import MlflowClient, experiment_name, load_config, num, split_seed, store_setup, tracking_uri
from mlflow.entities import ViewType


def fetch(client, exp_id, issue):
    runs, token = [], None
    while True:
        page = client.search_runs([exp_id], f"params.`rh.issue` = '{issue}'",
                                  run_view_type=ViewType.ALL, max_results=1000, page_token=token)
        runs += page
        if not (token := page.token):
            return runs


def fmt(x):
    return f"{x:.4g}"


def short(values, n):
    return ", ".join(dict.fromkeys(v[:n] if v else "无" for v in values))


def ids(runs):
    return ", ".join(r["id"] for r in runs)


def main():
    ap = argparse.ArgumentParser(prog="results.py")
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--metric", nargs="+", action="extend", help="metrics to show (default all)")
    ap.add_argument("--config", default="scripts/run.toml")
    a = ap.parse_args()
    cfg = load_config(a.config)

    uri = tracking_uri()
    with store_setup(uri):
        client = MlflowClient(uri)
        exp = client.get_experiment_by_name(experiment_name(cfg))
    found = sorted(fetch(client, exp.experiment_id, a.issue) if exp else [], key=lambda r: r.info.start_time)
    # One dict per run: the rh.* params without the prefix, plus status, deletion and metrics.
    runs = [{k[3:]: v for k, v in r.data.params.items() if k.startswith("rh.")}
            | {"id": r.info.run_id, "status": r.info.status, "metrics": r.data.metrics,
               "deleted": r.info.lifecycle_stage == "deleted"} for r in found]
    groups = {}
    for r in runs:
        r["ok"] = r.get("exit_code") == "0"
        cmd = split_seed(shlex.split(r.get("command", "")), cfg["seed_key"])[1]
        groups.setdefault(shlex.join(cmd), []).append(r)
    metrics = a.metric or sorted({m for r in runs for m, v in r["metrics"].items() if num(v)})

    # The table is read by people, so its text is Chinese; metric names and hashes stay as they are.
    head = ["命令", "n", "失败数", *(f"{m} {s}" for m in metrics for s in ("均值", "标准差")),
            "commit", "环境锁", "数据"]
    out = [f"#{a.issue} 的结果：{len(runs)} 个 run，{len(groups)} 组，按去掉 seed 的命令分组。", "",
           "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for cmd, rs in groups.items():
        ok = [r for r in rs if r["ok"]]
        failed = [r for r in rs if not r["ok"] and r["status"] != "RUNNING"]
        row = ["`" + cmd.replace("|", "\\|") + "`", str(len(ok)), str(len(failed))]
        for m in metrics:
            v = [r["metrics"][m] for r in ok if num(r["metrics"].get(m))]
            row += [fmt(statistics.mean(v)) if v else "—", fmt(statistics.stdev(v)) if len(v) > 1 else "—"]
        row += [short((r.get("commit") for r in rs), 7), short((r.get("env_lock_sha") for r in rs), 8),
                short((r.get("data_manifest_sha") for r in rs), 8)]
        out.append("| " + " | ".join(row) + " |")

    flags = []
    commits = list(dict.fromkeys(r["commit"] for r in runs if r.get("commit")))  # by run start
    if len(commits) > 1:
        first, last = commits[0], commits[-1]
        p = subprocess.run(["git", "diff", "--stat", first, last], capture_output=True, text=True,
                           errors="replace")
        flags += [f"- commit 不同：{short(commits, 7)}；`git diff --stat {first[:7]} {last[:7]}`：",
                  "", "```", (p.stdout or p.stderr).rstrip(), "```"]
    for key, name in (("env_lock_sha", "环境"), ("data_manifest_sha", "数据")):
        if len({r[key] for r in runs if key in r}) > 1:  # runs killed before launch have none
            flags.append(f"- {name}不同：{short((r[key] for r in runs if key in r), 8)}")
    missing = [r for r in runs if r.get("env_lock_missing")]
    if missing:
        files = sorted({f for r in missing for f in r["env_lock_missing"].split(",")})
        flags.append(f"- {len(missing)} 个 run 缺环境锁文件：{', '.join(files)}")
    if dirty := [r for r in runs if r.get("dirty") == "true"]:
        flags.append(f"- {len(dirty)} 个 run 的工作区不干净（见产物 diff.patch 和 untracked.txt）：{ids(dirty)}")
    if nometrics := [r for r in runs if r["ok"] and not r["metrics"]]:
        flags.append(f"- {len(nometrics)} 个 run 成功退出但没有指标：{ids(nometrics)}")
    if incomplete := [r for r in runs if r["status"] == "RUNNING"]:
        flags.append(f"- {len(incomplete)} 个 run 未完成（还在跑或已被杀）：{ids(incomplete)}")
    if deleted := [r for r in runs if r["deleted"]]:
        flags.append(f"- {len(deleted)} 个 run 已在 MLflow 中删除，但仍计入上表：{ids(deleted)}")
    print("\n".join(out + ["", "标注：", *(flags or ["- 无"])]))


if __name__ == "__main__":
    main()
