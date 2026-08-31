import unittest

from _repo import SRC  # noqa: F401
from grove.git import Git

PORCELAIN = """worktree /repo/main
HEAD aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
branch refs/heads/main

worktree /repo/main.fix
HEAD bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
branch refs/heads/fix/one
locked reason text

worktree /tmp/ghost
HEAD cccccccccccccccccccccccccccccccccccccccc
detached
prunable gitdir file points to non-existent location

"""


class TestPorcelainParser(unittest.TestCase):
    def setUp(self):
        self.records = Git.parse_worktree_porcelain(PORCELAIN)

    def test_count(self):
        self.assertEqual(len(self.records), 3)

    def test_fields(self):
        main, fix, ghost = self.records
        self.assertEqual(main.branch, "main")
        self.assertFalse(main.detached)
        self.assertEqual(fix.branch, "fix/one")
        self.assertEqual(fix.locked, "reason text")
        self.assertTrue(ghost.detached)
        self.assertIsNone(ghost.branch)
        self.assertIn("non-existent", ghost.prunable)


class TestVersion(unittest.TestCase):
    def test_parse_version(self):
        g = Git()
        # Avoid relying on the host git; verify the parser directly.
        g.run = lambda *a, **k: type("R", (), {"stdout": "git version 2.34.1\n"})()
        self.assertEqual(g.version(), (2, 34, 1))


if __name__ == "__main__":
    unittest.main()
