"""Include invented new-method regressions in every public core/full CI gate."""
from pathlib import Path


def load_tests(loader, tests, pattern):
    root = Path(__file__).resolve().parents[1]
    return loader.discover(str(root / 'experiments/litqa_evidence_first'),
                            pattern='test_*.py', top_level_dir=str(root))
