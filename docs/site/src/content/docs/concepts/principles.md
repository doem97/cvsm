---
title: Principles
description: The design principles behind rh, and what each one rules in and out.
sidebar:
  order: 7
---

rh is small on purpose: a few rules, each answering one major way agent-driven research goes wrong. These principles explain why it looks the way it does, and what it deliberately leaves to you.

## GitHub-native, no service to install

Workflow state lives in issues, PRs, checks and branch protection, and run records live in MLflow. There is no rh server, database or CLI. You can see everything in GitHub's own UI, and adopting rh is copying files.

## State on GitHub, sessions keep nothing

The repo holds no state, plan or progress files, and a session is never the record. Every state change goes to GitHub or git as it happens, so a session can end at any moment without losing anything, and a fresh session reads where things stand. See [State](/research-harness/concepts/state/).

## Mechanism, not policy

rh records facts and shows differences. It does not choose seeds, design experiments, decide when to rerun, or judge whether runs are comparable; you set those in the [study spec](/research-harness/concepts/study-spec/) and your instructions. It also leaves analysis, visualization and how an agent works inside a task to you.

## Few, fixed gates

Agents keep going until they reach the target, one of [four gates](/research-harness/concepts/gates-and-blockers/), or a blocker. The gates are the same for every project, and they are the only planned stops. The human decides only in sessions; agents carry out and record every action on GitHub. See [Talk, don't click](/research-harness/start/talk-dont-click/).

## Checks are mechanical where they can be

Each rule sits where it can be enforced best. What a script can check, `guard` and `merge.py` check. What no script can check is one line in AGENTS.md, held by the fresh-context [review](/research-harness/concepts/review/). Changes that need a human merge get a second look when you merge them.

## Written for capable models

Rules are short and concrete: AGENTS.md is at most 80 lines and each skill at most 120. They assume an agent that follows clearly written rules. Scripts fix the process, but they don't defend against malformed input, forgery or outsiders, and reviewers don't ask for such defenses unless a task requires them.

## A template, not a framework

rh ships no adapters for clusters, schedulers, storage or tracking services. `run.py` and `results.py` are a single-machine reference. Each adopter fits its own cluster, scheduler (for example SLURM) and tracking backend through its own issues, and keeps the [interfaces that stay fixed](/research-harness/reference/interfaces/).

:::tip
Every rule in rh answers one major failure. The same test works for your own additions: before adding a line to AGENTS.md, name the failure it prevents.
:::

## Related

- [Overview](/research-harness/start/overview/)
- [Interfaces that stay fixed](/research-harness/reference/interfaces/)
- [Adapt to your environment](/research-harness/guides/adapt-your-environment/)
- [Design document (Chinese)](https://github.com/doem97/research-harness/blob/main/docs/design/2026-10-16-harness-v1.md)
