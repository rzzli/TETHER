"""Separate current-policy recovery checks from frozen engine-0.4 integrations."""
from collections import Counter
import ast
from pathlib import Path
import unittest


LEGACY_INTEGRATION_CLASSES = {
    'experiments.litqa_refinement_recovery.test_original.OriginalTests': 9,
    'experiments.litqa_refinement_recovery.test_reconstruct.ReconstructionIntegrationTests': 4,
    'experiments.litqa_refinement_recovery.test_run_integration.RecoveryNativeIntegrationTests': 2,
    'experiments.litqa_refinement_recovery.test_run_integration.CompleteRecoveryControllerTests': 1,
}


def _flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _flatten(test)
        else:
            yield test


def _partition(suite):
    current, legacy = [], []
    for test in _flatten(suite):
        kind = type(test).__module__ + '.' + type(test).__qualname__
        (legacy if kind in LEGACY_INTEGRATION_CLASSES else current).append(test)
    counts = Counter(type(test).__module__ + '.' + type(test).__qualname__ for test in legacy)
    if counts != LEGACY_INTEGRATION_CLASSES:
        raise AssertionError('Frozen recovery integration inventory changed; review its explicit suite boundary')
    ids = [test.id() for test in (*current, *legacy)]
    if len(ids) != len(set(ids)):
        raise AssertionError('Duplicate recovery tests across compatibility groups')
    return current, legacy


def _recovery_suite(loader):
    root = Path(__file__).resolve().parents[1]
    suite = loader.discover(str(root/'experiments/litqa_refinement_recovery'),
                            pattern='test_*.py', top_level_dir=str(root))
    suite.addTests(loader.loadTestsFromName('experiments.litqa_analysis.test_bounded_reads'))
    return suite


def legacy_suite():
    """Select original methods; execution requires their matching old source/runtime."""
    _, legacy = _partition(_recovery_suite(unittest.TestLoader()))
    return unittest.TestSuite(legacy)


def legacy_test_inventory():
    """List preserved declarations without importing historical driver dependencies."""
    root = Path(__file__).resolve().parents[1]
    result = []
    for identity, count in LEGACY_INTEGRATION_CLASSES.items():
        module, _, owner = identity.rpartition('.')
        source = root.joinpath(*module.split('.')).with_suffix('.py')
        classes = [node for node in ast.parse(source.read_text(encoding='utf-8')).body
                   if isinstance(node, ast.ClassDef) and node.name == owner]
        if len(classes) != 1 or [ast.unparse(base) for base in classes[0].bases] != ['unittest.TestCase']:
            raise AssertionError('Frozen recovery integration inventory changed; review class declarations')
        methods = [node.name for node in classes[0].body
                   if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')]
        if len(methods) != count or len(set(methods)) != count:
            raise AssertionError('Frozen recovery integration inventory changed; review method declarations')
        result.extend(identity+'.'+name for name in methods)
    return sorted(result)


def load_tests(loader, tests, pattern):
    current, _ = _partition(_recovery_suite(loader))
    suite = unittest.TestSuite(current)
    suite.addTests(loader.loadTestsFromName('tests.refinement_recovery_policy'))
    return suite
