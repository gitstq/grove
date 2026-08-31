"""Shared helpers: bootstrap src/ onto sys.path and build throwaway git repos."""

import os
import shutil
import stat
import subprocess
import sys
import tempfile

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def force_rmtree(path):
    """rmtree that also clears the read-only bit Git sets on object files.

    Plain shutil.rmtree raises PermissionError on Windows where Git pack/object
    files are read-only.
    """

    def on_error(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=on_error)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


class TempRepo:
    """Create a real, committed git repository in a temporary directory."""

    def __init__(self, name="main"):
        self.tmp = tempfile.mkdtemp(prefix="grove-test-")
        self.path = os.path.join(self.tmp, name)
        os.makedirs(self.path)
        git(["init", "-b", "main"], self.path)
        git(["config", "user.email", "grove@example.com"], self.path)
        git(["config", "user.name", "Grove Test"], self.path)
        git(["config", "commit.gpgsign", "false"], self.path)
        with open(os.path.join(self.path, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# demo\n")
        git(["add", "."], self.path)
        git(["commit", "-m", "chore: initial commit"], self.path)

    def write(self, rel, content="x"):
        p = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(rel) else None
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
        return p

    def cleanup(self):
        force_rmtree(self.tmp)
