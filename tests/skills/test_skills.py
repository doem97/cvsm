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
    assert len(skill_text(name).splitlines()) <= 120  # the spec says about 100


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


@pytest.mark.parametrize("name", NAMES)
def test_no_direct_merge(name):
    assert not re.search(r"(^|[`$(;&|]\s*)gh pr merge", skill_text(name), re.M)  # merge only via merge.py


def test_implement_merges_through_merge_py():
    text = skill_text("implement")
    assert "python .github/scripts/merge.py <PR>`" in text
    assert "python .github/scripts/merge.py <PR> --human" in text


def test_review_verdict_line():
    text = skill_text("review")
    assert "`Verdict: pass @ <full head SHA>`" in text
    assert "`Verdict: changes @ <full head SHA>`" in text
    assert "patch is correct" not in text  # Codex's built-in review maps by [P0]/[P1] findings
    # The Codex path binds the Verdict to the reviewed commit, and keeps the review in a file
    # because agent shells may not keep variables between calls.
    assert "sha=$(git rev-parse HEAD)" in text
    assert "printf 'Verdict: %s @ %s\\n\\n' \"<pass|changes>\" \"$sha\"" in text
    assert "$out" not in text
    # Posting the verdict and removing the review file run only when the PR head is $sha.
    m = re.search(r"^sha=\$\(git rev-parse HEAD\)\n(.*?)^```", text, re.M | re.S)
    assert m, "review skill lost the `sha=$(git rev-parse HEAD)` posting block"
    block = m.group(1)
    assert block.startswith(
        'test "$(gh pr view <PR> --json headRefOid -q .headRefOid)" = "$sha" &&'
    )
    assert re.search(r"\| *\n? *gh pr comment <PR> --body-file - && rm ../codex-review-<PR>\.md\n$",
                     block)


@pytest.mark.parametrize("name", ["implement", "review", "run"])
def test_issue_body_is_read(name):
    # Without a TTY, `gh issue view N --comments` prints only the comments, not the body.
    assert re.search(r"gh issue view N(?! --comments)\b", skill_text(name))


def cleanup_block(text):
    return re.search(r"^```\n(git worktree remove .*?)^```", text, re.M | re.S).group(1)


def test_run_cleans_up_like_implement():
    run = cleanup_block(skill_text("run"))
    assert "git branch -D t/N-<slug>" in run
    assert run == cleanup_block(skill_text("implement"))


def test_run_uses_project_commands():
    # Launch and results commands come from AGENTS.md's `Run` line; this repo's values are only
    # an example, so no command block may spell them out.
    text = skill_text("run")
    blocks = "".join(re.findall(r"^```[^\n]*\n(.*?)^```", text, re.M | re.S))
    assert "<run> --issue N -- <cmd>" in blocks
    assert "<run> --issue N --gpus 4 -- <cmd>" in blocks
    assert "<results> --issue N --metric <Report metrics>" in blocks
    assert "scripts/run.py" not in blocks and "scripts/results.py" not in blocks
    assert not re.search(r"python scripts/run\.py --issue", text)


def test_run_checks_runs_against_study_spec():
    # The study body is the spec; the check runs right after launch and in the results comment.
    blocks = "".join(re.findall(r"^```[^\n]*\n(.*?)^```", skill_text("run"), re.M | re.S))
    spec = "gh issue view P --json body -q .body | <results> --issue N"
    assert f"{spec} --spec -\n" in blocks
    assert f"{spec} --metric <Report metrics> --spec -)" in blocks


@pytest.mark.parametrize("name", ["implement", "review"])
def test_code_held_to_study_spec(name):
    text = skill_text(name)
    assert "`$RUN_DIR/config.json`" in text and "differ beyond Arms" in text


def test_review_gets_study_spec():
    text = skill_text("review")
    codex = re.search(r'^codex exec review "(.*?)" >', text, re.M | re.S).group(1)
    assert "Arms, Controlled" in codex
    assert "its spec (`gh issue view P`)" in text  # pre-PR review prompt


def test_review_worktree_at_head_sha():
    # FETCH_HEAD can be overwritten by a parallel review in the same clone.
    text = skill_text("review")
    assert "git worktree add --detach ../worktrees/review-<PR> <sha>" in text
    assert not re.search(r"git worktree add .*FETCH_HEAD", text)
