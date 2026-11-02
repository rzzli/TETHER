"""Prepare a fresh, allowlisted Q06 workspace; never render a PDF or build a ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.presentation import package_tether_review_v2 as packet

safe = packet.safe
REVISIONS = ROOT / "paper/revisions/20261102"
PORTABLE = ROOT / "data/cache/p09-portable-presentation-20261101T202322Z"
WHEEL = ROOT / "data/cache/tether-050-qualified-build/wheels/tether_target_agents-0.5.0-py3-none-any.whl"
WHEEL_SHA = "b28f2680c675b6266c6ea6cc9cfd2002191af9f7d20396b5b2ec629a9909f8d8"
LEGACY = ROOT / "data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip"
RENDERER = ROOT / "tools/presentation/build_tether_manuscript.py"
RENDERER_SHA = "07330d35414b61d78e4039c03d1ab31e5530f9949e5180d51af9f6f29ed1569b"
RENDERER_RESULTS_SHA = "84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428"
FIGURES = ("figure1-flow.pdf", "figure2-availability.pdf", "figure3-controls.pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-name", required=True)
    args = parser.parse_args()
    safe.need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.stage_name), "Safe fresh stage name required")
    stage = ROOT / "data/cache/tether-q06" / args.stage_name
    report = HERE / ("STAGE-PREPARATION-" + args.stage_name + ".json")
    safe._absent(stage)
    safe._absent(report)
    stage.mkdir(parents=True, exist_ok=False)
    copied, archive_inputs = [], {}

    def copy(source, relative, *, archive=None, role=None, expected=None, replacements=()):
        source = safe._source_path(ROOT, Path(source).relative_to(ROOT).as_posix())
        raw = safe._read(source)
        before = safe.sha(raw)
        if expected:
            safe.need(before == expected, "Pinned staging input differs: " + source.name)
        changed = raw
        changes = []
        for old, new in replacements:
            old_bytes, new_bytes = old.encode(), new.encode()
            count = changed.count(old_bytes)
            if count:
                changed = changed.replace(old_bytes, new_bytes)
                changes.append(dict(before=old, after=new, occurrences=count))
        destination = stage / relative
        safe.need(destination.resolve().is_relative_to(stage.resolve()), "Stage path escapes root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(changed)
        safe.need(safe.sha(safe._read(source)) == before and destination.read_bytes() == changed, "Input changed or copy readback differs")
        copied.append(dict(source=source.relative_to(ROOT).as_posix(), destination=relative, source_sha256=before,
                           staged_sha256=safe.sha(changed), source_bytes=len(raw), staged_bytes=len(changed), exact_link_transformations=changes))
        if archive:
            safe.need(archive not in archive_inputs, "Duplicate archive input")
            archive_inputs[archive] = dict(path=destination, role=role)

    document_changes = (("](../../results/", "](results/"),
                        ("](../../release/tether-v2/CURRENT-SOFTWARE.md)", "](../documentation/CURRENT-SOFTWARE.md)"),
                        ("](../../release/tether-v2/SOFTWARE-QUALIFICATION.json)", "](../documentation/SOFTWARE-QUALIFICATION.json)"))
    for name in packet.PAPER_FILES:
        source = REVISIONS / name if name in ("manuscript.md", "supplement.md") else ROOT / "paper" / name
        role = "unfilled_owner_declaration_checklist" if name == "AUTHOR-DECLARATIONS.md" else "working_draft_documentation"
        copy(source, "paper/" + name, archive="paper/" + name, role=role, replacements=document_changes if source.parent == REVISIONS else ())
    readme_changes = (("](../../revisions/20261102/manuscript.md)", "](paper/manuscript.md)"),
                      ("](../../revisions/20261102/supplement.md)", "](paper/supplement.md)"),
                      ("](CURRENT-SOFTWARE.md)", "](documentation/CURRENT-SOFTWARE.md)"),
                      ("](SOFTWARE-QUALIFICATION.json)", "](documentation/SOFTWARE-QUALIFICATION.json)"))
    copy(ROOT / "paper/release/tether-v2/README.md", "paper/release/tether-v2/README.md", archive="README.md", role="working_draft_reviewer_instructions", replacements=readme_changes)
    for archive, (source, role) in packet.EXTRA_DOCUMENTS.items():
        copy(ROOT / source, source, archive=archive, role=role, expected=packet.SOFTWARE_PROOF_SHA256 if archive == packet.SOFTWARE_PROOF_NAME else None)
    outputs = packet._results(PORTABLE)
    for name, descriptor in outputs.items():
        copy(PORTABLE / name, "inputs/portable-results/" + name, archive="paper/results/" + name,
             role="portable_presentation_metadata" if name == "README.md" else "aggregated_technical_results", expected=descriptor["sha256"])
    copy(PORTABLE / "ARTIFACTS.json", "inputs/portable-results/ARTIFACTS.json", archive="paper/results/ARTIFACTS.json", role="portable_presentation_metadata", expected=packet.RESULTS_MANIFEST_SHA256)
    for archive, (source, digest, role) in packet.LEGACY_FILES.items():
        copy(ROOT / source, source, archive=archive, role=role, expected=digest)
    copy(LEGACY, "inputs/legacy/" + LEGACY.name, archive="reproduction/" + LEGACY.name, role="immutable_P09_reproduction_archive", expected=packet.P09_ARCHIVE_SHA256)
    copy(WHEEL, "inputs/wheels/" + WHEEL.name, archive="software/" + WHEEL.name, role="TETHER_software_wheel", expected=WHEEL_SHA)
    project = ROOT / "packages/tether"
    for name in ("pyproject.toml", "uv.lock", "README.md", "LICENSE"):
        changes = (("](../../docs/TETHER-VERIFICATION-SCOPE.md)", "](../../../../documentation/CURRENT-SOFTWARE.md#verification-scope)"),) if name == "README.md" else ()
        copy(project / name, "packages/tether/" + name, archive=packet.SOURCE_PREFIX + name, role="TETHER_project_source", replacements=changes)
    source_files = sorted((project / "src/tether").rglob("*.py"))
    safe.need(all(not any(part in ("__pycache__", "tests", "cache", ".pytest_cache") for part in p.relative_to(project).parts) for p in source_files), "Unexpected Python source subtree")
    for source in source_files:
        relative = source.relative_to(project).as_posix()
        copy(source, "packages/tether/" + relative, archive=packet.SOURCE_PREFIX + relative, role="TETHER_project_source")
    copy(ROOT / "LICENSE", "LICENSE")
    copy(RENDERER, "tools/presentation/build_tether_manuscript.py", expected=RENDERER_SHA)
    copy(ROOT / "paper/results/ARTIFACTS.json", "paper/results/ARTIFACTS.json", expected=RENDERER_RESULTS_SHA)
    figure_manifest = json.loads((stage / "paper/results/ARTIFACTS.json").read_text(encoding="utf-8"))
    for name in FIGURES:
        descriptor = figure_manifest["tables_and_outputs"]["figures/" + name]
        safe.need(descriptor["vector"] is True, "Renderer figure must remain vector")
        copy(ROOT / "paper/results/figures" / name, "paper/results/figures/" + name, expected=descriptor["sha256"])
    # Check portable link closure against the planned packet; PDF and outer
    # qualification are explicit pending members, never fake files on disk.
    entries = {name: record["path"].read_bytes() for name, record in archive_inputs.items()}
    entries[packet.PDF_NAME] = b""
    entries[packet.QUAL_NAME] = b"{}"
    packet._links(entries)
    packet._software_proof(entries[packet.SOFTWARE_PROOF_NAME])
    safe._public(entries["README.md"].decode())
    safe._public(entries["documentation/CURRENT-SOFTWARE.md"].decode())
    for relative in ("tmp/pdfs", "data/derived", "data/cache"):
        (stage / relative).mkdir(parents=True, exist_ok=True)
    closure = {name: record["role"] for name, record in archive_inputs.items()}
    closure.update({packet.PDF_NAME: "working_draft_documentation", packet.QUAL_NAME: "evaluation_only", packet.MANIFEST_NAME: "self_excluded_packet_manifest"})
    result = dict(status="PREPARED_SOURCE_STAGE_PDF_AND_QUALIFICATION_PENDING", prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        stage_root=str(stage), preparation_script_sha256=safe.sha(Path(__file__).read_bytes()),
        packager_sha256=safe.sha(Path(packet.__file__).read_bytes()), formatter_sha256=RENDERER_SHA,
        copied_inputs=copied, expected_archive_closure=closure, expected_archive_members=len(closure), python_source_files=len(source_files),
        exact_link_closure_checked=True, pending=[packet.PDF_NAME, packet.QUAL_NAME, packet.MANIFEST_NAME],
        pdf_created=False, packet_created=False, source_backend_executed=False, original_sources_preserved_by_hash=True,
        old_pdf_or_review_zip_opened=False, nested_P09_handling="opaque exact byte copy under its historical allowlist")
    with report.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "stage_root", "expected_archive_members", "python_source_files", "pending")}, indent=2))


if __name__ == "__main__":
    main()
