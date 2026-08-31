"""Configuration discovery, validation and worktree path-template rendering.

Grove reads JSON only (no third-party TOML/YAML dependency). Lookup order,
later wins:

1. Built-in defaults
2. Global config: ``~/.config/grove/config.json``
   (``%APPDATA%\\grove\\config.json`` on Windows)
3. Repo config: ``<repo-root>/.groveconfig.json``
4. ``--config FILE`` explicit override
5. Environment variables prefixed ``GROVE_``
"""

from __future__ import annotations

import json
import os
import re
import string
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional

from .errors import GroveError

DEFAULT_PATH_TEMPLATE = "{parent}/{repo}.{slug}"
DEFAULT_PORT_BASE = 40000
DEFAULT_PORT_SPAN = 20000  # deterministic ports live in [base, base+span)
VALID_STRATEGIES = ("hardlink", "copy", "symlink", "reflink")
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SPACE = re.compile(r"\s+")
_DASH = re.compile(r"-{2,}")


def sanitize_slug(name: str, max_len: int = 80) -> str:
    """Turn an arbitrary branch/name into a cross-platform safe directory slug.

    Examples::

        feature/login -> feature-login
        feat: x?      -> feat-x
        a/b/c         -> a-b-c
    """
    if name is None:
        raise GroveError("cannot sanitize empty name")
    slug = str(name).strip()
    slug = slug.replace("/", "-").replace("\\", "-")
    slug = _UNSAFE.sub("-", slug)
    slug = _SPACE.sub("-", slug)
    slug = _DASH.sub("-", slug)
    slug = slug.strip(".-_ ")
    if not slug:
        raise GroveError(f"name {name!r} reduces to an empty slug after sanitizing")
    return slug[:max_len].rstrip(".-_ ") or "worktree"


def _global_config_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "grove", "config.json")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "grove", "config.json")


@dataclass
class Config:
    """Runtime configuration for a single repository."""

    path_template: str = DEFAULT_PATH_TEMPLATE
    port_base: int = DEFAULT_PORT_BASE
    port_span: int = DEFAULT_PORT_SPAN
    cache_strategy: str = "hardlink"  # hardlink|copy|symlink|reflink
    default_base: Optional[str] = None  # branch/commit used when creating worktrees
    auto_prune: bool = True
    include_main_in_foreach: bool = False
    extra: Dict[str, object] = field(default_factory=dict)

    def validate(self) -> "Config":
        if self.cache_strategy not in VALID_STRATEGIES:
            raise GroveError(
                f"cache_strategy must be one of {VALID_STRATEGIES}, got {self.cache_strategy!r}"
            )
        if not (1024 <= int(self.port_base) <= 65535):
            raise GroveError("port_base must be between 1024 and 65535")
        if not (1 <= int(self.port_span) <= 65535 - int(self.port_base)):
            raise GroveError("port_span does not fit inside the valid port range")
        if "{slug}" not in self.path_template and "{branch}" not in self.path_template:
            raise GroveError("path_template must contain {slug} or {branch} to stay unique")
        return self

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _read_json(path: str) -> Dict[str, object]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise GroveError(f"invalid JSON in config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GroveError(f"config {path} must contain a JSON object")
    return data


def _merge(cfg: Config, data: Dict[str, object]) -> Config:
    fields_ = set(Config.__dataclass_fields__)  # type: ignore[attr-defined]
    for key, val in data.items():
        if key in fields_:
            cur_type = type(getattr(cfg, key))
            if val is None:
                continue
            if isinstance(getattr(cfg, key), bool) or cur_type is bool:
                setattr(cfg, key, bool(val))
            elif isinstance(getattr(cfg, key), int) and not isinstance(getattr(cfg, key), bool):
                setattr(cfg, key, int(val))
            else:
                setattr(cfg, key, val)
        else:
            cfg.extra[key] = val
    return cfg


def load_config(
    repo_root: Optional[str] = None,
    explicit: Optional[str] = None,
    environ: Optional[Dict[str, str]] = None,
) -> Config:
    """Resolve the effective :class:`Config` for ``repo_root``."""
    cfg = Config()
    global_path = _global_config_path()
    if os.path.isfile(global_path):
        cfg = _merge(cfg, _read_json(global_path))
    if repo_root:
        repo_cfg = os.path.join(repo_root, ".groveconfig.json")
        if os.path.isfile(repo_cfg):
            cfg = _merge(cfg, _read_json(repo_cfg))
    if explicit:
        if not os.path.isfile(explicit):
            raise GroveError(f"config file not found: {explicit}")
        cfg = _merge(cfg, _read_json(explicit))
    env = environ if environ is not None else os.environ
    if env.get("GROVE_PATH_TEMPLATE"):
        cfg.path_template = env["GROVE_PATH_TEMPLATE"]
    if env.get("GROVE_CACHE_STRATEGY"):
        cfg.cache_strategy = env["GROVE_CACHE_STRATEGY"]
    if env.get("GROVE_PORT_BASE"):
        cfg.port_base = int(env["GROVE_PORT_BASE"])
    return cfg.validate()


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        raise GroveError(
            f"unknown path template variable {{{key}}}; "
            "available: {parent},{repo},{slug},{branch},{agent},{name}"
        )


def render_path_template(
    template: str,
    *,
    parent: str,
    repo: str,
    slug: str,
    branch: str,
    agent: str = "",
    name: Optional[str] = None,
) -> str:
    """Render a path template, returning a normalized absolute path."""
    fields = {
        "parent": parent,
        "repo": repo,
        "slug": slug,
        "branch": branch,
        "agent": sanitize_slug(agent) if agent else "",
        "name": sanitize_slug(name) if name else slug,
    }
    try:
        rendered = template.format_map(_SafeDict(**fields))
    except KeyError as exc:  # pragma: no cover - _SafeDict raises GroveError
        raise GroveError(str(exc)) from exc
    # An empty {agent} may leave cosmetic artifacts ("--", ".."); tidy them.
    rendered = re.sub(r"[-_]{2,}", "-", rendered)
    rendered = rendered.replace("/./", "/")
    if not os.path.isabs(rendered):
        rendered = os.path.join(parent, rendered)
    return os.path.normpath(rendered)
