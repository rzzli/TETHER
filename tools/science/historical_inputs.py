"""Qualify nonclinical OT24.09 identifier projections, never clinical outcomes.

Raw parents remain quarantined: molecules contain clinical fields that are never
read by the projection. A release notice supplies a conservative calendar-day
availability bound, not a publication date for every underlying annotation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from tether_engine.serde import ContractError, parse_json, sha256_file

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/24.09/"
NOTICE = "https://community.opentargets.org/t/24-09-platform-release-now-live/1556.json"
ORIGIN = "2025-01-01T00:00:00Z"
PROJECTIONS = {
    "targets": ("id", "approvedSymbol", "approvedName", "synonyms", "symbolSynonyms", "nameSynonyms", "obsoleteSymbols", "obsoleteNames", "dbXrefs"),
    "diseases": ("id", "name", "synonyms", "dbXRefs", "obsoleteTerms"),
    "molecule": ("id", "name", "synonyms", "tradeNames", "crossReferences", "parentId", "childChemblIds", "drugType"),
    "mechanismOfAction": ("chemblIds", "targetName", "targetType", "mechanismOfAction", "actionType", "targets", "references"),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save_new(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False); stream.write("\n")


def project(row, product):
    if product not in PROJECTIONS:
        raise ContractError("Unapproved historical product")
    return {field: row.get(field) for field in PROJECTIONS[product]}


def integrity_map(payload):
    """Parse the publisher's sha1sum format and reject conflicting identities."""
    result = {}
    for line in payload.splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{40})\s+\*?(.+)", line.strip())
        if not match:
            raise ContractError("Malformed publisher SHA-1 manifest")
        digest, path = match.groups(); path = path.removeprefix("./")
        if path.startswith(("/", "\\")) or ".." in Path(path).parts or "\\" in path or ":" in path:
            raise ContractError("Unsafe publisher path")
        if path in result and result[path] != digest.lower():
            raise ContractError("Conflicting publisher file identity")
        result[path] = digest.lower()
    return result


def verify_manifest(manifest_path, *, audit_original_rows=False, expected_manifest_sha256=None):
    """Verify the complete transitive file closure, without reading any outcome.

    JSON is parsed from the same UTF-8 bytes whose digest is checked. Every returned
    ancestor pin is checked again before return. Callers can retain those pins and
    independently check them immediately before and after their dependent operation.
    Original-row decoding is optional; closure verification needs no pyarrow.
    """
    manifest_path = Path(manifest_path).resolve()
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_manifest_sha256 is not None and manifest_sha256 != expected_manifest_sha256:
        raise ContractError("Historical manifest checksum mismatch")
    manifest = parse_json(manifest_bytes)
    pins = {}

    def pin(path, digest, size, role):
        key = str(Path(path).resolve())
        entry = {"path": key, "sha256": digest, "bytes": size, "role": role}
        if key in pins and (pins[key]["sha256"], pins[key]["bytes"]) != (digest, size):
            raise ContractError("Conflicting ancestor pins")
        pins[key] = entry

    def checked_bytes(path, expected_digest, role, expected_size=None):
        payload = Path(path).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected_digest or (expected_size is not None and len(payload) != expected_size):
            raise ContractError("Historical ancestor changed: " + role)
        pin(path, digest, len(payload), role)
        return payload

    pin(manifest_path, manifest_sha256, len(manifest_bytes), "historical_manifest")
    if (manifest["release_id"] != "24.09" or manifest["origin_at"] != ORIGIN
            or manifest["future_fallback"] or manifest["clinical_outcome_queries"] != 0):
        raise ContractError("Historical boundary changed")
    dates = [datetime.fromisoformat(manifest[k].replace("Z", "+00:00")) for k in ("available_by", "origin_at")]
    if any(value.tzinfo is None for value in dates) or dates[0] >= dates[1]:
        raise ContractError("Input not available before origin")
    files = manifest["metadata"] + manifest["files"]
    retained_notice = None
    for item in files:
        path, receipt_path = Path(item["path"]), Path(item["receipt_path"])
        role = "historical_raw_metadata" if item in manifest["metadata"] else "historical_raw_data"
        raw_bytes = checked_bytes(path, item["sha256"], role, item["bytes"])
        receipt = parse_json(checked_bytes(receipt_path, item["receipt_sha256"], "historical_receipt"))
        if receipt["sha256"] != item["sha256"] or receipt["source_url"] != item["source_url"]:
            raise ContractError("Receipt identity mismatch")
        if receipt.get("bytes", item["bytes"]) != item["bytes"]:
            raise ContractError("Receipt size mismatch")
        if item.get("publisher_sha1"):
            if hashlib.sha1(raw_bytes).hexdigest() != item["publisher_sha1"]:
                raise ContractError("Publisher integrity changed")
        if item["source_url"] == NOTICE:
            if retained_notice is not None:
                raise ContractError("Duplicate official release notice")
            retained_notice = parse_json(raw_bytes)
    if retained_notice is not None:
        recomputed_available_by = availability(retained_notice)
        availability_basis = "retained_official_release_notice"
    else:
        fixture = manifest.get("availability_source", {})
        if (fixture.get("kind") != "test_fixture" or not files
                or any(item["source_url"] != "fixture" for item in files)):
            raise ContractError("Historical availability requires the retained official notice")
        recomputed_available_by = fixture.get("available_by")
        availability_basis = "explicit_test_fixture"
    if manifest["available_by"] != recomputed_available_by:
        raise ContractError("Historical availability differs from retained source")
    parents = {item["sha256"] for item in manifest["files"]}
    original_by_hash = {item["sha256"]: Path(item["path"]) for item in manifest["files"]}
    checked_rows = 0
    if len(manifest["products"]) != len(PROJECTIONS) or {p["product"] for p in manifest["products"]} != set(PROJECTIONS):
        raise ContractError("Projection products missing or unexpected")
    for product in manifest["products"]:
        path = Path(product["path"])
        parse_json(checked_bytes(product["schema_path"], product["schema_sha256"], "historical_schema"))
        if set(product["approved_columns"]) != set(PROJECTIONS[product["product"]]):
            raise ContractError("Projection column boundary changed")
        count = 0
        cached_key, cached_rows = None, None
        projection_hash, projection_bytes = hashlib.sha256(), 0
        with path.open("rb") as stream:
            for line in stream:
                projection_hash.update(line); projection_bytes += len(line)
                row = parse_json(line)
                if set(row["record"]) != set(PROJECTIONS[product["product"]]) or row["source"]["sha256"] not in parents:
                    raise ContractError("Unapproved field or missing original parent")
                if audit_original_rows:
                    import pyarrow.parquet as pq
                    locator = row["source"]
                    key = (locator["sha256"], locator["row_group"])
                    if key != cached_key:
                        original = original_by_hash[locator["sha256"]]
                        if not original.as_posix().endswith(locator["path"]):
                            raise ContractError("Original row path mismatch")
                        pf = pq.ParquetFile(original)
                        columns = [c for c in PROJECTIONS[product["product"]] if c in pf.schema_arrow.names]
                        cached_rows = pf.read_row_group(locator["row_group"], columns=columns).to_pylist()
                        cached_key = key
                    number = locator["row"]
                    expected = (json.loads(json.dumps(project(cached_rows[number], product["product"])))
                                if type(number) is int and 0 <= number < len(cached_rows) else None)
                    if expected is None or expected != row["record"]:
                        raise ContractError("Original row projection mismatch")
                count += 1
        if count != product["rows"]:
            raise ContractError("Projection row count mismatch")
        if projection_hash.hexdigest() != product["sha256"]:
            raise ContractError("Projection parsed-byte checksum mismatch")
        pin(path, projection_hash.hexdigest(), projection_bytes, "historical_projection")
        checked_rows += count
    for ancestor in pins.values():
        path = Path(ancestor["path"])
        if sha256_file(path) != ancestor["sha256"] or path.stat().st_size != ancestor["bytes"]:
            raise ContractError("Historical ancestor changed during verification: " + ancestor["role"])
    manifest_final_sha256 = sha256_file(manifest_path)
    if manifest_final_sha256 != manifest_sha256:
        raise ContractError("Historical manifest changed during verification")
    return {"status": "passed", "original_files": len(files), "projected_rows": checked_rows,
        "all_original_rows_audited": audit_original_rows,
        "clinical_outcome_queries": 0, "scientific_features_qualified": False,
        "manifest_sha256": manifest_sha256, "manifest_final_sha256": manifest_final_sha256,
        "available_by": recomputed_available_by, "availability_basis": availability_basis,
        "ancestor_pins": sorted(pins.values(), key=lambda item: item["path"])}


def availability(notice):
    posts = notice.get("post_stream", {}).get("posts", [])
    if not posts or "24.09" not in posts[0].get("cooked", ""):
        raise ContractError("Missing official OT24.09 release announcement")
    created = posts[0]["created_at"]
    if not created.startswith("2024-09-18T"):
        raise ContractError("Unexpected release-announcement date")
    # Conservative next-midnight upper bound avoids asserting exact FTP posting time.
    return "2024-09-19T00:00:00Z"


class Archive:
    def __init__(self, raw, receipts, cap=5 * 1024**3):
        self.raw, self.receipts, self.cap = Path(raw), Path(receipts), cap
        self.raw.mkdir(parents=True, exist_ok=True); self.receipts.mkdir(parents=True, exist_ok=True)

    def fetch(self, relative, *, url=None, expected_sha1=None):
        path = self.raw / relative
        receipt_path = self.receipts / (relative.replace("/", "__") + ".json")
        if path.exists() or receipt_path.exists():
            raise ContractError("Refusing to replace archived input or receipt")
        address = url or BASE + relative
        if not address.startswith((BASE, NOTICE)):
            raise ContractError("URL outside selected official release")
        path.parent.mkdir(parents=True, exist_ok=True)
        started = stamp()
        request = urllib.request.Request(address, headers={"User-Agent": "tether-public-historical-qualification/1"})
        with urllib.request.urlopen(request, timeout=45) as response:
            headers = dict(response.headers); status = response.status
            declared = int(response.headers.get("Content-Length", "0"))
            if declared > self.cap:
                raise ContractError("Selected file exceeds authorized budget")
            sha1, sha256, size = hashlib.sha1(), hashlib.sha256(), 0
            with path.open("xb") as stream:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > self.cap:
                        raise ContractError("Selected file exceeds authorized budget")
                    stream.write(block); sha1.update(block); sha256.update(block)
        if declared and declared != size:
            raise ContractError("Incomplete download")
        if expected_sha1 and sha1.hexdigest() != expected_sha1:
            raise ContractError("Publisher SHA-1 mismatch")
        receipt = {"status": "completed", "source_url": address, "path": str(path.resolve()),
            "retrieval_started_at": started, "retrieval_completed_at": stamp(), "http_status": status,
            "response_headers": headers, "bytes": size, "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest(),
            "publisher_sha1": expected_sha1, "publisher_sha1_matched": bool(expected_sha1)}
        save_new(receipt_path, receipt)
        return {**receipt, "receipt_path": str(receipt_path.resolve()), "receipt_sha256": sha256_file(receipt_path)}


def collect(raw, receipts, output):
    import pyarrow.parquet as pq
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    archive = Archive(raw, receipts)
    metadata = []
    for relative, url in (("release-notice.json", NOTICE), ("release_data_integrity.sha1", None),
                          ("release_data_integrity", None), ("conf/platform.conf", None)):
        item = archive.fetch(relative, url=url); metadata.append(item)
        print("metadata", relative, item["bytes"], flush=True)
    manifest_path = archive.raw / "release_data_integrity"
    publisher_manifest_sha1 = (archive.raw / "release_data_integrity.sha1").read_text().split()[0]
    if hashlib.sha1(manifest_path.read_bytes()).hexdigest() != publisher_manifest_sha1:
        raise ContractError("Publisher integrity manifest checksum mismatch")
    checksums = integrity_map(manifest_path.read_text())
    metadata.append(archive.fetch("input/manifest.json", expected_sha1=checksums["input/manifest.json"]))
    available_by = availability(json.loads((archive.raw / "release-notice.json").read_text()))
    selected = {}
    for product in PROJECTIONS:
        prefix = "output/etl/parquet/" + product + "/"
        selected[product] = sorted(p for p in checksums if p.startswith(prefix) and p.endswith(".parquet"))
        if not selected[product]:
            raise ContractError("No publisher-listed partitions for " + product)
    # Small release products only; rounded directory sizes are not admission proofs.
    all_paths = [p for paths in selected.values() for p in paths]
    if len(all_paths) * 5 * 1024**2 + sum(f["bytes"] for f in metadata) > 5 * 1024**3:
        raise ContractError("Worst-case selected partition budget exceeds authorization")
    archive.cap = 5 * 1024**2
    def get(path):
        for attempt in range(3):
            try:
                return archive.fetch(path, expected_sha1=checksums[path])
            except Exception:
                # Never overwrite partial/failed originals. Stop with exact path.
                if (archive.raw / path).exists() or attempt == 2:
                    raise
    with ThreadPoolExecutor(max_workers=12) as pool:
        files = list(pool.map(get, all_paths))
    if sum(f["bytes"] for f in metadata + files) > 5 * 1024**3:
        raise ContractError("Total acquisition exceeded authorization")
    print("raw files verified", len(files), sum(f["bytes"] for f in files), flush=True)
    file_index = {str(Path(f["path"]).relative_to(archive.raw)).replace("\\", "/"): f for f in files}
    products = []
    for product, paths in selected.items():
        destination = output / (product + ".jsonl")
        count, schemas, missing, parents = 0, set(), set(), []
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            for relative in paths:
                source = archive.raw / relative
                source_sha256 = file_index[relative]["sha256"]
                pf = pq.ParquetFile(source)
                schemas.add(str(pf.schema_arrow))
                columns = [field for field in PROJECTIONS[product] if field in pf.schema_arrow.names]
                missing.update(set(PROJECTIONS[product]) - set(columns))
                # Only approved columns are decoded. No clinical table is joined.
                for group in range(pf.num_row_groups):
                    for number, row in enumerate(pf.read_row_group(group, columns=columns).to_pylist()):
                        line = {"record": project(row, product), "source": {"path": relative,
                            "row_group": group, "row": number, "sha256": source_sha256}}
                        stream.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n"); count += 1
                parents.append(relative)
        schema_path = output / (product + "-schemas.json")
        save_new(schema_path, sorted(schemas))
        products.append({"product": product, "path": str(destination.resolve()), "sha256": sha256_file(destination),
            "bytes": destination.stat().st_size, "rows": count, "partitions": len(paths), "parents": parents,
            "approved_columns": list(PROJECTIONS[product]), "missing_columns": sorted(missing),
            "schema_path": str(schema_path.resolve()), "schema_sha256": sha256_file(schema_path)})
        print("projection", product, count, "missing", sorted(missing), flush=True)
    result = {"schema_version": 1, "status": "qualified_mapping_projections_only", "origin_at": ORIGIN,
        "release_id": "24.09", "available_by": available_by, "available_by_basis": "official dated release announcement; conservative next-day bound",
        "release_date": "2024-09-18", "publication_dates": "not inferred from dataset release",
        "annotation_dates": "individual dates not supplied; frozen integrated annotations bounded by release",
        "retrieved_at": stamp(), "raw_parents_role": "quarantined_originals_not_agent_visible",
        "metadata": metadata, "files": files, "products": products,
        "future_fallback": False, "clinical_outcome_queries": 0, "provider_spend_usd": 0,
        "scientific_features_qualified": False, "baseline_association_scores_qualified": False,
        "limits": ["Mapping candidates are resource annotations, not adjudicated regimen/target equivalence.",
            "Known-drug evidence, indications, approval status, maximum phase, warnings, clinical trial fields and overall association scores excluded.",
            "Exact upstream HGNC/EFO releases and individual annotation/publication timestamps require manifest assessment.",
            "No unsupported genetic/causal or predictive feature is derived."]}
    save_new(output / "manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--raw", required=True)
    parser.add_argument("--receipts", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); result = collect(args.raw, args.receipts, args.output)
    print(json.dumps({"status": result["status"], "products": [(p["product"], p["rows"]) for p in result["products"]]}))


if __name__ == "__main__":
    main()
