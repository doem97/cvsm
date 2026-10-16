"""PR guard: layout, scope, protected paths and PR format.

Runs from main under pull_request_target. It reads the PR through `gh api`
and never checks out or executes PR code. Rules live in .github/guard.toml.
"""
import json
import os
import re
import subprocess
import sys
import tomllib

SECTIONS = ("## Changes", "## Acceptance", "## Out of scope")
GLOB_TOKENS = re.compile(r"\*\*/|\*\*|\*|\?|.", re.S)
GLOB_REGEX = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}
REF_REPO = r"([\w.-]+/[\w.-]+)"
CLOSING = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+"
                     rf"(?:https://github\.com/{REF_REPO}/issues/|{REF_REPO}#|#)(\d+)\b", re.IGNORECASE)


def glob_match(path: str, pattern: str) -> bool:
    # Only `**`, `*` and `?` are wildcards; everything else, `[` included, is literal.
    regex = "".join(GLOB_REGEX.get(tok) or re.escape(tok) for tok in GLOB_TOKENS.findall(pattern))
    return re.fullmatch(regex, path) is not None


def literal_prefix(pattern: str) -> str:
    return re.split(r"[*?]", pattern, maxsplit=1)[0]


def closing_refs(body: str, repo: str | None = None) -> list[int]:
    # `owner/repo#N` and issue URLs count only when they name this repo; other repos are ignored.
    refs = [int(n) for url, short, n in CLOSING.findall(body or "")
            if not (url or short) or (url or short).lower() == (repo or "").lower()]
    return list(dict.fromkeys(refs))


def parse_sections(body: str) -> dict[str, str]:
    sections, name = {}, None
    for line in (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith("### "):
            name = line[4:].strip()
            sections[name] = []
        elif name is not None:
            sections[name].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_scope(issue_body: str) -> list[str]:
    scope = []
    for line in parse_sections(issue_body).get("Scope", "").split("\n"):
        line = line.strip()
        if line.startswith(("- ", "* ")):
            line = line[2:]
        line = line.replace("`", "").strip()
        if line and line != "_No response_":
            scope.append(line)
    return scope


def any_match(path: str, patterns: list[str]) -> bool:
    return any(glob_match(path, p) for p in patterns)


def check_file(f: dict, scope: list[str] | None, cfg: dict) -> list[str]:
    fails, new = [], f["filename"]
    if f["status"] != "removed":
        if not any_match(new, cfg["layout"]):
            fails.append(f"{new}: not in the layout allowlist")
        if new.endswith(".md") and not any_match(new, cfg["markdown"]):
            fails.append(f"{new}: .md files are not allowed here")
        if new.rsplit("/", 1)[-1].split(".")[0].upper() in cfg["forbidden_names"]:
            fails.append(f"{new}: forbidden file name")
    if scope is None:  # no usable issue Scope; that failure is already reported
        return fails
    paths = [new] + ([f["previous_filename"]] if f.get("previous_filename") else [])
    for p in paths:
        if not any_match(p, scope):
            fails.append(f"{p}: outside the issue Scope")
            continue
        for g in cfg["protected"]:
            if glob_match(p, g) and not any(
                    glob_match(p, s) and s.startswith(literal_prefix(g)) for s in scope):
                fails.append(f"{p}: protected by `{g}`; the Scope must name it explicitly")
                break
    return fails


def check(pr: dict, files: list[dict], issue: dict | None, cfg: dict) -> list[str]:
    fails, body = [], (pr.get("body") or "").replace("\r\n", "\n")
    refs = closing_refs(body, pr.get("repo"))
    n = refs[0] if len(refs) == 1 else None
    if n is None:
        fails.append(f"PR body must close exactly one issue with `Closes #N` (found {len(refs)})")

    scope = None
    if n is not None and issue is None:
        fails.append(f"issue #{n} not found or not readable")
    elif n is not None:
        if issue["state"].lower() != "open":
            fails.append(f"issue #{n} is not open")
        if "code" not in issue["labels"]:
            fails.append(f"issue #{n} does not have the `code` label")
        entries = parse_scope(issue["body"])
        wild = [s for s in entries if not literal_prefix(s)]
        if not entries:
            fails.append(f"issue #{n} has an empty Scope")
        elif wild:
            fails.append(f"issue #{n} Scope entries must start with a literal path, not a wildcard: {', '.join(wild)}")
        else:
            scope = entries

    for f in files:
        fails += check_file(f, scope, cfg)

    types = "|".join(map(re.escape, cfg["types"]))
    num = str(n) if n is not None else r"\d+"
    if not re.fullmatch(rf"({types})\(#{num}\): \S.{{0,71}}", pr.get("title") or ""):
        want = f"#{n}" if n is not None else "#N"
        fails.append(f"PR title must match `<type>({want}): <summary>` (summary at most 72 chars),"
                     f" type one of {', '.join(cfg['types'])}")

    lines = body.rstrip("\n").split("\n")
    missing = [h for h in SECTIONS if h not in (line.strip() for line in lines)]
    if missing:
        fails.append(f"PR body is missing section(s): {', '.join(missing)}")
    if len(lines) > cfg["max_body_lines"]:
        fails.append(f"PR body has {len(lines)} lines; the limit is {cfg['max_body_lines']}")

    limit = cfg.get("max_diff_lines")
    if limit is not None:
        size = sum(f["additions"] + f["deletions"] for f in files
                   if not any_match(f["filename"], cfg.get("test_paths", [])))
        if size > limit:
            fails.append(f"diff has {size} changed lines outside test paths; the limit is {limit}")
    return fails


def gh_api(path: str, *flags: str):
    p = subprocess.run(["gh", "api", path, *flags], capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 else None


def main() -> int:
    repo, number = os.environ["REPO"], os.environ["PR_NUMBER"]
    with open(".github/guard.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    pr = gh_api(f"repos/{repo}/pulls/{number}")
    pages = gh_api(f"repos/{repo}/pulls/{number}/files", "--paginate", "--slurp")
    if pr is None or pages is None:
        print(f"guard: cannot read PR #{number} through the API")
        return 1
    files = [f for page in pages for f in page]
    refs = closing_refs(pr.get("body") or "", repo)
    issue = None
    if len(refs) == 1:
        raw = gh_api(f"repos/{repo}/issues/{refs[0]}")
        if raw is not None:
            issue = {"number": raw["number"], "state": raw["state"], "body": raw.get("body") or "",
                     "labels": [label["name"] for label in raw.get("labels", [])]}
    fails = check({"number": pr["number"], "title": pr["title"], "body": pr.get("body") or "", "repo": repo},
                  files, issue, cfg)
    for msg in fails:
        print(f"guard: {msg}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write("## guard\n\n" + ("".join(f"- {m}\n" for m in fails) or "All checks passed.\n"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
