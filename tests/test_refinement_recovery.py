"""Run every invented recovery regression in the public core/full CI gates."""
from pathlib import Path


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1]
    suite = loader.discover(str(root/'experiments/litqa_refinement_recovery'),
                            pattern='test_*.py', top_level_dir=str(root))
    suite.addTests(loader.loadTestsFromName('experiments.litqa_analysis.test_bounded_reads'))
    return suite
