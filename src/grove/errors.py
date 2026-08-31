"""Typed errors and stable process exit codes for Grove.

Exit codes are part of the public contract so that AI agents and CI pipelines
can branch on them reliably:

* 0  success
* 1  generic Grove error (bad arguments, invalid state, unsafe operation)
* 2  underlying git command failed
* 3  user aborted a confirmation (or --yes was not given on a TTY-less run)
"""

EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_GIT = 2
EXIT_ABORT = 3


class GroveError(Exception):
    """Base class for every Grove-side failure."""


class GitError(GroveError):
    """Raised when an underlying ``git`` invocation fails.

    ``returncode`` carries git's exit status; ``stdout``/``stderr`` preserve the
    raw output for diagnostics and ``--json`` error reports.
    """

    def __init__(self, message, returncode=None, argv=None, stdout="", stderr=""):
        super().__init__(message)
        self.returncode = returncode
        self.argv = argv or []
        self.stdout = stdout
        self.stderr = stderr


class UserAbort(GroveError):
    """Raised when the user declines a destructive confirmation."""
