---
name: review
description: Use in a fresh session whose only input is a PR number, to review that PR against its issue and post one comment whose first line is the Verdict.
---

# review

Review one PR in a fresh session. The only input is the PR number. Read the PR, its diff, the
issue it closes with its comments, and the Decisions on that issue's parent; never the
implementer's session or summaries. Change no code; the only write is one PR comment.

## 1. Read

```
gh pr view <PR> --json title,body,headRefOid,headRefName,files
gh pr diff <PR>
gh issue view N --comments                       # N from `Closes #N` in the PR body
gh issue view N --json parent -q .parent.number  # parent P
gh issue view P --comments                       # its Decision: comments
```

Read AGENTS.md, the spec (the design doc in `docs/`, if the project has one), and the code
around the diff. To run the
Acceptance commands or probe behavior, check out the head in a scratch worktree from the
main clone, and remove it afterwards:

```
git fetch origin pull/<PR>/head
git worktree add --detach ../worktrees/review-<PR> FETCH_HEAD
git worktree remove --force ../worktrees/review-<PR>
```

## 2. Checklist (high-intelligence mode)

1. Contract: the diff meets the issue's Goal and Acceptance, stays inside its Scope, and
   follows the Decisions on the issue and its parent.
2. Correctness on realistic inputs and error paths, assuming capable, cooperative agents and
   users.
3. Consistency with AGENTS.md, the spec and the existing code.
4. Tests that pin the contract, so a regression would fail them.
5. Simplicity: nothing the contract does not need; no avoidable new concept or layer.

Do not ask for defenses against malformed formats, forgery, outsiders or adversarial input
unless the issue requires them.

A finding is blocking when it breaks item 1, 2, 3 or 4. Everything else is minor.
The verdict is `changes` only if at least one finding is blocking; otherwise `pass`.

## 3. Post the comment

Take the full head SHA right before posting. If it differs from the SHA you reviewed,
review the new head first.

```
gh pr view <PR> --json headRefOid -q .headRefOid
gh pr comment <PR> --body "$(cat <<'EOF'
Verdict: pass @ <full head SHA>

<findings in your own format and language; mark each non-blocking one as minor>
EOF
)"
```

- The first line is exactly `Verdict: pass @ <full head SHA>` or
  `Verdict: changes @ <full head SHA>`.
- Below it, the findings in the reviewing tool's own format and language, unedited and
  untranslated. Point each at a file and line, with the reason and, when clear, the fix.
- Post one comment per review. Do not approve, label, push or edit anything.

## 4. Per tool

The implementer starts the review. A reviewing session posts its own comment; output of the
built-in Codex review is posted by the session that ran it.

- Claude Code: a fresh subagent gets the prompt
  "Follow `.agents/skills/review/SKILL.md` for PR #<PR>." and posts its own comment.
- Codex, own session: a fresh
  `codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #<PR>."`
  posts its own comment (`codex exec` is sandboxed without network by default; `gh` needs it).
- Codex, built-in review: run it in a checkout of the PR head (the implementer's worktree, or
  the scratch worktree above). `--base` cannot be combined with instructions, so the
  instructions name the base:

```
out=$(codex exec review "Review the changes of this branch against origin/main \
(git diff origin/main...HEAD). Issue #N: <issue body and its Decisions>. \
Checklist: <section 2 above>.")
```

  Its stdout is the review: a summary and `[P0]`–`[P3]` findings, ending with an overall
  correctness verdict when the tool prints one. Map `patch is correct` to `pass` and
  `patch is incorrect` to `changes`; with no such verdict in the output, any `[P0]` or `[P1]`
  finding means `changes`, otherwise `pass`. The session that ran it posts `$out` verbatim
  under the Verdict line:

```
gh pr comment <PR> --body "$(printf 'Verdict: %s @ %s\n\n%s\n' "<pass|changes>" "<full head SHA>" "$out")"
```

## 5. Finish

Report to the session that asked for the review: the comment link and the verdict, in Chinese.
