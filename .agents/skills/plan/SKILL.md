---
name: plan
description: Use when the human wants to discuss new work and turn it into a published study (research) or plan (development) parent issue with its code and run sub-issues.
---

# plan

Discuss the work with the human in the session, draft a parent issue and its sub-issues,
and publish them only on the human's explicit instruction (gate 1). Stop after publishing.
AGENTS.md rules apply throughout; this skill adds the procedure. Below, `<results>` is the
results command named on the `Run` line of AGENTS.md Project, the part before `--issue N`.

## 1. Read state and context

Read state as AGENTS.md State says, then what the plan builds on:

```
gh issue list --state open --label study
gh issue list --state open --label plan
gh issue list --state open --label needs-decision
gh pr list --state open
gh issue view <N>                 # an earlier study or task: body, parent, sub-issues
gh issue view <N> --comments      # its comments: results comments and Decisions
<results> --issue <N>             # run records of an earlier run issue
```

Read the code the work will touch, and the papers and records the human points to.
Write nothing to GitHub or to files while discussing.

## 2. Discuss

Talk with the human in Chinese until the draft below is complete: the question or goal, what
result answers it, the budget, and for a study its spec; raise every ambiguity that would change
a deliverable now. The human approves the spec but cannot check the work below it, so work out
with them the ideal fair comparison, complete and justified before publishing:
- Arms: the only settings in which the arms differ.
- Controlled: walk the usual confounders with the human and fix every one that applies:
  data and split; preprocessing and augmentation; model and init; optimizer and schedule;
  effective batch and training length; precision; tuning budget; evaluation protocol and
  checkpoint selection; seeds. Each gets a value and a reason: a paper, the human's records
  or an earlier result; ask the human for any you cannot source. Seeds and tuning grids are
  `in` lines, so every arm runs every value.
- Adaptable: engineering settings that may differ between runs, such as the per-device
  batch, each with the rule that keeps the comparison intact.
- Keys are the dotted keys of a run's resolved config (`config.json`). Name them from the
  code; a setting the code cannot yet take through config needs a code sub-issue.

## 3. Draft the issues

Parent issue, one of:
- `study`: the `### ` sections of `.github/ISSUE_TEMPLATE/study.yml`, in order: Question,
  Arms, Controlled, Adaptable, Criteria, Budget, Context; spec lines in its formats.
- `plan` (development work, no form): `### Goal` and `### Context`.

Sub-issues, with the exact `### ` sections of their forms:
- `code` (`.github/ISSUE_TEMPLATE/code.yml`):
  - `### Goal`: at most 3 sentences; the outcome, not the steps.
  - `### Scope`: path globs, one per line, none starting with a wildcard; the smallest set
    that covers the work. List a protected path (AGENTS.md Files) only when the task must change it.
  - `### Acceptance`: shell commands, one per line, run from the repo root; all exit 0 iff done.
  - `### Budget`: time, e.g. `2h`.
  - `### Merge`: `human` by default. `agent` only for a low-risk task whose Scope matches
    no path in `protected` of `.github/guard.toml`.
- `run` (`.github/ISSUE_TEMPLATE/run.yml`), blocked by the code issues it needs:
  - `### Runs`: one command per line with its config overrides and seed; each line is the
    `<cmd>` that the Run command in AGENTS.md Project wraps. A line may start with options of
    that command before `--`, e.g. `--gpus 4 -- python train.py seed=1`. Each line runs
    one arm, each arm an issue runs gets every `in` value; the study's run issues run every arm.
  - `### Budget`: GPU hours.
  - `### Report`: metric names, space-separated.

## 4. Order the sub-issues into waves

- Wave 1: issues with no blocker. Wave k: issues blocked only by issues in earlier waves.
- Issues in the same wave can be ready at the same time, so their Scopes must be disjoint:
  no path may match globs of two of them. If two Scopes overlap, chain them with
  blocked-by, which moves one to a later wave. Then parallel PRs never conflict.
- Show the human the whole draft in Chinese and revise until they approve: the parent, every
  sub-issue body, and the graph with placeholders, for example:

```
Wave 1: A code <title> (Scope: src/pkg/core/**)  |  B code <title> (Scope: src/pkg/methods/foo/**)
Wave 2: C run <title>  blocked by A, B
```

## 5. Publish (gate 1)

Publish only when the human explicitly says so. Create the parent first, then the sub-issues
wave by wave so every blocker already exists. Each `gh issue create` prints the issue URL.

```
url=$(gh issue create --label study --title "<title>" --body "$(cat <<'EOF'
### Question
...
EOF
)")
P=${url##*/}

url=$(gh issue create --label code --title "<title>" --parent "$P" --body "...")
A=${url##*/}

url=$(gh issue create --label run --title "<title>" --parent "$P" --blocked-by "$A,$B" --body "...")
```

- Use `--label plan` for a development parent; omit `--blocked-by` in wave 1. Pass every body
  through a quoted heredoc as in the first example: in double quotes, backticks run as commands.
- Check: `gh issue view "$P"` lists every sub-issue; `gh issue view <N>` shows each blocked-by.

## 6. Record and stop

```
gh issue comment "$P" --body "Decision: 发布 <研究或计划>及子 issue #A、#B、#C — <一行理由>"
```

Then report the three lines of AGENTS.md Report in Chinese, with links, and stop. Do not claim
or start any sub-issue unless the instruction names a target beyond publishing.

Changing a published task's Goal, Scope, Acceptance or Merge, or a study's Arms, Controlled or
Adaptable, is gate 1 as well: edit it (`gh issue edit <N>`, body as in section 5) only on the
human's explicit instruction, then record a Decision on that issue.
