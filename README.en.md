<div align="center">

# 🌳 Grove

**Make Git worktrees as easy as branches — a zero-dependency orchestrator for running many AI agents in parallel**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/gitstq/grove/actions/workflows/ci.yml/badge.svg)](https://github.com/gitstq/grove/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Zero Dependencies](https://img.shields.io/badge/runtime%20deps-0-ff69b4.svg)](requirements.txt)

**🌐 Language：** [简体中文](README.md) ｜ [繁體中文](README.zh-TW.md) ｜ [English](README.en.md)

</div>

---

## 🎉 Introduction

**Grove** is a **Git worktree orchestration engine** written entirely with the
Python standard library. When you run several AI coding agents (Claude Code,
Codex, Cursor, …) on 5–10 tasks at once, Git's native
[worktrees](https://git-scm.com/docs/git-worktree) give every task an isolated
working directory so they never step on each other's changes. The native CLI,
however, is clunky — creating a single worktree forces you to type the branch
name three times:

```bash
git worktree add -b feature/login ../repo.feature/login   # name twice
cd ../repo.feature/login                                  # and a third time
```

Grove collapses this into one line. You only ever think in **branch names**;
paths are computed from a template:

```bash
grove add feature/login      # create branch + worktree in one step
grove list                   # live status of every worktree
grove foreach -j -- npm test # run tests in every worktree, in parallel
grove remove feature/login   # safe cleanup with an uncommitted-change guard
```

> 💡 **The pain it removes**: directories colliding when agents run in
> parallel, hand-calculating worktree paths, the lack of bulk operations,
> reinstalling build caches for every checkout, conflicting dev-server ports,
> and accidentally deleting uncommitted work during cleanup.

### 🌟 Differentiators

- 🪶 **Genuinely zero third-party runtime dependencies** — only the Python
  standard library plus the system `git`. Installs instantly, works offline,
  no Rust/Node toolchain required.
- 🤖 **Agent/CI-first** — every command speaks `--json` and returns stable
  exit codes, so automation, pipelines and AI agents can drive it reliably.
- ⚡ **Parallel orchestration primitives** — `grove exec` and
  `grove foreach --parallel` run a command in one or every worktree, aggregate
  labelled output and inject `GROVE_BRANCH` and related environment variables.
- 🧩 **Cross-platform build-cache sharing** — `grove share` reuses
  `node_modules`, `target`, `.venv` across worktrees via hardlink / copy /
  symlink with automatic fallback (works on Windows, macOS and Linux).
- 🔢 **Deterministic ports** — `grove port` derives a stable, collision-free
  local port per worktree from an FNV-1a hash.
- 🛡️ **Safety rails** — uncommitted-change guards, `--dry-run`, confirmations
  and path-traversal rejection. Nothing destructive happens by default.
- 🧭 **Inspiration** — the product problem was validated by the trending
  worktree manager *worktrunk* (written in Rust). Grove uses **none of its
  code**; it is an independent, from-scratch Python implementation with extra
  emphasis on parallel orchestration, cross-platform caching and JSON
  automation.

---

## ✨ Features

| Capability | Command | What it does |
| --- | --- | --- |
| 🌱 One-step worktree | `grove add <branch>` | branch + worktree at once; `--base/--agent/--detach` |
| 🔀 Check out a PR | `grove add pr:123` | fetch a pull request into its own worktree/branch |
| 📋 Live overview | `grove list` | dirty/untracked counts, ahead/behind, last commit, agent |
| 🔎 Locate & inspect | `grove where / info / cd` | resolve a branch or path to a worktree, scriptable |
| 🧹 Safe cleanup | `grove remove / prune` | dirty guard, optional branch deletion, `--force`, `--dry-run` |
| 🚀 Run in one tree | `grove exec <name> -- <cmd>` | run any command inside a worktree with its env |
| 🏃 Bulk / parallel | `grove foreach [-j] -- <cmd>` | run sequentially or in parallel with labelled output |
| 📦 Cache sharing | `grove share <name> <path…>` | reuse the main tree's caches with multi-strategy fallback |

- 🔢 **Deterministic port**: `grove port <name>` prints a stable port for a
  per-worktree dev server.
- ⚙️ **Templated paths + two-level config**: variables such as
  `{parent}/{repo}.{slug}`, global + per-repo JSON config and `GROVE_*`
  environment overrides.
- 🩺 **Self-check**: `grove doctor` validates the git version, configuration
  and worktree metadata integrity.
- 🖥️ **Cross-platform**: identical behaviour on Windows / macOS / Linux, with
  an `--ascii` mode for legacy terminals.
- 🧪 **Well tested**: 34 unit tests exercise the full lifecycle against real,
  throwaway git repositories.

---

## 🚀 Quick Start

### Requirements

- 🐍 Python **3.8+** (no third-party runtime dependencies)
- 🐙 **Git ≥ 2.20** installed and on `PATH` (`git --version`)

### Install

```bash
# Option 1 — pip / pipx (recommended; provides the global `grove` command)
pip install grove-wt
grove --version

# Option 2 — no install: clone and use the source launcher
git clone https://github.com/gitstq/grove.git
cd grove
python run_grove.py --version
```

> On Windows you can also use `py -m grove`. If `grove` clashes with another
> program in your shell, use `python -m grove` instead.

### 30-second tour

```bash
cd your-repo

# 1) Spin up a worktree for each parallel task
grove add feature/auth   --agent agent-1
grove add feature/search --agent agent-2

# 2) Inspect everything (the main worktree is marked ◆)
grove list

# 3) Jump into one (pair with the shell snippet below to cd directly)
cd "$(grove where feature/auth)"

# 4) Run tests across all worktrees in parallel
grove foreach --parallel -- npm test

# 5) Clean up safely (uncommitted changes block removal)
grove remove feature/auth
```

### Shell integration for direct `cd` (optional)

A child process cannot change its parent shell's directory, so `grove cd` only
prints the path. Add this to `~/.bashrc` / `~/.zshrc` to get a `gcd` helper
(fish and PowerShell variants live in
[examples/shell-integration.md](examples/shell-integration.md)):

```bash
gcd() { local t; t="$(grove where "$1" 2>/dev/null)" || { grove add "$1" || return 1; t="$(grove where "$1")"; }; cd "$t" || return 1; }
```

---

## 📖 Usage Guide

### Command reference

```text
grove add <name> [-b BASE] [-a AGENT] [-p PATH] [--detach]
grove list|ls [--json] [--porcelain] [--ascii]
grove info <name> [--json]
grove where <name>          # print the worktree's absolute path
grove cd <name>             # semantic alias of `where`
grove remove|rm <name> [-f] [--keep-branch] [-y] [-n]
grove prune [-n]
grove exec <name> -- <cmd...>
grove foreach|each [-j] [--include-main] -- <cmd...>
grove share <name> <relpath...> [-s hardlink|copy|symlink|reflink] [-f] [-n]
grove port <name>
grove doctor [--json]
grove config [--json]
```

### Global flags (valid before or after the subcommand)

| Flag | Meaning |
| --- | --- |
| `-C, --repo DIR` | act as if started in DIR (like `git -C`) |
| `--config FILE` | load an extra JSON config file |
| `--json` | machine-readable JSON output (best for automation) |
| `--ascii` | ASCII-only glyphs for terminals without Unicode |
| `-n, --dry-run` | print the plan, change nothing |
| `-y, --yes` | approve destructive prompts non-interactively (CI) |

### 1) Create a worktree — `grove add`

```bash
grove add feature/login                # new branch + worktree from the default base
grove add hotfix -b release/v2         # branch from a specific ref
grove add experiment --detach          # detached HEAD, no branch
grove add pr:123                       # check out pull request #123
grove add feat/x -p ../custom/path     # custom destination path
grove add feat/x -n                    # dry-run: show the plan only
```

The default path template is `{parent}/{repo}.{slug}`: with the main checkout
at `/code/app`, branch `feat/x` lands in `/code/app.feat-x`. The `slug` turns
`feat/x` into the cross-platform-safe directory name `feat-x`.

### 2) Live overview — `grove list`

```bash
grove list            # human-readable table
grove list --json     # structured output for jq / agents / CI
grove list --porcelain# raw `git worktree list --porcelain`
```

Columns: main marker `◆`, branch, state (`●n` = n changes, `↑n/↓n` =
ahead/behind upstream), last-commit age, path, commit subject and agent label.

### 3) Bulk `grove foreach` and single `grove exec`

```bash
# Install dependencies in every non-main worktree, in parallel
grove foreach -j -- npm ci

# Include the main worktree
grove foreach --include-main -- pytest -q

# Run in just one worktree
grove exec feature/auth -- npm run build
```

Each run receives `GROVE_BRANCH`, `GROVE_WORKTREE` and `GROVE_REPO_ROOT`. If
any worktree fails, the overall exit code is non-zero for pipeline gating.

### 4) Share build caches — `grove share`

```bash
# After `npm install` in the main tree, hardlink node_modules into a new tree
grove share feature/auth node_modules
grove share feature/x target .venv -s hardlink
grove share feature/x node_modules -s symlink    # use a symlink instead
grove share feature/x node_modules -n            # dry-run
```

Strategies: `hardlink` (default; inode-efficient on the same volume, with
per-file copy fallback), `copy` (fully independent), `symlink` (live shared
directory) and `reflink` (best-effort CoW with fallback). Paths must be
repo-relative; `../` traversal is rejected.

### 5) Deterministic ports — `grove port`

```bash
grove port feature/auth   # e.g. 44483 — stable forever for this branch
```

Use it to give every worktree a stable, collision-free dev-server port:

```bash
grove exec feature/auth -- sh -c 'PORT=$(grove port feature/auth) npm run dev'
```

### 6) Cleanup — `grove remove` / `grove prune`

```bash
grove remove feature/auth               # refuses with uncommitted changes
grove remove feature/auth -f            # discard changes and delete the branch
grove remove feature/auth --keep-branch # remove the tree, keep the branch
grove prune                             # drop stale admin entries + metadata
grove remove feature/auth -n            # dry-run
```

### ⚙️ Configuration

Precedence (later wins): built-in defaults → global
`~/.config/grove/config.json` (`%APPDATA%\grove\config.json` on Windows) →
repo-root `.groveconfig.json` → `--config` → `GROVE_*` variables.

```json
{
  "path_template": "{parent}/{repo}.{slug}",
  "port_base": 40000,
  "port_span": 20000,
  "cache_strategy": "hardlink",
  "default_base": "main",
  "auto_prune": true,
  "include_main_in_foreach": false
}
```

Template variables: `{parent}` (parent of the main checkout), `{repo}` (main
directory name), `{slug}` (sanitized branch), `{branch}` (raw branch),
`{agent}` (agent label), `{name}`. See
[examples/groveconfig.example.json](examples/groveconfig.example.json).

### 🧭 Recipe: run N AI agents in parallel

```bash
for name in feat/auth feat/billing feat/search; do
  grove add "$name" --agent "$name"
  ( cd "$(grove where "$name")" && your-ai-cli "implement $name and self-test" & )
done

grove list --json | jq -r '.[] | select(.is_main|not) | "\(.branch)\t\(.changed)\t\(.path)"'
grove share feat/auth node_modules      # reuse dependencies
grove foreach -j -- npm test            # parallel regression
grove foreach -- git status --short     # summarise changes
```

### 🖼️ Demo

A mock terminal of `grove list` is shown below (a full demo gif will be kept at
`docs/demo.gif`):

<div align="center"><img src="docs/demo.svg" alt="mock terminal of grove list" width="760"></div>

### ❓ FAQ

- **How is this different from raw `git worktree`?** Grove addresses trees by
  branch name, computes paths for you, and adds bulk execution, cache sharing,
  port allocation, an overview and safety rails. It still shells out to native
  git and never changes your repository layout.
- **Does it pollute my repo?** It writes a single `grove-meta.json` (agent
  labels, etc.) inside the shared git directory, so it never shows up in
  `git status`; delete that file to remove all traces.
- **Does it need network access?** Everything works offline except `pr:N`,
  which fetches a pull request.
- **Which platforms are supported?** Windows / macOS / Linux, Python 3.8+,
  Git 2.20+.

---

## 💡 Design & Roadmap

### Design principles

1. **Zero dependencies as reliability.** In the minimal environments where AI
   agents and CI run, every dependency is a failure source. Grove relies only
   on the standard library and system git, so it runs anywhere, instantly.
2. **Composition over reinvention.** Grove does not reimplement Git; it wraps
   native worktrees into composable, scriptable primitives that fit automation
   through `--json` and stable exit codes.
3. **Safe by default.** Every destructive action has a dirty-state guard, a
   dry-run and a confirmation; you must opt in with `--force/--yes`.
4. **Built for parallelism.** Multi-agent work demands bulk, parallel,
   isolated and observable operations — `foreach/exec/share/port/list` are
   designed around exactly those four needs.

### Why the Python standard library

It offers the best cross-platform consistency and the broadest reach across
AI/data workflows. `subprocess`, `argparse`, `concurrent.futures` and
`pathlib` already cover every requirement, so no compiler toolchain is needed
and every line is easy to audit and run.

### 🗺️ Roadmap

- [ ] v1.1 — interactive worktree picker (arrow-key browsing with diff/log preview)
- [ ] v1.1 — `grove merge` end-to-end merge workflow (squash/rebase/cleanup)
- [ ] v1.2 — lifecycle hooks (create / pre-merge / post-merge)
- [ ] v1.2 — session templates for Claude Code / Codex / Cursor
- [ ] v1.3 — remote status aggregation (CI status, PR summaries)
- [ ] v1.3 — shell completion (bash/zsh/fish/PowerShell)

Ideas are welcome in [Issues](https://github.com/gitstq/grove/issues); see
[CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute.

---

## 📦 Packaging & Deployment

Grove is a **CLI tool / library** distributed as a Python wheel — no binary
download is required.

### Build from source

```bash
make build                    # compile check + tests + wheel/sdist into dist/
# Or without make:
bash scripts/build.sh         # Linux / macOS
powershell scripts/build.ps1  # Windows
```

Artifacts:

```text
dist/grove_wt-1.0.0-py3-none-any.whl   # universal pure-Python wheel
dist/grove-wt-1.0.0.tar.gz             # source distribution
```

### Install and verify locally

```bash
pip install dist/grove_wt-1.0.0-py3-none-any.whl
grove --version && grove doctor
```

### Use it as a library

```python
from grove import WorktreeManager, Config

mgr = WorktreeManager(cwd="/path/to/repo", config=Config(cache_strategy="hardlink"))
wt = mgr.add("feature/x", agent="agent-1")
for w in mgr.list():
    print(w.label, w.path, w.dirty)
report = mgr.foreach(["pytest", "-q"], parallel=True)
print(report.ok)
```

Compatibility: Python 3.8–3.13 on Windows, macOS and Linux. The CI matrix on
GitHub Actions covers ubuntu / macos / windows.

---

## 🤝 Contributing

Issues, PRs and doc translations are very welcome — please read
[CONTRIBUTING.md](CONTRIBUTING.md) first:

- Commit messages follow the **Angular convention**: `feat:` / `fix:` /
  `docs:` / `refactor:` / `test:` / `chore:` / `ci:`.
- Keep the zero-runtime-dependency promise; new commands need both `--json`
  and unit tests.
- Run `python -m unittest discover -s tests` and keep it green before opening
  a PR.
- For issues, include `grove --version`, `git --version`, OS, the command and
  expected vs actual output.

---

## 📄 License

Released under the **[MIT License](LICENSE)** — free for personal and
commercial use, just retain the copyright notice.

<div align="center">

🌳 **Grove — give every parallel task its own little grove.**

If Grove helps you, a ⭐ is much appreciated!

</div>
