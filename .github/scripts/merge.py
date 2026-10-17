"""Tiered merge, the only way an agent merges: python .github/scripts/merge.py N

Merges PR N only if its issue says `Merge: agent`, no changed path is protected in
guard.toml and the latest `Verdict:` comment passes the current head; otherwise it
refuses (exit 2) and the human merges. Branch protection still enforces the checks.
"""
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import any_match, closing_refs, parse_sections  # noqa: E402

CONFIG = Path(__file__).resolve().parents[1] / "guard.toml"
VERDICT = re.compile(r"Verdict: (pass|changes) @ ([0-9a-f]{7,40})", re.IGNORECASE)


def merge_mode(issue_body: str | None) -> str:
    value = parse_sections(issue_body).get("Merge", "").strip().lower()
    return "agent" if value == "agent" else "human"


def latest_verdict(comments: list[str]) -> str | None:
    firsts = [(c or "").strip().splitlines()[0].strip() for c in comments if (c or "").strip()]
    return next((line for line in reversed(firsts) if line.startswith("Verdict:")), None)


def check(pr: dict, files: list[dict], comments: list[str], issue: dict | None, cfg: dict) -> list[str]:
    reasons, refs = [], closing_refs(pr.get("body") or "", pr.get("repo"))
    if len(refs) != 1:
        reasons.append(f"PR 正文要恰好关闭一个 issue（`Closes #N`），现在是 {len(refs)} 个")
    elif issue is None:
        reasons.append(f"读不到 issue #{refs[0]}")
    elif (mode := merge_mode(issue.get("body"))) != "agent":
        reasons.append(f"issue #{refs[0]} 的 Merge 是 {mode}，不是 agent")

    for f in files:
        for p in [f["filename"]] + ([f["previous_filename"]] if f.get("previous_filename") else []):
            if any_match(p, cfg["protected"]):
                reasons.append(f"改了受保护路径 {p}")

    head, line = pr["head"].lower(), latest_verdict(comments)
    m = VERDICT.fullmatch(line) if line else None
    if line is None:
        reasons.append("PR 上没有审查结论（第一行 `Verdict: pass @ <head SHA>` 的评论）")
    elif m is None:
        reasons.append(f"最新审查结论格式不对：{line}")
    elif m.group(1).lower() != "pass":
        reasons.append(f"最新审查结论是 changes：{line}")
    elif not head.startswith(m.group(2).lower()):
        reasons.append(f"最新的 pass 针对 {m.group(2)}，不是当前 head {head[:7]}")
    return reasons


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh_api(path: str, *flags: str):
    p = gh("api", path, *flags)
    return json.loads(p.stdout) if p.returncode == 0 else None


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0].isdigit():
        print("用法：python .github/scripts/merge.py N（N 是 PR 编号）")
        return 1
    number = argv[0]
    pr = gh_api(f"repos/{{owner}}/{{repo}}/pulls/{number}")
    repo = pr["base"]["repo"]["full_name"] if pr else None
    pages = gh_api(f"repos/{repo}/pulls/{number}/files", "--paginate", "--slurp") if repo else None
    notes = gh_api(f"repos/{repo}/issues/{number}/comments", "--paginate", "--slurp") if repo else None
    if pr is None or pages is None or notes is None:
        print(f"读不到 PR #{number} 或它的文件、评论，没有合并")
        return 1
    refs = closing_refs(pr.get("body") or "", repo)
    issue = gh_api(f"repos/{repo}/issues/{refs[0]}") if len(refs) == 1 else None
    with open(CONFIG, "rb") as fh:
        cfg = tomllib.load(fh)
    head = pr["head"]["sha"]
    reasons = check({"title": pr["title"], "body": pr.get("body") or "", "head": head, "repo": repo},
                    [f for page in pages for f in page], [c.get("body") or "" for page in notes for c in page],
                    issue, cfg)
    if reasons:
        print(f"不合并 PR #{number}：")
        for r in reasons:
            print(f"- {r}")
        print("等人合并")
        return 2
    p = gh("pr", "merge", number, "--squash", "--match-head-commit", head,
           "--subject", f"{pr['title']} (#{number})", "--body", "")
    if p.returncode != 0:
        print(f"合并 PR #{number} 失败：{(p.stderr or p.stdout).strip()}")
        return 1
    print(f"已合并 PR #{number}（squash，head {head[:7]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
