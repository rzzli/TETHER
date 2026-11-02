"""Positive-allowlist TETHER review packet; no acquisition or study execution.

Only package() reads payload bodies. source_inventory() reads the pinned portable
manifest and source filenames so the external freezer can bind every member.
The nested legacy archive is copied as opaque, exactly pinned bytes.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys
import tomllib
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.science import package_p09_release as safe
from tools.science import p05_wheel_allowlist as wheel_safe

WHEEL_NAME = "tether_target_agents-0.4.0-py3-none-any.whl"
PDF_NAME = "paper/tether-source-reporting-preprint.pdf"
SOURCE_PREFIX = "software/source/packages/tether/"
QUAL_NAME = "TETHER-QUALIFICATION.json"
MANIFEST_NAME = "PACKET-MANIFEST.json"
P09_PROTOCOL = "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529"
P09_ARCHIVE_SHA256 = "f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e"
RESULTS_MANIFEST_SHA256 = "da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4"
PAPER_FILES = ("manuscript.md", "supplement.md", "references.bib", "references.json",
               "RELATED-WORK-SOURCE-AUDIT.md", "AUTHOR-DECLARATIONS.md")
LEGACY_FILES = {
    "reproduction/qualification.json": ("paper/release/qualification.json", "e166e3e8de8a138b0e4cbb6412a4e105850bd6b2a4e001eef419f77873e994ba", "evaluation_only"),
    "reproduction/RELEASE-RECORD.json": ("paper/release/RELEASE-RECORD.json", "a7382b2d50246247f6f98f18e672543d2f5b656fe3bdc4f4166382bbd9ffab13", "public_P09_release_hash_record"),
    "reproduction/README.md": ("paper/release/PACKAGE-README.md", "a4f95279ed1bf982a775a37e9c3e28f66d57886a6fb4ad9526f80d4b224fcc0d", "P09_reproduction_instructions"),
}
QUALIFICATION = dict(schema_version=1, method="tether.review_packet_qualification.v1",
    status="PASS_LOCAL_TETHER_REVIEW_ARTIFACT", role="evaluation_only", agent_visible=False,
    scientific_validation="not_established", study_independence="not_established",
    publication_authorized=False, owner_declarations="deferred", author_acceptance="pending",
    submission_ready=False, public_deposit=None, tether_version="0.4.0", compatibility_engine_version="0.3.11")
QUAL_FIELDS = set(QUALIFICATION) | {"qualified_at_utc", "payloads", "checks", "evidence", "environment", "scope_notes",
                                   "new_model_calls", "new_provider_downloads", "provider_spending_usd"}


def _root(path):
    path = Path(path).absolute()
    safe.need(path == path.resolve(strict=True) and path.is_dir(), "Unaliased workspace/input root required")
    return path


def _under(root, path):
    path = Path(path).absolute()
    safe.need(path.is_relative_to(root), "Explicit input must stay within the workspace")
    return safe._source_path(root, path.relative_to(root).as_posix())


def _pinned(path, expected, maximum=safe.MAX_MEMBER):
    raw = safe._read(path, maximum)
    safe.need(safe.sha(raw) == expected, "Pinned input bytes differ: " + Path(path).name)
    return raw


def _results(root):
    raw = _pinned(safe._source_path(root, "ARTIFACTS.json"), RESULTS_MANIFEST_SHA256, 4 * 1024**2)
    manifest = safe._json(raw)
    safe.need(type(manifest) is dict, "Portable result manifest must be an object")
    outputs, comparisons = manifest.get("tables_and_outputs"), manifest.get("historical_payload_comparisons")
    safe.need(manifest.get("status") == "PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION"
              and manifest.get("manifest_self_excluded") is True and type(outputs) is dict and len(outputs) == 38
              and type(comparisons) is list and len(comparisons) == 37, "Portable result inventory differs")
    historical = {v["path"]: v for v in comparisons}
    safe.need(len(historical) == 37 and set(historical) == set(outputs) - {"README.md"}, "Historical result closure differs")
    for name, record in outputs.items():
        safe._relative(name)
        safe.need(type(record) is dict and record.get("path") == name and type(record.get("bytes")) is int
                  and 0 <= record["bytes"] <= safe.MAX_MEMBER and type(record.get("sha256")) is str
                  and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]), "Result descriptor differs")
        if name in historical:
            old = historical[name]
            safe.need(old.get("matches_historical") is True and old.get("sha256") == record["sha256"]
                      and type(old.get("bytes")) is int and old["bytes"] == record["bytes"], "Historical result binding differs")
    return outputs


def source_inventory(workspace, results_root, wheel, legacy_zip):
    """Return ZIP name -> (physical source, fixed role), without reading payloads."""
    workspace, results_root = _root(workspace), _root(results_root)
    safe.need(results_root.is_relative_to(workspace), "Portable results must be inside the workspace")
    inventory = {"README.md": (safe._source_path(workspace, "paper/release/tether/README.md"), "working_draft_reviewer_instructions")}
    for name in PAPER_FILES:
        role = "unfilled_owner_declaration_checklist" if name == "AUTHOR-DECLARATIONS.md" else "working_draft_documentation"
        inventory["paper/" + name] = (safe._source_path(workspace, "paper/" + name), role)
    inventory[PDF_NAME] = (safe._source_path(workspace, PDF_NAME), "working_draft_documentation")
    for name in _results(results_root):
        inventory["paper/results/" + name] = (safe._source_path(results_root, name),
            "portable_presentation_metadata" if name == "README.md" else "aggregated_technical_results")
    inventory["paper/results/ARTIFACTS.json"] = (safe._source_path(results_root, "ARTIFACTS.json"), "portable_presentation_metadata")
    for name, (relative, _, role) in LEGACY_FILES.items():
        inventory[name] = (safe._source_path(workspace, relative), role)
    inventory["reproduction/asof-research-artifact-0.1.0.zip"] = (_under(workspace, legacy_zip), "immutable_P09_reproduction_archive")
    wheel = _under(workspace, wheel)
    safe.need(wheel.name == WHEEL_NAME, "TETHER wheel filename differs")
    inventory["software/" + WHEEL_NAME] = (wheel, "TETHER_software_wheel")
    project = safe._source_path(workspace, "packages/tether")
    for name in ("pyproject.toml", "uv.lock", "README.md", "LICENSE"):
        inventory[SOURCE_PREFIX + name] = (safe._source_path(project, name), "TETHER_project_source")
    code_root = safe._source_path(project, "src/tether")
    code_names = []
    for directory, children, files in os.walk(code_root, followlinks=False):
        children[:] = sorted(n for n in children if n not in ("__pycache__", "tests", "cache", ".pytest_cache"))
        for child in children:
            safe._source_path(code_root, (Path(directory) / child).relative_to(code_root).as_posix())
        for name in sorted(files):
            if name.endswith(".py"):
                relative = (Path(directory) / name).relative_to(project).as_posix()
                code_names.append(relative)
                inventory[SOURCE_PREFIX + relative] = (safe._source_path(project, relative), "TETHER_project_source")
    safe.need("src/tether/__init__.py" in code_names and "src/tether/_cli.py" in code_names, "Complete TETHER source is required")
    safe.need(len(inventory) == len({n.casefold() for n in inventory}), "Packet member aliases")
    for name in inventory:
        safe._relative(name)
    return inventory


def _qualification(raw):
    value = safe._json(raw)
    safe.need(type(value) is dict and all(k in value and type(value[k]) is type(v) and value[k] == v
              for k, v in QUALIFICATION.items()), "TETHER public qualification contract differs")
    safe.need(set(value) <= QUAL_FIELDS and {"payloads", "qualified_at_utc"} <= set(value), "Unallowlisted/missing qualification fields")
    safe._public(value)
    safe.need(type(value["payloads"]) is dict and value["payloads"], "Explicit payload allowlist required")
    for name, record in value["payloads"].items():
        safe._relative(name)
        safe.need(name not in (QUAL_NAME, MANIFEST_NAME) and type(record) is dict
                  and set(record) == {"sha256", "bytes", "role"} and type(record["bytes"]) is int
                  and 0 <= record["bytes"] <= safe.MAX_MEMBER and type(record["sha256"]) is str
                  and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) and type(record["role"]) is str,
                  "Qualification payload descriptor differs")
    safe.need(len(value["payloads"]) == len({n.casefold() for n in value["payloads"]}), "Qualification path aliases")
    safe.need(sum(v["bytes"] for v in value["payloads"].values()) <= safe.MAX_TOTAL, "Qualified payload total exceeds bound")
    for name in ("new_model_calls", "new_provider_downloads", "provider_spending_usd"):
        safe.need(name not in value or type(value[name]) is int and value[name] == 0, "New provider/model activity is not this packet")
    safe.need("scope_notes" not in value or type(value["scope_notes"]) is list
              and all(type(v) is str for v in value["scope_notes"]), "Scope notes must be strings")
    forbidden = {"raw_rows", "reference_facts", "expected_facts", "human_responses", "clinical_outcomes", "answers", "native_values", "model_outputs"}
    def inspect(item):
        if type(item) is dict:
            safe.need(not forbidden.intersection(item), "Answer/private payload field in public qualification")
            for child in item.values(): inspect(child)
        elif type(item) is list:
            for child in item: inspect(child)
    inspect(value)
    for name in ("checks", "evidence", "environment"):
        safe.need(name not in value or type(value[name]) is dict, "Qualification scoped metadata must be an object")
    return value, safe._timestamp(value["qualified_at_utc"])


def _source_contract(entries):
    value = tomllib.loads(entries[SOURCE_PREFIX + "pyproject.toml"].decode("utf-8"))
    project = value.get("project", {})
    safe.need(value.get("build-system") == {"requires": ["setuptools>=68"], "build-backend": "setuptools.build_meta"},
              "TETHER source build backend differs")
    safe.need(project.get("name") == "tether-target-agents" and project.get("version") == "0.4.0"
              and project.get("requires-python") == ">=3.11" and project.get("dependencies") == ["asof-target-agents==0.3.11"]
              and project.get("optional-dependencies") == {"ingest": ["pyarrow==21.0.0"]}
              and project.get("scripts") == {"tether": "tether._cli:main"}, "TETHER source packaging contract differs")
    sources = value.get("tool", {}).get("uv", {}).get("sources", {})
    safe.need(sources == {"asof-target-agents": {"path": "../.."}}, "TETHER source layout binding differs")
    safe.need(value.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find")
              == {"where": ["src"], "include": ["tether", "tether.*"]}, "Source wheel namespace closure differs")


def verify_tether_wheel(raw, sources, license_bytes):
    """Verify the whole new wheel and exact source projection; never import it."""
    info = "tether_target_agents-0.4.0.dist-info/"
    metadata_names = {info + n for n in ("METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD", "licenses/LICENSE")}
    expected = {"tether/" + name: payload for name, payload in sources.items()}
    required = set(expected) | metadata_names
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        names = [v.filename for v in members]
        safe.need(not archive.comment and len(names) == len(set(names)) == len({n.casefold() for n in names})
                  and set(names) == required, "Whole TETHER wheel allowlist differs")
        safe.need(len(raw) == 22 + sum(76 + 2 * len(member.filename.encode()) + member.compress_size for member in members),
                  "Whole TETHER wheel physical byte closure differs")
        offset = 0
        for member in sorted(members, key=lambda v: v.header_offset):
            safe.need(member.header_offset == offset and not member.flag_bits & 8, "Wheel local member layout differs")
            offset += 30 + len(member.filename.encode()) + member.compress_size
        safe.need(archive.start_dir == offset, "Wheel central directory offset differs")
        for member in members:
            wheel_safe._safe_name(member.filename)
            safe.need(not member.is_dir() and stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG)
                      and not member.flag_bits & 1 and not member.extra and not member.comment
                      and member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "Wheel member type/metadata differs")
            maximum = len(expected[member.filename]) if member.filename in expected else 4 * 1024**2
            safe.need(member.file_size <= maximum, "Wheel member exceeds its reviewed bound")
        payloads = {name: archive.read(name) for name in names}
    safe.need(all(payloads[n] == v for n, v in expected.items()), "Wheel/source Python bytes differ")
    safe.need(payloads[info + "licenses/LICENSE"] == license_bytes, "Wheel/source license differs")
    wheel_safe._headers(payloads[info + "METADATA"], {
        "Metadata-Version": "2.4", "Name": "tether-target-agents", "Version": "0.4.0",
        "Summary": "TETHER: auditable evidence-agent execution with a frozen compatibility engine",
        "License": license_bytes.decode("utf-8"), "Requires-Python": ">=3.11", "License-File": "LICENSE", "Dynamic": "license-file",
        "Requires-Dist": ("asof-target-agents==0.3.11", 'pyarrow==21.0.0; extra == "ingest"'), "Provides-Extra": ("ingest",),
    }, repeats=("Requires-Dist", "Provides-Extra"))
    wheel_safe._headers(payloads[info + "WHEEL"], {"Wheel-Version": "1.0", "Generator": "setuptools (84.0.0)", "Root-Is-Purelib": "true", "Tag": "py3-none-any"})
    safe.need(payloads[info + "entry_points.txt"] == b"[console_scripts]\ntether = tether._cli:main\n"
              and payloads[info + "top_level.txt"] == b"tether\n", "Wheel CLI/namespace differs")
    rows = list(csv.reader(io.StringIO(payloads[info + "RECORD"].decode("utf-8"), newline=""), strict=True))
    safe.need(all(len(row) == 3 for row in rows) and len(rows) == len(required)
              and {row[0] for row in rows} == required and len({row[0] for row in rows}) == len(rows), "Wheel RECORD closure differs")
    for name, recorded_hash, size in rows:
        if name == info + "RECORD":
            safe.need(recorded_hash == size == "", "Wheel RECORD self-entry differs")
        else:
            payload = payloads[name]
            expected_hash = "sha256=" + base64.urlsafe_b64encode(bytes.fromhex(safe.sha(payload))).rstrip(b"=").decode()
            safe.need(recorded_hash == expected_hash and size == str(len(payload)), "Wheel RECORD hash/size differs")
    return {name: safe.sha(payload) for name, payload in expected.items()}


def _links(entries):
    names = set(entries) | {MANIFEST_NAME}
    for name, raw in entries.items():
        if not name.endswith(".md"):
            continue
        for match in re.finditer(r"\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)", raw.decode("utf-8")):
            target = (match.group(1) or match.group(2)).strip()
            parsed = urlsplit(target)
            if parsed.scheme in ("http", "https"):
                continue
            safe.need(not parsed.scheme and not parsed.netloc, "Nonrelative Markdown file link")
            if parsed.path:
                path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                safe._relative(path)
                safe.need(path in names or any(n.startswith(path.rstrip("/") + "/") for n in names), "Packet Markdown link is missing: " + path)


def _output(workspace, output):
    output = Path(output).absolute()
    safe.need(output.suffix.lower() == ".zip", "ZIP output required")
    parent = output.parent.resolve(strict=True)
    safe.need(any(parent.is_relative_to((workspace / "data" / name).resolve()) for name in ("cache", "derived")),
              "Output stays in ignored workspace cache/derived")
    output = parent / output.name
    partial = output.with_name(output.name + ".partial")
    safe._absent(output)
    safe._absent(partial)
    return output, partial


def package(workspace, results_root, wheel, legacy_zip, qualification, qualification_sha256, output):
    """Validate all fixed inputs, write/read back once, then publish without replacement."""
    workspace, results_root = _root(workspace), _root(results_root)
    output, partial = _output(workspace, output)
    safe.need(type(qualification_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", qualification_sha256), "External qualification byte SHA required")
    qualification_raw = _pinned(_under(workspace, qualification), qualification_sha256, 4 * 1024**2)
    qualified, timestamp = _qualification(qualification_raw)
    inventory = source_inventory(workspace, results_root, wheel, legacy_zip)
    safe.need(set(qualified["payloads"]) == set(inventory), "Qualified payload/source member closure differs")
    protected = [results_root, Path(wheel).absolute().parent, Path(legacy_zip).absolute().parent]
    safe.need(not any(output.is_relative_to(p) or partial.is_relative_to(p) for p in protected), "Output is inside an immutable input tree")
    entries, records = {}, {}
    for name, (path, role) in sorted(inventory.items()):
        proof = qualified["payloads"][name]
        safe.need(proof["role"] == role, "Qualified payload role differs: " + name)
        raw = _pinned(path, proof["sha256"])
        safe.need(len(raw) == proof["bytes"], "Qualified payload byte count differs: " + name)
        entries[name] = raw
        records[name] = proof
    safe.need(entries["reproduction/asof-research-artifact-0.1.0.zip"] and safe.sha(entries["reproduction/asof-research-artifact-0.1.0.zip"]) == P09_ARCHIVE_SHA256,
              "Immutable legacy P09 archive differs")
    for name, (_, expected, _) in LEGACY_FILES.items():
        safe.need(safe.sha(entries[name]) == expected, "Immutable legacy P09 file differs: " + name)
    # The manifest bytes independently bind every historical result, not merely
    # the new qualification's account of the same payloads.
    for name, proof in _results(results_root).items():
        safe.need(safe.sha(entries["paper/results/" + name]) == proof["sha256"]
                  and len(entries["paper/results/" + name]) == proof["bytes"], "Historical/portable result bytes differ")
    safe.need(safe.sha(entries["paper/results/ARTIFACTS.json"]) == RESULTS_MANIFEST_SHA256, "Portable manifest changed during packaging")
    safe.need(entries[SOURCE_PREFIX + "LICENSE"] == safe._read(safe._source_path(workspace, "LICENSE")), "Project license copy differs")
    _source_contract(entries)
    sources = {name[len(SOURCE_PREFIX + "src/tether/"):]: raw for name, raw in entries.items()
               if name.startswith(SOURCE_PREFIX + "src/tether/")}
    wheel_projection = verify_tether_wheel(entries["software/" + WHEEL_NAME], sources, entries[SOURCE_PREFIX + "LICENSE"])
    readme = entries["README.md"].decode("utf-8")
    safe.need(readme.strip() and "\x00" not in readme, "Standalone public guide required")
    safe._public(readme)
    entries[QUAL_NAME] = qualification_raw
    records[QUAL_NAME] = dict(sha256=qualification_sha256, bytes=len(qualification_raw), role="evaluation_only")
    safe.need(sum(map(len, entries.values())) <= safe.MAX_TOTAL, "Packet total exceeds bound")
    _links(entries)
    manifest = dict(schema_version=1, method="tether.review_packet_manifest.v1", status="LOCAL_TETHER_REVIEW_ARTIFACT_AUTHOR_FACTS_DEFERRED",
        role="evaluation_only", agent_visible=False, scientific_validation="not_established", study_independence="not_established",
        publication_authorized=False, owner_declarations="deferred", author_acceptance="pending", submission_ready=False, public_deposit=None,
        qualified_at_utc=qualified["qualified_at_utc"], qualification_sha256=qualification_sha256, tether_version="0.4.0", compatibility_engine_version="0.3.11",
        p09_protocol_sha256=P09_PROTOCOL, p09_archive_sha256=P09_ARCHIVE_SHA256, portable_results_manifest_sha256=RESULTS_MANIFEST_SHA256,
        compression="ZIP_STORED", zip_timestamp_policy="UTC DOS floor to two-second precision; microseconds discarded",
        manifest_self_excluded=True, packager_sha256=safe.sha(safe._read(Path(__file__))),
        reused_helpers_sha256={"package_p09_release.py": safe.sha(safe._read(Path(safe.__file__))),
                              "p05_wheel_allowlist.py": safe.sha(safe._read(Path(wheel_safe.__file__)))},
        wheel_source_projection=wheel_projection, files=records)
    entries[MANIFEST_NAME] = safe._wire(manifest)
    safe.need(sum(map(len, entries.values())) <= safe.MAX_TOTAL, "Packet plus generated manifest exceeds bound")
    try:
        with partial.open("xb") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
                for name in sorted(entries):
                    safe._write_member(archive, name, entries[name], timestamp)
            stream.flush()
            os.fsync(stream.fileno())
        archive_raw = safe._verify_zip(partial, entries, timestamp)
        staging = safe._publish(partial, output)
        return dict(status="PACKAGED_LOCAL_TETHER_REVIEW_AND_READBACK_VERIFIED", archive_sha256=safe.sha(archive_raw),
                    archive_bytes=len(archive_raw), members=len(entries), manifest_sha256=safe.sha(entries[MANIFEST_NAME]),
                    qualification_sha256=qualification_sha256, output=str(output), retained_staging_path=staging,
                    publication_authorized=False, owner_declarations="deferred")
    except BaseException as error:
        if partial.exists():
            error.add_note("Partial TETHER ZIP retained for inspection: " + str(partial))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace-root", "results-root", "wheel", "legacy-zip", "qualification", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--qualification-sha256", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(package(args.workspace_root, args.results_root, args.wheel, args.legacy_zip,
                             args.qualification, args.qualification_sha256, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
