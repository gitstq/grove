"""Command-line interface for Grove.

Run ``grove --help`` for the full surface. Every command supports ``--json`` for
agent/CI consumption and uses stable exit codes (see :mod:`grove.errors`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import List, Optional, Sequence

from . import __version__
from .config import load_config
from .core import WorktreeManager
from .errors import EXIT_ABORT, EXIT_GENERIC, EXIT_GIT, GitError, GroveError, UserAbort
from .git import Git


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def _emit(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    else:
        print(obj)


def _glyphs(ascii_mode: bool):
    if ascii_mode:
        return {"main": "*", "dirty": "!", "locked": "L", "detached": "(detached)", "up": "^", "down": "v"}
    return {"main": "◆", "dirty": "●", "locked": "🔒", "detached": "(detached)", "up": "↑", "down": "↓"}


def _truncate(text: str, width: int) -> str:
    text = text or ""
    return text if len(text) <= width else text[: width - 1] + "…"


def _format_list(manager: WorktreeManager, ascii_mode: bool) -> str:
    g = _glyphs(ascii_mode)
    wts = manager.list()
    rows = []
    for w in wts:
        mark = g["main"] if w.is_main else " "
        flags = []
        if w.dirty:
            flags.append(f"{g['dirty']}{w.changed}")
        if w.ahead:
            flags.append(f"{g['up']}{w.ahead}")
        if w.behind:
            flags.append(f"{g['down']}{w.behind}")
        if w.locked is not None:
            flags.append(g["locked"])
        label = w.label if w.branch else g["detached"]
        rows.append((mark, label, ",".join(flags) or "-", w.age, w.path, _truncate(w.subject, 48), w.agent))
    headers = ("", "BRANCH", "STATE", "AGE", "PATH", "LAST COMMIT", "AGENT")
    widths = [max(len(str(r[i])) for r in (rows + [headers])) for i in range(len(headers))]
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    out = [line, "  ".join("-" * widths[i] for i in range(len(headers)))]
    for r in rows:
        out.append("  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #
SUBCOMMANDS = {
    "add", "list", "ls", "info", "where", "cd", "remove", "rm", "prune",
    "exec", "foreach", "each", "share", "port", "doctor", "config",
}
_VALUE_FLAGS = {"-C", "--repo", "--config"}
_BOOL_FLAGS = {"--json", "--ascii", "-n", "--dry-run", "-y", "--yes"}


def _normalize_globals(argv: Sequence[str]) -> List[str]:
    """Relocate global flags placed BEFORE the subcommand to just after it.

    argparse lets subparsers shadow parent-level options, so we give subparsers
    single ownership of the global flags and canonicalize their position. This
    lets users write both ``grove -C repo list --json`` and
    ``grove list --json -C repo``.
    """
    tokens = list(argv)
    sub_idx = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _VALUE_FLAGS:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        sub_idx = i  # first bare token is the subcommand
        break
    if sub_idx is None:
        return tokens  # e.g. --version / --help with no subcommand
    pre = tokens[:sub_idx]
    sub = tokens[sub_idx]
    post = tokens[sub_idx + 1:]
    moved = [t for t in pre if t not in ("--",)]
    return [sub, *moved, *post]


def build_parser() -> argparse.ArgumentParser:
    # Global flags live on every subparser (single ownership); _normalize_globals
    # relocates any that were typed before the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-C", "--repo", default=None, help="run as if Grove was started in this path")
    common.add_argument("--config", dest="config_path", default=None, help="explicit JSON config file")
    common.add_argument("--json", action="store_true", help="machine-readable JSON output")
    common.add_argument("--ascii", action="store_true", help="ASCII-only glyphs (legacy terminals)")
    common.add_argument("-n", "--dry-run", action="store_true", help="show the plan without changing anything")
    common.add_argument("-y", "--yes", action="store_true", help="assume yes for destructive confirmations")

    p = argparse.ArgumentParser(
        prog="grove",
        description="Zero-dependency Git worktree orchestrator for parallel AI-agent workflows.",
        epilog="Docs: https://github.com/gitstq/grove | Every command supports --json.",
    )
    p.add_argument("--version", action="version", version=f"grove {__version__}")

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("add", parents=[common], help="create a worktree (and its branch) in one step")
    sp.add_argument("name", help="branch name, or pr:123 to check out a pull request")
    sp.add_argument("-b", "--base", help="base ref (branch/commit) to branch from")
    sp.add_argument("-a", "--agent", default="", help="agent/session label for orchestration")
    sp.add_argument("-p", "--path", help="override the computed worktree path")
    sp.add_argument("--detach", action="store_true", help="create a detached HEAD worktree")

    sp = sub.add_parser("list", aliases=["ls"], parents=[common], help="list worktrees with live status")
    sp.add_argument("--porcelain", action="store_true", help="alias of git worktree list --porcelain")

    sp = sub.add_parser("info", parents=[common], help="show one worktree's full status")
    sp.add_argument("name")

    sp = sub.add_parser("where", parents=[common], help="print a worktree's path (scriptable)")
    sp.add_argument("name")

    sp = sub.add_parser("cd", parents=[common], help="alias of `where`, for shell integration")
    sp.add_argument("name")

    sp = sub.add_parser("remove", aliases=["rm"], parents=[common], help="safely remove a worktree")
    sp.add_argument("name")
    sp.add_argument("-f", "--force", action="store_true", help="remove even with uncommitted changes")
    sp.add_argument("--keep-branch", action="store_true", help="do not delete the checked-out branch")

    sub.add_parser("prune", parents=[common], help="prune administrative/stale worktree entries")

    sp = sub.add_parser("exec", parents=[common], help="run a command inside one worktree")
    sp.add_argument("name")
    sp.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command and arguments")

    sp = sub.add_parser("foreach", aliases=["each"], parents=[common], help="run a command across worktrees")
    sp.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command and arguments")
    sp.add_argument("-j", "--parallel", action="store_true", help="run concurrently")
    sp.add_argument("--include-main", action="store_true", help="also run in the main worktree")

    sp = sub.add_parser("share", parents=[common], help="share build caches (node_modules/target/.venv) from main")
    sp.add_argument("name")
    sp.add_argument("paths", nargs="+", help="repo-relative cache paths")
    sp.add_argument("-s", "--strategy", choices=["hardlink", "copy", "symlink", "reflink"])
    sp.add_argument("-f", "--force", action="store_true")

    sp = sub.add_parser("port", parents=[common], help="deterministic per-worktree dev-server port")
    sp.add_argument("name")

    sp = sub.add_parser("doctor", parents=[common], help="validate environment, config and worktree state")

    sub.add_parser("config", parents=[common], help="show the resolved configuration")
    return p


def _clean_remainder(parts: Sequence[str]) -> List[str]:
    parts = list(parts or [])
    if parts and parts[0] == "--":
        parts = parts[1:]
    return parts


def _make_manager(args: argparse.Namespace) -> WorktreeManager:
    cwd = os.path.abspath(args.repo) if args.repo else os.getcwd()
    git = Git(cwd=cwd)
    git.ensure_supported()
    root = git.repo_root()
    cfg = load_config(repo_root=root, explicit=args.config_path)

    def confirm(_msg: str) -> bool:
        if args.yes:
            return True
        if not sys.stdin.isatty():
            raise UserAbort("non-interactive run; pass --yes to approve destructive actions")
        ans = input(f"{_msg} [y/N]: ").strip().lower()
        return ans in ("y", "yes")

    return WorktreeManager(cwd=cwd, config=cfg, git=git, confirm=confirm)


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #
def _cmd_add(m: WorktreeManager, args) -> int:
    result = m.add(
        args.name, base=args.base, agent=args.agent, path=args.path,
        detach=args.detach, dry_run=args.dry_run,
    )
    if args.dry_run:
        if args.json:
            _emit(result, True)
        else:
            print("(dry-run) planned worktree:")
            for k in ("branch", "path", "base", "create_branch", "detach", "pr"):
                print(f"  {k:14}: {result.get(k)}")
        return 0
    wt = m.info(result.path)
    if args.json:
        _emit(wt.to_dict(), True)
    else:
        print(f"✓ worktree ready: {wt.label} -> {wt.path}")
    return 0


def _cmd_list(m: WorktreeManager, args) -> int:
    if args.porcelain:
        print(m.git.run(["worktree", "list", "--porcelain"], cwd=m.root).stdout.rstrip())
        return 0
    if args.json:
        _emit([w.to_dict() for w in m.list()], True)
    else:
        print(_format_list(m, args.ascii))
    return 0


def _cmd_remove(m: WorktreeManager, args) -> int:
    res = m.remove(
        args.name, force=args.force,
        delete_branch=not args.keep_branch, yes=args.yes, dry_run=args.dry_run,
    )
    if args.json:
        _emit(res, True)
    elif args.dry_run:
        print("(dry-run) would remove:")
        for k, v in res.items():
            print(f"  {k:14}: {v}")
    else:
        msg = f"✓ removed {res['removed']}"
        if res.get("branch_deleted"):
            msg += f" (branch {res['branch']} deleted)"
        print(msg)
    return 0


def _cmd_exec(m: WorktreeManager, args) -> int:
    cmd = _clean_remainder(args.cmd)
    if not cmd:
        raise GroveError("exec: missing command (use `grove exec NAME -- <cmd>`)")
    wt = m.resolve(args.name)
    env = m._exec_env(wt)
    return subprocess.call(cmd, cwd=wt.path, env=env)


def _cmd_foreach(m: WorktreeManager, args) -> int:
    cmd = _clean_remainder(args.cmd)
    result = m.foreach(cmd, parallel=args.parallel, include_main=args.include_main)
    if args.json:
        _emit(result.to_dict(), True)
        return 0 if result.ok else EXIT_GENERIC
    for r in result.results:
        bar = "=" * 72
        print(f"{bar}\n[{r.name}] {r.path}\n$ {' '.join(cmd)}\n{bar}")
        if r.stdout:
            print(r.stdout.rstrip())
        if r.stderr:
            print(r.stderr.rstrip(), file=sys.stderr)
        print(f"-> exit {r.returncode}\n")
    return 0 if result.ok else EXIT_GENERIC


def _cmd_share(m: WorktreeManager, args) -> int:
    report = m.share(args.name, args.paths, strategy=args.strategy,
                     force=args.force, dry_run=args.dry_run)
    if args.json:
        _emit(report, True)
    else:
        for item in report:
            tag = item.get("used_strategy", "planned")
            print(f"✓ {item['rel']}: {tag} -> {item['target']}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_globals(list(argv) if argv is not None else sys.argv[1:]))
    try:
        if args.command == "config":
            cwd = os.path.abspath(args.repo) if args.repo else os.getcwd()
            root = Git(cwd=cwd).repo_root()
            cfg = load_config(repo_root=root, explicit=args.config_path)
            _emit(cfg.to_dict(), args.json)
            return 0

        m = _make_manager(args)
        if args.command in ("add",):
            return _cmd_add(m, args)
        if args.command in ("list", "ls"):
            return _cmd_list(m, args)
        if args.command == "info":
            wt = m.info(args.name)
            if args.json:
                _emit(wt.to_dict(), True)
            else:
                print(_format_one(wt))
            return 0
        if args.command in ("where", "cd"):
            print(m.where(args.name))
            return 0
        if args.command in ("remove", "rm"):
            return _cmd_remove(m, args)
        if args.command == "prune":
            res = m.prune(dry_run=args.dry_run)
            _emit(res, args.json) if args.json else print(
                "dry-run:\n" + res["git_output"] if args.dry_run else
                ("pruned " + str(len(res["removed_worktrees"])) + " stale worktree(s)"))
            return 0
        if args.command == "exec":
            return _cmd_exec(m, args)
        if args.command in ("foreach", "each"):
            return _cmd_foreach(m, args)
        if args.command == "share":
            return _cmd_share(m, args)
        if args.command == "port":
            print(m.deterministic_port(args.name))
            return 0
        if args.command == "doctor":
            checks = m.doctor()
            if args.json:
                _emit(checks, True)
                return 0 if all(c["ok"] for c in checks) else EXIT_GENERIC
            for c in checks:
                print(f"[{'OK' if c['ok'] else 'XX'}] {c['check']:22} {c['detail']}")
            return 0 if all(c["ok"] for c in checks) else EXIT_GENERIC
        parser.error(f"unknown command {args.command}")
        return EXIT_GENERIC
    except UserAbort as exc:
        print(f"aborted: {exc}", file=sys.stderr)
        return EXIT_ABORT
    except GitError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "type": "git", "stderr": exc.stderr},
                             ensure_ascii=False), file=sys.stderr)
        else:
            print(f"git error: {exc}", file=sys.stderr)
        return EXIT_GIT
    except GroveError as exc:
        if args.json:
            print(json.dumps({"error": str(exc), "type": "grove"}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_GENERIC


def _format_one(wt) -> str:
    lines = [
        f"branch : {wt.label}",
        f"path   : {wt.path}",
        f"head   : {wt.last_sha or wt.head or '-'}  {wt.subject}",
        f"state  : dirty={wt.dirty} changed={wt.changed} ahead={wt.ahead} behind={wt.behind}",
        f"age    : {wt.age}" + (f"  agent={wt.agent}" if wt.agent else ""),
    ]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
