"""Fixed P10 local working packet; no acquisition, rendering or study execution.

Only package() reads the real allowlisted inputs. self_test() uses invented
payloads and isolated temporary directories. The current repository README,
raw PDF build manifests, renderer, environments and private outputs are excluded.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.science import package_p09_release as safe

QUALIFICATION = {
    "schema_version": 1, "method": "p10.local_working_packet_qualification.v1",
    "status": "PASS_LOCAL_WORKING_DRAFT", "role": "evaluation_only", "agent_visible": False,
    "scientific_validation": "not_established", "study_independence": "not_established",
    "publication_authorized": False, "owner_declarations": "deferred", "public_deposit": None,
    "current_hosted_ci": "not_executed",
}
PAPER_SHA256 = {
    "paper/manuscript.md": "79a49c7bbaba7ad65786cc5e1bbfd872ae941396990b2d17315f685e4ca3b507",
    "paper/supplement.md": "d1a63bec471b13d44e888c4f40857d67d2cd13e504c2acef856659c3f5fabb85",
    "paper/references.bib": "8804ee43da0da28b71773eb9a55ad0e7b78fb7d881e8b8423562473a2b87d05f",
    "paper/references.json": "d7cf590dd04f094c83931182517ec5d755e5309e87891e9b1c05c1fd70b5bed2",
    "paper/RELATED-WORK-SOURCE-AUDIT.md": "e7adea0f9302389248627c969397827e9f8db3d224713577d3d4b655ad05422c",
    "paper/AUTHOR-DECLARATIONS.md": "e7622bc990b3d38c3a1f092d62b520e2b0ed1c558ec2168aacc6f040f16ee2cb",
    "paper/asof-source-reporting-preprint-v2.pdf": "c9778533984d2a04451c0f535b54704397977a13de1832dc4dfe9364d25d766d",
}
PDF_NAME = "paper/asof-source-reporting-preprint-v2.pdf"
P09_PROTOCOL = "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529"
P09_SOURCES = {
    "reproduction/asof-research-artifact-0.1.0.zip": (
        "data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip",
        "f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e", "immutable_P09_reproduction_archive"),
    "reproduction/qualification.json": ("paper/release/qualification.json",
        "e166e3e8de8a138b0e4cbb6412a4e105850bd6b2a4e001eef419f77873e994ba", "evaluation_only"),
    "reproduction/RELEASE-RECORD.json": ("paper/release/RELEASE-RECORD.json",
        "a7382b2d50246247f6f98f18e672543d2f5b656fe3bdc4f4166382bbd9ffab13", "public_P09_release_hash_record"),
    "reproduction/README.md": ("paper/release/PACKAGE-README.md",
        "a4f95279ed1bf982a775a37e9c3e28f66d57886a6fb4ad9526f80d4b224fcc0d", "P09_reproduction_instructions"),
}
P09_ZIP_NAME = "reproduction/asof-research-artifact-0.1.0.zip"
RESULTS_ROOT = ROOT / "data/cache/p09-portable-presentation-20261101T202322Z"
RESULTS_MANIFEST_SHA256 = "da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4"
MANIFEST_NAME = "PACKET-MANIFEST.json"
QUALIFICATION_FIELDS = set(QUALIFICATION) | {
    "frozen_at_utc", "paper_sha256", "pdf_sha256", "pdf_pages", "source_pdf_audit_sha256",
    "source_pdf_audit_status", "p09_archive_sha256", "p09_protocol_sha256", "portable_results_manifest_sha256",
    "source_pdf_audit_method", "source_pdf_audit_checks", "pdf_text_units", "pdf_vector_figures", "pdf_visual_status",
    "pdf_source_preservation_status", "scope_notes", "new_model_calls", "new_provider_downloads", "provider_spending_usd", "packet_purpose",
}


def _pinned(path, expected, maximum=safe.MAX_MEMBER):
    raw = safe._read(path, maximum)
    safe.need(safe.sha(raw) == expected, "Allowlisted source byte hash differs: " + Path(path).name)
    return raw


def _check_links(entries):
    """Resolve Markdown file links against this packet without network access."""
    names = set(entries) | {MANIFEST_NAME}
    for name, raw in entries.items():
        if not name.endswith(".md"):
            continue
        text = raw.decode("utf-8")
        for match in re.finditer(r"\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)", text):
            target = (match.group(1) or match.group(2)).strip()
            parsed = urlsplit(target)
            if parsed.scheme in ("http", "https"):
                continue
            safe.need(not parsed.scheme and not parsed.netloc, "Unsupported Markdown link scheme")
            if not parsed.path:
                continue
            path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
            safe._relative(path)
            safe.need(path in names or any(n.startswith(path.rstrip("/") + "/") for n in names),
                      "Markdown link is outside the packet: " + name + " -> " + path)


def _qualify(raw):
    value = safe._json(raw)
    safe.need(type(value) is dict and all(k in value and type(value[k]) is type(v) and value[k] == v
              for k, v in QUALIFICATION.items()), "P10 working-draft qualification contract differs")
    safe.need(set(value) <= QUALIFICATION_FIELDS, "Unallowlisted field in sanitized P10 qualification")
    safe._public(value)
    safe.need(all(type(value[k]) is int and value[k] == 0 for k in ("new_model_calls", "new_provider_downloads", "provider_spending_usd") if k in value),
              "Working packet must not claim new model/provider execution")
    safe.need(all(type(value[k]) is int and value[k] > 0 for k in ("source_pdf_audit_checks", "pdf_text_units") if k in value)
              and ("pdf_vector_figures" not in value or type(value["pdf_vector_figures"]) is int and value["pdf_vector_figures"] == 3)
              and all(value[k] == "passed" for k in ("pdf_visual_status", "pdf_source_preservation_status") if k in value),
              "Completed source/PDF check fields differ")
    safe.need("scope_notes" not in value or type(value["scope_notes"]) is list and all(type(v) is str for v in value["scope_notes"]),
              "Scope notes must be public strings")
    safe.need(value.get("paper_sha256") == PAPER_SHA256, "Qualification paper source bindings differ")
    safe.need(value.get("pdf_sha256") == PAPER_SHA256[PDF_NAME] and type(value.get("pdf_pages")) is int
              and value["pdf_pages"] == 18, "Qualification PDF binding/pages differ")
    safe.need(value.get("source_pdf_audit_status") == "passed" and type(value.get("source_pdf_audit_sha256")) is str
              and re.fullmatch(r"[0-9a-f]{64}", value["source_pdf_audit_sha256"]) is not None,
              "Completed independent source/PDF audit pin required")
    safe.need(value.get("p09_archive_sha256") == P09_SOURCES[P09_ZIP_NAME][1]
              and value.get("p09_protocol_sha256") == P09_PROTOCOL
              and value.get("portable_results_manifest_sha256") == RESULTS_MANIFEST_SHA256,
              "Qualification P09/results bindings differ")
    return value, safe._timestamp(value.get("frozen_at_utc"))


def package(readme, qualification, output):
    """Read fixed approved inputs, then exclusively write and verify one ZIP."""
    output, partial = safe._output_paths(output)
    protected = [RESULTS_ROOT.resolve(), (ROOT / P09_SOURCES[P09_ZIP_NAME][0]).parent.resolve(),
                 (ROOT / "data/cache/p09-runtime-bundle-20261101T213500Z").resolve()]
    safe.need(not any(output.is_relative_to(p) or partial.is_relative_to(p) for p in protected),
              "Packet output must stay outside immutable input trees")
    readme_raw = safe._read(readme, 4 * 1024**2)
    qualification_raw = safe._read(qualification, 4 * 1024**2)
    qualified, timestamp = _qualify(qualification_raw)
    readme_text = readme_raw.decode("utf-8")
    safe.need(bool(readme_text.strip()) and "\x00" not in readme_text, "Standalone reviewer README required")
    safe._public(readme_text)
    entries, records = {}, {}
    def add(name, raw, role):
        safe._relative(name)
        safe.need(name not in entries and name.casefold() not in {n.casefold() for n in entries}, "Duplicated packet member")
        safe.need(len(raw) <= safe.MAX_MEMBER, "Packet member exceeds bound")
        if name.endswith((".md", ".bib")):
            safe._public(raw.decode("utf-8"))
        elif name.endswith(".json"):
            safe._public(safe._json(raw))
        entries[name] = raw
        records[name] = dict(sha256=safe.sha(raw), bytes=len(raw), role=role)
    add("README.md", readme_raw, "working_draft_reviewer_instructions")
    add("P10-QUALIFICATION.json", qualification_raw, "evaluation_only")
    for name, digest in PAPER_SHA256.items():
        role = "unfilled_owner_declaration_checklist" if name.endswith("AUTHOR-DECLARATIONS.md") else "working_draft_documentation"
        add(name, _pinned(safe._source_path(ROOT, name), digest), role)
    result_root = RESULTS_ROOT.absolute()
    safe.need(result_root == result_root.resolve(strict=True) and result_root.is_dir(), "Unaliased portable result root required")
    manifest_raw = _pinned(safe._source_path(result_root, "ARTIFACTS.json"), RESULTS_MANIFEST_SHA256, 4 * 1024**2)
    result_manifest = safe._json(manifest_raw)
    outputs = result_manifest.get("tables_and_outputs")
    comparisons = result_manifest.get("historical_payload_comparisons")
    safe.need(result_manifest.get("status") == "PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION"
              and result_manifest.get("manifest_self_excluded") is True and type(outputs) is dict and len(outputs) == 38
              and type(comparisons) is list and len(comparisons) == 37, "Portable result manifest contract differs")
    historical = {item["path"]: item for item in comparisons}
    safe.need(len(historical) == 37 and set(historical) == set(outputs) - {"README.md"}, "All37 historical result commitments required")
    for name, proof in outputs.items():
        safe._relative(name)
        safe.need(proof.get("path") == name and type(proof.get("bytes")) is int and proof["bytes"] >= 0
                  and type(proof.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", proof["sha256"]),
                  "Portable result descriptor differs")
        raw = _pinned(safe._source_path(result_root, name), proof["sha256"])
        safe.need(len(raw) == proof["bytes"], "Portable result byte count differs")
        if name in historical:
            old = historical[name]
            safe.need(old.get("matches_historical") is True and old.get("sha256") == proof["sha256"]
                      and type(old.get("bytes")) is int and old["bytes"] == proof["bytes"], "Historical result comparison differs")
        add("paper/results/" + name, raw, "portable_presentation_metadata" if name == "README.md" else "aggregated_technical_results")
    add("paper/results/ARTIFACTS.json", manifest_raw, "portable_presentation_metadata")
    for name, (relative, digest, role) in P09_SOURCES.items():
        add(name, _pinned(safe._source_path(ROOT, relative), digest), role)
    safe.need(len(entries) == 52 and sum(map(len, entries.values())) <= safe.MAX_TOTAL, "Fixed packet count/size bound differs")
    _check_links(entries)
    manifest = dict(schema_version=1, method="p10.local_working_packet_manifest.v1", role="evaluation_only", agent_visible=False,
        status="LOCAL_WORKING_DRAFT_AUTHOR_FACTS_DEFERRED", publication_authorized=False, public_deposit=None,
        scientific_validation="not_established", study_independence="not_established", owner_declarations="deferred",
        frozen_at_utc=qualified["frozen_at_utc"], p09_protocol_sha256=P09_PROTOCOL,
        p09_archive_sha256=P09_SOURCES[P09_ZIP_NAME][1], p10_qualification_sha256=safe.sha(qualification_raw),
        independent_source_pdf_audit_sha256=qualified["source_pdf_audit_sha256"], pdf_pages=18,
        compression="ZIP_STORED", zip_timestamp_policy="UTC DOS floor to two-second precision; microseconds discarded",
        manifest_self_excluded=True, packager_sha256=safe.sha(Path(__file__).read_bytes()),
        shared_zip_helpers_sha256=safe.sha(Path(safe.__file__).read_bytes()), files=records)
    entries[MANIFEST_NAME] = safe._wire(manifest)
    try:
        with partial.open("xb") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
                for name in sorted(entries):
                    safe._write_member(archive, name, entries[name], timestamp)
            stream.flush(); os.fsync(stream.fileno())
        archive_raw = safe._verify_zip(partial, entries, timestamp)
        staging = safe._publish(partial, output)
        return dict(status="PACKAGED_LOCAL_WORKING_DRAFT_AND_READBACK_VERIFIED", archive_sha256=safe.sha(archive_raw),
            archive_bytes=len(archive_raw), members=len(entries), manifest_sha256=safe.sha(entries[MANIFEST_NAME]),
            p10_qualification_sha256=safe.sha(qualification_raw), p09_archive_sha256=P09_SOURCES[P09_ZIP_NAME][1],
            output=str(output), retained_staging_path=staging, publication_authorized=False, owner_declarations="deferred")
    except BaseException as error:
        if partial.exists():
            error.add_note("Partial working ZIP retained: " + str(partial))
        raise


def self_test():
    """Quick invented 53-member, repeat, tamper and no-clobber boundaries."""
    import tempfile
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix="p10-packet-fictional-", dir=ROOT / "data/cache") as temporary:
        base = Path(temporary); paper = {}; p09 = {}; result_root = base / "results"; result_root.mkdir()
        for name in PAPER_SHA256:
            target = base / name; target.parent.mkdir(parents=True, exist_ok=True)
            raw = b"{}\n" if name.endswith(".json") else b"Fictional bounded packet fixture.\n"
            if name == "paper/manuscript.md": raw = b"![Invented figure](results/figures/figure1-flow.pdf)\n"
            target.write_bytes(raw); paper[name] = safe.sha(raw)
        # Keep public packet names while redirecting each fixed source to fixtures.
        paper_sources = {name: (base / name).relative_to(ROOT).as_posix() for name in paper}
        for name, (_, _, role) in P09_SOURCES.items():
            target = base / name; target.parent.mkdir(parents=True, exist_ok=True)
            raw = b"{}\n" if name.endswith(".json") else b"Invented immutable archive/instructions.\n"
            target.write_bytes(raw); p09[name] = (target.relative_to(ROOT).as_posix(), safe.sha(raw), role)
        names = ["figures/figure1-flow.pdf", "figures/figure2-availability.pdf", "figures/figure3-controls.pdf"] + ["tables/invented-" + str(i) + ".csv" for i in range(34)]
        outputs = {}; historical = []
        for name in names + ["README.md"]:
            path = result_root / name; path.parent.mkdir(parents=True, exist_ok=True); raw = b"Invented result only.\n"; path.write_bytes(raw)
            outputs[name] = dict(path=name, sha256=safe.sha(raw), bytes=len(raw))
            if name != "README.md": historical.append(dict(outputs[name], matches_historical=True))
        rm = dict(status="PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION", manifest_self_excluded=True,
                  tables_and_outputs=outputs, historical_payload_comparisons=historical)
        rm_raw = safe._wire(rm); (result_root / "ARTIFACTS.json").write_bytes(rm_raw)
        q = {**QUALIFICATION, "paper_sha256": paper, "pdf_sha256": paper[PDF_NAME], "pdf_pages": 18,
             "source_pdf_audit_status": "passed", "source_pdf_audit_sha256": "a" * 64, "frozen_at_utc": "2026-11-01T23:55:03.123456+00:00",
             "p09_protocol_sha256": P09_PROTOCOL, "p09_archive_sha256": p09[P09_ZIP_NAME][1], "portable_results_manifest_sha256": safe.sha(rm_raw),
             "source_pdf_audit_checks": 30, "pdf_text_units": 273, "pdf_vector_figures": 3, "pdf_visual_status": "passed",
             "pdf_source_preservation_status": "passed", "scope_notes": ["Invented helper fixture; no actual source/PDF qualification."]}
        readme = base / "reviewer.md"; readme.write_bytes(b"# Invented reviewer packet\n[Paper](paper/manuscript.md)\n")
        qualification = base / "qual.json"; qualification.write_bytes(safe._wire(q))
        original_source_path = safe._source_path
        def fictional_source(root, relative):
            return original_source_path(ROOT, paper_sources[relative]) if root == ROOT and relative in paper_sources else original_source_path(root, relative)
        with patch.dict(globals(), PAPER_SHA256=paper, P09_SOURCES=p09, RESULTS_ROOT=result_root, RESULTS_MANIFEST_SHA256=safe.sha(rm_raw)), patch.object(safe, "_source_path", side_effect=fictional_source):
            first = package(readme, qualification, base / "first.zip"); second = package(readme, qualification, base / "second.zip")
            safe.need(first["archive_sha256"] == second["archive_sha256"] and first["members"] == 53, "Invented deterministic test failed")
            try: package(readme, qualification, base / "first.zip")
            except FileExistsError: pass
            else: raise AssertionError("Existing output was not rejected")
            safe.need(safe.sha((base / "first.zip").read_bytes()) == first["archive_sha256"], "Existing output changed")
            bad = base / "bad-qual.json"; bad.write_bytes(safe._wire(dict(q, owner_name="Invented excluded owner fact")))
            try: package(readme, bad, base / "bad-meta.zip")
            except ValueError: pass
            else: raise AssertionError("Unallowlisted owner metadata was accepted")
            safe.need(not (base / "bad-meta.zip").exists() and not (base / "bad-meta.zip.partial").exists(), "Rejected metadata wrote a ZIP")
            target = base / "paper/supplement.md"; target.write_bytes(b"Changed fixture")
            try: package(readme, qualification, base / "tamper.zip")
            except ValueError: pass
            else: raise AssertionError("Changed pinned source was accepted")
            safe.need(not (base / "tamper.zip").exists() and not (base / "tamper.zip.partial").exists(), "Tamper created partial publication")
    return dict(status="PASS_FICTIONAL_HELPER_BOUNDARIES", tests=5, actual_inputs_read=False, actual_packet_built=False,
                cases=["53-member closure/readback", "byte-identical repeat", "existing-output rejection", "unallowlisted owner metadata before ZIP creation", "pinned-source tamper before ZIP creation"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(package(args.readme, args.qualification, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
