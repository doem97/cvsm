import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / ".codex" / "rules" / "harness.rules"
HEADINGS = ["State", "Gates", "Blockers", "Report", "Git", "Files", "Context", "Skills", "Project"]


def agents():
    return (ROOT / "AGENTS.md").read_text()


def section(name):
    m = re.search(rf"^## {name}\n(.*?)(?=^## |\Z)", agents(), re.M | re.S)
    assert m, name
    return m.group(1)


def test_agents_length():
    assert len(agents().splitlines()) <= 80


def test_agents_headings_in_order():
    assert re.findall(r"^## (.+)$", agents(), re.M) == HEADINGS


def test_agents_formats():
    lines = [l.strip().removeprefix("- ").strip("`") for l in agents().splitlines()]
    assert any("`Decision: <choice> — <one-line reason>`" in l for l in lines)
    for prefix in ("Blocked:", "Evidence:", "Options:", "Recommend:"):
        assert any(l.startswith(prefix) for l in lines), prefix
    for prefix in ("Done:", "Waiting for you:", "Next:"):
        assert any(l.startswith(prefix) for l in lines), prefix


def test_agents_state_starts_with_read_rule():
    first = next(l for l in section("State").splitlines() if l.strip())
    assert "GitHub" in first and "needs-decision" in first


def test_agents_agrees_with_guard_toml():
    cfg = tomllib.loads((ROOT / ".github" / "guard.toml").read_text())
    text = agents()  # adopters list their eval/data paths under Project
    for p in cfg["protected"] + cfg["markdown"]:
        assert p.removesuffix("**") in text, p
    for name in cfg["forbidden_names"]:
        assert name in text, name
    git = section("Git")
    assert all(t in git for t in cfg["types"])
    assert str(cfg["max_body_lines"]) in git


def test_agents_project_fields():
    text = section("Project")  # adopters replace the values, not the fields
    for field in ("Layout:", "Test:", "Language:", "Protected eval/data paths:", "Run:", "Storage:"):
        assert f"- {field}" in text, field


def test_claude_md_imports_agents():
    assert (ROOT / "CLAUDE.md").read_text() == "@AGENTS.md\n"


def test_claude_settings_deny_merge():
    s = json.loads((ROOT / ".claude" / "settings.json").read_text())
    assert "Bash(gh pr merge:*)" in s["permissions"]["deny"]


def load_form(name):
    form = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / name).read_text())
    assert form["name"] and form["description"]
    return form, {b["attributes"]["label"]: b for b in form["body"]}


def required(field):
    return (field.get("validations") or {}).get("required") is True


def test_study_form():
    form, fields = load_form("study.yml")
    assert form["labels"] == ["study"]
    assert list(fields) == ["Question", "Comparison", "Criteria", "Budget", "Context"]
    for name in ("Question", "Comparison", "Criteria"):
        assert fields[name]["type"] == "textarea" and required(fields[name])
    assert "config differences" in fields["Comparison"]["attributes"]["description"]


def test_run_form():
    form, fields = load_form("run.yml")
    assert form["labels"] == ["run"]
    assert list(fields) == ["Runs", "Budget", "Report"]
    assert fields["Runs"]["type"] == "textarea" and required(fields["Runs"])
    assert "seed" in fields["Runs"]["attributes"]["description"]
    assert "GPU hours" in fields["Budget"]["attributes"]["description"]
    assert "Metric names" in fields["Report"]["attributes"]["description"]


def test_codex_rules_static():
    text = RULES.read_text()
    assert '["gh", "pr", "merge"]' in text and 'decision = "forbidden"' in text
    assert '"prompt"' not in text  # under approval policy never, prompt becomes forbidden


def codex_check(*cmd):
    out = subprocess.run(
        ["codex", "execpolicy", "check", "--rules", str(RULES), *cmd],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out.strip().splitlines()[-1])


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex not on PATH")
def test_codex_forbids_merge():
    assert codex_check("gh", "pr", "merge", "12")["decision"] == "forbidden"
    assert codex_check("gh", "pr", "merge", "--squash", "3")["decision"] == "forbidden"
    assert codex_check("gh", "pr", "view", "12")["matchedRules"] == []
    assert codex_check("gh", "pr", "create")["matchedRules"] == []
