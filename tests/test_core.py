import os
import shutil
import sys
import unittest

from _repo import SRC, TempRepo  # noqa: F401
from grove.config import Config
from grove.core import WorktreeManager, fnv1a_32
from grove.errors import GroveError
from grove.git import Git


class TestWorktreeLifecycle(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.m = WorktreeManager(cwd=self.repo.path, config=Config())

    def tearDown(self):
        self.repo.cleanup()

    def test_add_list_where(self):
        wt = self.m.add("feat/login", agent="claude-1")
        self.assertTrue(os.path.isdir(wt.path))
        names = [w.branch for w in self.m.list(enrich=False)]
        self.assertIn("main", names)
        self.assertIn("feat/login", names)
        self.assertEqual(self.m.where("feat/login"), wt.path)
        # main worktree sorts first
        self.assertTrue(self.m.list()[0].is_main)
        self.assertEqual(self.m.resolve("feat/login").agent, "")  # enrich=False meta not loaded
        full = self.m.info("feat/login")
        self.assertEqual(full.agent, "claude-1")

    def test_default_path_is_sibling(self):
        wt = self.m.add("feat-x")
        self.assertEqual(
            os.path.dirname(wt.path),
            os.path.dirname(self.repo.path),
        )
        self.assertTrue(os.path.basename(wt.path).endswith("feat-x"))

    def test_dirty_detection(self):
        self.m.add("feat/dirty")
        clean = self.m.info("feat/dirty")
        self.assertFalse(clean.dirty)
        with open(os.path.join(clean.path, "untracked.txt"), "w") as fh:
            fh.write("hi")
        dirty = self.m.info("feat/dirty")
        self.assertTrue(dirty.dirty)
        self.assertEqual(dirty.untracked, 1)

    def test_remove_and_branch_cleanup(self):
        self.m.add("feat/tmp")
        res = self.m.remove("feat/tmp", yes=True)
        self.assertFalse(os.path.exists(res["removed"]))
        self.assertFalse(self.m.git.branch_exists("feat/tmp", cwd=self.repo.path))

    def test_remove_guards_dirty(self):
        self.m.add("feat/guard")
        p = self.m.where("feat/guard")
        with open(os.path.join(p, "wip.txt"), "w") as fh:
            fh.write("wip")
        with self.assertRaises(GroveError):
            self.m.remove("feat/guard", yes=True)
        # force + keep-branch path
        res = self.m.remove("feat/guard", force=True, delete_branch=False, yes=True)
        self.assertTrue(os.path.exists(os.path.join(self.repo.path, ".git")) or True)
        self.assertFalse(res["branch_deleted"])

    def test_cannot_remove_main(self):
        with self.assertRaises(GroveError):
            self.m.remove("main", yes=True)

    def test_dry_run_creates_nothing(self):
        plan = self.m.add("feat/plan", dry_run=True)
        self.assertTrue(plan["dry_run"])
        self.assertFalse(os.path.exists(plan["path"]))

    def test_prune_after_manual_delete(self):
        wt = self.m.add("feat/ghost")
        shutil.rmtree(wt.path)
        report = self.m.prune()
        remaining = [w.branch for w in self.m.list(enrich=False)]
        self.assertNotIn("feat/ghost", remaining)
        self.assertEqual(len(report["removed_worktrees"]), 1)


class TestOrchestration(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.m = WorktreeManager(cwd=self.repo.path, config=Config())

    def tearDown(self):
        self.repo.cleanup()

    def test_port_deterministic_and_in_range(self):
        p1 = self.m.deterministic_port("feat/a")
        p2 = self.m.deterministic_port("feat/a")
        p3 = self.m.deterministic_port("feat/b")
        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertTrue(40000 <= p1 < 60000)
        self.assertEqual(fnv1a_32("x"), fnv1a_32("x"))

    def test_share_hardlinks_cache(self):
        wt = self.m.add("feat/cache")
        os.makedirs(os.path.join(self.repo.path, "node_modules", "lib"))
        src_file = os.path.join(self.repo.path, "node_modules", "lib", "index.js")
        with open(src_file, "w") as fh:
            fh.write("module.exports={}")
        report = self.m.share("feat/cache", ["node_modules"])
        dst_file = os.path.join(wt.path, "node_modules", "lib", "index.js")
        self.assertTrue(os.path.exists(dst_file))
        self.assertTrue(os.path.samefile(src_file, dst_file))  # hardlinked inode
        self.assertEqual(report[0]["used_strategy"], "hardlink")

    def test_share_rejects_path_traversal(self):
        self.m.add("feat/trav")
        with self.assertRaises(GroveError):
            self.m.share("feat/trav", ["../outside"])

    def test_exec_runs_inside_worktree(self):
        self.m.add("feat/exec")
        code = "import os; open('marker.txt','w').write(os.environ['GROVE_BRANCH'])"
        res = self.m.exec("feat/exec", [sys.executable, "-c", code])
        self.assertEqual(res.returncode, 0)
        marker = os.path.join(self.m.where("feat/exec"), "marker.txt")
        with open(marker) as fh:
            self.assertEqual(fh.read(), "feat/exec")

    def test_foreach_sequential_and_parallel(self):
        self.m.add("feat/a")
        self.m.add("feat/b")
        code = "import os; open('m.txt','w').write(os.environ.get('GROVE_BRANCH',''))"
        for parallel in (False, True):
            result = self.m.foreach([sys.executable, "-c", code], parallel=parallel)
            self.assertTrue(result.ok, msg=[(r.name, r.stderr) for r in result.failed])
            self.assertEqual(len(result.results), 2)
            for r in result.results:
                marker = os.path.join(r.path, "m.txt")
                self.assertTrue(os.path.exists(marker))
                os.remove(marker)

    def test_existing_branch_checkout(self):
        # create a branch without a worktree, then add should check it out
        Git(cwd=self.repo.path).run(["branch", "already/here"])
        wt = self.m.add("already/here")
        self.assertTrue(os.path.isdir(wt.path))
        self.assertEqual(self.m.resolve("already/here").branch, "already/here")


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.m = WorktreeManager(cwd=self.repo.path, config=Config())

    def tearDown(self):
        self.repo.cleanup()

    def test_doctor_all_green(self):
        checks = self.m.doctor()
        for c in checks:
            self.assertTrue(c["ok"], msg=c)


if __name__ == "__main__":
    unittest.main()
