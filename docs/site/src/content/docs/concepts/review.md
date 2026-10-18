---
title: Review
description: How every change gets a fresh-context review, and how the Verdict line gates merging.
sidebar:
  order: 3
---

Every PR is reviewed by a fresh session that starts from the PR number alone and never sees the implementer's session. Its one comment opens with a `Verdict:` line for a specific head SHA, which is what makes a PR merge-ready.

## Why a fresh context

An implementer's session is full of its own reasoning, and a reviewer that reads it inherits its blind spots. So the reviewer is a new session that reads the sources the implementer had to satisfy:

- the PR and its diff;
- the issue it closes (`Closes #N`), with its comments;
- the Decisions on that issue's parent;
- if the parent is a study, its spec: Arms, Controlled and Adaptable.

It also reads AGENTS.md, the project's design doc and the code around the diff. It is never given the implementer's summary or reasoning. It changes no code; its only write is one PR comment.

## Two loops

**Inner loop, before the PR.** The implementer runs every Acceptance command and the project's tests, then asks a fresh reviewer to check the diff against the issue. That review posts nothing to GitHub. The implementer fixes what is worth fixing and starts the next round with a new reviewer, until Acceptance passes and nothing blocking remains. Most quality comes from here.

**Outer loop, on the PR.** Once the PR is open, a fresh PR review is the final independent check. On `changes`, the implementer fixes the findings, reruns Acceptance and gets a fresh review of the new head. Three `changes` in a row is a blocker.

## The checklist

1. **Contract**: the diff meets the issue's Goal and Acceptance, stays inside its Scope, and follows the Decisions. Under a study, every key of the spec is set through config and written to `$RUN_DIR/config.json`, and no change alters a Controlled setting or makes the arms differ beyond Arms.
2. **Correctness** on realistic inputs and error paths.
3. **Consistency** with AGENTS.md, the design doc and the existing code.
4. **Tests** that pin the contract, so a regression would fail them.
5. **Simplicity**: nothing the contract does not need.

A finding is blocking when it breaks item 1, 2, 3 or 4; everything else is minor. The verdict is `changes` only if at least one finding is blocking. Reviewers assume capable, cooperative agents and do not ask for defenses against malformed input, forgery or outsiders unless the issue requires them.

## The Verdict comment

```text
Verdict: pass @ <full head SHA>

<findings in the review tool's own format and language>
```

- The first line is exactly `Verdict: pass @ <SHA>` or `Verdict: changes @ <SHA>`, for the full head SHA taken right before posting. If the head moved, the reviewer reviews the new head first.
- Below it, the review tool's findings stay unedited and untranslated, each pointing at a file and line. This is the one exception to a project's human-facing language.
- `merge.py` reads the newest comment whose first line starts with `Verdict:` and requires a pass whose SHA is a prefix, at least 7 characters, of the current head.

## Starting a review

- **Claude Code**: a fresh subagent with the prompt "Follow `.agents/skills/review/SKILL.md` for PR #13."
- **Codex**: `codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #13."` The flag is needed because `gh` needs the network.
- **Codex built-in review**: `codex exec review` in a checkout of the PR head, given the issue, its Decisions, the parent's spec and the checklist. Any `[P0]` or `[P1]` finding maps to `changes`, otherwise `pass`, and the session that ran it posts the output verbatim under the Verdict line.

## Minor findings after a pass

A pass ends the loop. The implementer fixes the minor findings inside Scope; if it pushed fixes, it gets one more fresh review. Then it posts one PR comment proposing, for each remaining minor, a new issue, an existing issue or no action, each with a one-line reason. Your merge instruction approves those proposals, and the agent that merges carries them out.

:::tip
The findings may be in English even when your project's human-facing text is Chinese. You don't need to read them on GitHub: the reviewer reports the verdict and the comment link to the session that asked, and that session explains them to you.
:::

## Related

- [Merging](/research-harness/concepts/merging/)
- [Gates and blockers](/research-harness/concepts/gates-and-blockers/)
- [Skills](/research-harness/reference/skills/)
- [Claude Code and Codex](/research-harness/guides/claude-code-and-codex/)
