import ast
import os
import unittest

from _helpers import ROOT_DIR


FORBIDDEN = (
    "machine",
    "network",
    "st7565",
    "calsci_keypad",
    "data_modules",
    "process_modules",
    "input_modules",
)


class ImportGuardTests(unittest.TestCase):
    def test_non_adapter_modules_do_not_import_device_or_legacy_modules(self):
        violations = []
        for dirpath, _, filenames in os.walk(ROOT_DIR):
            if "/adapters" in dirpath or "/tests" in dirpath or "__pycache__" in dirpath:
                continue
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, "r") as handle:
                    tree = ast.parse(handle.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._check_name(path, alias.name, violations)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        self._check_name(path, node.module, violations)

        self.assertEqual(violations, [])

    def _check_name(self, path, name, violations):
        for forbidden in FORBIDDEN:
            if name == forbidden or name.startswith(forbidden + "."):
                violations.append((os.path.relpath(path, ROOT_DIR), name))


if __name__ == "__main__":
    unittest.main()
