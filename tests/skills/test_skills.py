import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
NAMES = ["plan", "implement", "review", "run"]
FILE_EXT = re.compile(r"\.(py|md|toml|yml|yaml|json|rules|txt|sh)$")


def skill_text(name):
    return (SKILLS / name / "SKILL.md").read_text()


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    return yaml.safe_load(m.group(1))


def test_skill_dirs():
    assert sorted(p.name for p in SKILLS.iterdir() if p.is_dir()) == sorted(NAMES)


@pytest.mark.parametrize("name", NAMES)
def test_skill_frontmatter(name):
    meta = frontmatter(skill_text(name))
    assert meta["name"] == name
    assert isinstance(meta["description"], str) and meta["description"].strip()
    assert "\n" not in meta["description"].strip()


@pytest.mark.parametrize("name", NAMES)
def test_skill_length(name):
    assert len(skill_text(name).splitlines()) <= 150


def test_claude_skills_symlink():
    link = ROOT / ".claude" / "skills"
    assert link.is_symlink()
    assert not Path(link.readlink()).is_absolute()  # relative, so it works in every clone
    assert link.resolve() == SKILLS.resolve()


def test_names_match_agents_md():
    agents = (ROOT / "AGENTS.md").read_text()
    section = re.search(r"^## Skills\n(.*?)(?=^## |\Z)", agents, re.M | re.S).group(1)
    assert re.findall(r"^- `([\w-]+)`:", section, re.M) == NAMES


def backtick_paths(text):
    """Repo paths in inline code and fenced blocks: tokens with a `/` that start with `.` or
    end in a file extension; placeholders, globs, variables and parent paths are skipped."""
    fenced = re.findall(r"^```[^\n]*\n(.*?)^```", text, re.M | re.S)
    inline = re.findall(r"`([^`\n]+)`", re.sub(r"^```.*?^```", "", text, flags=re.M | re.S))
    for span in fenced + inline:
        for token in span.split():
            token = token.strip("\"'(),;:")
            if "/" not in token or re.search(r"[<>$*{}]|\.\.|://", token) or token.startswith(("/", "~")):
                continue
            if token.startswith(".") or FILE_EXT.search(token):
                yield token


@pytest.mark.parametrize("name", NAMES)
def test_referenced_paths_exist(name):
    paths = list(backtick_paths(skill_text(name)))
    missing = [p for p in paths if not (ROOT / p).exists()]
    assert not missing, missing


def test_backtick_paths_detects_paths():
    text = "Run `python scripts/run.py --issue N -- <cmd>` then\n```\npython .github/scripts/merge.py <PR>\n```\n" \
           "`git diff origin/main...HEAD` `../worktrees/N-<slug>` `src/pkg/**`"
    assert list(backtick_paths(text)) == [".github/scripts/merge.py", "scripts/run.py"]
