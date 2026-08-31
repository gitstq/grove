# Changelog

All notable changes to **Grove** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-31

### Added
- `grove add` — create a worktree (and branch) in a single step; branch name
  is typed exactly once. Supports `--base`, `--agent`, `--path` and `--detach`.
- `grove pr:123` style checkout — fetch a GitHub pull request straight into a
  dedicated worktree and branch.
- `grove list` / `ls` — live status table: dirty count, untracked count,
  ahead/behind vs upstream, last commit age and subject, agent label.
  `--json` for agents/CI and `--porcelain` passthrough.
- `grove info / where / cd` — resolve a branch or path to a worktree and print
  scriptable metadata.
- `grove remove` / `rm` — safe removal with an uncommitted-change guard,
  optional branch deletion, `--force`, `--keep-branch`, `--dry-run`.
- `grove prune` — clean stale administrative worktree entries and metadata.
- `grove exec` and `grove foreach` (`--parallel`, `--include-main`) — run a
  command in one or every worktree, with aggregated, labelled output and
  `GROVE_BRANCH` / `GROVE_WORKTREE` / `GROVE_REPO_ROOT` environment injection.
- `grove share` — reuse heavy build caches (`node_modules`, `target`,
  `.venv`, ...) from the main worktree via hardlink / copy / symlink /
  best-effort reflink with automatic per-file fallback.
- `grove port` — deterministic FNV-1a per-worktree dev-server port.
- `grove doctor` — environment, config and worktree-integrity self-check.
- `grove config` — show the resolved global + repo configuration.
- Configurable JSON path templates and two-level config
  (`~/.config/grove/config.json` + repo `.groveconfig.json`), plus
  `GROVE_*` environment overrides.
- Zero third-party runtime dependencies; pure Python standard library;
  cross-platform (Windows / macOS / Linux); Python 3.8+.
- Full unit-test suite (34 tests) driving real throwaway git repositories.
