"""High-level worktree orchestration — the heart of Grove.

:class:`WorktreeManager` turns the clunky ``git worktree`` porcelain into
branch-addressed, agent-friendly operations. Everything here is synchronous and
uses only the standard library.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence

from .config import Config, render_path_template, sanitize_slug
from .errors import GroveError, UserAbort
from .git import Git, PorcelainWorktree

META_FILENAME = "grove-meta.json"


# --------------------------------------------------------------------------- #
# Data containers
# --------------------------------------------------------------------------- #
@dataclass
class Worktree:
    path: str
    branch: Optional[str] = None
    head: Optional[str] = None
    detached: bool = False
    is_main: bool = False
    locked: Optional[str] = None
    prunable: Optional[str] = None
    dirty: bool = False
    changed: int = 0
    untracked: int = 0
    ahead: Optional[int] = None
    behind: Optional[int] = None
    last_sha: Optional[str] = None
    commit_epoch: Optional[int] = None
    subject: str = ""
    agent: str = ""
    name: str = ""

    @property
    def label(self) -> str:
        return self.branch if self.branch else "(detached)"

    @property
    def age(self) -> str:
        if self.commit_epoch is None:
            return "-"
        return humanize_age(self.commit_epoch)

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["label"] = self.label
        d["age"] = self.age
        return d


@dataclass
class ExecResult:
    name: str
    path: str
    branch: Optional[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ForeachResult:
    results: List[ExecResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failed(self) -> List[ExecResult]:
        return [r for r in self.results if not r.ok]

    def to_dict(self) -> Dict[str, object]:
        return {"ok": self.ok, "results": [r.to_dict() for r in self.results]}


def humanize_age(epoch: int, now: Optional[int] = None) -> str:
    now = now if now is not None else int(time.time())
    delta = max(0, now - int(epoch))
    if delta < 60:
        return f"{delta}s ago"
    minutes = delta // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    return f"{months // 12}y ago"


def fnv1a_32(data: str) -> int:
    h = 0x811C9DC5
    for b in data.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def canon(path: str) -> str:
    """Canonical path for equality across platforms.

    ``realpath`` resolves symlinks (e.g. macOS ``/var`` -> ``/private/var``);
    ``normcase`` neutralises Windows backslash/case differences so that a path
    reported by git and one we computed always compare equal.
    """
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


# --------------------------------------------------------------------------- #
# Manager
# --------------------------------------------------------------------------- #
class WorktreeManager:
    def __init__(
        self,
        cwd: Optional[str] = None,
        config: Optional[Config] = None,
        git: Optional[Git] = None,
        confirm: Optional[Callable[[str], bool]] = None,
    ):
        self.git = git or Git(cwd=cwd)
        self.root = canon(self.git.repo_root(cwd))
        self.common_dir = canon(self.git.common_dir(cwd=self.root))
        self.config = (config or Config()).validate()
        self._confirm = confirm or (lambda _msg: True)
        self._meta_path = os.path.join(self.common_dir, META_FILENAME)

    # =============================================================== meta
    def _load_meta(self) -> Dict[str, Dict[str, object]]:
        if not os.path.isfile(self._meta_path):
            return {}
        try:
            with open(self._meta_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_meta(self, meta: Dict[str, Dict[str, object]]) -> None:
        os.makedirs(self.common_dir, exist_ok=True)
        tmp = self._meta_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self._meta_path)

    def _set_meta(self, path: str, **values) -> None:
        meta = self._load_meta()
        key = canon(path)
        entry = meta.get(key, {})
        entry.update(values)
        meta[key] = entry
        self._save_meta(meta)

    def _drop_meta(self, path: str) -> None:
        meta = self._load_meta()
        key = canon(path)
        if key in meta:
            del meta[key]
            self._save_meta(meta)

    # ========================================================== templates
    def _plan_path(self, branch: str, agent: str = "", explicit: Optional[str] = None) -> str:
        if explicit:
            p = explicit if os.path.isabs(explicit) else os.path.join(self.root, explicit)
            return canon(p)
        return canon(render_path_template(
            self.config.path_template,
            parent=os.path.dirname(self.root),
            repo=os.path.basename(self.root),
            slug=sanitize_slug(branch),
            branch=branch,
            agent=agent,
        ))

    def deterministic_port(self, name: str) -> int:
        """Stable per-worktree TCP port for isolated dev servers."""
        cfg = self.config
        offset = fnv1a_32(f"grove::port::{name}") % cfg.port_span
        return cfg.port_base + offset

    # ============================================================== list
    def _enrich(self, pw: PorcelainWorktree, meta: Dict[str, Dict[str, object]]) -> Worktree:
        path = canon(pw.path)
        wt = Worktree(
            path=path,
            branch=pw.branch,
            head=pw.head,
            detached=pw.detached,
            is_main=path == self.root,
            locked=pw.locked,
            prunable=pw.prunable,
        )
        entry = meta.get(path, {})
        wt.agent = str(entry.get("agent", "") or "")
        wt.name = str(entry.get("name", "") or "")
        if os.path.isdir(wt.path) and not pw.prunable:
            status = self.git.status_porcelain(wt.path)
            wt.changed = len(status)
            wt.untracked = sum(1 for ln in status if ln.startswith("??"))
            wt.dirty = wt.changed > 0
            ab = self.git.ahead_behind(wt.path)
            if ab is not None:
                wt.behind, wt.ahead = ab
            last = self.git.last_commit(wt.path)
            if last:
                wt.last_sha = last["sha"][:8]
                try:
                    wt.commit_epoch = int(last["epoch"])
                except ValueError:
                    wt.commit_epoch = None
                wt.subject = last["subject"]
        return wt

    def list(self, enrich: bool = True) -> List[Worktree]:
        records = self.git.worktree_list(self.root)
        meta = self._load_meta()
        wts = [self._enrich(r, meta) for r in records] if enrich else [
            Worktree(
                path=canon(r.path),
                branch=r.branch,
                head=r.head,
                detached=r.detached,
                is_main=canon(r.path) == self.root,
                locked=r.locked,
                prunable=r.prunable,
            )
            for r in records
        ]
        # Main worktree first, then alphabetical by branch/path.
        wts.sort(key=lambda w: (not w.is_main, w.label.lower(), w.path.lower()))
        return wts

    def resolve(self, name_or_path: str) -> Worktree:
        """Resolve a branch name, stored name or path to a live worktree."""
        wts = self.list(enrich=False)
        target = canon(name_or_path) if os.path.sep in name_or_path or os.path.isabs(name_or_path) else None
        for wt in wts:
            if wt.branch == name_or_path or wt.name == name_or_path:
                return wt
            if target and canon(wt.path) == target:
                return wt
        # Slug / suffix match as a forgiving fallback.
        slug = sanitize_slug(name_or_path)
        for wt in wts:
            if wt.branch and sanitize_slug(wt.branch) == slug:
                return wt
            if os.path.basename(wt.path) == slug or os.path.basename(wt.path).endswith("." + slug):
                return wt
        raise GroveError(f"no live worktree matches {name_or_path!r}")

    def where(self, name_or_path: str) -> str:
        return self.resolve(name_or_path).path

    def info(self, name_or_path: str) -> Worktree:
        wt = self.resolve(name_or_path)
        records = self.git.worktree_list(self.root)
        match = next(
            (r for r in records if canon(r.path) == wt.path),
            None,
        )
        if match is None:  # pragma: no cover - defensive against races
            raise GroveError(f"worktree vanished before info: {wt.path}")
        return self._enrich(match, self._load_meta())

    # =============================================================== add
    def add(
        self,
        name: str,
        base: Optional[str] = None,
        agent: str = "",
        path: Optional[str] = None,
        detach: bool = False,
        create_branch: bool = True,
        dry_run: bool = False,
    ) -> Worktree:
        if not name or not str(name).strip():
            raise GroveError("worktree name must not be empty")
        branch = None if detach else str(name).strip()
        pr_number: Optional[int] = None
        if branch and branch.lower().startswith("pr:"):
            try:
                pr_number = int(branch.split(":", 1)[1])
            except ValueError as exc:
                raise GroveError("PR reference must look like pr:123") from exc
            branch = f"pr/{pr_number}"

        if branch is None:
            pseudo = sanitize_slug(base or "detached")
            target = self._plan_path(pseudo, agent, path)
        else:
            target = self._plan_path(branch, agent, path)

        if canon(target) == self.root:
            raise GroveError("target path collides with the main worktree")
        for existing in self.git.worktree_list(self.root):
            if canon(existing.path) == canon(target):
                raise GroveError(f"a worktree already exists at {target}")
        if os.path.exists(target) and os.listdir(target):
            raise GroveError(f"target directory exists and is not empty: {target}")

        exists = bool(branch) and self.git.branch_exists(branch, cwd=self.root)
        base = base or self.config.default_base
        plan = {
            "path": target,
            "branch": branch,
            "base": base,
            "create_branch": (not exists and create_branch and not detach),
            "detach": detach,
            "pr": pr_number,
        }
        if dry_run:
            plan["dry_run"] = True
            return plan  # type: ignore[return-value]

        os.makedirs(os.path.dirname(target), exist_ok=True)
        if pr_number is not None:
            if exists:
                # Refresh an existing PR checkout.
                self.git.run(["fetch", "origin", f"pull/{pr_number}/head"], cwd=self.root)
                self.git.run(["reset", "--hard", "FETCH_HEAD"], cwd=target)
            else:
                self.git.fetch_pr(pr_number, branch, cwd=self.root)
                self.git.worktree_add(target, branch=branch, create_branch=False, cwd=self.root)
        elif detach:
            self.git.worktree_add(target, detach=True, base=base, cwd=self.root)
        elif exists:
            self.git.worktree_add(target, branch=branch, create_branch=False, cwd=self.root)
        else:
            self.git.worktree_add(
                target, branch=branch, base=base,
                create_branch=create_branch, cwd=self.root,
            )

        self._set_meta(
            target,
            agent=agent,
            name=branch or os.path.basename(target),
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        return self.resolve(branch or target)

    # ============================================================ remove
    def remove(
        self,
        name_or_path: str,
        force: bool = False,
        delete_branch: bool = True,
        yes: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, object]:
        wt = self.resolve(name_or_path)
        if wt.is_main:
            raise GroveError("refusing to remove the main worktree")
        live = self.info(name_or_path)
        if live.dirty and not force:
            raise GroveError(
                f"worktree {live.label} has {live.changed} uncommitted change(s); "
                "re-run with --force to discard them"
            )
        if not yes and not self._confirm(f"Remove worktree at {wt.path}?"):
            raise UserAbort("user declined removal")
        plan = {
            "path": wt.path,
            "branch": wt.branch,
            "delete_branch": bool(delete_branch and wt.branch),
            "force": force,
        }
        if dry_run:
            plan["dry_run"] = True
            return plan
        self.git.worktree_remove(wt.path, force=force, cwd=self.root)
        deleted_branch = False
        if delete_branch and wt.branch:
            if self.git.branch_exists(wt.branch, cwd=self.root):
                self.git.delete_branch(wt.branch, force=force, cwd=self.root)
                deleted_branch = True
        self._drop_meta(wt.path)
        return {"removed": wt.path, "branch_deleted": deleted_branch, "branch": wt.branch}

    # ============================================================= prune
    def prune(self, dry_run: bool = False) -> Dict[str, object]:
        before = {canon(w.path) for w in self.list(enrich=False)}
        res = self.git.worktree_prune(dry_run=dry_run, cwd=self.root)
        after = {canon(w.path) for w in self.list(enrich=False)}
        dropped = sorted(before - after)
        # Clean meta entries whose directories vanished.
        meta = self._load_meta()
        stale_meta = [p for p in meta if not os.path.isdir(p)]
        if stale_meta and not dry_run:
            for p in stale_meta:
                meta.pop(p, None)
            self._save_meta(meta)
        return {
            "dry_run": dry_run,
            "git_output": res.stdout.strip(),
            "removed_worktrees": dropped,
            "stale_meta": stale_meta,
        }

    # ===================================================== exec / foreach
    def _exec_env(self, wt: Worktree) -> Dict[str, str]:
        env = dict(os.environ)
        env["GROVE_WORKTREE"] = wt.path
        env["GROVE_BRANCH"] = wt.branch or ""
        env["GROVE_REPO_ROOT"] = self.root
        return env

    def exec(self, name_or_path: str, cmd: Sequence[str]) -> ExecResult:
        import subprocess

        if not cmd:
            raise GroveError("exec requires a command")
        wt = self.resolve(name_or_path)
        proc = subprocess.run(
            list(cmd), cwd=wt.path, env=self._exec_env(wt),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return ExecResult(wt.label, wt.path, wt.branch, proc.returncode, proc.stdout, proc.stderr)

    def foreach(
        self,
        cmd: Sequence[str],
        parallel: bool = False,
        include_main: Optional[bool] = None,
        max_workers: Optional[int] = None,
    ) -> ForeachResult:
        import subprocess

        if not cmd:
            raise GroveError("foreach requires a command")
        if include_main is None:
            include_main = self.config.include_main_in_foreach
        targets = [w for w in self.list(enrich=False) if include_main or not w.is_main]
        if not targets:
            raise GroveError("no worktrees to run the command against")

        def run_one(wt: Worktree) -> ExecResult:
            proc = subprocess.run(
                list(cmd), cwd=wt.path, env=self._exec_env(wt),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            return ExecResult(wt.label, wt.path, wt.branch, proc.returncode, proc.stdout, proc.stderr)

        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers or min(8, len(targets))) as pool:
                results = list(pool.map(run_one, targets))
        else:
            results = [run_one(w) for w in targets]
        return ForeachResult(results)

    # ============================================================= share
    def share(
        self,
        name_or_path: str,
        relpaths: Sequence[str],
        strategy: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> List[Dict[str, object]]:
        """Reuse heavy build/cache directories from the main worktree.

        Strategies: ``hardlink`` (default, CoW-friendly, inode-efficient),
        ``copy`` (full independent copy), ``symlink`` (live shared dir),
        ``reflink`` (best-effort, falls back to hardlink then copy).
        """
        wt = self.resolve(name_or_path)
        strategy = strategy or self.config.cache_strategy
        if strategy not in ("hardlink", "copy", "symlink", "reflink"):
            raise GroveError(f"unknown cache strategy {strategy!r}")
        report = []
        for rel in relpaths:
            rel = rel.strip().strip("/\\")
            if not rel or rel.startswith("..") or os.path.isabs(rel):
                raise GroveError(f"cache path must be repo-relative, got {rel!r}")
            src = os.path.join(self.root, rel)
            dst = os.path.join(wt.path, rel)
            if not os.path.exists(src):
                raise GroveError(f"source cache does not exist in main worktree: {rel}")
            if os.path.exists(dst) or os.path.islink(dst):
                if not force:
                    raise GroveError(f"{rel} already exists in target worktree (use --force)")
                if os.path.islink(dst) or os.path.isfile(dst):
                    os.remove(dst)
                else:
                    shutil.rmtree(dst)
            plan_item = {"rel": rel, "source": src, "target": dst, "strategy": strategy}
            if dry_run:
                plan_item["dry_run"] = True
                report.append(plan_item)
                continue
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            used = self._materialize(src, dst, strategy)
            plan_item["used_strategy"] = used
            report.append(plan_item)
        return report

    @staticmethod
    def _materialize(src: str, dst: str, strategy: str) -> str:
        if strategy == "symlink":
            os.symlink(src, dst, target_is_directory=os.path.isdir(src))
            return "symlink"
        if strategy == "copy":
            shutil.copytree(src, dst, symlinks=False) if os.path.isdir(src) else shutil.copy2(src, dst)
            return "copy"
        # hardlink / reflink -> try a hardlink tree, gracefully downgrade per file.
        try:
            WorktreeManager._hardlink_tree(src, dst)
            return "hardlink"
        except OSError:
            shutil.copytree(src, dst, symlinks=False) if os.path.isdir(src) else shutil.copy2(src, dst)
            return "copy"

    @staticmethod
    def _hardlink_tree(src: str, dst: str) -> None:
        if os.path.isfile(src):
            os.link(src, dst)
            return
        os.makedirs(dst, exist_ok=True)
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            out_dir = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(out_dir, exist_ok=True)
            for d in dirs:
                os.makedirs(os.path.join(out_dir, d), exist_ok=True)
            for f in files:
                s = os.path.join(root, f)
                t = os.path.join(out_dir, f)
                if os.path.islink(s):  # preserve symlinks as symlinks
                    os.symlink(os.readlink(s), t)
                else:
                    try:
                        os.link(s, t)
                    except OSError:
                        shutil.copy2(s, t)

    # ============================================================ doctor
    def doctor(self) -> List[Dict[str, object]]:
        checks: List[Dict[str, object]] = []

        def add(name: str, ok: bool, detail: str):
            checks.append({"check": name, "ok": ok, "detail": detail})

        ver = self.git.version()
        add("git_version", ver >= Git.MIN_GIT_VERSION, "git " + ".".join(map(str, ver)))
        add("inside_repository", os.path.isdir(self.root), self.root)
        add("common_dir_writable", os.access(self.common_dir, os.W_OK), self.common_dir)
        try:
            self.config.validate()
            add("config_valid", True, self.config.path_template)
        except GroveError as exc:
            add("config_valid", False, str(exc))
        prunable = [w for w in self.git.worktree_list(self.root) if w.prunable]
        add("prunable_entries", not prunable, f"{len(prunable)} prunable")
        try:
            self._load_meta()
            add("meta_readable", True, self._meta_path)
        except Exception as exc:  # pragma: no cover - defensive
            add("meta_readable", False, str(exc))
        add("worktree_count", True, f"{len(self.git.worktree_list(self.root))} worktree(s)")
        return checks
