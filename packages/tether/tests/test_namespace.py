"""Compatibility identities and entrypoints for the TETHER public namespace."""
from __future__ import annotations

import importlib
from importlib import resources
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"


def subprocess_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


class NamespaceTests(unittest.TestCase):
    def test_public_and_engine_versions_are_separate(self):
        import tether
        import asof
        self.assertEqual(tether.__version__, "0.4.2")
        self.assertEqual(tether.__core_version__, "0.3.11")
        self.assertEqual(asof.__version__, "0.3.11")

    def test_import_orders_preserve_modules_classes_and_metadata(self):
        script = r'''
import importlib, sys
first, second = sys.argv[1:]
for suffix, symbol in [('contracts', 'Case'), ('study.source_fact_sources', 'VerifiedReference'), ('archive.paths', 'ArchiveResolver')]:
    module = importlib.import_module(first + '.' + suffix)
    original = (module.__spec__, module.__loader__, module.__package__, module.__file__)
    other = importlib.import_module(second + '.' + suffix)
    assert module is other
    assert getattr(module, symbol) is getattr(other, symbol)
    assert (module.__spec__, module.__loader__, module.__package__, module.__file__) == original
    assert getattr(module, symbol).__module__.startswith('asof.')
print('identity-and-metadata-pass')
'''
        for first, second in (("asof", "tether"), ("tether", "asof")):
            result = subprocess.run([sys.executable, "-B", "-c", script, first, second],
                env=subprocess_env(), capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("identity-and-metadata-pass", result.stdout)

    def test_nested_alias_monkeypatch_is_visible_in_engine(self):
        public = importlib.import_module("tether.study.source_fact_sources")
        legacy = importlib.import_module("asof.study.source_fact_sources")
        sentinel = object()
        with patch("tether.study.source_fact_sources._need", sentinel):
            self.assertIs(legacy._need, sentinel)

    def test_finite_inventory_covers_only_the_reviewed_engine_modules(self):
        import asof
        from tether._aliases import _LEGACY_MODULES
        root = Path(asof.__file__).parent
        modules = set()
        for file in root.rglob("*.py"):
            parts = file.relative_to(root).parts
            if file.name == "__init__.py":
                name = ".".join(parts[:-1])
            else:
                name = ".".join(file.relative_to(root).with_suffix("").parts)
            if name and name not in ("__main__", "study.__main__", "archive.__main__", "cli"):
                modules.add(name)
        self.assertEqual(modules, set(_LEGACY_MODULES) - {"demo", "demo.v2", "study.resources"})

    def test_resource_aliases_resolve_the_original_files(self):
        for suffix in ("study", "study.resources", "demo.v2"):
            public = resources.files("tether." + suffix)
            legacy = resources.files("asof." + suffix)
            self.assertEqual(sorted(x.name for x in public.iterdir()), sorted(x.name for x in legacy.iterdir()))
        name = "synthetic-orientation-v1.json"
        self.assertEqual(resources.files("tether.study.resources").joinpath(name).read_bytes(),
                         resources.files("asof.study.resources").joinpath(name).read_bytes())

    def test_serialization_and_fingerprint_match_original_objects(self):
        from tether.agents import Usage
        from tether.serde import encode, decode, fingerprint
        from asof.agents import Usage as LegacyUsage
        from asof.serde import fingerprint as legacy_fingerprint
        value = Usage(3, 4, 0.0)
        restored = decode(LegacyUsage, encode(value))
        self.assertIs(type(restored), Usage)
        self.assertEqual(restored, value)
        self.assertEqual(fingerprint(restored), legacy_fingerprint(value))

    def test_unapproved_names_fail_before_target_resolution(self):
        import tether
        from tether._aliases import _AliasFinder
        for name in ("tether.not_approved", "tether.study.not_approved", "tether.os", "tether.study.resources.not_approved"):
            with patch("tether._aliases.importlib.util.find_spec", side_effect=AssertionError("must not resolve an unknown target")):
                with self.assertRaises(ModuleNotFoundError) as captured:
                    _AliasFinder().find_spec(name)
                self.assertEqual(captured.exception.name, name)
        with self.assertRaises(AttributeError):
            getattr(tether, "not_approved")

    def test_plain_import_does_not_eagerly_load_optional_scientific_modules(self):
        script = "import sys,tether; assert 'pyarrow' not in sys.modules; assert 'asof.ingest' not in sys.modules; assert 'asof.study.native' not in sys.modules; print('lazy-pass')"
        result = subprocess.run([sys.executable, "-B", "-c", script], env=subprocess_env(),
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("lazy-pass", result.stdout)

    def test_installer_is_idempotent(self):
        import tether
        from tether._aliases import install
        before = sum(bool(getattr(x, "_tether_alias_finder", False)) for x in sys.meta_path)
        install()
        importlib.reload(tether)
        self.assertEqual(before, 1)
        self.assertEqual(sum(bool(getattr(x, "_tether_alias_finder", False)) for x in sys.meta_path), 1)

    def test_nested_main_normal_import_does_not_clobber_engine_parent(self):
        for suffix in ("study", "archive"):
            public = importlib.import_module("tether." + suffix + ".__main__")
            legacy = importlib.import_module("asof." + suffix + ".__main__")
            parent = importlib.import_module("asof." + suffix)
            self.assertIs(public, legacy)
            self.assertIs(parent.__main__, legacy)

    def test_subprocess_entrypoint_help_is_canonical_and_offline(self):
        for module in ("tether", "tether.study", "tether.archive"):
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, "-B", "-m", module, "--help"],
                    env=subprocess_env(), capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("tether", result.stdout.lower())
                self.assertNotIn("usage: asof", result.stdout.lower())
                self.assertNotIn("runtimewarning", result.stderr.lower())

    def test_bounded_advanced_entrypoints_offer_help_without_execution(self):
        for suffix in ("authority_four_arm", "baseline_smoke", "fixed_evidence_smoke", "native_diagnostic", "retrieval_smoke"):
            with self.subTest(module=suffix):
                module = "tether.study." + suffix
                result = subprocess.run([sys.executable, "-B", "-m", module, "--help"],
                    env=subprocess_env(), capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("usage:", result.stdout.lower())
                self.assertNotIn("runtimewarning", result.stderr.lower())
                self.assertIs(importlib.import_module(module), importlib.import_module("asof.study." + suffix))

    def test_canonical_cli_alias_is_the_public_front_door(self):
        public = importlib.import_module("tether.cli")
        front = importlib.import_module("tether._cli")
        self.assertIs(public, front)
        self.assertIs(public.main, front.main)


if __name__ == "__main__":
    unittest.main()
