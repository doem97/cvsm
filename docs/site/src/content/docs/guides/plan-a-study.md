---
title: Plan a study
description: Turn a research question into a published study issue with a complete spec and its code and run sub-issues.
sidebar:
  order: 2
---

You plan a study by talking it through with an agent that follows the `plan` skill. Nothing is created on GitHub until you say "publish", which is gate 01.

## 1. Start the discussion

Say what you want to study, for example "let's plan this study" or "I want to study X", and point the agent at the papers, records and earlier results it should build on.

The agent first reads state: open `study`, `plan` and `needs-decision` issues, open PRs, the earlier studies and tasks you mention, and their results comments and Decisions. It also reads the code the work will touch. While you discuss, it writes nothing to GitHub or to files.

## 2. Work out the fair comparison

The agent discusses with you until the draft is complete: the question, the result that answers it, the budget and, for a study, the spec. It raises every ambiguity that would change a deliverable now, not later.

The spec has three sections. Settle each one:

1. **Arms** (各组): the only settings in which the arms differ. One line per arm, `<arm>: <key>=<value> ...`.
2. **Controlled** (受控): walk the usual confounders and fix every one that applies:
   - data and split;
   - preprocessing and augmentation;
   - model and init;
   - optimizer and schedule;
   - effective batch and training length;
   - precision;
   - tuning budget;
   - evaluation protocol and checkpoint selection;
   - seeds.

   Each line gets a value and a reason: a paper, your records or an earlier result. The agent asks you for any reason it can't source. Seeds and tuning grids are `in` lines (`seed in 1,2,3  # ...`), so every arm runs every value.
3. **Adaptable** (可调整): engineering settings that may differ between runs, such as the per-device batch, each with the rule that keeps the comparison intact. This section may be empty.

Keys are the dotted keys of a run's resolved config (`config.json`). The agent names them from the code. A setting the code can't yet take through config needs a `code` sub-issue.

:::note
This spec is what every run is checked against, from the run's own record. See [Study spec](/cvsm/concepts/study-spec/) for why it is the layer you approve, and [Issue forms](/cvsm/reference/issue-forms/#study) for the exact line formats.
:::

An example spec:

```
### Arms
full: model.adapter=none
lora: model.adapter=lora model.lora.rank=8

### Controlled
data.split=val  # held-out split from data.sha256
model.backbone=vit_b16  # paper X, Table 2
optim.lr=3e-4  # paper X, Table 2
train.epochs=30  # paper X, Table 2
train.effective_batch=256  # paper X, Table 2
seed in 1,2,3  # three seeds, as in paper X

### Adaptable
train.per_device_batch  # fit to GPU memory; effective batch stays 256
train.accum  # follows per_device_batch
```

## 3. Review the draft issues

The agent drafts the parent and its sub-issues with the exact `### ` sections of the forms:

- The **study** parent: Question, Arms, Controlled, Adaptable, Criteria, Budget, Context, in that order. (Development work uses a `plan` parent with `### Goal` and `### Context`, and has no form.)
- **`code`** sub-issues: Goal (at most 3 sentences, the outcome, not the steps), Scope (path globs, none starting with a wildcard, the smallest set that covers the work), Acceptance (shell commands run from the repo root; all exit 0 if and only if the task is done), Budget (time, e.g. `2h`) and Merge (`human` by default; `agent` only for a low-risk task whose Scope matches no protected path).
- **`run`** sub-issues, blocked by the code issues they need: Runs (one command per line with its config overrides and seed; each line runs one arm; each arm an issue runs gets every `in` value; the study's run issues together run every arm), Budget (GPU hours) and Report (metric names, space-separated).

The agent orders the sub-issues into waves. Wave 1 has no blocker; wave k is blocked only by earlier waves. Issues in the same wave may be worked on in parallel, so their Scopes must be disjoint: when two overlap, one is chained behind the other with blocked-by. Parallel PRs then never conflict.

It shows you the whole draft in Chinese, with the graph:

```
Wave 1: A code <title> (Scope: src/pkg/core/**)  |  B code <title> (Scope: src/pkg/methods/foo/**)
Wave 2: C run <title>  blocked by A, B
```

Revise it until you approve.

## 4. Publish

:::caution[Gate 01: publish]
Say "publish" only when the spec and every sub-issue are what you want. Publishing is the approval that every later run is held to.
:::

On "publish", the agent creates the parent first, then the sub-issues wave by wave, so every blocker already exists. Parents and dependencies are set with `gh issue create --parent P --blocked-by M`, never written into the body. It checks that the parent lists every sub-issue and that each blocked-by is in place, records `Decision: 发布 ... — <reason>` on the parent, reports its three lines (`Done:`, `Waiting for you:`, `Next:`) and stops. It doesn't claim or start any sub-issue unless your instruction names a target beyond publishing.

## Change a published study

Changing a study's Arms, Controlled or Adaptable, or a task's Goal, Scope, Acceptance or Merge, is gate 01 too. Tell the agent the change explicitly; it edits the issue and records a Decision on it.

## Related

- [Study spec](/cvsm/concepts/study-spec/)
- [Gates and blockers](/cvsm/concepts/gates-and-blockers/)
- [Run experiments](/cvsm/guides/run-experiments/)
- [Issue forms](/cvsm/reference/issue-forms/)
- [Skills: plan](/cvsm/reference/skills/#plan)
