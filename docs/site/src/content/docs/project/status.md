---
title: Status
description: rh is a pre-release; what that means for its interfaces, this site and known limitations.
sidebar:
  order: 1
---

rh is a pre-release. It runs its own development, and its interfaces may still change before the first release.

## What pre-release means

- The [interfaces that stay fixed](/research-harness/reference/interfaces/) are fixed for adopters' implementations, but rh itself may still change them before the first release.
- As of 2026-10-18 there are no tags or versioned releases. Record the rh commit you copied in your adoption commit, so you can compare later rh changes against it.
- This docs site is published on GitHub Pages with the first release.

## Known limitations

- **Results text is Chinese only.** The reference `results.py` writes its table headers, flags and `规格核对` lines in Chinese. A project that wants another language changes `results.py`.
- Other built-in text is Chinese too: the descriptions in the issue forms, the messages of `merge.py`, and the language the skills name for discussions, PR bodies and reports. The `Language` line of `AGENTS.md` sets a project's own language; the files that hard-code Chinese have to be edited to match.
- `run.py` and `results.py` are a single-machine reference. Clusters, schedulers and remote storage are for each adopter to fit; see [Adapt rh to your environment](/research-harness/guides/adapt-your-environment/).
- Branch protection on a private repo needs a paid GitHub plan.

## Related

- [Built with rh](/research-harness/project/built-with-rh/)
- [License](/research-harness/project/license/)
- [Adopt rh](/research-harness/guides/adopt/)
