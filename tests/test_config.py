import os
import tempfile
import unittest

from _repo import SRC  # noqa: F401  (bootstrap)
from grove.config import (
    Config,
    load_config,
    render_path_template,
    sanitize_slug,
)
from grove.errors import GroveError


class TestSanitize(unittest.TestCase):
    def test_slash_to_dash(self):
        self.assertEqual(sanitize_slug("feature/login"), "feature-login")

    def test_unsafe_windows_chars(self):
        self.assertEqual(sanitize_slug('feat: x?<>|*'), "feat-x")

    def test_nested_branch(self):
        self.assertEqual(sanitize_slug("release/1.2/hotfix"), "release-1.2-hotfix")

    def test_empty_rejected(self):
        with self.assertRaises(GroveError):
            sanitize_slug("///")


class TestTemplate(unittest.TestCase):
    def test_default_template(self):
        p = render_path_template(
            "{parent}/{repo}.{slug}",
            parent="/work/demo", repo="demo", slug="feat-x", branch="feat/x",
        )
        self.assertEqual(p, os.path.normpath("/work/demo/demo.feat-x"))

    def test_agent_variable_and_tidy(self):
        p = render_path_template(
            "{parent}/{repo}-{agent}-{slug}",
            parent="/w", repo="r", slug="s", branch="s", agent="bot1",
        )
        self.assertTrue(p.endswith("r-bot1-s"))

    def test_unknown_variable_rejected(self):
        with self.assertRaises(GroveError):
            render_path_template("{nope}", parent=".", repo="r", slug="s", branch="s")

    def test_preserves_underscores_in_parent(self):
        # Regression: a tidy regex once collapsed "-_" inside real paths.
        p = render_path_template(
            "{parent}/{repo}.{slug}",
            parent="/tmp/grove-test-_o7zymzs", repo="main", slug="feat-x", branch="feat/x",
        )
        self.assertEqual(
            p, os.path.normpath("/tmp/grove-test-_o7zymzs/main.feat-x")
        )


class TestConfig(unittest.TestCase):
    def test_invalid_strategy(self):
        with self.assertRaises(GroveError):
            Config(cache_strategy="magic").validate()

    def test_merge_repo_and_env(self):
        d = tempfile.mkdtemp()
        global_dir = os.path.join(d, "global")
        repo_dir = os.path.join(d, "repo")
        os.makedirs(global_dir)
        os.makedirs(repo_dir)
        with open(os.path.join(global_dir, "config.json"), "w") as fh:
            fh.write('{"port_base": 41000, "cache_strategy": "copy"}')
        with open(os.path.join(repo_dir, ".groveconfig.json"), "w") as fh:
            fh.write('{"port_base": 42000}')
        # Point the global loader at our temp global file.
        import grove.config as gc
        orig = gc._global_config_path
        gc._global_config_path = lambda: os.path.join(global_dir, "config.json")
        try:
            cfg = load_config(repo_root=repo_dir, environ={})
        finally:
            gc._global_config_path = orig
        self.assertEqual(cfg.port_base, 42000)  # repo overrides global
        self.assertEqual(cfg.cache_strategy, "copy")  # inherited from global


if __name__ == "__main__":
    unittest.main()
