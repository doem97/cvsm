<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
  <img alt="research-harness. Agents do the work. You hold the gates. Agent trajectories pass four human gates (publish, merge, budget, conclude) and resolve into a results table checked against the study spec." src="docs/assets/hero-light.svg" width="100%">
</picture>

**Let coding agents run your ML research, and keep every comparison fair.**

rh is a template you copy into a research repo, not a service. GitHub issues hold the state, and one rules file (`AGENTS.md`) plus four skills hold the procedure, for Claude Code and Codex alike. You decide in a session at four gates: publish, merge, budget and conclude. Every run is checked against the study spec you approved, from its own record.

![status: pre-release](https://img.shields.io/badge/status-pre--release-5C616B?style=flat-square&labelColor=0B0C0F) ![agents: Claude Code and Codex](https://img.shields.io/badge/agents-Claude_Code_%C2%B7_Codex-5C616B?style=flat-square&labelColor=0B0C0F) ![install: no service](https://img.shields.io/badge/install-no_service-5C616B?style=flat-square&labelColor=0B0C0F) ![human gates: 4](https://img.shields.io/badge/human_gates-4-F04A0E?style=flat-square&labelColor=0B0C0F) ![runs: checked against the spec](https://img.shields.io/badge/runs-checked_against_the_spec-2F6FE0?style=flat-square&labelColor=0B0C0F) ![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-5C616B?style=flat-square&labelColor=0B0C0F)

[中文](docs/README.zh-CN.md) · [Docs](https://doem97.github.io/research-harness/) · [Quick start](https://doem97.github.io/research-harness/start/quick-start/)

## The spec is the contract

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/contract-dark.svg">
  <img alt="A study spec card, readable by you and approved at gate 01. Below it, denser layers of agent work: code, config, launches and runs. A blue arrow runs from six run records back up to the spec, with the spec check those records produced." src="docs/assets/contract-light.svg" width="100%">
</picture>

The spec states the arms, the settings held fixed (each with a reason), and what may adapt. It is the one layer you can truly read. Agents do the work below it, and rh checks every run against it from the run's own record, right after launch and in every results comment.

## Start

1. **Copy the template** into your repo:

   ```
   git -C <rh clone> archive HEAD \
     AGENTS.md .agents .claude .codex .github scripts tests \
     ':!.github/workflows/pages.yml' | tar -x -C <your repo>
   ```

2. **Fill in the Project section of `AGENTS.md`**, one line per field: layout, test command, language, protected paths, Run command and run records.
3. **Push to `main` and run `bash scripts/setup.sh`** as a repo admin. It sets the labels, squash-only merges and branch protection.

Then open Claude Code or Codex in the repo and say "let's plan this study". The [adoption guide](https://doem97.github.io/research-harness/guides/adopt/) covers `guard.toml`, `run.toml`, CI and an optional machine account.

## Learn more

- **Start:** [Overview](https://doem97.github.io/research-harness/start/overview/) · [Quick start](https://doem97.github.io/research-harness/start/quick-start/) · [Talk, don't click](https://doem97.github.io/research-harness/start/talk-dont-click/)
- **Concepts:** [State](https://doem97.github.io/research-harness/concepts/state/) · [Gates and blockers](https://doem97.github.io/research-harness/concepts/gates-and-blockers/) · [Review](https://doem97.github.io/research-harness/concepts/review/) · [Merging](https://doem97.github.io/research-harness/concepts/merging/) · [Run records](https://doem97.github.io/research-harness/concepts/run-records/) · [Study spec](https://doem97.github.io/research-harness/concepts/study-spec/) · [Principles](https://doem97.github.io/research-harness/concepts/principles/)
- **Guides:** [Adopt](https://doem97.github.io/research-harness/guides/adopt/) · [Plan a study](https://doem97.github.io/research-harness/guides/plan-a-study/) · [Run experiments](https://doem97.github.io/research-harness/guides/run-experiments/) · [Adapt your environment](https://doem97.github.io/research-harness/guides/adapt-your-environment/) · [Claude Code and Codex](https://doem97.github.io/research-harness/guides/claude-code-and-codex/)
- **Reference:** [AGENTS.md](https://doem97.github.io/research-harness/reference/agents-md/) · [Skills](https://doem97.github.io/research-harness/reference/skills/) · [Issue forms](https://doem97.github.io/research-harness/reference/issue-forms/) · [guard](https://doem97.github.io/research-harness/reference/guard/) · [merge.py](https://doem97.github.io/research-harness/reference/merge-py/) · [run.py](https://doem97.github.io/research-harness/reference/run-py/) · [results.py](https://doem97.github.io/research-harness/reference/results-py/) · [Interfaces](https://doem97.github.io/research-harness/reference/interfaces/)
- **Project:** [Status](https://doem97.github.io/research-harness/project/status/) · [Built with rh](https://doem97.github.io/research-harness/project/built-with-rh/) · [License](https://doem97.github.io/research-harness/project/license/)

rh is a pre-release, and its interfaces may still change. The docs site goes live with the first release.

## License

[Apache-2.0](LICENSE).
