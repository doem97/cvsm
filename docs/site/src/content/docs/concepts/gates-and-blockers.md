---
title: Gates and blockers
description: The four planned stops where you decide, and the blockers that stop an agent unplanned.
sidebar:
  order: 2
---

An agent stops only at its target, at one of four gates, or at a blocker; otherwise it keeps going. Gates are planned stops that happen even when everything works, and blockers are problems the agent cannot resolve alone.

## The four gates

| Gate | When | What you say |
|---|---|---|
| **01 Publish** | New or changed approved work: publishing a plan; changing a task's Goal, Scope, Acceptance or Merge, or a study's Arms, Controlled or Adaptable; changing a protected path | "publish", or approve the change |
| **02 Merge** | A PR is merge-ready, unless its task says `Merge: agent` | "merge", or "merge #13" |
| **03 Budget** | The next step would exceed the budget in tokens, time or GPU hours | "continue", with a new budget if you like |
| **04 Conclude** | All of a study's sub-issues are closed and it awaits analysis | your conclusion, e.g. "conclude #10: …" |

:::caution[Gates are yours]
An explicit instruction approves what it names, and the agent records it as `Decision: <choice> — <one-line reason>` on the issue. Without one, the agent does not publish, change the spec, merge a task that needs you, go past a budget or close a study. Mechanically, the deny rules stop agents from running `gh pr merge` directly, and `merge.py` without `--human` refuses protected paths and heads without a passing review. Using `--human` only on your instruction rests on AGENTS.md, like every other gate.
:::

### Gate 02 in detail

Under `Merge: agent`, the agent merges a merge-ready PR itself with `python .github/scripts/merge.py <PR>`, which refuses protected paths and heads without a passing review. Otherwise, or if merge.py refuses, the merge-ready PR is the request: the agent adds no label and no blocker comment, and waits for "merge". See [Merging](/research-harness/concepts/merging/).

### Gate 03 in detail

For a run task, GPU hours used are the sum over the issue's runs, failed ones included, of wall time times the number of GPUs. Before launching a run that would take the total past Budget, the agent reports the hours used, the estimate for the rest and the runs not yet launched, and waits.

## Blockers

The agent also stops when:

- the same failure happens 3 times in a row;
- 3 `changes` verdicts come in a row;
- an ambiguity would change the deliverable;
- a study's Controlled setting cannot be met without changing the comparison.

The last one is reported as `Blocked: 这个对比按规格做不了，因为 <X>` ("this comparison can't be done to spec, because X"), with three options: change the implementation, relax the spec (which is gate 01), or drop the comparison.

## How the agent asks

It asks once per blocker, with evidence, at most 3 options and a recommendation.

- **You are in the session**: it asks there.
- **You are not**: it adds `needs-decision` to the issue, posts a four-line blocker comment, and moves on to other ready work. It removes the label once you have answered.

```text
Blocked: <one line>
Evidence: <links>
Options: <at most 3>
Recommend: <option>
```

## What the agent handles alone

These are not blockers, and the agent does not ask:

- test or CI failures, merge conflicts and infra retries;
- bugs inside the task's Scope;
- a `changes` verdict: it fixes the findings and gets a fresh review of the new head;
- changing an Adaptable setting within its rule, noted in the results comment.

A bug outside Scope becomes a new issue; the agent keeps working and keeps the fix out of the current PR.

:::tip
"What's waiting for me?" lists every `needs-decision` issue and every merge-ready PR in one answer, which is the quickest way to clear the queue after time away.
:::

## Related

- [Talk, don't click](/research-harness/start/talk-dont-click/)
- [Merging](/research-harness/concepts/merging/)
- [Review](/research-harness/concepts/review/)
- [The study spec](/research-harness/concepts/study-spec/)
