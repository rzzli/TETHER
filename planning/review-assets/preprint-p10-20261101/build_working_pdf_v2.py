"""Use the unchanged reviewed renderer with explicit, separate P10 output paths.

Production study/source code and the retained P08 PDF/build are not overwritten.
The wrapper is part of the local presentation provenance, not a portable renderer.
"""
from pathlib import Path
import hashlib
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "tools/science/build_preprint_manuscript.py"
EXPECTED_RENDERER = "0d6044702a8e6f97de605f7f92acf140c337f7a3f19b1bf6a2c0abb0b432238f"
assert hashlib.sha256(RENDERER.read_bytes()).hexdigest() == EXPECTED_RENDERER
spec = importlib.util.spec_from_file_location("p10_pinned_renderer", RENDERER)
renderer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = renderer
spec.loader.exec_module(renderer)
renderer.OUTPUT = ROOT / "paper/asof-source-reporting-preprint-v2.pdf"
renderer.BUILD = ROOT / "paper/PDF-BUILD-v2.json"
original_publish = renderer.publish_document


def publish_to_versioned_paths(pdf, manifest, preview_root, **kwargs):
    # Original defaults were bound at definition. Override them explicitly;
    # preserve explicit test destinations used by the publication regressions.
    kwargs.setdefault("out_pdf", renderer.OUTPUT)
    kwargs.setdefault("out_build", renderer.BUILD)
    if "pdf" in manifest:
        manifest["presentation_revision"] = {
            "revision": 2, "phase": "P10",
            "wrapper_path": Path(__file__).relative_to(ROOT).as_posix(),
            "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "effective_overrides": {"OUTPUT": renderer.OUTPUT.relative_to(ROOT).as_posix(),
                "BUILD": renderer.BUILD.relative_to(ROOT).as_posix(),
                "publish_default_output_paths": "explicit versioned paths; test overrides preserved"},
            "source_delta_path": "planning/review-assets/preprint-p10-20261101/SOURCE-DELTA-v2.json",
            "source_delta_sha256": hashlib.sha256((Path(__file__).parent / "SOURCE-DELTA-v2.json").read_bytes()).hexdigest(),
            "prior_pdf_preserved": "paper/asof-source-reporting-preprint.pdf",
            "frozen_P09_inner_paper_modified": False,
        }
    return original_publish(pdf, manifest, preview_root, **kwargs)


renderer.publish_document = publish_to_versioned_paths
if __name__ == "__main__":
    renderer.main()
