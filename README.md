<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="CVSM, the Controlled-Variable State Machine Protocol. Agent trajectories pass four human gates (publish, merge, budget, conclude) and resolve into a results table checked against the study spec." src="docs/assets/hero-light.svg" width="100%">
</picture>

# Controlled-Variable State Machine Protocol (CVSM)

A state machine protocol for running controlled ML experiments with coding agents. You write the study spec: which variables differ between arms, which are held fixed, and which may adapt. Agents implement and run the study through GitHub issues and pull requests, one state at a time. Every run records its resolved config, and a script checks it against the spec and reports any difference the spec does not allow. You decide at four points: publish, merge, budget and conclude.

CVSM is a set of files you copy into a research repo, not a service. GitHub issues hold the state, and one rules file (`AGENTS.md`) plus four skills hold the procedure, for Claude Code and Codex alike.

![status: pre-release](https://img.shields.io/badge/status-pre--release-5C616B?style=flat-square&labelColor=0B0C0F) ![agents: Claude Code and Codex](https://img.shields.io/badge/agents-Claude_Code_%C2%B7_Codex-5C616B?style=flat-square&labelColor=0B0C0F) ![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-5C616B?style=flat-square&labelColor=0B0C0F)

[中文](docs/README.zh-CN.md) · [Docs](https://doem97.github.io/cvsm/) · [Quick start](https://doem97.github.io/cvsm/start/quick-start/)

## Every run is checked against the study spec

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/contract-dark.svg">
  <img alt="A study spec card, readable by you and approved at gate 01. Below it, denser layers of agent work: code, config, launches and runs. A blue arrow runs from six run records back up to the spec, with the spec check those records produced." src="docs/assets/contract-light.svg" width="100%">
</picture>

The spec states the arms, the settings held fixed (each with a reason), and what may adapt. It is the one layer you can truly read. Agents do the work below it, and CVSM checks every run against it from the run's own record, right after launch and in every results comment.

## You adopt CVSM by copying its files into your repo

1. **Copy the files** into your repo:

   ```
   git -C <cvsm clone> archive HEAD \
     AGENTS.md .agents .claude .codex .github scripts tests \
     ':!.github/workflows/pages.yml' | tar -x -C <your repo>
   ```

2. **Fill in the Project section of `AGENTS.md`**, one line per field: layout, test command, language, protected paths, Run command and run records.
3. **Push to `main` and run `bash scripts/setup.sh`** as a repo admin. It sets the labels, squash-only merges and branch protection.

Then open Claude Code or Codex in the repo and say "let's plan this study". The [adoption guide](https://doem97.github.io/cvsm/guides/adopt/) covers `guard.toml`, `run.toml`, CI and an optional machine account.

## The docs cover each part in detail

- **Start:** [Overview](https://doem97.github.io/cvsm/start/overview/) · [Quick start](https://doem97.github.io/cvsm/start/quick-start/) · [Talk, don't click](https://doem97.github.io/cvsm/start/talk-dont-click/)
- **Concepts:** [State](https://doem97.github.io/cvsm/concepts/state/) · [Gates and blockers](https://doem97.github.io/cvsm/concepts/gates-and-blockers/) · [Review](https://doem97.github.io/cvsm/concepts/review/) · [Merging](https://doem97.github.io/cvsm/concepts/merging/) · [Run records](https://doem97.github.io/cvsm/concepts/run-records/) · [Study spec](https://doem97.github.io/cvsm/concepts/study-spec/) · [Principles](https://doem97.github.io/cvsm/concepts/principles/)
- **Guides:** [Adopt](https://doem97.github.io/cvsm/guides/adopt/) · [Plan a study](https://doem97.github.io/cvsm/guides/plan-a-study/) · [Run experiments](https://doem97.github.io/cvsm/guides/run-experiments/) · [Adapt your environment](https://doem97.github.io/cvsm/guides/adapt-your-environment/) · [Claude Code and Codex](https://doem97.github.io/cvsm/guides/claude-code-and-codex/)
- **Reference:** [AGENTS.md](https://doem97.github.io/cvsm/reference/agents-md/) · [Skills](https://doem97.github.io/cvsm/reference/skills/) · [Issue forms](https://doem97.github.io/cvsm/reference/issue-forms/) · [guard](https://doem97.github.io/cvsm/reference/guard/) · [merge.py](https://doem97.github.io/cvsm/reference/merge-py/) · [run.py](https://doem97.github.io/cvsm/reference/run-py/) · [results.py](https://doem97.github.io/cvsm/reference/results-py/) · [Interfaces](https://doem97.github.io/cvsm/reference/interfaces/)
- **Project:** [Status](https://doem97.github.io/cvsm/project/status/) · [Built with CVSM](https://doem97.github.io/cvsm/project/built-with-cvsm/) · [License](https://doem97.github.io/cvsm/project/license/)
- **Design notes** (Chinese): [docs/design/2026-10-16-harness-v1.md](docs/design/2026-10-16-harness-v1.md)

CVSM is a pre-release, and its interfaces may still change. The docs site goes live with the first release.

## License

[Apache-2.0](LICENSE).
