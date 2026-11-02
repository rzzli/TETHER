"""Independent read-only inspection of the exact TETHER review ZIP.

Uses standard ZIP/RECORD/hash/metadata inspection, not the packet writer. Provider
originals, protected/human data, model inputs and runtime execution are excluded.
"""
from __future__ import annotations

import base64
from collections import Counter
import configparser
import csv
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ARCHIVE = ROOT / "data/derived/tether-review-20261102T045858Z/tether-review-0.4.0.zip"
REPEAT = ARCHIVE.with_name("tether-review-0.4.0-repeat.zip")
ZIP_SHA = "e57af7f4e99cf879f9944c83a19d2106f013935ff99f8681803124ed63443b8c"
MANIFEST_SHA = "667e3a19c366d8cabf178f0dbf74d8e53b74cd68d4f163f948b8a07778bfa904"
QUAL_SHA = "69ffeb1b4ac59dd2c5f4dee5afd2a3442d0adf9558fd0d2ba784a8f8e3dfbbdc"
P09_SHA = "f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e"
WHEEL_SHA = "26bb8059ac0eb1e1b9d6c965dedae2409f7d418fbdb48d13f0c524f8354c4ddf"
WHEEL_NAME = "software/tether_target_agents-0.4.0-py3-none-any.whl"
PYTHON_FILES = (
    "__init__.py", "__main__.py", "_aliases.py", "_cli.py", "_presentation.py",
    "archive/__init__.py", "archive/__main__.py", "study/__init__.py", "study/__main__.py",
    "study/authority_four_arm.py", "study/baseline_smoke.py", "study/fixed_evidence_smoke.py",
    "study/native_diagnostic.py", "study/retrieval_smoke.py",
)
PAPER_PINS = {
    "paper/manuscript.md": "99ee5893568d4734a393669a88e06920c882d65aa064e7f20a9ad689488e096f",
    "paper/supplement.md": "1f5c2073c7736d7a1b300c375bf84fb574d31df89ff57fa35b45feb60f80daa6",
    "paper/tether-source-reporting-preprint.pdf": "c5cd6d70d5d4c85a64baf82b59b98618b9714d52840217fe77790c5ce9d4b0b1",
    "paper/references.bib": "8804ee43da0da28b71773eb9a55ad0e7b78fb7d881e8b8423562473a2b87d05f",
    "paper/references.json": "d7cf590dd04f094c83931182517ec5d755e5309e87891e9b1c05c1fd70b5bed2",
    "paper/RELATED-WORK-SOURCE-AUDIT.md": "9561053ed65ebc756eaf4f1e0bfb6a09762fb8efb9877003584308f3ffe438ba",
    "paper/AUTHOR-DECLARATIONS.md": "e7622bc990b3d38c3a1f092d62b520e2b0ed1c558ec2168aacc6f040f16ee2cb",
}
LEGACY_PINS = {
    "reproduction/asof-research-artifact-0.1.0.zip": P09_SHA,
    "reproduction/README.md": "a4f95279ed1bf982a775a37e9c3e28f66d57886a6fb4ad9526f80d4b224fcc0d",
    "reproduction/RELEASE-RECORD.json": "a7382b2d50246247f6f98f18e672543d2f5b656fe3bdc4f4166382bbd9ffab13",
    "reproduction/qualification.json": "e166e3e8de8a138b0e4cbb6412a4e105850bd6b2a4e001eef419f77873e994ba",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise AssertionError("Duplicate JSON key")
            out[key] = value
        return out
    def invalid(text):
        raise AssertionError("Nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def main():
    from pypdf import PdfReader
    import tomllib
    checks = []
    def need(name, value):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise AssertionError(name)
    def safe_name(name):
        need("safe member " + name, bool(name) and not name.startswith("/") and "\\" not in name and ":" not in name and all(part not in ("", ".", "..") for part in name.split("/")))
    def public_text(name, text):
        path_pattern = r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|/Users/|/home/|(?<![A-Za-z0-9_.:/])/(?:tmp|private|var|mnt|media|etc)/|(?<!\\)\\\\[^\\/\s]+[\\/]"
        credential_pattern = r"(?i)[?&](?:access_token|token|signature|x-amz-signature|x-amz-credential)=|bearer\s+[A-Za-z0-9]|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:api_key|access_token|password|client_secret|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9+/_-]{12,}"
        need(name + " no private absolute root", re.search(path_pattern, text) is None)
        need(name + " no credential-like value", re.search(credential_pattern, text) is None)

    raw, repeat = ARCHIVE.read_bytes(), REPEAT.read_bytes()
    need("external whole ZIP byte pin", len(raw) == 21552273 and sha(raw) == ZIP_SHA)
    need("fresh-process repeat bytes identical", raw == repeat)
    archive = zipfile.ZipFile(io.BytesIO(raw))
    infos = archive.infolist()
    names = [x.filename for x in infos]
    need("72 unique sorted case-distinct members", len(names) == len(set(names)) == len({x.casefold() for x in names}) == 72 and names == sorted(names))
    need("no archive comment and valid CRCs", not archive.comment and archive.testzip() is None)
    need("exact stored physical byte closure", len(raw) == 22 + sum(76 + 2 * len(x.filename.encode()) + x.file_size for x in infos))
    members = {x.filename: archive.read(x) for x in infos}
    need("manifest external pin", sha(members["PACKET-MANIFEST.json"]) == MANIFEST_SHA)
    need("qualification external pin", sha(members["TETHER-QUALIFICATION.json"]) == QUAL_SHA)
    manifest = strict_json(members["PACKET-MANIFEST.json"])
    qualification = strict_json(members["TETHER-QUALIFICATION.json"])
    moment = datetime.fromisoformat(qualification["qualified_at_utc"])
    need("qualification freeze explicitly UTC", moment.tzinfo is not None and moment.utcoffset().total_seconds() == 0)
    timestamp = (moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second // 2 * 2)
    for info in infos:
        safe_name(info.filename)
        need("metadata " + info.filename, info.date_time == timestamp and info.compress_type == zipfile.ZIP_STORED and info.file_size == info.compress_size and not info.extra and not info.comment and info.create_system == 3 and info.create_version == info.extract_version == 20 and info.external_attr == (stat.S_IFREG | 0o644) << 16 and not info.flag_bits & 1)
    figure_names = {"paper/results/figures/" + prefix + suffix for prefix in ("figure1-flow", "figure2-availability", "figure3-controls") for suffix in ("-caption.md", "-data.json", "-preview.png", ".pdf", ".svg")}
    table_names = {"paper/results/tables/" + stem + suffix for stem in ("constructed_control_verdicts", "constructed_policy_summary", "decision_schedule", "native_case_results", "native_fact_accounting", "native_missingness", "native_operation_resources", "output_schedule", "paired_discordance", "paired_verdict_cells", "resource_phases") for suffix in (".csv", ".md")}
    result_names = figure_names | table_names | {"paper/results/README.md", "paper/results/ARTIFACTS.json"}
    source_names = {"software/source/packages/tether/src/tether/" + name for name in PYTHON_FILES}
    source_metadata = {"software/source/packages/tether/" + name for name in ("README.md", "LICENSE", "pyproject.toml", "uv.lock")}
    expected = set(PAPER_PINS) | set(LEGACY_PINS) | result_names | source_names | source_metadata | {WHEEL_NAME, "README.md", "TETHER-QUALIFICATION.json", "PACKET-MANIFEST.json"}
    need("independent exact allowlist closure", set(names) == expected and len(expected) == 72)
    need("manifest self-exclusion and closure", manifest["manifest_self_excluded"] is True and set(manifest["files"]) == expected - {"PACKET-MANIFEST.json"})
    for name, descriptor in manifest["files"].items():
        need("descriptor " + name, set(descriptor) == {"bytes", "sha256", "role"} and type(descriptor["bytes"]) is int and descriptor["bytes"] == len(members[name]) and descriptor["sha256"] == sha(members[name]) and type(descriptor["role"]) is str and bool(descriptor["role"]))
    expected_roles = {name: "working_draft_documentation" for name in PAPER_PINS}
    expected_roles["paper/AUTHOR-DECLARATIONS.md"] = "unfilled_owner_declaration_checklist"
    expected_roles.update({name: "aggregated_technical_results" for name in figure_names | table_names})
    expected_roles.update({name: "portable_presentation_metadata" for name in ("paper/results/README.md", "paper/results/ARTIFACTS.json")})
    expected_roles.update({name: "TETHER_project_source" for name in source_names | source_metadata})
    expected_roles.update({"README.md": "working_draft_reviewer_instructions", "TETHER-QUALIFICATION.json": "evaluation_only", WHEEL_NAME: "TETHER_software_wheel",
        "reproduction/asof-research-artifact-0.1.0.zip": "immutable_P09_reproduction_archive",
        "reproduction/README.md": "P09_reproduction_instructions", "reproduction/qualification.json": "evaluation_only",
        "reproduction/RELEASE-RECORD.json": "public_P09_release_hash_record"})
    need("independent role-map closure", set(expected_roles) == set(manifest["files"]))
    for name, role in expected_roles.items():
        need("approved semantic role " + name, manifest["files"][name]["role"] == role)
    for name, expected_sha in {**PAPER_PINS, **LEGACY_PINS}.items():
        need("prior independently pinned file " + name, sha(members[name]) == expected_sha)
    flags = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False, "publication_authorized": False, "owner_declarations": "deferred", "author_acceptance": "pending", "submission_ready": False, "public_deposit": None, "scientific_validation": "not_established", "study_independence": "not_established", "tether_version": "0.4.0", "compatibility_engine_version": "0.3.11"}
    for record_name, record in (("manifest", manifest), ("qualification", qualification)):
        for key, value in flags.items():
            need(record_name + " typed scope " + key, key in record and type(record[key]) is type(value) and record[key] == value)
    need("qualification method/status", qualification["method"] == "tether.review_packet_qualification.v1" and qualification["status"] == "PASS_LOCAL_TETHER_REVIEW_ARTIFACT")
    need("qualification top-level field allowlist", set(qualification) == set(flags) | {"method", "status", "payloads", "checks", "environment", "evidence", "new_model_calls", "new_provider_downloads", "provider_spending_usd", "qualified_at_utc", "scope_notes"})
    need("qualification payload closure", set(qualification["payloads"]) == expected - {"PACKET-MANIFEST.json", "TETHER-QUALIFICATION.json"})
    need("qualification descriptors equal manifest", all(value == manifest["files"][key] for key, value in qualification["payloads"].items()))
    need("no new calls/downloads/provider spending", all(type(qualification[k]) is int and qualification[k] == 0 for k in ("new_model_calls", "new_provider_downloads", "provider_spending_usd")))
    for key, counts in {"tether_full": (49, 49, 0), "tether_core": (49, 49, 0), "legacy_targeted_full": (115, 115, 0), "legacy_targeted_core": (115, 96, 19), "packet_helper": (12, 12, 0)}.items():
        row = qualification["checks"][key]
        need("terminal test counts " + key, all(type(row[k]) is int for k in ("tests_collected", "tests_executed", "approved_optional_skips", "errors", "failures")) and (row["tests_collected"], row["tests_executed"], row["approved_optional_skips"]) == counts and row["errors"] == row["failures"] == 0)
    log_sources = {"tether_full": "TETHER-TESTS-FULL.txt", "tether_core": "TETHER-TESTS-CORE.txt",
        "legacy_targeted_full": "LEGACY-TARGETED-FULL.txt", "legacy_targeted_core": "LEGACY-TARGETED-CORE.txt",
        "packet_helper": "PACKET-HELPER-TESTS-v1.txt"}
    for key, filename in log_sources.items():
        data = (HERE / filename).read_bytes()
        row = qualification["checks"][key]
        need("terminal test transcript hash " + key, sha(data) == row["sha256"])
        text = data.decode("utf-8-sig")
        runs = re.findall(r"Ran (\d+) tests? in [0-9.]+s", text)
        need("terminal test transcript count/status " + key, bool(runs) and int(runs[-1]) == row["tests_collected"] and re.search(r"\nOK(?:\s*\(skipped=\d+\))?\s*(?:\n|$)", text) is not None)
    evidence_sources = {"frontdoor_independent": "FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json",
        "installed_source_isolation": "ISOLATED-INSTALLED-QUALIFICATION.json", "paper_independent": "PAPER-RENAME-PEER-REVIEW.json",
        "preservation_and_visual": "PRESERVATION-AND-PAPER-QA.json", "wheel_independent": "WHEEL-PEER-REVIEW-v1.json"}
    for key, filename in evidence_sources.items():
        data = (HERE / filename).read_bytes()
        need("retained independent evidence " + key, sha(data) == qualification["evidence"][key]["sha256"] and strict_json(data)["status"] == qualification["evidence"][key]["status"])
    results = strict_json(members["paper/results/ARTIFACTS.json"])
    need("portable metadata independently pinned", sha(members["paper/results/ARTIFACTS.json"]) == "da802210539141fd7e25418d1440b1f749c3e5d16e6b62ddc7562db01cc11eb4")
    comparisons = results["historical_payload_comparisons"]
    need("exact 37 historical payload commitments", len(comparisons) == 37 and {"paper/results/" + x["path"] for x in comparisons} == figure_names | table_names)
    for row in comparisons:
        name = "paper/results/" + row["path"]
        need("historical result " + name, row["matches_historical"] is True and sha(members[name]) == row["sha256"] and len(members[name]) == row["bytes"])
    nested = zipfile.ZipFile(io.BytesIO(members["reproduction/asof-research-artifact-0.1.0.zip"]))
    need("315 immutable nested members and CRC", len(nested.namelist()) == 315 and nested.testzip() is None)
    nested_manifest = strict_json(nested.read("RELEASE-MANIFEST.json"))
    need("nested manifest pin and closure", sha(nested.read("RELEASE-MANIFEST.json")) == "30f9cca157eff20d250d89dbc91497290936e27d64fb5038754a813a6fc4c40e" and set(nested.namelist()) == set(nested_manifest["files"]) | {"RELEASE-MANIFEST.json"})
    for name, row in nested_manifest["files"].items():
        data = nested.read(name)
        need("immutable nested member " + name, len(data) == row["bytes"] and sha(data) == row["sha256"])
    need("nested source authority remains e284", nested_manifest["protocol_sha256"] == "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529")
    wheel_raw = members[WHEEL_NAME]
    need("new wheel external pin", sha(wheel_raw) == WHEEL_SHA)
    wheel = zipfile.ZipFile(io.BytesIO(wheel_raw))
    dist = "tether_target_agents-0.4.0.dist-info/"
    wheel_metadata = {dist + x for x in ("METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD", "licenses/LICENSE")}
    wheel_expected = {"tether/" + x for x in PYTHON_FILES} | wheel_metadata
    need("20-member exact wheel closure and CRC", len(wheel.namelist()) == 20 and set(wheel.namelist()) == wheel_expected and wheel.testzip() is None and not wheel.comment)
    for item in wheel.infolist():
        safe_name(item.filename)
        need("regular wheel member " + item.filename, stat.S_ISREG(item.external_attr >> 16) and not item.flag_bits & 1)
    records = list(csv.reader(io.StringIO(wheel.read(dist + "RECORD").decode())))
    need("wheel RECORD exact unique closure", len(records) == len(wheel_expected) and all(len(x) == 3 for x in records) and {x[0] for x in records} == wheel_expected)
    for name, digest, size in records:
        if name == dist + "RECORD":
            need("RECORD self row empty", digest == size == "")
        else:
            data = wheel.read(name)
            actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            need("RECORD proof " + name, digest == "sha256=" + actual and size == str(len(data)))
    for name in PYTHON_FILES:
        wheel_name = "tether/" + name
        packet_name = "software/source/packages/tether/src/" + wheel_name
        need("wheel/source byte projection " + name, wheel.read(wheel_name) == members[packet_name] and manifest["wheel_source_projection"][wheel_name] == sha(members[packet_name]))
        need("source workspace byte projection " + name, (ROOT / "packages/tether/src" / wheel_name).read_bytes() == members[packet_name])
    metadata = BytesParser().parsebytes(wheel.read(dist + "METADATA"))
    need("wheel identity and exact dependencies", metadata["Name"] == "tether-target-agents" and metadata["Version"] == "0.4.0" and metadata["Requires-Python"] == ">=3.11" and metadata.get_all("Requires-Dist") == ["asof-target-agents==0.3.11", 'pyarrow==21.0.0; extra == "ingest"'])
    entrypoints = configparser.ConfigParser()
    entrypoints.read_string(wheel.read(dist + "entry_points.txt").decode())
    need("one canonical tether entrypoint", entrypoints.sections() == ["console_scripts"] and dict(entrypoints["console_scripts"]) == {"tether": "tether._cli:main"})
    need("wheel only exports tether", wheel.read(dist + "top_level.txt").strip() == b"tether")
    need("wheel/source license exact", wheel.read(dist + "licenses/LICENSE") == members["software/source/packages/tether/LICENSE"])
    project = tomllib.loads(members["software/source/packages/tether/pyproject.toml"].decode())
    need("source project identity and relative core location", project["project"]["name"] == "tether-target-agents" and project["project"]["version"] == "0.4.0" and project["project"]["dependencies"] == ["asof-target-agents==0.3.11"] and project["tool"]["uv"]["sources"]["asof-target-agents"] == {"path": "../.."})
    readme = members["README.md"].decode()
    need("source instructions use fresh sibling work", "Join-Path (Split-Path -Parent $packet) 'tether-local-work'" in readme and "New-Item -ItemType Directory -Path $sourceWork -ErrorAction Stop" in readme and "@('pyproject.toml', 'uv.lock', 'LICENSE', 'src')" in readme and "source/core/$name" in readme and "packages/tether') -Recurse" in readme)
    need("offline install/build and explicit scope", all(x in readme for x in ("uv venv --offline", "uv pip install --offline --no-index --no-deps", "uv build --offline --build-constraints", "same outside-work tree", "not newly qualified scientific study results", "current hosted CI", "remain deferred")))
    local_links = []
    for name, data in members.items():
        if name.endswith((".md", ".json", ".toml", ".lock", ".py", ".bib")):
            text = data.decode("utf-8")
            public_text(name, text)
            if name.endswith(".json"):
                strict_json(data)
        if name.endswith(".md"):
            for match in re.finditer(r"!?\[[^\]\n]*\]\((?:<([^>\n]+)>|([^\)\n]+))\)", data.decode()):
                target = (match[1] or match[2]).strip()
                parsed = urlsplit(target)
                if parsed.scheme in ("http", "https") or not parsed.path:
                    continue
                need(name + " relative link scheme", not parsed.scheme and not parsed.netloc)
                logical = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                need(name + " resolved link " + target, logical in expected or any(x.startswith(logical.rstrip("/") + "/") for x in expected))
                local_links.append({"source": name, "target": logical})
    pdf = PdfReader(io.BytesIO(members["paper/tether-source-reporting-preprint.pdf"]))
    need("current branded reviewed PDF", len(pdf.pages) == 18 and pdf.metadata["/Title"].startswith("TETHER:") and pdf.metadata["/Author"] == "")
    public_text("current PDF metadata", json.dumps(dict(pdf.metadata)))
    need("owner deferral and old name explicitly retained", "previously named AsOf" in members["paper/manuscript.md"].decode() and "not ready for submission or publication" in members["paper/manuscript.md"].decode() and "unchanged" in readme and "Legacy filenames and identifiers" in readme)
    record_path = ROOT / "paper/release/tether/RELEASE-RECORD.json"
    record_raw = record_path.read_bytes()
    record = strict_json(record_raw)
    need("external record matches actual packet", record["archive"]["sha256"] == ZIP_SHA and record["archive"]["bytes"] == len(raw) and record["archive"]["members"] == 72 and record["archive"]["fresh_process_repeat_bytes_equal"] is True and record["manifest_sha256"] == MANIFEST_SHA and record["qualification_sha256"] == QUAL_SHA and record["tether_wheel_sha256"] == WHEEL_SHA)
    need("workspace qualification/readme match packet", (ROOT / "paper/release/tether/QUALIFICATION.json").read_bytes() == members["TETHER-QUALIFICATION.json"] and (ROOT / "paper/release/tether/README.md").read_bytes() == members["README.md"])
    need("packet remained read-only", sha(ARCHIVE.read_bytes()) == ZIP_SHA and ARCHIVE.read_bytes() == REPEAT.read_bytes())
    report = {"schema_version": 1, "method": "tether.independent_actual_packet_review.v1", "status": "PASS_ACTUAL_TETHER_REVIEW_PACKET",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "role": "evaluation_only", "agent_visible": False,
        "check_count": len(checks), "unresolved_findings": [], "archive_sha256": ZIP_SHA, "archive_bytes": len(raw), "members": 72,
        "fresh_process_repeat_bytes_equal": True, "manifest_sha256": MANIFEST_SHA, "qualification_sha256": QUAL_SHA,
        "external_record_sha256": sha(record_raw), "wheel_sha256": WHEEL_SHA,
        "closure": {"paper": 7, "results": 39, "historical_numerical_payloads": 37, "legacy_reproduction": 4,
            "new_python_sources": 14, "new_project_metadata": 4, "new_wheel": 1, "top_level": 3,
            "nested_legacy_members": 315, "wheel_members": 20},
        "resolved_markdown_links": local_links, "publication_authorized": False, "submission_ready": False,
        "owner_declarations": "deferred", "scientific_validation": "not_established", "new_model_calls": 0, "network_calls": 0,
        "external_provider_or_protected_or_human_originals_opened": 0,
        "scope": "ZIP/metadata/source/wheel/CRC/hash/link/permissions inspection only; no source-building/runtime/model/scientific execution. Previously allowed nested HGNC bytes hashed opaquely under the immutable P09 exception.",
        "source_build_instructions": "Layout/path and offline/fresh-worktree commands inspected; not executed in this independent packet review.",
        "check_count_scope": "Overlapping implementation and byte-consistency checks; not independent biomedical observations.",
        "script_sha256": sha(Path(__file__).read_bytes())}
    with (HERE / "PACKET-PEER-REVIEW.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    with (HERE / "PACKET-PEER-CHECKS.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump({"schema_version": 1, "status": "PASS", "checks": checks}, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "checks": len(checks), "members": 72, "links": len(local_links)}))


if __name__ == "__main__":
    main()
