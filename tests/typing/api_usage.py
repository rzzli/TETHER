"""Static consumer contract; no execution occurs during type checking."""
from pathlib import Path
from tether.api import PolicyInputs, RunArtifacts, BundleArtifact, run_offline, verify_run, export_run, verify_bundle


def use_api(inputs: PolicyInputs, output: Path, bundle_output: Path, roots: tuple[Path, ...]) -> BundleArtifact:
    result: RunArtifacts = run_offline(inputs, output, source_roots=roots)
    verification: dict[str, object] = verify_run(result, source_roots=roots)
    assert verification["scientific_validation"] == "not_established"
    bundle: BundleArtifact = export_run(result, bundle_output, source_roots=roots)
    verify_bundle(bundle)
    return bundle
