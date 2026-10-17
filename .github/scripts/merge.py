"""Tiered merge, the only way an agent merges: python .github/scripts/merge.py N

Merges PR N only if its issue says `Merge: agent`, no changed path is protected in
guard.toml and the newest verdict comment passes the current head. It fails closed:
any doubt refuses (exit 2) and the human merges. The rules come from the PR's base
branch; local copies of guard.py or merge.py that differ from it refuse to run.
"""
import base64
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard import any_match, closing_refs, parse_sections  # noqa: E402

PASS = re.compile(r"Verdict: pass @ ([0-9a-fA-F]{7,40})")
MENTION = re.compile(r"verdict[\s*_`]*:", re.IGNORECASE)  # `Verdict:`, `**Verdict**:`, `verdict :` ...
SOURCES = (".github/scripts/merge.py", ".github/scripts/guard.py")


def merge_mode(issue_body: str | None) -> str:
    lines = (issue_body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    heads = [line for line in lines if line.startswith("### ") and line[4:].strip().lower() == "merge"]
    value = parse_sections(issue_body).get("Merge", "").strip().lower()
    return "agent" if len(heads) == 1 and value == "agent" else "human"


def check_verdict(comments: list[dict], head: str) -> str | None:
    deciding = next((c for c in reversed(comments) if MENTION.search(c.get("body") or "")), None)
    if deciding is None:
        return "PR 上没有审查结论（第一行 `Verdict: pass @ <head SHA>` 的评论）"
    first = ((deciding.get("body") or "").strip().splitlines() or [""])[0].strip()
    m = PASS.fullmatch(first)
    if m is None or not head.lower().startswith(m.group(1).lower()):
        return (f"最新的审查评论 {deciding.get('html_url', '')} 第一行不是 "
                f"`Verdict: pass @ <当前 head {head[:7]}>`，而是：{first[:100]}")
    return None


def check(pr: dict, files: list[dict], comments: list[dict], issue: dict | None, cfg: dict) -> list[str]:
    reasons, refs = [], closing_refs(pr.get("body") or "", pr.get("repo"))
    if len(refs) != 1:
        reasons.append(f"PR 正文要恰好关闭一个 issue（`Closes #N`），现在是 {len(refs)} 个")
    elif issue is None:
        reasons.append(f"读不到 issue #{refs[0]}")
    elif (mode := merge_mode(issue.get("body"))) != "agent":
        reasons.append(f"issue #{refs[0]} 的 Merge 是 {mode}，不是 agent（要求恰好一个 `### Merge` 段，内容只有 agent）")

    for f in files:
        for p in [f["filename"]] + ([f["previous_filename"]] if f.get("previous_filename") else []):
            if any_match(p, cfg["protected"]):
                reasons.append(f"改了受保护路径 {p}")

    if (reason := check_verdict(comments, pr["head"])) is not None:
        reasons.append(reason)
    return reasons


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh_api(path: str, *flags: str):
    p = gh("api", path, *flags)
    return json.loads(p.stdout) if p.returncode == 0 else None


def base_file(repo: str, ref: str, rel: str) -> bytes | None:
    raw = gh_api(f"repos/{repo}/contents/{rel}?ref={quote(ref, safe='')}")
    return base64.b64decode(raw["content"]) if raw and raw.get("encoding") == "base64" else None


def refuse(number: str, reasons: list[str]) -> int:
    print(f"不合并 PR #{number}：")
    for r in reasons:
        print(f"- {r}")
    print("等人合并")
    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0].isdigit():
        print("用法：python .github/scripts/merge.py N（N 是 PR 编号）")
        return 1
    number = argv[0]
    pr = gh_api(f"repos/{{owner}}/{{repo}}/pulls/{number}")
    repo, ref = (pr["base"]["repo"]["full_name"], pr["base"]["ref"]) if pr else (None, None)
    pages = gh_api(f"repos/{repo}/pulls/{number}/files", "--paginate", "--slurp") if repo else None
    notes = gh_api(f"repos/{repo}/issues/{number}/comments", "--paginate", "--slurp") if repo else None
    base = {rel: base_file(repo, ref, rel) for rel in (".github/guard.toml", *SOURCES)} if repo else {}
    if pr is None or pages is None or notes is None or None in base.values():
        print(f"读不到 PR #{number}、它的文件、评论，或 {ref or '目标分支'} 上的规则文件，没有合并")
        return 1
    root = Path(__file__).resolve().parents[2]
    stale = [rel for rel in SOURCES if (root / rel).read_bytes() != base[rel]]
    if stale:
        return refuse(number, [f"本地的 {rel} 和 {ref} 上的不一致；先把主 clone 更新到最新的 {ref}，再从那里运行"
                               for rel in stale])
    refs = closing_refs(pr.get("body") or "", repo)
    issue = gh_api(f"repos/{repo}/issues/{refs[0]}") if len(refs) == 1 else None
    head = pr["head"]["sha"]
    reasons = check({"title": pr["title"], "body": pr.get("body") or "", "head": head, "repo": repo},
                    [f for page in pages for f in page], [c for page in notes for c in page],
                    issue, tomllib.loads(base[".github/guard.toml"].decode()))
    if reasons:
        return refuse(number, reasons)
    p = gh("pr", "merge", number, "--squash", "--match-head-commit", head,
           "--subject", f"{pr['title']} (#{number})", "--body", "")
    if p.returncode != 0:
        print(f"合并 PR #{number} 失败：{(p.stderr or p.stdout).strip()}")
        return 1
    print(f"已合并 PR #{number}（squash，head {head[:7]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
