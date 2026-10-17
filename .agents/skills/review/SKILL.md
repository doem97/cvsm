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
gh issue view N             # N from `Closes #N`: Goal, Scope, Acceptance, Merge; parent P
gh issue view N --comments  # its Decisions
gh issue view P --comments  # the parent's Decision: comments
```

Read AGENTS.md, the spec (the design doc in `docs/`, if the project has one), and the code
around the diff. To run the Acceptance commands or probe behavior, check out the head in a
scratch worktree from the main clone:

```
git fetch origin pull/<PR>/head
git worktree add --detach ../worktrees/review-<PR> FETCH_HEAD
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
- Remove the scratch worktree, if you made one: `git worktree remove --force ../worktrees/review-<PR>`.

## 4. Starting a review (for the implementer)

A PR review gets only the PR number. `codex exec` is sandboxed without network by default and
`gh` needs it, hence `-s danger-full-access`.
- Claude Code: a fresh subagent with the prompt "Follow `.agents/skills/review/SKILL.md` for PR #<PR>."
- Codex: `codex exec -s danger-full-access "Follow .agents/skills/review/SKILL.md for PR #<PR>."`
- Codex built-in review, in a checkout of the PR head. In Codex 0.163 `--base` cannot be
  combined with instructions, so the instructions name the base. Pass the issue body, the
  issue's Decisions and its parent's `Decision:` comments, and the checklist above:

```
git fetch origin
out=$(codex exec review "Review the changes of this branch against origin/main \
(git diff origin/main...HEAD). Issue #N: <issue body>. Decisions on #N and its parent #P: \
<their Decision: comments>. Checklist: <section 2>.")
```

  Its stdout is the review: a summary and findings tagged `[P0]`–`[P3]`. Any `[P0]` or `[P1]`
  finding means `changes`, otherwise `pass`. In the checkout Codex reviewed, compare its SHA
  with the PR head; if they differ, review the current head instead. The session that ran it
  posts `$out` verbatim under the Verdict line, with the reviewed SHA:

```
sha=$(git rev-parse HEAD)
gh pr view <PR> --json headRefOid -q .headRefOid   # must equal $sha
gh pr comment <PR> --body "$(printf 'Verdict: %s @ %s\n\n%s\n' "<pass|changes>" "$sha" "$out")"
```

A pre-PR review in the implementer's inner loop gets only the issue number and the diff, uses
the checklist above and posts nothing. Give a fresh subagent, or
`codex exec -s danger-full-access "<prompt>"` in the worktree, this prompt:
"Review `git diff origin/main...HEAD` in <worktree> against issue #N (`gh issue view N`, then
`gh issue view N --comments`) and the Decisions on its parent P (`gh issue view P --comments`),
with the checklist in `.agents/skills/review/SKILL.md`. Report blocking and minor findings
here; post nothing to GitHub."

A reviewer reports the comment link and the verdict, in Chinese, to the session that asked.
