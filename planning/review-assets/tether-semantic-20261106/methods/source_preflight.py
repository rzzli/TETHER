"""Read-only independent verification of original SciFact source authorities.

No experiment, preparation, or decomposition module is imported. Raw tar members
are read in memory; no archive extraction or prediction/scoring is performed.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import traceback


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).resolve().parent / "source-preflight-attempt02"
BASELINE = ROOT / "data/benchmark/scifact/native-20261105T234805Z-attempt01"
PREP = ROOT / "data/benchmark/scifact/preparation-20261105-attempt03"
RAW = ROOT / "data/raw/scifact_public/20261105-attempt01/scifact-data.tar.gz"
ACCEPTANCE = ROOT / "planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json"
EXPECTED = {
    BASELINE / "RECEIPT.json": "3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968",
    PREP / "manifest.json": "cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8",
    RAW: "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be",
    Path(str(RAW) + ".receipt.json"): "b2aa9586681fbc22b1dbcd563daa6f49582f71f09331a80df78a5d4553fe4ba2",
    ACCEPTANCE: "3426f85542f3a2b3355542e9292168db2f5f2ce39c713836a3c0e7cc1202d462",
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse(content):
    def object_pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(content.decode("utf-8"), object_pairs_hook=object_pairs)


def bounded(path, limit=64 * 1024 * 1024):
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400, "Nonregular or reparse input")
    need(info.st_size <= limit, "Oversized input")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    need(len(raw) == info.st_size, "Input changed size or exceeds limit")
    return raw


def pin(path, expected=None):
    raw = bounded(path)
    got = digest(raw)
    need(expected is None or expected == got, "Authority digest mismatch: " + str(path))
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": got}


def safe_child(base, relative):
    parts = PurePosixPath(relative).parts
    need(relative and "\\" not in relative and ":" not in relative and not relative.startswith("/") and all(p not in (".", "..", "") for p in parts), "Unsafe relative path")
    target = base.joinpath(*parts).resolve()
    need(target.is_relative_to(base.resolve()), "Path escapes input root")
    return target


def write(name, value):
    with (OUTPUT / name).open("xb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def inventory(receipt):
    expected = receipt["outputs"]
    need(len(expected) == 1601, "Original stage receipt count differs from external anchor")
    actual = {}
    for path in BASELINE.rglob("*"):
        info = path.lstat()
        need(not path.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400, "Link/reparse in original stage")
        if path.is_file():
            actual[path.relative_to(BASELINE).as_posix()] = path
    need(set(actual) == set(expected) | {"RECEIPT.json"}, "Original stage exact file set differs from receipt")
    records = {name: pin(safe_child(BASELINE, name), value) for name, value in expected.items()}
    return records


def main():
    anchors = {str(path): pin(path, expected) for path, expected in EXPECTED.items()}
    acceptance = parse(bounded(ACCEPTANCE))
    receipt = parse(bounded(BASELINE / "RECEIPT.json"))
    need(acceptance["stage_receipt_sha256"] == EXPECTED[BASELINE / "RECEIPT.json"], "Root acceptance stage join mismatch")
    before = inventory(receipt)
    output_bytes = sum(x["bytes"] for x in before.values())
    receipt_bytes = anchors[str(BASELINE / "RECEIPT.json")]["bytes"]
    need(output_bytes + receipt_bytes == acceptance["inventories"]["stage"]["retained_bytes"] == 36570027, "Original stage byte count mismatch")
    manifest = parse(bounded(PREP / "manifest.json"))
    frozen = parse(bounded(BASELINE / "FROZEN.json"))
    need(frozen["preparation_manifest_sha256"] == EXPECTED[PREP / "manifest.json"], "Baseline does not bind preparation")
    need(Path(frozen["preparation_root"]).resolve() == PREP.resolve(), "Baseline preparation path mismatch")
    need(manifest["archive"]["sha256"] == EXPECTED[RAW], "Preparation archive identity mismatch")
    need(manifest["archive"]["receipt_sha256"] == EXPECTED[Path(str(RAW) + ".receipt.json")], "Preparation archive receipt mismatch")
    source_receipt = parse(bounded(Path(str(RAW) + ".receipt.json")))
    need(source_receipt["sha256"] == EXPECTED[RAW] and source_receipt["bytes"] == len(bounded(RAW)), "Acquisition payload mismatch")
    acquisition_pin = pin(Path(manifest["acquisition"]["path"]), manifest["acquisition"]["sha256"])
    products = {}
    for name, product in manifest["products"].items():
        path = safe_child(PREP, product["path"])
        products[name] = pin(path, product["sha256"])
        need(products[name]["bytes"] == product["bytes"], "Prepared product byte count mismatch: " + name)
    payloads, inventory_observed = {}, []
    with tarfile.open(fileobj=io.BytesIO(bounded(RAW)), mode="r:gz") as archive:
        names = set()
        for item in archive:
            need(item.name not in names and len(names) < 100, "Duplicate/excess raw members")
            names.add(item.name)
            parts = PurePosixPath(item.name).parts
            need(item.name and not item.name.startswith("/") and "\\" not in item.name and ":" not in item.name and all(p not in (".", "..", "") for p in parts), "Unsafe tar member")
            need(item.isfile() or item.isdir(), "Tar link or nonregular member")
            need(0 <= item.size <= 32 * 1024 * 1024, "Tar member size limit")
            inventory_observed.append({"name": item.name, "bytes": item.size, "kind": "file" if item.isfile() else "directory"})
            if item.name in manifest["members"]:
                stream = archive.extractfile(item)
                need(stream is not None, "Missing tar payload")
                payload = stream.read(32 * 1024 * 1024 + 1)
                need(len(payload) == item.size, "Truncated tar payload")
                expected = manifest["members"][item.name]
                need(digest(payload) == expected["sha256"] and len(payload) == expected["bytes"], "Raw member digest mismatch")
                payloads[item.name] = payload
    expected_inventory = [{k: x[k] for k in ("name", "bytes", "kind")} for x in manifest["inventory"]]
    need(inventory_observed == expected_inventory, "Archive inventory disagrees with anchored preparation")
    need(set(payloads) == set(manifest["members"]), "Missing source member")
    bindings = {"corpus": {}, "claims": {}}
    projected_corpus, projected_claims = [], {}
    for name, payload in payloads.items():
        rows, row_bindings = [], {}
        for line_number, raw_line in enumerate(payload.splitlines(keepends=True), 1):
            row = parse(raw_line)
            bind = {"member": name, "line_1based": line_number, "raw_line_sha256": digest(raw_line)}
            if name == "data/corpus.jsonl":
                view = {k: row[k] for k in ("doc_id", "title", "abstract")}
                key = str(view["doc_id"])
                bind["projected_sha256"] = digest(canonical(view))
            else:
                view = {"id": row["id"], "claim": row["claim"], "evidence": row.get("evidence", {}), "cited_doc_ids": row.get("cited_doc_ids", [])}
                key = str(view["id"])
                bind["reference_sha256"] = digest(canonical(view))
                bind["query_sha256"] = digest(canonical({k: view[k] for k in ("id", "claim")}))
            bind["field_sha256"] = {k: digest(canonical(v)) for k, v in view.items()}
            need(key not in row_bindings, "Duplicate source ID")
            row_bindings[key] = bind
            rows.append(view)
        if name == "data/corpus.jsonl":
            projected_corpus = sorted(rows, key=lambda x: x["doc_id"])
            bindings["corpus"] = row_bindings
        else:
            split = name.removeprefix("data/claims_").removesuffix(".jsonl")
            projected_claims[split] = sorted(rows, key=lambda x: x["id"])
            bindings["claims"][split] = row_bindings
    def verify_projection(product, rows):
        rebuilt = b"".join(canonical(row) + b"\n" for row in rows)
        original = bounded(Path(products[product]["path"]))
        need(rebuilt == original, "Independent raw source projection differs: " + product)
        return {"rows": len(rows), "sha256": digest(rebuilt), "bytes": len(rebuilt)}
    projections = {
        "corpus": verify_projection("corpus", projected_corpus),
        "references_dev": verify_projection("references_dev", projected_claims["dev"]),
        "queries_dev": verify_projection("queries_dev", [{k: x[k] for k in ("id", "claim")} for x in projected_claims["dev"]]),
    }
    need(canonical(bindings) + b"\n" == bounded(Path(products["source_bindings"]["path"])), "Independent source bindings differ from original")
    need([x["id"] for x in projected_claims["dev"]] == frozen["dev_schedule"], "Original development schedule differs from source IDs")
    need(len(projected_corpus) == 5183 and len(projected_claims["dev"]) == 300, "Original source population differs")
    after = inventory(receipt)
    need(before == after, "Original baseline changed during preflight")
    need(anchors == {str(path): pin(path, expected) for path, expected in EXPECTED.items()}, "Authority changed during preflight")
    for product in products.values():
        need(product == pin(Path(product["path"])), "Preparation product changed during preflight")
    write("VERIFIED-BASELINE-INVENTORY.json", {"stage_receipt_sha256": EXPECTED[BASELINE / "RECEIPT.json"], "outputs": before})
    result = {"status": "PASS", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
              "kind": "independent_original_scifact_source_authority_preflight", "script": pin(Path(__file__)),
              "scope": "Read-only archive, source projection and inventory verification. No new diagnostic error computation, model execution, scoring, fitting, tuning, downloads or original-file writes.",
              "anchors": anchors, "acquisition": acquisition_pin, "baseline_outputs_verified": len(before),
              "baseline_output_bytes_excluding_receipt": output_bytes, "baseline_receipt_bytes": receipt_bytes,
              "baseline_retained_bytes_including_receipt": output_bytes + receipt_bytes, "baseline_exact_fileset": True,
              "baseline_rechecked_unchanged": True, "prepared_products_verified": products, "independent_projections": projections,
              "source_bindings_byte_identical": True,
              "source_binding_rows": {"corpus": len(bindings["corpus"]), "claims": {k: len(v) for k, v in bindings["claims"].items()}},
              "source_inventory": inventory_observed, "all_300_development_ids_original_order_verified": True,
              "inventory_record": pin(OUTPUT / "VERIFIED-BASELINE-INVENTORY.json")}
    write("PREFLIGHT.json", result)
    print(json.dumps({"status": "PASS", "baseline_outputs": len(before), "prepared_products": len(products), "record": pin(OUTPUT / "PREFLIGHT.json")}))


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=False)
    try:
        main()
    except Exception as exc:
        write("FAILED.json", {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise
