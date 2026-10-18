---
title: AGENTS.md
description: Every section of the rules file, what each rule means, and what tests hold it to.
sidebar:
  order: 1
---

`AGENTS.md` holds all of the agents' rules in at most 80 lines. Its first eight sections are the same in every project; the last one, Project, is where each adopter fills in its own values.

Source: [`AGENTS.md`](https://github.com/doem97/research-harness/blob/main/AGENTS.md).

## Shape

| Constraint | Checked by |
|---|---|
| At most 80 lines | `tests/rules/test_rules.py` |
| Sections, in this order: State, Gates, Blockers, Report, Git, Files, Context, Skills, Project | `tests/rules/test_rules.py` |
| The formats `Decision:`, `Blocked:`, `Evidence:`, `Options:`, `Recommend:`, `Done:`, `Waiting for you:`, `Next:` appear | `tests/rules/test_rules.py` |
| Every `protected`, `markdown` and `forbidden_names` entry of `guard.toml`, the PR title types and the body line limit appear | `tests/rules/test_rules.py` |
| The Project fields `Layout`, `Test`, `Language`, `Protected eval/data paths`, `Run`, `Run records` are present | `tests/rules/test_rules.py` |

Agent instructions are in English, because models follow English instructions more precisely. `AGENTS.md` is the only instruction file; there is no `CLAUDE.md`.

## State

How an agent knows where things stand. State is read from GitHub at the start of every instruction, never from chat memory.

| Rule | Meaning |
|---|---|
| Read state first | Open `study` and `plan` issues with their sub-issue summaries, open PRs with their checks, and `needs-decision` issues. |
| Parents and sub-issues | A `study` (research) or `plan` (development) parent has `code` or `run` sub-issues. It awaits analysis once all are closed. No labels beyond these five. |
| Links are native | Parents and dependencies are set with `gh issue create --parent P --blocked-by M`, never written in the body. |
| Bodies follow the forms | Issue bodies use the `### ` sections of the matching form in `.github/ISSUE_TEMPLATE/`. |
| Waiting | Blocked by an issue that is still open. |
| Ready | Open, not blocked, no linked branch. |
| In progress | Has a linked branch. Claim with `gh issue develop`, then check `gh issue develop --list N`; if another branch is linked too, delete yours and pick other work. |
| Who continues | An in-progress issue is continued only if the instruction names it or this session claimed it. This makes parallel sessions safe. |
| Needs decision | Label `needs-decision` plus a blocker comment; the label comes off once the human answers. |
| In review | PR open, checks or review not finished. |
| Merge-ready | `guard` and `test` green, and the latest review is `Verdict: pass @ <head SHA>` for the current head. |
| Done | A `code` issue closes when its PR merges (`Closes #N`); the agent closes a `run` issue itself with its results comment. |
| Abandon or close a parent | Only on the human's explicit instruction. |
| Write as you go | Every state change goes to GitHub or git when it happens; the session can end at any moment. |

## Gates

Each instruction names a target state, and the agent keeps going until the target, a gate or a blocker.

- "do `#12`" means merged if the task says `Merge: agent`, otherwise merge-ready. "take `#10` to analysis" means all its sub-issues closed. "continue" means the next gate.
- The four gates, where the agent stops even when everything works:
  1. **New or changed approved work:** publishing a plan; changing a task's Goal, Scope, Acceptance or Merge, or a study's Arms, Controlled or Adaptable; changing a protected path.
  2. **Merging,** unless the task says `Merge: agent`. Then the agent merges once merge-ready with `python .github/scripts/merge.py <PR>`, which refuses protected paths and unreviewed heads. Otherwise, or if it refuses, the merge-ready PR is itself the request: no label or blocker comment. The agent merges only on the human's explicit instruction, with `python .github/scripts/merge.py <PR> --human`.
  3. **Exceeding a budget:** tokens, time or GPU hours.
  4. **Concluding and closing a study.**
- An explicit instruction approves what it names; the agent doesn't ask again.
- Each decision is recorded as an issue comment: `Decision: <choice> — <one-line reason>`.

## Blockers

When to stop and ask, and what to handle alone.

- **Stop and ask:** a gate is reached; the same failure 3 times in a row; three `changes` verdicts in a row; an ambiguity that would change the deliverable; a study's Controlled line that can't be met without changing the comparison. The last one is phrased `Blocked: 这个对比按规格做不了，因为 <X>`, with the options: change the implementation, relax the spec (gate 1), or drop the comparison.
- **Handle without asking:** test or CI failures, merge conflicts, infra retries, bugs inside Scope, changing an Adaptable setting within its rule (stated in the results comment), and a `changes` verdict (fix its findings, then get a fresh review of the new head).
- **After a pass:** fix its minor findings inside Scope; if fixes were pushed, get one more fresh review. Then post one PR comment proposing, for each remaining minor, a new issue, an existing issue or no action. The human's merge instruction approves the proposals (under `Merge: agent`, the instruction naming the task does), and the agent that merges carries them out.
- **Bug outside Scope:** open a new issue and keep working; keep the fix out of the current PR.
- **How to ask:** once per blocker, with evidence, at most 3 options and a recommendation. In the session if the user is there; otherwise add `needs-decision`, post the blocker comment, and move on to other ready work.
- **Blocker comment,** four lines: `Blocked: <one line>`, `Evidence: <links>`, `Options: <at most 3>`, `Recommend: <option>`.

## Report

At every stop the agent reports exactly three lines, with links: `Done: <what was completed>`, `Waiting for you: <what the human must do, or nothing>`, `Next: <what comes next>`.

## Git

- One task = one issue = one branch `t/<N>-<slug>` = one worktree `../worktrees/<N>-<slug>` (relative to the main clone) = one PR.
- PR title `<type>(#N): <summary>`, with type one of `feat`, `fix`, `refactor`, `test`, `exp`, `docs`, `chore`; N is the issue the PR closes.
- PR body from `.github/pull_request_template.md`: first line `Closes #N`, then `## Changes` (at most 5 items), `## Acceptance` (commands and results), `## Out of scope` (new issues, or none); at most 40 lines.
- Never run `gh pr merge` directly; merge only through `.github/scripts/merge.py`. Never push to main, force-push, create tags, or touch another task's branch.

## Files

- Add files only where `layout` in `.github/guard.toml` allows.
- `.md` files only in `README.md`, `AGENTS.md`, `docs/`, `.agents/skills/` and `.github/`. Never add `CLAUDE.md`.
- No files named `TODO`, `NOTES`, `PLAN` or `PROGRESS`, in any case, with any extension.
- Change only paths the issue's Scope matches.
- Protected: `AGENTS.md`, `.agents/`, `.codex/`, `.claude/`, `.github/` and the eval/data paths in Project. Change them only when a Scope entry names them explicitly.
- A method task changes only its own module, configs and tests; a shared-code change is a separate task.
- `docs/` belongs to the human; edit it only when Scope names it.
- Never edit or delete a run record (an MLflow run), and never run `mlflow gc`.

## Context

- Before acting, read the issue, the code in its Scope and the interfaces that code uses; the skill lists the rest.
- Write only to GitHub (issues, comments, PRs), to files in Scope and to run records. Keep no memory, notes, docs or discussion.
- Record decisions and conclusions on GitHub.
- Get each review from a fresh session that follows the `review` skill. A pre-PR review gets only the issue and the diff; a PR review only the PR number (the built-in Codex review also gets the issue, its Decisions and, under a study, the spec). Never pass it your summary or reasoning.

## Skills

Skills live in `.agents/skills/<name>/SKILL.md`, one per role: `plan`, `implement`, `review`, `run`. See [Skills](/research-harness/reference/skills/).

## Project

The only section an adopter edits, one line per field. rh's own values are shown for reference.

| Field | Meaning | rh's own value |
|---|---|---|
| `Layout` | How code directories divide; where shared code and method modules live | the template itself; no `src/`; `scripts/` holds the reference run and results scripts |
| `Test` | The test command, the same one CI runs | `python -m pytest -q` |
| `Language` | The language of human-facing text | see below |
| `Protected eval/data paths` | Eval and data paths agents may not change at will; match `protected` in `guard.toml` | none |
| `Run` | The Run command and the results-comment command | `python scripts/run.py --issue N -- <cmd>`; `python scripts/results.py --issue N` |
| `Run records` | The MLflow backend run records go to | the backend `MLFLOW_TRACKING_URI` names; if unset, `mlflow.db` at the main clone root; experiment set in `scripts/run.toml` |

rh's `Language` line: `README.md` is English, with a Chinese version at `docs/README.zh-CN.md`, kept in sync. Other human-facing text is Chinese: PR bodies, issue and PR comments, reports, issue-form descriptions and the results comment. Review comments keep the reviewing tool's own text below the Verdict line. Agent instructions (`AGENTS.md`, skills), code, PR titles and format keywords (`Closes`, `Decision:`, `Blocked:`, `Verdict:` and so on) stay English. An adopter sets its own language on this line.

## Related

- [Gates and blockers](/research-harness/concepts/gates-and-blockers/)
- [State](/research-harness/concepts/state/)
- [Skills](/research-harness/reference/skills/)
- [guard](/research-harness/reference/guard/)
- [Adopt rh](/research-harness/guides/adopt/)
