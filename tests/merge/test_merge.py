import base64
import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MERGE = ROOT / ".github" / "scripts" / "merge.py"
_spec = importlib.util.spec_from_file_location("merge", MERGE)
merge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge)

REPO = "o/r"
HEAD = "0123456789abcdef0123456789abcdef01234567"
OLD = "fedcba9876543210fedcba9876543210fedcba98"
TITLE = "feat(#12): add the thing"
BODY = "Closes #12\n\n## Changes\n- x\n\n## Acceptance\n- y\n\n## Out of scope\nnone\n"
GUARD_TOML = (ROOT / ".github" / "guard.toml").read_text()


def issue_body(merge_value="agent"):
    lines = ["### Goal", "", "Do it.", "", "### Scope", "", "src/**", "", "### Acceptance", "", "pytest", "",
             "### Budget", "", "2h"]
    if merge_value is not None:
        lines += ["", "### Merge", "", merge_value]
    return "\n".join(lines)


def f(name, status="modified", prev=None):
    d = {"filename": name, "status": status}
    if prev:
        d["previous_filename"] = prev
    return d


def verdict(word="pass", sha=HEAD[:7]):
    return f"Verdict: {word} @ {sha}\n\n审查意见。"


def run(body=BODY, files=None, comments=None, issue="default"):
    pr = {"body": body, "head": HEAD, "repo": REPO}
    files = [f("src/a.py"), f("tests/test_a.py")] if files is None else files
    comments = [verdict()] if comments is None else comments
    issue = {"number": 12, "body": issue_body()} if issue == "default" else issue
    return merge.check(pr, files, comments, issue, tomllib.loads(GUARD_TOML))


# --- Merge field

@pytest.mark.parametrize("value,mode", [
    ("agent", "agent"), ("AGENT", "agent"), ("  Agent  ", "agent"),
    (None, "human"), ("_No response_", "human"), ("", "human"), ("human", "human"),
])
def test_merge_mode(value, mode):
    assert merge.merge_mode(issue_body(value)) == mode


def test_merge_mode_empty_body():
    assert merge.merge_mode(None) == "human"


# --- check

def test_allows_agent_task_with_fresh_pass():
    assert run() == []


@pytest.mark.parametrize("value", [None, "_No response_", "human"])
def test_refuses_human_task(value):
    reasons = run(issue={"number": 12, "body": issue_body(value)})
    assert len(reasons) == 1 and "Merge" in reasons[0] and "#12" in reasons[0]


def test_refuses_missing_issue():
    reasons = run(issue=None)
    assert len(reasons) == 1 and "#12" in reasons[0]


@pytest.mark.parametrize("body", ["Part of #12\n", "Closes #12, fixes #13\n"])
def test_refuses_zero_or_two_closing_refs(body):
    reasons = run(body=body, issue=None)
    assert len(reasons) == 1 and "Closes #N" in reasons[0]


@pytest.mark.parametrize("files,path", [
    ([f("AGENTS.md")], "AGENTS.md"),
    ([f(".github/scripts/guard.py", "removed")], ".github/scripts/guard.py"),
    ([f(".codex/rules/x.rules", "renamed", prev="src/x.rules")], ".codex/rules/x.rules"),
    ([f("src/x.rules", "renamed", prev=".codex/rules/x.rules")], ".codex/rules/x.rules"),
])
def test_refuses_protected_paths(files, path):
    reasons = run(files=files)
    assert len(reasons) == 1 and path in reasons[0]


@pytest.mark.parametrize("comments,needle", [
    ([], "Verdict: pass @"),
    (["LGTM"], "Verdict: pass @"),
    ([verdict("changes")], "changes"),
    ([verdict(sha=OLD[:7])], OLD[:7]),
    ([verdict(sha=HEAD[:6])], HEAD[:6]),
    ([verdict(), verdict("changes")], "changes"),
])
def test_refuses_without_fresh_pass(comments, needle):
    reasons = run(comments=comments)
    assert len(reasons) == 1 and needle in reasons[0], reasons


@pytest.mark.parametrize("comments", [
    [verdict("changes"), verdict()],
    [verdict(sha=OLD[:7]), verdict(sha=HEAD)],
    [verdict(), "thanks, merging soon"],
])
def test_newest_verdict_wins(comments):
    assert run(comments=comments) == []


def test_reasons_are_collected():
    reasons = run(files=[f("AGENTS.md"), f(".github/x.yml")], comments=[],
                  issue={"number": 12, "body": issue_body("human")})
    assert len(reasons) == 4


# --- main(): the I/O layer, against a fake `gh`

FAKE_GH = r"""#!/usr/bin/env python3
import json, os, sys
data = json.load(open(os.environ["FAKE_GH_DATA"]))
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\n")
if args[:2] == ["pr", "merge"]:
    if data.get("merge_fails"):
        sys.stderr.write("GraphQL: Required status check \"test\" is failing\n")
        sys.exit(1)
    sys.exit(0)
assert args[0] == "api", args
path = args[1]
if path.endswith(("/files", "/comments")):
    assert "--paginate" in args and "--slurp" in args, args
if path not in data:
    sys.stderr.write("gh: Not Found (HTTP 404)\n")
    sys.exit(1)
print(json.dumps(data[path]))
"""

TOML_PATH = "repos/o/r/contents/.github/guard.toml?ref=main"


def contents(text):
    return {"encoding": "base64", "content": base64.encodebytes(text.encode()).decode()}


def responses(merge_value="agent", comments=None, files=None):
    return {
        "repos/{owner}/{repo}/pulls/7": {"number": 7, "title": TITLE, "body": BODY, "head": {"sha": HEAD},
                                         "base": {"ref": "main", "repo": {"full_name": REPO}}},
        "repos/o/r/pulls/7/files": [[f("src/a.py")], files or [f("tests/b.py", "renamed", prev="tests/a.py")]],
        "repos/o/r/issues/7/comments": [[{"body": "first"}], [{"body": c} for c in (comments or [verdict()])]],
        "repos/o/r/issues/12": {"number": 12, "body": issue_body(merge_value)},
        TOML_PATH: contents(GUARD_TOML),
    }


def run_main(tmp_path, data, args=("7",)):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    (tmp_path / "data.json").write_text(json.dumps(data))
    log = tmp_path / "gh.log"
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               FAKE_GH_DATA=str(tmp_path / "data.json"), FAKE_GH_LOG=str(log))
    p = subprocess.run([sys.executable, str(MERGE), *args], cwd=tmp_path, env=env, capture_output=True, text=True)
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return p, calls


def merge_calls(calls):
    return [c for c in calls if c[:2] == ["pr", "merge"]]


MERGE_CMD = ["pr", "merge", "7", "--squash", "--match-head-commit", HEAD, "--subject", f"{TITLE} (#7)", "--body", ""]


def test_main_merges_when_allowed(tmp_path):
    p, calls = run_main(tmp_path, responses())
    assert p.returncode == 0, p.stdout + p.stderr
    assert merge_calls(calls) == [MERGE_CMD]
    assert "已合并" in p.stdout


def test_main_refuses(tmp_path):
    p, calls = run_main(tmp_path, responses("human", comments=[verdict(sha=OLD[:7])], files=[f("AGENTS.md")]))
    assert p.returncode == 2, p.stdout + p.stderr
    assert merge_calls(calls) == []
    lines = p.stdout.strip().splitlines()
    assert lines[-1] == "等人合并"
    assert any("Merge" in line for line in lines)
    assert any("AGENTS.md" in line for line in lines)
    assert any(OLD[:7] in line for line in lines)


def test_main_merge_failure(tmp_path):
    data = responses()
    data["merge_fails"] = True
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 1
    assert merge_calls(calls) == [MERGE_CMD]
    assert "Required status check" in p.stdout


def test_main_uses_base_guard_toml(tmp_path):
    # The base branch protects src/** although the local guard.toml does not.
    data = responses()
    data[TOML_PATH] = contents(GUARD_TOML.replace("protected = [", 'protected = ["src/**", ', 1))
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 2 and merge_calls(calls) == []
    assert "src/a.py" in p.stdout


def test_main_unreadable(tmp_path):
    data = responses()
    del data[TOML_PATH]
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 1 and merge_calls(calls) == []
    (tmp_path / "pr").mkdir()
    p, calls = run_main(tmp_path / "pr", {})
    assert p.returncode == 1 and merge_calls(calls) == [] and "Traceback" not in p.stderr


@pytest.mark.parametrize("args", [(), ("x",), ("7", "8"), ("--human",)])
def test_main_usage(tmp_path, args):
    p, calls = run_main(tmp_path, responses(), args)
    assert p.returncode == 1 and calls == []


# --- --human: the human decided, so no checks

def test_human_merges_despite_failing_checks(tmp_path):
    data = responses("human", comments=[verdict("changes")], files=[f("AGENTS.md")])
    for path in ("repos/o/r/pulls/7/files", "repos/o/r/issues/7/comments", "repos/o/r/issues/12", TOML_PATH):
        del data[path]  # --human must not need them
    p, calls = run_main(tmp_path, data, ("7", "--human"))
    assert p.returncode == 0, p.stdout + p.stderr
    assert merge_calls(calls) == [MERGE_CMD]
    assert "人的指示" in p.stdout


def test_human_flag_first(tmp_path):
    p, calls = run_main(tmp_path, responses("human"), ("--human", "7"))
    assert p.returncode == 0 and merge_calls(calls) == [MERGE_CMD]


def test_human_merge_failure(tmp_path):
    data = responses()
    data["merge_fails"] = True
    p, calls = run_main(tmp_path, data, ("7", "--human"))
    assert p.returncode == 1 and merge_calls(calls) == [MERGE_CMD]
    assert "Required status check" in p.stdout
