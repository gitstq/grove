"""Grove — zero-dependency Git worktree orchestrator for parallel AI-agent workflows.

Public API:
    from grove import WorktreeManager, Config, GroveError, load_config

The package only depends on the Python standard library and a system ``git``
executable. It is safe to import on Windows, macOS and Linux.
"""

from .errors import GroveError, GitError, UserAbort, EXIT_OK, EXIT_GENERIC, EXIT_GIT, EXIT_ABORT
from .config import Config, load_config, sanitize_slug, render_path_template
from .core import WorktreeManager, Worktree, ForeachResult

__all__ = [
    "WorktreeManager",
    "Worktree",
    "ForeachResult",
    "Config",
    "load_config",
    "sanitize_slug",
    "render_path_template",
    "GroveError",
    "GitError",
    "UserAbort",
    "EXIT_OK",
    "EXIT_GENERIC",
    "EXIT_GIT",
    "EXIT_ABORT",
    "__version__",
]

__version__ = "1.0.0"
