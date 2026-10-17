## State
- Start every instruction by reading state from GitHub, never from chat memory: open `study`/`plan` issues with their sub-issue summaries, open PRs with their checks, and issues labelled `needs-decision`.
- A parent issue (`study` for research, `plan` for development) has sub-issues labelled `code` or `run`; it awaits analysis once all of them are closed. Use no label other than these and `needs-decision`.
- Set parents and dependencies with `gh issue create --parent P --blocked-by M`; never write them into the body.
- Write issue bodies with the `### ` sections of the matching form in `.github/ISSUE_TEMPLATE/`.
- Waiting: blocked by an issue that is still open. Ready: open, not blocked, no linked branch.
- In progress: has a linked branch. Claim a ready issue with `gh issue develop`, then run `gh issue develop --list N`; if another branch is linked too, delete yours and pick other work.
- Continue an in-progress issue only if the instruction names it or this session claimed it.
- Needs decision: label `needs-decision` plus a blocker comment; remove the label once the human has answered.
- In review: PR open, checks or review not finished. Merge-ready: `guard` and `test` green, and the latest review is `Verdict: pass @ <head SHA>` for the current head.
- Done: a `code` issue closes when its PR merges (`Closes #N`); close a `run` issue yourself with its results comment.
- Abandon a task (close it as not planned) or close a parent (as completed with the conclusion, or as not planned) only on the human's explicit instruction.
- Write every state change to GitHub or git as it happens; the session can end at any moment.

## Gates
- Each instruction names a target state: "do #12" means merged if the task says `Merge: agent` and merge-ready otherwise, "take #10 to analysis" means all its sub-issues closed, "continue" means the next gate.
- Stop only at the target, at a gate, or at a blocker; otherwise keep going.
- Stop at these four gates even when everything works:
  1. New or changed approved work: publishing a plan; changing a task's Goal, Scope, Acceptance or Merge; changing a protected path.
  2. Merging, unless the task says `Merge: agent`. Then merge once merge-ready with `python .github/scripts/merge.py <PR>`, which refuses protected paths and unreviewed heads. Otherwise, or if it refuses, the merge-ready PR is the request: add no label or blocker comment. Merge it only when the human explicitly tells you to, with `python .github/scripts/merge.py <PR> --human`.
  3. Exceeding a budget: tokens, time or GPU hours.
  4. Concluding and closing a study.
- An explicit instruction from the user approves what it names; do not ask again.
- Record each decision as an issue comment: `Decision: <choice> — <one-line reason>`.

## Blockers
- Stop and ask when a gate is reached, the same failure happens 3 times in a row, three `changes` verdicts come in a row, or an ambiguity would change the deliverable.
- Handle without asking: test or CI failures, merge conflicts, infra retries, bugs inside Scope, and a `changes` verdict: fix its findings, then get a fresh review of the new head. A pass ends the loop; fix its minor findings inside Scope and get one more fresh review, then post one PR comment proposing for each remaining minor a new issue, an existing issue or no action. The human's merge instruction approves the proposals (under `Merge: agent`, the instruction naming the task does), and the agent that merges carries them out.
- For a bug outside Scope, open a new issue and keep working; keep the fix out of the current PR.
- Ask once per blocker, with evidence, at most 3 options and a recommendation.
- If the user is in the session, ask there. Otherwise add `needs-decision`, post the blocker comment, and move on to other ready work.
- Blocker comment, four lines:
  - `Blocked: <one line>`
  - `Evidence: <links>`
  - `Options: <at most 3>`
  - `Recommend: <option>`

## Report
- At every stop, report exactly three lines, with links:
  - `Done: <what was completed>`
  - `Waiting for you: <what the human must do, or nothing>`
  - `Next: <what comes next>`

## Git
- One task = one issue = one branch `t/<N>-<slug>` = one worktree `../worktrees/<N>-<slug>` (relative to the main clone) = one PR.
- PR title: `<type>(#N): <summary>`, type one of feat, fix, refactor, test, exp, docs, chore; N is the issue the PR closes.
- PR body: `.github/pull_request_template.md`; first line `Closes #N`, `## Changes` (at most 5 items), `## Acceptance` (commands and results), `## Out of scope` (new issues, or none); at most 40 lines.
- Never run `gh pr merge` directly; merge only through `.github/scripts/merge.py`. Never push to main, force-push, create tags, or touch another task's branch.

## Files
- Add files only where `layout` in `.github/guard.toml` allows.
- Put `.md` files only in README.md, AGENTS.md, docs/, .agents/skills/ and .github/; AGENTS.md is the only instruction file, so never add CLAUDE.md.
- Never create files named TODO, NOTES, PLAN or PROGRESS (any case, any extension).
- Change only paths that your issue's Scope matches.
- Protected: AGENTS.md, .agents/, .codex/, .claude/, .github/ and the eval/data paths in Project; change them only when a Scope entry names them explicitly.
- A method task changes only its own module, configs and tests; a shared-code change is a separate task.
- docs/ belongs to the human; edit it only when your Scope names it.
- Never edit or delete a run record (an MLflow run), and never run `mlflow gc`.

## Context
- Before acting, read your issue, the code in its Scope and the interfaces that code uses; your skill lists the rest.
- Write only to GitHub (issues, comments, PRs), to files in Scope and to run records; keep no memory, notes, docs or discussion.
- Record decisions and conclusions on GitHub.
- Get each review from a fresh session that follows the `review` skill: a pre-PR review gets only the issue and the diff, a PR review only the PR number; never pass it your summary or reasoning.

## Skills
- Skills live in `.agents/skills/<name>/SKILL.md`; follow the one for your role.
- `plan`: discussing work and publishing a study or plan with its sub-issues; stops at publishing.
- `implement`: a `code` issue, from claim to merge-ready, or to merged when the task says `Merge: agent`.
- `review`: one PR, in a fresh session; ends with one comment whose first line is `Verdict: pass @ <head SHA>` or `Verdict: changes @ <head SHA>`.
- `run`: a `run` issue, from its Runs to the results comment and closing.

## Project
<!-- Adopters replace this section with their own project's values. -->
- Layout: this repo is the template itself; there is no src/, and scripts/ holds the reference run and results scripts.
- Test: `python -m pytest -q`
- Language: human-facing text is Chinese (PR bodies, issue and PR comments, reports, issue-form descriptions, README, the results comment), except review comments, which keep the reviewing tool's own text below the Verdict line; agent instructions (AGENTS.md, skills), code, PR titles and format keywords stay English.
- Protected eval/data paths: none.
- Run: `python scripts/run.py --issue N -- <cmd>`; results comment: `python scripts/results.py --issue N`.
- Run records: MLflow runs in the backend that `MLFLOW_TRACKING_URI` names; if unset, `mlflow.db` at the main clone root. The experiment is set in `scripts/run.toml`.
