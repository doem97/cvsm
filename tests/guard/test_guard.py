import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / ".github" / "scripts" / "guard.py"
_spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

GOOD_BODY = """Closes #12

## Changes
- Add the thing.

## Acceptance
- `python -m pytest -q`

## Out of scope
none
"""


def repo_cfg():
    return tomllib.loads((ROOT / ".github" / "guard.toml").read_text())


def cfg(**over):
    # The repo config plus a project-style source tree with a protected eval path.
    c = repo_cfg()
    c["layout"] = c["layout"] + ["src/**"]
    c["protected"] = c["protected"] + ["src/pkg/eval/**"]
    c.update(over)
    return c


def issue_body(scope_lines, nl="\n"):
    return nl.join([
        "### Goal", "", "Do it.", "",
        "### Scope", "", *scope_lines, "",
        "### Acceptance", "", "python -m pytest -q", "",
        "### Budget", "", "_No response_",
    ])


def mk_issue(scope=("src/**", "tests/**", "docs/**"), state="open", labels=("code",), number=12):
    return {"number": number, "state": state, "labels": list(labels), "body": issue_body(list(scope))}


def f(name, status="modified", prev=None, add=1, dele=0):
    d = {"filename": name, "status": status, "additions": add, "deletions": dele}
    if prev:
        d["previous_filename"] = prev
    return d


REPO = "doem97/research-harness"


def run(files=None, title="feat(#12): add the thing", body=GOOD_BODY, issue="default", c=None):
    pr = {"number": 7, "title": title, "body": body, "repo": REPO}
    if files is None:
        files = [f("src/pkg/methods/a.py"), f("tests/test_a.py")]
    return guard.check(pr, files, mk_issue() if issue == "default" else issue, c or cfg())


# --- glob_match / literal_prefix

@pytest.mark.parametrize("path,pattern,ok", [
    ("src/a/b.py", "src/**", True),
    ("srcx/a.py", "src/**", False),
    ("a.md", "*.md", True),
    ("d/a.md", "*.md", False),
    ("AGENTS.md", "AGENTS.md", True),
    ("AGENTS.mdx", "AGENTS.md", False),
    ("x/AGENTS.md", "AGENTS.md", False),
    ("a/b.py", "a/**/b.py", True),
    ("a/x/y/b.py", "a/**/b.py", True),
    ("a/b", "a?b", False),
    ("a.b", "a?b", True),
    ("src/[ab].py", "src/[ab].py", True),
    ("src/a.py", "src/[ab].py", False),
    ("a/[!x]/b", "a/[!x]/b", True),
    ("a/c/b", "a/[!x]/b", False),
    ("a/x/y", "a[!b]x/y", False),
    ("src/[x.py", "src/[*.py", True),
    ("src/]x.py", "src/]*", True),
    ("any/deep/path", "**", True),
])
def test_glob_match(path, pattern, ok):
    assert guard.glob_match(path, pattern) is ok


@pytest.mark.parametrize("pattern,prefix", [
    (".github/**", ".github/"), ("AGENTS.md", "AGENTS.md"), ("src/[ab]/x", "src/[ab]/x"), ("[a-z]**", "[a-z]"),
    ("src/pkg/eval/**", "src/pkg/eval/"), ("a?b", "a"), ("**", ""),
])
def test_literal_prefix(pattern, prefix):
    assert guard.literal_prefix(pattern) == prefix


# --- closing_refs

@pytest.mark.parametrize("body,refs", [
    ("Closes #12", [12]),
    ("fixes #3 and Resolves #4", [3, 4]),
    ("see #12", []),
    ("Closes owner/repo#12", []),
    ("CLOSES #7", [7]),
    ("closed #1\nfixed #2\nresolved #3\nfix #4\nresolve #5\nclose #6", [1, 2, 3, 4, 5, 6]),
    ("Closes: #9", [9]),
    ("Closes #", []),
    ("Closes #12\r\n", [12]),
    ("Closes #12 and closes #12", [12]),
    ("encloses #5", []),
])
def test_closing_refs(body, refs):
    assert guard.closing_refs(body) == refs


@pytest.mark.parametrize("body,refs", [
    ("Closes doem97/research-harness#5", [5]),
    ("Closes DOEM97/Research-Harness#5", [5]),
    ("Closes other/repo#5", []),
    ("Closes #2 and fixes doem97/research-harness#3", [2, 3]),
    ("Closes https://github.com/doem97/research-harness/issues/5", [5]),
    ("Closes https://github.com/other/repo/issues/5", []),
    ("Closes #5, closes doem97/research-harness#5", [5]),
])
def test_closing_refs_same_repo(body, refs):
    assert guard.closing_refs(body, REPO) == refs


def test_glob_brackets_never_raise():
    for pattern in ["[", "]", "a[", "[]", "[!", "a[b", "[a-", "x[^]y", "[\\]"]:
        assert guard.glob_match(pattern, pattern) is True
        assert guard.glob_match("a", pattern) is False


# --- parse_sections / parse_scope

def test_parse_sections():
    s = guard.parse_sections(issue_body(["src/**"]))
    assert list(s) == ["Goal", "Scope", "Acceptance", "Budget"]
    assert s["Goal"] == "Do it."


def test_parse_scope_normal():
    assert guard.parse_scope(issue_body(["src/**", "tests/**"])) == ["src/**", "tests/**"]


def test_parse_scope_no_response():
    assert guard.parse_scope(issue_body(["_No response_"])) == []


def test_parse_scope_missing_section():
    assert guard.parse_scope("### Goal\n\nx\n") == []
    assert guard.parse_scope(None) == []


def test_parse_scope_crlf():
    assert guard.parse_scope(issue_body(["src/**", "tests/**"], nl="\r\n")) == ["src/**", "tests/**"]


def test_parse_scope_bullets_backticks_blanks():
    lines = ["- tests/**", "`src/**`", "", "* `docs/**`", "  - `a.py`  ", "```", "b.py", "```"]
    assert guard.parse_scope(issue_body(lines)) == ["tests/**", "src/**", "docs/**", "a.py", "b.py"]


def test_parse_scope_keeps_leading_wildcard():
    assert guard.parse_scope(issue_body(["**", "*.py"])) == ["**", "*.py"]


# --- check: pass cases

def test_check_passes_well_formed():
    assert run() == []


def test_check_passes_github_scope():
    issue = mk_issue(scope=[".github/**"])
    assert run(files=[f(".github/x.yml")], issue=issue) == []


def test_check_passes_explicit_eval_scope():
    issue = mk_issue(scope=["src/pkg/eval/**"])
    assert run(files=[f("src/pkg/eval/m.py")], issue=issue) == []


def test_check_passes_rename_within_scope_and_removed_file():
    files = [f("src/b.py", "renamed", prev="src/a.py"), f("src/old.py", "removed")]
    assert run(files=files) == []


def test_check_passes_deleting_stray_files():
    # Removing a forbidden or misplaced file is the fix, not a violation.
    assert run(files=[f("docs/TODO.txt", "removed"), f("src/notes.md", "removed")]) == []


def test_check_passes_filled_pr_template():
    body = (ROOT / ".github" / "pull_request_template.md").read_text().replace("Closes #", "Closes #12", 1)
    assert run(body=body) == []


# --- check: one failure each

def one(msgs, *needles):
    assert len(msgs) == 1, msgs
    for n in needles:
        assert n in msgs[0], msgs
    return msgs[0]


def test_fail_no_ref():
    one(run(body=GOOD_BODY.replace("Closes #12", "Part of #12"), issue=None), "exactly one")


def test_fail_same_repo_second_ref():
    body = GOOD_BODY.replace("Closes #12", "Closes #12 and fixes doem97/research-harness#3")
    one(run(body=body), "exactly one", "found 2")


def test_pass_full_same_repo_ref():
    assert run(body=GOOD_BODY.replace("Closes #12", "Closes doem97/research-harness#12")) == []


def test_fail_two_refs():
    one(run(body=GOOD_BODY.replace("Closes #12", "Closes #12, fixes #13")), "exactly one")


def test_fail_issue_missing():
    one(run(issue=None), "#12", "not found")


def test_fail_closed_issue():
    one(run(issue=mk_issue(state="closed")), "#12", "open")


def test_fail_missing_code_label():
    one(run(issue=mk_issue(labels=["run"])), "code")


def test_fail_empty_scope():
    one(run(issue=mk_issue(scope=["_No response_"])), "Scope", "empty")


@pytest.mark.parametrize("entry", ["*", "*.py", "?**", "?", "[a-z]**"])
def test_fail_scope_without_literal_prefix(entry):
    msg = run(issue=mk_issue(scope=["src/**", "tests/**", entry]))
    if entry.startswith("["):  # `[` is literal now, so this entry is merely unused
        assert msg == []
    else:
        one(msg, entry, "wildcard")


def test_fail_wildcard_scope():
    one(run(issue=mk_issue(scope=["**"])), "**")


def test_fail_outside_layout():
    one(run(files=[f("random/x.py")], issue=mk_issue(scope=["random/**"])), "random/x.py", "layout")


def test_fail_markdown_location():
    one(run(files=[f("src/guide.md", "added")]), "src/guide.md", ".md")


def test_fail_notes_md_twice():
    # `notes` is the forbidden stem NOTES in any case, so this path breaks two rules.
    msgs = run(files=[f("src/notes.md", "added")])
    assert len(msgs) == 2 and any(".md" in m for m in msgs) and any("forbidden" in m for m in msgs)


def test_fail_forbidden_name():
    one(run(files=[f("docs/TODO.txt", "added")]), "docs/TODO.txt", "forbidden")


def test_fail_forbidden_name_any_case():
    one(run(files=[f("src/progress.py", "added")]), "src/progress.py", "forbidden")


def test_fail_rename_out_of_scope():
    files = [f("scripts/a.py", "renamed", prev="src/a.py")]
    one(run(files=files), "scripts/a.py", "Scope")


def test_fail_rename_from_out_of_scope():
    files = [f("src/a.py", "renamed", prev="scripts/a.py")]
    one(run(files=files), "scripts/a.py", "Scope")


def test_fail_delete_agents_md_out_of_scope():
    one(run(files=[f("AGENTS.md", "removed")]), "AGENTS.md", "Scope")


def test_fail_delete_agents_md_without_explicit_scope():
    issue = mk_issue(scope=["src/**", "AGENTS*"])
    one(run(files=[f("AGENTS.md", "removed")], issue=issue), "AGENTS.md", "protected")


def test_fail_protected_eval_with_broad_scope():
    one(run(files=[f("src/pkg/eval/m.py")]), "src/pkg/eval/m.py", "protected")


def test_fail_bad_title():
    one(run(title="Add the thing"), "title")


@pytest.mark.parametrize("title", [
    "feature(#12): add", "feat(#12):add", "feat(#12): ", "feat (#12): add", "feat(#12): " + "x" * 73,
])
def test_fail_bad_title_variants(title):
    one(run(title=title), "title")


def test_pass_title_max_length():
    assert run(title="feat(#12): " + "x" * 72) == []


def test_fail_title_names_other_issue():
    one(run(title="feat(#13): add the thing"), "title", "#12")


def test_fail_body_too_long():
    body = GOOD_BODY.replace("none\n", "none\n" + "x\n" * 40)
    one(run(body=body), "40")


def test_body_at_limit_passes():
    lines = GOOD_BODY.rstrip("\n").split("\n")
    body = "\n".join(lines + ["x"] * (40 - len(lines))) + "\n"
    assert run(body=body) == []


def test_fail_missing_section():
    one(run(body=GOOD_BODY.replace("## Out of scope\n", "")), "## Out of scope")


def test_fail_diff_over_limit_excluding_tests():
    files = [f("src/a.py", add=300, dele=50), f("tests/test_a.py", add=500)]
    assert run(files=files, c=cfg(max_diff_lines=400)) == []
    files.append(f("src/b.py", add=51))
    one(run(files=files, c=cfg(max_diff_lines=400)), "401", "400")


def test_failures_are_collected():
    msgs = run(files=[f("src/guide.md", "added"), f("scripts/x.py")], title="bad")
    assert len(msgs) == 3


# --- repo config, workflows, forms

def test_repo_guard_toml():
    c = repo_cfg()
    assert c["types"] == ["feat", "fix", "refactor", "test", "exp", "docs", "chore"]
    assert c["max_body_lines"] == 40
    assert c["forbidden_names"] == ["TODO", "NOTES", "PLAN", "PROGRESS"]
    assert {"AGENTS.md", ".agents/**", ".codex/**", ".claude/**", ".github/**"} <= set(c["protected"])
    assert "max_diff_lines" not in c


def load_yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text())


def triggers(wf):
    return wf.get("on", wf.get(True))  # PyYAML reads the bare key `on` as True


def test_guard_workflow():
    wf = load_yaml(".github/workflows/guard.yml")
    on = triggers(wf)
    assert list(on) == ["pull_request_target"]
    assert set(on["pull_request_target"]["types"]) == {"opened", "edited", "synchronize", "reopened", "ready_for_review"}
    assert set(wf["permissions"].values()) == {"read"}
    assert set(wf["permissions"]) == {"contents", "pull-requests", "issues"}
    job = wf["jobs"]["guard"]
    assert "permissions" not in job
    for step in job["steps"]:
        assert "ref" not in (step.get("with") or {})
        assert "github.event.pull_request.head" not in json.dumps(step)
    uses = [s.get("uses") for s in job["steps"]]
    assert "actions/checkout@v4" in uses and "actions/setup-python@v5" in uses
    run_step = [s for s in job["steps"] if "run" in s][-1]
    assert run_step["run"].strip() == "python .github/scripts/guard.py"
    assert {"GH_TOKEN", "PR_NUMBER", "REPO"} <= set(run_step["env"])


def test_test_workflow():
    wf = load_yaml(".github/workflows/test.yml")
    assert "pull_request" in triggers(wf)
    assert set(wf["permissions"].values()) == {"read"}
    runs = " ".join(s.get("run", "") for s in wf["jobs"]["test"]["steps"])
    assert "pytest==8.3.3" in runs and "pyyaml==6.0.2" in runs and "python -m pytest -q" in runs


def test_code_form():
    form = load_yaml(".github/ISSUE_TEMPLATE/code.yml")
    assert form["labels"] == ["code"]
    fields = {b["attributes"]["label"]: b for b in form["body"]}
    assert list(fields) == ["Goal", "Scope", "Acceptance", "Budget"]
    for name in ("Goal", "Scope", "Acceptance"):
        assert fields[name]["type"] == "textarea"
        assert fields[name]["validations"]["required"] is True
    assert fields["Budget"]["type"] == "input"


def test_pr_template():
    text = (ROOT / ".github" / "pull_request_template.md").read_text()
    lines = text.splitlines()
    assert lines[0] == "Closes #"
    for h in ("## Changes", "## Acceptance", "## Out of scope"):
        assert h in lines
    assert lines[lines.index("## Out of scope") + 1:].count("none") == 1


# --- main(): the I/O layer, against a fake `gh`

FAKE_GH = r"""#!/usr/bin/env python3
import json, os, sys
data = json.load(open(os.environ["FAKE_GH_DATA"]))
args = sys.argv[1:]
assert args[0] == "api", args
path = args[1]
if path.endswith("/files"):
    assert "--paginate" in args and "--slurp" in args, args
if path not in data:
    print(json.dumps({"message": "Not Found", "status": "404"}))
    sys.stderr.write("gh: Not Found (HTTP 404)\n")
    sys.exit(1)
print(json.dumps(data[path]))
"""


def run_main(tmp_path, responses):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    (tmp_path / "data.json").write_text(json.dumps(responses))
    summary = tmp_path / "summary.md"
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", PR_NUMBER="7",
               REPO="o/r", GH_TOKEN="x", FAKE_GH_DATA=str(tmp_path / "data.json"),
               GITHUB_STEP_SUMMARY=str(summary))
    p = subprocess.run([sys.executable, str(GUARD)], cwd=ROOT, env=env, capture_output=True, text=True)
    return p, summary.read_text() if summary.exists() else ""


def responses(issue=True):
    r = {
        "repos/o/r/pulls/7": {"number": 7, "title": "feat(#12): add the thing", "body": GOOD_BODY},
        # --paginate --slurp yields a list of pages
        "repos/o/r/pulls/7/files": [[f("docs/a.txt")], [f("tests/b.py", "renamed", prev="tests/a.py")]],
    }
    if issue:
        r["repos/o/r/issues/12"] = {"number": 12, "state": "open", "labels": [{"name": "code"}],
                                    "body": issue_body(["docs/**", "tests/**"])}
    return r


def test_main_pass(tmp_path):
    p, summary = run_main(tmp_path, responses())
    assert p.returncode == 0, p.stdout + p.stderr
    assert "guard:" not in p.stdout
    assert summary


def test_main_fail_and_summary(tmp_path):
    r = responses()
    r["repos/o/r/pulls/7/files"][0].append(f("src/x.py"))
    p, summary = run_main(tmp_path, r)
    assert p.returncode == 1
    assert "guard: " in p.stdout and "src/x.py" in p.stdout
    assert "src/x.py" in summary


def test_main_missing_issue(tmp_path):
    p, summary = run_main(tmp_path, responses(issue=False))
    assert p.returncode == 1
    assert "Traceback" not in p.stderr
    assert "guard: " in p.stdout and "#12" in p.stdout and "not found" in p.stdout
