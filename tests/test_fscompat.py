import os
import tempfile
import unittest

from core.fscompat import dirname, ensure_dir, exists, is_dir, root_dir_from_file


class FsCompatTests(unittest.TestCase):
    def test_dir_helpers_handle_posix_paths(self):
        self.assertEqual(dirname("/a/b/c.py"), "/a/b")
        self.assertEqual(dirname("/a/b/"), "/a")
        self.assertEqual(dirname("core/bootstrap.py"), "core")
        self.assertEqual(root_dir_from_file("/root/project/core/bootstrap.py", levels=2), "/root/project")

    def test_ensure_dir_creates_nested_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "alpha", "beta")
            ensure_dir(nested)
            self.assertTrue(exists(nested))
            self.assertTrue(is_dir(nested))


if __name__ == "__main__":
    unittest.main()
