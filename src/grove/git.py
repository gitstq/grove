"""Thin, dependency-free wrapper around the system ``git`` executable.

The module deliberately uses only :mod:`subprocess` and text parsing — no
third-party Git library — so Grove stays installable anywhere a Git CLI exists.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .errors import GitError, GroveError


@dataclass
class PorcelainWorktree:
    """One record parsed from ``git worktree list --porcelain``."""

    path: str
    head: Optional[str] = None
    branch: Optional[str] = None  # short branch name, None when detached
    detached: bool = False
    bare: bool = False
    locked: Optional[str] = None  # lock reason or "" when locked without reason
    prunable: Optional[str] = None


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    argv: List[str] = field(default_factory=list)


class Git:
    """Run git commands scoped to a working directory with friendly errors."""

    MIN_GIT_VERSION = (2, 20, 0)  # required for robust worktree porcelain

    def __init__(self, cwd: Optional[str] = None, git_bin: Optional[str] = None):
        self.git_bin = git_bin or shutil.which("git") or "git"
        self.cwd = cwd or os.getcwd()
        self._version: Optional[tuple] = None

    # ------------------------------------------------------------------ low
    def run(
        self,
        args: Sequence[str],
        cwd: Optional[str] = None,
        check: bool = True,
        input_text: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        argv = [self.git_bin, *[str(a) for a in args]]
        run_env = os.environ.copy()
        # Stable, parseable output regardless of the user's locale/config.
        run_env["GIT_TERMINAL_PROMPT"] = "0"
        run_env.setdefault("LC_ALL", "C.UTF-8")
        run_env.setdefault("GIT_PAGER", "cat")
        if env:
            run_env.update(env)
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd or self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                input=input_text,
                env=run_env,
            )
        except FileNotFoundError as exc:  # pragma: no cover - guarded by version()
            raise GroveError(f"git executable not found: {self.git_bin!r}") from exc
        res = CommandResult(proc.returncode, proc.stdout, proc.stderr, argv)
        if check and proc.returncode != 0:
            raise GitError(
                f"git command failed ({proc.returncode}): {' '.join(argv[1:])}\n"
                f"{proc.stderr.strip()}",
                returncode=proc.returncode,
                argv=argv,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        return res

    def quiet_ok(self, args: Sequence[str], cwd: Optional[str] = None) -> bool:
        """Return True when a command exits 0, False otherwise (no raise)."""
        try:
            self.run(args, cwd=cwd, check=True)
            return True
        except GitError:
            return False

    # -------------------------------------------------------------- version
    def version(self) -> tuple:
        if self._version is None:
            out = self.run(["--version"]).stdout
            # "git version 2.34.1"
            parts = out.split()
            nums = []
            for tok in parts[-1].split("."):
                num = ""
                for ch in tok:
                    if ch.isdigit():
                        num += ch
                    else:
                        break
                if num:
                    nums.append(int(num))
            self._version = tuple((nums + [0, 0, 0])[:3])
        return self._version

    def ensure_supported(self) -> tuple:
        ver = self.version()
        if ver < self.MIN_GIT_VERSION:
            raise GroveError(
                f"Grove requires git >= {'.'.join(map(str, self.MIN_GIT_VERSION))}, "
                f"found {'.'.join(map(str, ver))}"
            )
        return ver

    # --------------------------------------------------------- repo queries
    def repo_root(self, cwd: Optional[str] = None) -> str:
        res = self.run(["rev-parse", "--show-toplevel"], cwd=cwd)
        return res.stdout.strip()

    def common_dir(self, cwd: Optional[str] = None) -> str:
        """Absolute path of the shared git dir (holds worktree admin metadata)."""
        res = self.run(["rev-parse", "--git-common-dir"], cwd=cwd)
        val = res.stdout.strip()
        if not os.path.isabs(val):
            val = os.path.abspath(os.path.join(cwd or self.cwd, val))
        return os.path.normpath(val)

    def current_branch(self, cwd: Optional[str] = None) -> Optional[str]:
        res = self.run(["symbolic-ref", "--short", "-q", "HEAD"], cwd=cwd, check=False)
        return res.stdout.strip() or None if res.returncode == 0 else None

    def head_sha(self, cwd: Optional[str] = None, short: bool = False) -> Optional[str]:
        args = ["rev-parse"]
        if short:
            args.append("--short")
        args.append("HEAD")
        res = self.run(args, cwd=cwd, check=False)
        return res.stdout.strip() or None if res.returncode == 0 else None

    def branch_exists(self, branch: str, cwd: Optional[str] = None) -> bool:
        return self.quiet_ok(["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=cwd)

    def remote_default_branch(self, remote: str = "origin", cwd: Optional[str] = None) -> Optional[str]:
        res = self.run(["symbolic-ref", f"refs/remotes/{remote}/HEAD"], cwd=cwd, check=False)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().split("/", 2)[-1]
        return None

    # ------------------------------------------------------------- worktree
    def worktree_add(
        self,
        path: str,
        branch: Optional[str] = None,
        base: Optional[str] = None,
        create_branch: bool = True,
        detach: bool = False,
        cwd: Optional[str] = None,
    ) -> CommandResult:
        args = ["worktree", "add"]
        if detach:
            args.append("--detach")
        elif branch and create_branch:
            args += ["-b", branch]
        args.append(os.path.abspath(path))
        if detach and base:
            args.append(base)
        elif not detach and not create_branch and branch:
            args.append(branch)  # checkout an existing branch
        elif base:
            args.append(base)
        return self.run(args, cwd=cwd)

    def worktree_remove(self, path: str, force: bool = False, cwd: Optional[str] = None) -> CommandResult:
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(os.path.abspath(path))
        return self.run(args, cwd=cwd)

    def worktree_prune(self, dry_run: bool = False, cwd: Optional[str] = None) -> CommandResult:
        args = ["worktree", "prune", "-v"]
        if dry_run:
            args.append("--dry-run")
        return self.run(args, cwd=cwd)

    @staticmethod
    def parse_worktree_porcelain(text: str) -> List[PorcelainWorktree]:
        """Parse ``git worktree list --porcelain`` output into records."""
        records: List[PorcelainWorktree] = []
        cur: Optional[PorcelainWorktree] = None
        for raw in text.splitlines():
            line = raw.rstrip("\n")
            if line.startswith("worktree "):
                if cur is not None:
                    records.append(cur)
                cur = PorcelainWorktree(path=line[len("worktree "):])
                continue
            if cur is None:
                continue
            if line.startswith("HEAD "):
                cur.head = line[5:].strip()
            elif line.startswith("branch "):
                ref = line[7:].strip()
                cur.branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
            elif line == "detached":
                cur.detached = True
            elif line == "bare":
                cur.bare = True
            elif line.startswith("locked"):
                cur.locked = line[len("locked"):].strip()
            elif line.startswith("prunable"):
                cur.prunable = line[len("prunable"):].strip()
        if cur is not None:
            records.append(cur)
        return records

    def worktree_list(self, cwd: Optional[str] = None) -> List[PorcelainWorktree]:
        res = self.run(["worktree", "list", "--porcelain"], cwd=cwd)
        return self.parse_worktree_porcelain(res.stdout)

    # -------------------------------------------------------------- status
    def status_porcelain(self, cwd: str) -> List[str]:
        res = self.run(["status", "--porcelain", "--untracked-files=all"], cwd=cwd, check=False)
        return [ln for ln in res.stdout.splitlines() if ln.strip()]

    def ahead_behind(self, cwd: str) -> Optional[tuple]:
        """Return (ahead, behind) vs upstream, or None when no upstream."""
        res = self.run(
            ["rev-list", "--left-right", "--count", "@{upstream}...HEAD"],
            cwd=cwd,
            check=False,
        )
        if res.returncode != 0:
            return None
        parts = res.stdout.split()
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    def last_commit(self, cwd: str) -> Optional[Dict[str, str]]:
        res = self.run(["log", "-1", "--format=%H%x1f%ct%x1f%s"], cwd=cwd, check=False)
        if res.returncode != 0 or not res.stdout.strip():
            return None
        fields = res.stdout.strip().split("\x1f")
        if len(fields) != 3:
            return None
        return {"sha": fields[0], "epoch": fields[1], "subject": fields[2]}

    def is_merged(self, branch: str, into: str, cwd: Optional[str] = None) -> bool:
        return self.quiet_ok(["merge-base", "--is-ancestor", branch, into], cwd=cwd)

    def delete_branch(self, branch: str, force: bool = False, cwd: Optional[str] = None) -> CommandResult:
        return self.run(["branch", "-D" if force else "-d", branch], cwd=cwd)

    def fetch_pr(self, number: int, branch: str, remote: str = "origin", cwd: Optional[str] = None) -> CommandResult:
        return self.run(["fetch", remote, f"pull/{number}/head:{branch}"], cwd=cwd)
