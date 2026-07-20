from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_static_policy_module():
    script = ROOT / "scripts/static_policy_scan.py"
    spec = importlib.util.spec_from_file_location("static_policy_scan_for_test", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("static policy scan could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticPolicyTest(unittest.TestCase):
    def test_repository_local_virtual_environment_is_excluded(self) -> None:
        module = load_static_policy_module()
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "src"
            source.mkdir()
            virtual_environment = temporary / ".venv/site-packages/example"
            virtual_environment.mkdir(parents=True)
            (virtual_environment / "metadata.txt").write_text(
                "maintainer" + "@example.invalid\n" + "token" + " = 'dependency-owned-value'\n",
                encoding="utf-8",
            )
            (temporary / "README.md").write_text("Synthetic project content.\n", encoding="utf-8")

            module.ROOT = temporary
            module.SOURCE = source
            self.assertEqual(module.production_imports(), [])
            self.assertEqual(module.content_violations(), [])


if __name__ == "__main__":
    unittest.main()
