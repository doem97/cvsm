---
title: guard
description: The PR check that enforces format, file locations, Scope and protected paths, with every key of guard.toml and every check of guard.py.
sidebar:
  order: 4
---

guard is a required check on every PR. It reads the PR through the GitHub API, checks it against `.github/guard.toml` and the issue the PR closes, and never checks out or runs code from the PR.

Sources: [`.github/guard.toml`](https://github.com/doem97/research-harness/blob/main/.github/guard.toml), [`.github/scripts/guard.py`](https://github.com/doem97/research-harness/blob/main/.github/scripts/guard.py), [`.github/workflows/guard.yml`](https://github.com/doem97/research-harness/blob/main/.github/workflows/guard.yml).

## Workflow

| Item | Value |
|---|---|
| Trigger | `pull_request_target`, types `opened`, `edited`, `synchronize`, `reopened`, `ready_for_review` |
| Code that runs | the workflow and `guard.py` as they are on the base branch, with `guard.toml` from there; PR code is never checked out |
| Permissions | `contents: read`, `pull-requests: read`, `issues: read` |
| Job name | `guard`; branch protection requires a check of this name |
| Python | 3.12 on `ubuntu-latest`; standard library only |
| Environment | `GH_TOKEN`, `PR_NUMBER`, `REPO` |
| Exit | 0 when every check passes; 1 on any failure, or when the PR can't be read through the API |
| Output | one `guard: <message>` line per failure, and a `## guard` section in the job summary |

:::tip
Because guard runs from main, a change to `guard.toml` takes effect only after it merges. When a task needs a path that `layout` doesn't allow yet, land the layout entry first, in its own task.
:::

## guard.toml

| Key | Type | rh's value | Meaning |
|---|---|---|---|
| `layout` | globs | `README.md`, `AGENTS.md`, `.gitignore`, `.agents/**`, `.claude/**`, `.codex/**`, `.github/**`, `docs/**`, `scripts/**`, `tests/**` | Where files may exist. Adopters add their own directories and root files (`src/**`, `configs/**`, `pyproject.toml`, lock files, the data manifest). |
| `markdown` | globs | `README.md`, `AGENTS.md`, `docs/**`, `.agents/skills/**`, `.github/**` | Where `.md` files may exist. |
| `forbidden_names` | names | `TODO`, `NOTES`, `PLAN`, `PROGRESS` | File names refused anywhere, in any case and with any extension. |
| `protected` | globs | `AGENTS.md`, `.agents/**`, `.codex/**`, `.claude/**`, `.github/**` | Paths a PR may change only when its issue's Scope names them explicitly. Adopters add eval and data paths. `merge.py` reads this list too. |
| `types` | names | `feat`, `fix`, `refactor`, `test`, `exp`, `docs`, `chore` | Allowed PR title types. |
| `max_body_lines` | integer | `40` | Longest allowed PR body. |
| `test_paths` | globs | `tests/**` | Paths left out of `max_diff_lines`. |
| `max_diff_lines` | integer | unset (commented out, example `400`) | Optional. Most changed lines (additions plus deletions) outside `test_paths`. |

Task #39 adds `LICENSE`, the Apache-2.0 licence at the repo root, to rh's own `layout`.

### Glob syntax

| Token | Matches |
|---|---|
| `**/` | zero or more whole directories |
| `**` | anything, `/` included |
| `*` | anything except `/` |
| `?` | one character except `/` |
| anything else | itself, literally (`[` included) |

A glob must match the whole path.

## Checks

guard runs every check and reports every failure, in this order.

### 1. Closing reference

- The PR body closes exactly one issue. Closing keywords are `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`, any case, with an optional colon, followed by `#N`, `owner/repo#N` or an issue URL.
- References to other repos are ignored, and a repeated reference counts once.

### 2. The issue

- It exists and can be read.
- It is open.
- It has the `code` label.
- Its `### Scope` section is not empty.
- No Scope entry starts with a wildcard (`*` or `?`).

### 3. Each changed file

For every file except removed ones:

- its path matches `layout`;
- if it ends in `.md`, its path matches `markdown`;
- its base name before the first dot, upper-cased, is not in `forbidden_names`.

For every file, removed ones included, and for the old path of a rename:

- the path matches a Scope entry;
- if it matches a `protected` glob, some Scope entry both matches the path and begins with that glob's literal prefix. A broad entry such as `src/**` therefore never unlocks `.github/**`; the Scope has to name `.github/...` itself.

### 4. Title

The PR title matches `<type>(#N): <summary>`: `type` from `types`, `N` the closed issue, and a summary of 1 to 72 characters that starts with a non-space.

### 5. Body

- The body contains the lines `## Changes`, `## Acceptance` and `## Out of scope`.
- It has at most `max_body_lines` lines.

### 6. Diff size (optional)

When `max_diff_lines` is set, the changed lines outside `test_paths` stay within it.

:::note
guard doesn't count the items under `## Changes`; the limit of 5 is a rule in `AGENTS.md`. It also doesn't judge the content of a change. That is the fresh-context review's job.
:::

## Run it locally

From the repo root, logged in to gh:

```sh
REPO=owner/repo PR_NUMBER=15 python .github/scripts/guard.py
```

It reads `.github/guard.toml` from the current directory, so run it from a checkout of main to get CI's result.

## Related

- [AGENTS.md: Files](/research-harness/reference/agents-md/#files)
- [merge.py](/research-harness/reference/merge-py/)
- [Issue forms](/research-harness/reference/issue-forms/)
- [Adopt rh](/research-harness/guides/adopt/)
- [Merging](/research-harness/concepts/merging/)
