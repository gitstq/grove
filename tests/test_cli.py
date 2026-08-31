import contextlib
import io
import json
import os
import tempfile
import unittest

from _repo import SRC, TempRepo  # noqa: F401
from grove.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def run_cli(self, *argv):
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = main(["-C", self.repo.path, *argv])
        return code, buf.getvalue(), err.getvalue()

    def test_add_list_json_where(self):
        code, _, _ = self.run_cli("add", "feat/cli", "-a", "codex-2")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("list", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        branches = [row["branch"] for row in data]
        self.assertIn("feat/cli", branches)
        code, out, _ = self.run_cli("where", "feat/cli")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isdir(out.strip()))

    def test_info_human(self):
        self.run_cli("add", "feat/info")
        code, out, _ = self.run_cli("info", "feat/info")
        self.assertEqual(code, 0)
        self.assertIn("feat/info", out)

    def test_port_is_int(self):
        code, out, _ = self.run_cli("port", "feat/web")
        self.assertEqual(code, 0)
        self.assertTrue(1024 <= int(out.strip()) <= 65535)

    def test_doctor(self):
        code, out, _ = self.run_cli("doctor", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(all(c["ok"] for c in json.loads(out)))

    def test_remove_via_cli(self):
        self.run_cli("add", "feat/gone")
        code, _, _ = self.run_cli("remove", "feat/gone", "-y")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("list", "--json")
        self.assertNotIn("feat/gone", [r["branch"] for r in json.loads(out)])

    def test_outside_repo_returns_git_exit_code(self):
        empty = tempfile.mkdtemp()
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            code = main(["-C", empty, "list"])
        self.assertEqual(code, 2)  # EXIT_GIT

    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
