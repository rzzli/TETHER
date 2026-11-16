"""Data-only source controls, independent of private experiment code pins."""
from pathlib import Path
from unittest.mock import patch

from tools.science import run_source_validation_experiment as producer


def author_controls(workspace):
    """Keep real authoring/path checks with an explicitly fictional code identity.

    These controls test source admission and deterministic decisions. They do not
    qualify the historical producer's private code inventory or its experiment.
    The marker is hashed normally and is never imported or executed.
    """
    workspace = Path(workspace).resolve()
    marker = workspace / 'fictional-author-identity.py'
    marker.write_bytes(b'# Fictional identity for data-only unit controls.\n')
    root = workspace / 'data/cache/fixtures'
    with patch.object(producer, 'WORKSPACE', workspace), \
            patch.object(producer, 'code_paths', return_value=[marker]):
        producer.author_fictional_fixtures(root)
    return root
