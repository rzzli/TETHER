"""Maintained CLI primitives must not import research drivers."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

import tether
import tether_engine


class CoreDependencyTests(unittest.TestCase):
    def test_cli_cold_import_has_no_study_or_repository_dependency(self):
        roots = [str(Path(module.__file__).resolve().parent.parent)
                 for module in (tether_engine, tether)]
        code = (f'import sys; sys.path[:0] = {roots!r}\n'
                'import json, tether._cli, tether_engine.cli\n'
                'print(json.dumps(sorted(name for name in sys.modules '
                'if name.split(".")[0] in ("tools", "experiments") '
                'or name == "tether_engine.study" or name.startswith("tether_engine.study."))))')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code],
                                capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_catalog_utility_import_preserves_package_search_path(self):
        root = Path(__file__).resolve().parents[1]
        code = (f"import sys; sys.path.insert(0, {str(root)!r})\n"
                "before = list(sys.path)\n"
                "import tools.data.build_tether_policy\n"
                "assert sys.path == before, sys.path")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code],
                                capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compatibility_paths_share_one_implementation(self):
        from tether_engine import file_proofs, stable_read
        from tether_engine.study import proofs as old_proofs, stable_read as old_reads
        self.assertIs(old_proofs, file_proofs)
        self.assertIs(old_reads, stable_read)
        self.assertEqual(file_proofs._package_root(), Path(tether_engine.__file__).resolve().parent)

    def test_core_source_imports_do_not_point_back_to_study(self):
        for module in (tether_engine, tether):
            for path in Path(module.__file__).resolve().parent.glob('*.py'):
                with self.subTest(file=path.name):
                    tree = ast.parse(path.read_text(encoding='utf-8'))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            name = node.module or ''
                            self.assertFalse(name == 'tether_engine.study' or name.startswith('tether_engine.study.'))
                            self.assertFalse(node.level and (name == 'study' or name.startswith('study.')))
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                self.assertFalse(alias.name == 'tether_engine.study' or alias.name.startswith('tether_engine.study.'))
