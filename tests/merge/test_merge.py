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
SCRIPTS = ROOT / ".github" / "scripts"
MERGE = SCRIPTS / "merge.py"
_spec = importlib.util.spec_from_file_location("merge", MERGE)
merge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge)

REPO = "o/r"
HEAD = "0123456789abcdef0123456789abcdef01234567"
OLD = "fedcba9876543210fedcba9876543210fedcba98"
TITLE = "feat(#12): add the thing"
BODY = "Closes #12\n\n## Changes\n- x\n\n## Acceptance\n- y\n\n## Out of scope\nnone\n"


def cfg():
    return tomllib.loads((ROOT / ".github" / "guard.toml").read_text())


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
    return f"Verdict: {word} @ {sha}\n\n审查通过。"


def as_comments(bodies):
    return [{"body": b, "html_url": f"https://github.com/o/r/pull/7#issuecomment-{i}"} for i, b in enumerate(bodies)]


def run(body=BODY, files=None, comments=None, issue="default"):
    pr = {"number": 7, "title": TITLE, "body": body, "head": HEAD, "repo": REPO}
    files = [f("src/a.py"), f("tests/test_a.py")] if files is None else files
    comments = [verdict()] if comments is None else comments
    issue = {"number": 12, "body": issue_body()} if issue == "default" else issue
    return merge.check(pr, files, as_comments(comments), issue, cfg())


# --- Merge field

@pytest.mark.parametrize("value,mode", [
    ("agent", "agent"), ("AGENT", "agent"), ("  Agent  ", "agent"), (None, "human"),
    ("_No response_", "human"), ("", "human"), ("human", "human"),
    ("agent\n\nbut ask me first", "human"), ("agent please", "human"),
])
def test_merge_mode(value, mode):
    assert merge.merge_mode(issue_body(value)) == mode


@pytest.mark.parametrize("extra", ["\n\n### Merge\n\nagent", "\n\n### Merge\n\nhuman", "\n\n### merge\n\nagent"])
def test_merge_mode_two_sections_is_human(extra):
    assert merge.merge_mode(issue_body("agent") + extra) == "human"


def test_merge_mode_empty_body_and_crlf():
    assert merge.merge_mode(None) == "human"
    assert merge.merge_mode(issue_body("agent").replace("\n", "\r\n")) == "agent"


# --- check

def test_allows_agent_task_with_fresh_pass():
    assert run() == []


def test_allows_full_sha_and_uppercase_hex():
    assert run(comments=[verdict(sha=HEAD.upper())]) == []


@pytest.mark.parametrize("value", [None, "_No response_", "human", "agent\nnot yet"])
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
    ([verdict(), "Verdict: maybe"], "Verdict: maybe"),
    # A later changes in any non-canonical shape still overrides the earlier pass.
    ([verdict(), "verdict: changes @ " + HEAD[:7]], "verdict: changes"),
    ([verdict(), "**Verdict: changes @ " + HEAD[:7] + "**"], "**Verdict: changes"),
    ([verdict(), "**Verdict**: changes"], "**Verdict**: changes"),
    ([verdict(), "Thanks.\nVerdict: changes @ " + HEAD[:7]], "Thanks."),
    ([verdict(), "Review done.\n\nOverall verdict : needs work"], "Review done."),
    # A pass that is not on the first line does not count.
    (["See below.\nVerdict: pass @ " + HEAD], "See below."),
    (["verdict: pass @ " + HEAD[:7]], "verdict: pass"),
    (["Verdict: pass @ " + HEAD[:7] + " (with nits)"], "with nits"),
])
def test_refuses_without_fresh_pass(comments, needle):
    reasons = run(comments=comments)
    assert len(reasons) == 1 and needle in reasons[0], reasons


def test_reason_names_the_deciding_comment():
    reasons = run(comments=[verdict(), "lgtm", verdict("changes"), "ok"])
    assert len(reasons) == 1 and "issuecomment-2" in reasons[0]


@pytest.mark.parametrize("comments", [
    [verdict("changes"), verdict()],
    [verdict(sha=OLD[:7]), verdict()],
    [verdict(), "thanks, merging soon"],
    [verdict("changes", sha=OLD[:7]), "  Verdict: pass @ " + HEAD[:10] + "  \r\nok"],
])
def test_latest_verdict_wins(comments):
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


def contents(data: bytes):
    # The contents API wraps base64 at 60 columns.
    b64 = base64.b64encode(data).decode()
    return {"encoding": "base64", "content": "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60)) + "\n"}


def source(rel, text=None):
    data = (ROOT / rel).read_bytes() if text is None else text.encode()
    return {f"repos/o/r/contents/{rel}?ref=main": contents(data)}


def responses(merge_value="agent", comments=None, files=None, body=BODY):
    return {
        "repos/{owner}/{repo}/pulls/7": {"number": 7, "title": TITLE, "body": body, "head": {"sha": HEAD},
                                         "base": {"ref": "main", "repo": {"full_name": REPO}}},
        "repos/o/r/pulls/7/files": [[f("src/a.py")], files or [f("tests/b.py", "renamed", prev="tests/a.py")]],
        "repos/o/r/issues/7/comments": [[{"body": "first", "html_url": "u0"}],
                                        [{"body": c, "html_url": "u1"} for c in (comments or [verdict()])]],
        "repos/o/r/issues/12": {"number": 12, "body": issue_body(merge_value)},
        **source(".github/guard.toml"), **source(".github/scripts/guard.py"), **source(".github/scripts/merge.py"),
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


def test_main_merges_when_allowed(tmp_path):
    p, calls = run_main(tmp_path, responses())
    assert p.returncode == 0, p.stdout + p.stderr
    assert merge_calls(calls) == [["pr", "merge", "7", "--squash", "--match-head-commit", HEAD,
                                   "--subject", f"{TITLE} (#7)", "--body", ""]]
    assert "已合并" in p.stdout


def test_main_refuses(tmp_path):
    p, calls = run_main(tmp_path, responses("human", comments=[verdict(sha=OLD[:7])], files=[f("AGENTS.md")]))
    assert p.returncode == 2, p.stdout + p.stderr
    assert merge_calls(calls) == []
    lines = p.stdout.strip().splitlines()
    assert lines[-1] == "等人合并"
    assert any("Merge" in line for line in lines)
    assert any("AGENTS.md" in line for line in lines)
    assert any(OLD[:7] in line and "u1" in line for line in lines)


def test_main_refuses_later_bold_changes(tmp_path):
    p, calls = run_main(tmp_path, responses(comments=[verdict(), "**Verdict: changes @ " + HEAD[:7] + "**"]))
    assert p.returncode == 2 and merge_calls(calls) == []


def test_main_merge_failure(tmp_path):
    data = responses()
    data["merge_fails"] = True
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 1
    assert len(merge_calls(calls)) == 1
    assert "Required status check" in p.stdout + p.stderr


def test_main_issue_read_fails(tmp_path):
    data = responses()
    del data["repos/o/r/issues/12"]
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 2 and merge_calls(calls) == []
    assert "#12" in p.stdout and "Traceback" not in p.stderr


def test_main_other_repo_ref(tmp_path):
    data = responses(body=BODY.replace("Closes #12", "Closes other/repo#12"))
    data["repos/other/repo/issues/12"] = data["repos/o/r/issues/12"]
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 2 and merge_calls(calls) == []
    assert "Closes #N" in p.stdout
    assert not any("issues/12" in c[1] for c in calls if c[0] == "api")


@pytest.mark.parametrize("rel", [".github/scripts/merge.py", ".github/scripts/guard.py"])
def test_main_refuses_local_script_differing_from_base(tmp_path, rel):
    data = responses()
    data.update(source(rel, (ROOT / rel).read_text() + "# changed on main\n"))
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 2, p.stdout + p.stderr
    assert merge_calls(calls) == []
    assert rel in p.stdout and p.stdout.strip().splitlines()[-1] == "等人合并"


def test_main_source_read_fails(tmp_path):
    data = responses()
    del data["repos/o/r/contents/.github/guard.toml?ref=main"]
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 1 and merge_calls(calls) == []


def test_main_uses_base_guard_toml(tmp_path):
    # main protects src/** although the local guard.toml does not, so src/a.py blocks the merge.
    toml = (ROOT / ".github" / "guard.toml").read_text().replace('protected = [', 'protected = ["src/**", ', 1)
    data = responses()
    data.update(source(".github/guard.toml", toml))
    p, calls = run_main(tmp_path, data)
    assert p.returncode == 2 and merge_calls(calls) == []
    assert "src/a.py" in p.stdout
    # and main no longer protects AGENTS.md although the local guard.toml does, so it merges.
    toml = (ROOT / ".github" / "guard.toml").read_text().replace('"AGENTS.md", ".agents', '".agents', 1)
    data = responses(files=[f("AGENTS.md")])
    data.update(source(".github/guard.toml", toml))
    (tmp_path / "again").mkdir()
    p, calls = run_main(tmp_path / "again", data)
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(merge_calls(calls)) == 1


def test_main_unreadable_pr(tmp_path):
    p, calls = run_main(tmp_path, {})
    assert p.returncode == 1
    assert merge_calls(calls) == [] and "Traceback" not in p.stderr


@pytest.mark.parametrize("args", [(), ("x",), ("7", "8")])
def test_main_usage(tmp_path, args):
    p, calls = run_main(tmp_path, responses(), args)
    assert p.returncode == 1 and calls == []
