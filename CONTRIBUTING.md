# Contributing to Grove 🌳

Thanks for taking the time to improve Grove! This document explains how to get
a change merged with minimal friction.

## Development setup

Grove is pure standard-library Python — no runtime dependencies.

```bash
git clone https://github.com/gitstq/grove.git
cd grove
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python -m unittest discover -s tests -v              # run the full suite
```

You need a system `git` (>= 2.20) on your `PATH`; tests create real throwaway
repositories in a temporary directory.

## Coding standards

- Keep the **zero third-party runtime dependency** promise — use the standard
  library only. If a change truly needs a dependency, open an issue first.
- Target Python **3.8+**: no `match` statements, no `tomllib`, use
  `from __future__ import annotations`.
- Every new command/flag must support `--json` and carry unit tests.
- Respect cross-platform paths: use `pathlib`/`os.path`, never hard-code `/`.
- Destructive operations must be guarded (dirty checks, `--dry-run`, `--yes`).

## Commit messages (Angular Convention)

Use the Angular commit format, optionally scoped:

```
<type>(<scope>): <short summary>
```

Types: `feat` (new feature), `fix` (bug fix), `docs` (documentation only),
`style` (formatting), `refactor`, `perf`, `test`, `chore` (build/tooling),
`ci`.

Examples:

```
feat(core): add parallel foreach executor
fix(cli): keep global flags placed before the subcommand
docs(readme): add Traditional Chinese translation
```

## Pull requests

1. Fork and create a branch named `feat/<short-topic>` or `fix/<short-topic>`.
2. Add tests; ensure `python -m unittest discover -s tests` is green.
3. Update `CHANGELOG.md` under an `Unreleased` heading.
4. Keep PRs focused; describe the problem, solution and how you tested it.

## Issues

When filing a bug, include: `grove --version`, `git --version`, OS, the exact
command, expected vs actual output, and `grove doctor --json` if relevant.
Feature requests are welcome — describe the workflow you want to enable.

## Code of conduct

Be kind and constructive. We follow a standard contributor covenant spirit:
respectful discussion, no harassment, assume good faith.
