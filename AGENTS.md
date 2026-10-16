## State
- Start every instruction by reading state from GitHub, never from chat memory: open `study`/`plan` issues with their sub-issue summaries, open PRs with their checks, and issues labelled `needs-decision`.
- A parent issue (`study` for research, `plan` for development) has sub-issues labelled `code` or `run`; it awaits analysis once all of them are closed. Use no label other than these and `needs-decision`.
- Set parents and dependencies with `gh issue create --parent P --blocked-by M`; never write them into the body.
- Write issue bodies with the `### ` sections of the matching form in `.github/ISSUE_TEMPLATE/`.
- Waiting: blocked by an issue that is still open. Ready: open, not blocked, no linked branch.
- In progress: has a linked branch. Claim a ready issue with `gh issue develop`, then run `gh issue develop --list N`; if another branch is linked too, delete yours and pick other work.
- Continue an in-progress issue only if the instruction names it or this session claimed it.
- Needs decision: label `needs-decision` plus a blocker comment; remove the label once the human has answered.
- In review: PR open, checks or review not finished. Merge-ready: `guard` and `test` green, no blocking review finding.
- Done: a `code` issue closes when the human merges its PR (`Closes #N`); close a `run` issue yourself with its results comment.
- Only the human abandons a task (closes it as not planned) and closes a parent (as completed with the conclusion, or as not planned).
- Write every state change to GitHub or git as it happens; the session can end at any moment.

## Gates
- Each instruction names a target state: "do #12" means merge-ready, "take #10 to analysis" means all its sub-issues closed, "continue" means the next gate.
- Stop only at the target, at a gate, or at a blocker; otherwise keep going.
- Stop at these four gates even when everything works:
  1. New or changed approved work: publishing a plan; changing a task's Goal, Scope or Acceptance; changing a protected path.
  2. Merging. Only the human merges; the merge-ready PR is the request, so add no label or blocker comment.
  3. Exceeding a budget: tokens, time or GPU hours.
  4. Concluding and closing a study.
- An explicit instruction from the user approves what it names; do not ask again.
- Record each decision as an issue comment: `Decision: <choice> — <one-line reason>`.

## Blockers
- Stop and ask when a gate is reached, the same failure happens 3 times in a row, or an ambiguity would change the deliverable.
- Handle without asking: test or CI failures, review findings, merge conflicts, infra retries, bugs inside Scope.
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
- Never run `gh pr merge`, push to main, force-push, create tags, or touch another task's branch.

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
- Get each review from a fresh session (`codex exec review --base main` with the issue as its brief, or a fresh subagent), never from the implementer's session.

## Skills
- Skills live in `.agents/skills/<name>/SKILL.md`; follow the one for your role.
- `plan`: discussing work and publishing a study or plan with its sub-issues; stops at publishing.
- `implement`: a `code` issue, from claim to merge-ready.
- `review`: one PR, in a fresh session; ends with one review comment.
- `run`: a `run` issue, from its Runs to the results comment and closing.

## Project
<!-- Adopters replace this section with their own project's values. -->
- Layout: this repo is the template itself; there is no src/, and scripts/ holds the reference run and results scripts.
- Test: `python -m pytest -q`
- Language: write PR bodies, issue and PR comments, and reports in Chinese; keep PR titles, format keywords and repo files in English.
- Protected eval/data paths: none.
- Run: `python scripts/run.py --issue N -- <cmd>`; results comment: `python scripts/results.py --issue N`.
- Run records: MLflow runs in the backend that `MLFLOW_TRACKING_URI` names (MLflow's default if unset); the experiment is set in `scripts/run.toml`.
