"""Merge a PR the harness way: python .github/scripts/merge.py <PR> [--human]

Without --human (an agent merging a `Merge: agent` task) it merges only if the issue
the PR closes says `Merge: agent`, no changed path is protected in the base branch's
guard.toml, and the newest `Verdict:` comment passes the current head; otherwise it
refuses (exit 2). With --human the human decided, so it merges without these checks.
Either way it squash-merges the current head; branch protection still runs the checks.
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


def merge_mode(issue_body: str | None) -> str:
    return "agent" if parse_sections(issue_body).get("Merge", "").strip().lower() == "agent" else "human"


def check(pr: dict, files: list[dict], comments: list[str], issue: dict | None, cfg: dict) -> list[str]:
    reasons, refs = [], closing_refs(pr.get("body") or "", pr.get("repo"))
    if len(refs) != 1:
        reasons.append(f"PR 正文要恰好关闭一个 issue（`Closes #N`），现在是 {len(refs)} 个")
    elif issue is None:
        reasons.append(f"读不到 issue #{refs[0]}")
    elif merge_mode(issue.get("body")) != "agent":
        reasons.append(f"issue #{refs[0]} 的 Merge 不是 agent")

    for f in files:
        for p in [f["filename"]] + ([f["previous_filename"]] if f.get("previous_filename") else []):
            if any_match(p, cfg["protected"]):
                reasons.append(f"改了受保护路径 {p}")

    firsts = [(c or "").strip().split("\n")[0].strip() for c in comments]
    verdict = next((line for line in reversed(firsts) if line.startswith("Verdict:")), None)
    m = PASS.fullmatch(verdict or "")
    if verdict is None:
        reasons.append("PR 上没有审查结论（第一行 `Verdict: pass @ <head SHA>` 的评论）")
    elif m is None or not pr["head"].lower().startswith(m.group(1).lower()):
        reasons.append(f"最新的审查结论不是当前 head {pr['head'][:7]} 的 pass：{verdict}")
    return reasons


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def gh_api(path: str, *flags: str):
    p = gh("api", path, *flags)
    return json.loads(p.stdout) if p.returncode == 0 else None


def main(argv: list[str]) -> int:
    human, args = "--human" in argv, [a for a in argv if a != "--human"]
    if len(args) != 1 or not args[0].isdigit():
        print("用法：python .github/scripts/merge.py <PR> [--human]（PR 编号）")
        return 1
    number = args[0]
    pr = gh_api(f"repos/{{owner}}/{{repo}}/pulls/{number}")
    if pr is None:
        print(f"读不到 PR #{number}，没有合并")
        return 1
    head = pr["head"]["sha"]
    if not human:
        repo, ref = pr["base"]["repo"]["full_name"], pr["base"]["ref"]
        pages = gh_api(f"repos/{repo}/pulls/{number}/files", "--paginate", "--slurp")
        notes = gh_api(f"repos/{repo}/issues/{number}/comments", "--paginate", "--slurp")
        toml = gh_api(f"repos/{repo}/contents/.github/guard.toml?ref={quote(ref, safe='')}")
        if pages is None or notes is None or toml is None:
            print(f"读不到 PR #{number} 的文件、评论，或 {ref} 上的 guard.toml，没有合并")
            return 1
        refs = closing_refs(pr.get("body") or "", repo)
        issue = gh_api(f"repos/{repo}/issues/{refs[0]}") if len(refs) == 1 else None
        reasons = check({"body": pr.get("body") or "", "head": head, "repo": repo},
                        [f for page in pages for f in page], [c.get("body") or "" for page in notes for c in page],
                        issue, tomllib.loads(base64.b64decode(toml["content"]).decode()))
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
    print(f"已按人的指示合并 PR #{number}（squash，head {head[:7]}）" if human
          else f"已合并 PR #{number}（squash，head {head[:7]}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
