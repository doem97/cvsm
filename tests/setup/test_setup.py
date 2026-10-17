import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / "scripts" / "setup.sh"

# Records each call as {"args": argv, "stdin": text}; `gh repo view` answers o/default.
FAKE_GH = r"""#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
stdin = sys.stdin.read() if "--input" in args else ""
with open(os.environ["FAKE_GH_LOG"], "a") as fh:
    fh.write(json.dumps({"args": args, "stdin": stdin}) + "\n")
if args[:2] == ["repo", "view"]:
    print("o/default")
"""


def run_setup(tmp_path, *args):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "gh").write_text(FAKE_GH)
    (bindir / "gh").chmod(0o755)
    log = tmp_path / "gh.log"
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", FAKE_GH_LOG=str(log))
    p = subprocess.run(["bash", str(SETUP), *args], cwd=tmp_path, env=env, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL)
    assert p.returncode == 0, p.stdout + p.stderr
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_syntax():
    assert subprocess.run(["bash", "-n", str(SETUP)]).returncode == 0


def test_applies_labels_settings_and_protection(tmp_path):
    calls = run_setup(tmp_path, "owner/repo")
    labels = [c["args"] for c in calls if c["args"][:2] == ["label", "create"]]
    assert labels == [
        ["label", "create", name, "--repo", "owner/repo", "--color", color, "--description", desc, "--force"]
        for name, color, desc in [
            ("study", "1d76db", "Research study (parent issue)"),
            ("plan", "5319e7", "Development plan (parent issue)"),
            ("code", "0e8a16", "Code task: one issue, one branch, one PR"),
            ("run", "fbca04", "Run task: closes with a results comment"),
            ("needs-decision", "d93f0b", "Agent stopped; waiting for the human"),
        ]
    ]

    [patch] = [c["args"] for c in calls if "PATCH" in c["args"]]
    assert patch[:4] == ["api", "-X", "PATCH", "repos/owner/repo"]
    pairs = [(flag, *field.split("=", 1)) for flag, field in zip(patch, patch[1:]) if flag in ("-F", "-f")]
    assert {k: (flag, v) for flag, k, v in pairs} == {
        "allow_squash_merge": ("-F", "true"), "allow_merge_commit": ("-F", "false"),
        "allow_rebase_merge": ("-F", "false"), "delete_branch_on_merge": ("-F", "true"),
        "squash_merge_commit_title": ("-f", "PR_TITLE"), "squash_merge_commit_message": ("-f", "BLANK"),
    }

    [put] = [c for c in calls if "PUT" in c["args"]]
    assert put["args"][:4] == ["api", "-X", "PUT", "repos/owner/repo/branches/main/protection"]
    assert "--input" in put["args"] and put["args"][put["args"].index("--input") + 1] == "-"
    assert json.loads(put["stdin"]) == {
        "required_status_checks": {"strict": False, "contexts": ["guard", "test"]},
        "enforce_admins": True,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }
    assert not any(c["args"][:2] == ["repo", "view"] for c in calls)


def test_default_repo_from_gh(tmp_path):
    calls = run_setup(tmp_path)
    assert calls[0]["args"] == ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    assert all("o/default" in " ".join(c["args"]) for c in calls[1:])
