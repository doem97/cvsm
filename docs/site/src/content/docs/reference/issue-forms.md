---
title: Issue forms
description: The study, code and run issue forms, every `### ` section they produce, and which tool reads each one.
sidebar:
  order: 3
---

Three issue forms in `.github/ISSUE_TEMPLATE/` fix the sections of every task and study body. guard, `merge.py`, the results command and the skills read bodies by their `### ` headings, so the heading names can't change.

Sources: [`study.yml`](https://github.com/doem97/research-harness/blob/main/.github/ISSUE_TEMPLATE/study.yml), [`code.yml`](https://github.com/doem97/research-harness/blob/main/.github/ISSUE_TEMPLATE/code.yml), [`run.yml`](https://github.com/doem97/research-harness/blob/main/.github/ISSUE_TEMPLATE/run.yml).

## Overview

| Form | Form name | Label | Sections, in order |
|---|---|---|---|
| `study.yml` | 研究 | `study` | Question, Arms, Controlled, Adaptable, Criteria, Budget, Context |
| `code.yml` | 代码任务 | `code` | Goal, Scope, Acceptance, Budget, Merge |
| `run.yml` | 运行任务 | `run` | Runs, Budget, Report |

A development parent, labelled `plan`, has no form; its body has `### Goal` and `### Context`. Agents write bodies with these exact sections and set parents and dependencies with `gh issue create --parent P --blocked-by M`, never in the body. The forms' descriptions are in Chinese, the language of rh's own human-facing text.

## study

A research question, answered by `code` and `run` sub-issues. Arms, Controlled and Adaptable are the spec every run is checked against.

| Section | Field | Required | Format |
|---|---|---|---|
| `### Question` | textarea | yes | The question the study answers. |
| `### Arms` | textarea | yes | One arm per line: `<arm>: <key>=<value> [<key>=<value> ...]`. Only the settings in which the arms differ, e.g. `lora: model.adapter=lora model.lora.rank=8`. |
| `### Controlled` | textarea | yes | One setting per line, reason required: `<key>=<value>  # <reason>` (every run takes this value) or `<key> in <v1>,<v2>,...  # <reason>` (every arm runs every value, e.g. seeds and tuning grids). |
| `### Adaptable` | textarea | no | One per line: `<key>  # <rule>`. Engineering settings that may differ between runs and be changed within their rule, e.g. `train.per_device_batch`. May be empty. |
| `### Criteria` | textarea | yes | What result answers the question. |
| `### Budget` | input | no | GPU hours and time, e.g. 4 GPU hours, 1 day. |
| `### Context` | textarea | no | Links to related studies, results comments and papers. |

Spec line rules, as `results.py` reads them:

- One item per line; any line may end with `  # <comment>` (whitespace before `#`).
- Keys are the dotted keys of the run's `config.json`. A key appears in one section at most.
- Values that parse as JSON (numbers, `true`/`false`/`null`, lists) compare as JSON, so `1` and `1.0` are equal; others compare as strings.
- `in` values are split on commas outside brackets, so a value may be a JSON list.
- The Controlled description lists the usual confounders to cover: data and split, preprocessing and augmentation, model and init, optimizer and schedule, effective batch and training length, precision, tuning budget, evaluation protocol and checkpoint selection, seeds.

## code

One code or file change, limited to a fixed Scope.

| Section | Field | Required | Format | Read by |
|---|---|---|---|---|
| `### Goal` | textarea | yes | At most 3 sentences; the outcome, not the steps. | implement, review |
| `### Scope` | textarea | yes | Path globs, one per line, none starting with a wildcard. | guard |
| `### Acceptance` | textarea | yes | Commands, one per line, run from the repo root. | implement, review |
| `### Budget` | input | no | Time, e.g. `2h`. | implement |
| `### Merge` | dropdown | default `human` | `human`: the human merges. `agent`: the agent merges with `merge.py` after a passing review. A PR that touches a protected path is always merged by the human. | `merge.py` |

guard reads Scope lines with a leading `- ` or `* ` and backticks stripped, and ignores `_No response_`. Globs use `**` (crosses `/`), `*` and `?` (don't); every other character is literal.

## run

A set of experiment runs, whose results are posted as one comment.

| Section | Field | Required | Format |
|---|---|---|---|
| `### Runs` | textarea | yes | One command per line, with its config overrides and seed. With Run-command options, `<options> -- <cmd>`, e.g. `--gpus 4 -- python train.py seed=1`. |
| `### Budget` | input | no | GPU hours, e.g. 2. |
| `### Report` | input | no | Metric names, space-separated; passed to the results command as `--metric`. |

Each Runs line runs one arm. Each arm an issue runs gets every value of each Controlled `in` line, and the study's run issues together run every arm.

## Related

- [Study spec](/research-harness/concepts/study-spec/)
- [Plan a study](/research-harness/guides/plan-a-study/)
- [guard](/research-harness/reference/guard/)
- [results.py](/research-harness/reference/results-py/)
- [Interfaces that stay fixed](/research-harness/reference/interfaces/)
