"""Resolve the missing pinned public table files; HEAD only, no payload transfer."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
RAW = Path("E:/projects_data/drug_target_agents_data")
INVENTORY = ROOT / "data/manifests/public/2026-10-10-download-size-inventory.json"


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return pin(path)


def resolve(entry):
    url = entry["url"]
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.netloc != "ftp.ebi.ac.uk" or parsed.query
            or not parsed.path.startswith("/pub/databases/opentargets/platform/25.09/output/credible_set/")):
        raise ValueError("Unexpected source URL")
    with urlopen(Request(url, method="HEAD"), timeout=45) as response:
        if response.status != 200 or response.url != url:
            raise ValueError("Unexpected source response")
        size = int(response.headers["Content-Length"])
        if size <= 0 or size > entry["planning_upper_bytes"]:
            raise ValueError("Source size exceeds retained inventory bound")
        return {"url": url, "bytes": size, "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"), "accept_ranges": response.headers.get("Accept-Ranges"),
                "checked_at_utc": datetime.now(timezone.utc).isoformat()}


def main():
    now = datetime.now(timezone.utc)
    batch = "preprint-p02-credible-completion-" + now.strftime("%Y%m%dT%H%M%SZ")
    folder = ROOT / "data/manifests/private" / batch
    folder.mkdir()
    inventory = json.loads(INVENTORY.read_bytes())
    release = next(row for row in inventory["inventories"] if row.get("release_id") == "25.09")
    files = sorted((row for row in release["files"] if row.get("component") == "credible_set"
                    and row["relative_path"].endswith(".parquet")), key=lambda row: row["relative_path"])
    if len(files) != 25:
        raise ValueError("Pinned inventory must contain exactly 25 table files")
    missing = [row for row in files if not (RAW / "raw/open_targets_platform/25.09/output" / row["relative_path"]).exists()]
    if len(missing) != 23:
        raise ValueError("Local file membership changed; inspect rather than change scope")
    write_new(folder / "request.json", {"batch_id": batch, "inventory": pin(INVENTORY),
              "purpose": "Complete missing same-release public inputs for the CTLA4 locus join; do not modify old worker or files",
              "scheduled_urls": [row["url"] for row in missing], "max_batch_bytes": 3 * 1024**3,
              "model_calls": 0, "provider_spending_usd": 0, "payloads_downloaded": 0})
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            heads = list(pool.map(resolve, missing))
        records = []
        for entry, head in zip(missing, heads):
            relative = "raw/open_targets_platform/25.09/" + batch + "/credible_set/" + PurePosixPath(entry["relative_path"]).name
            target = (RAW / relative).resolve()
            if not target.is_relative_to(RAW.resolve()) or target.exists():
                raise ValueError("Unsafe or occupied new target")
            identifier = "p02-credible-" + hashlib.sha256((batch + entry["url"]).encode()).hexdigest()[:20]
            if (RAW / "manifests/receipts" / (identifier + ".json")).exists():
                raise ValueError("New receipt identity already exists")
            records.append({"receipt_id": identifier, "dataset_id": "ot_credible_set", "release_id": "25.09",
                            "relative_path": relative, "url": entry["url"], "format": "parquet",
                            "expected_bytes": head["bytes"], "expected_sha256": None,
                            "planning_upper_bytes": head["bytes"]})
        if sum(row["planning_upper_bytes"] for row in records) > 3 * 1024**3:
            raise ValueError("Resolved batch exceeds 3 GiB cap")
        queue = write_new(folder / "queue.json", {"schema_version": 1, "batch_id": batch,
                          "created_at_utc": now.isoformat(), "files": records})
        report = {"schema_version": 1, "status": "RESOLVED_PUBLIC_FILE_METADATA_NO_PAYLOADS",
                  "queue": queue, "inventory": pin(INVENTORY), "heads": heads,
                  "file_count": len(records), "exact_payload_bytes": sum(row["expected_bytes"] for row in records),
                  "raw_root": str(RAW), "source_release": "25.09", "isolated_batch_id": batch,
                  "old_files_or_receipts_overwritten": False, "provider_checksum_known": False,
                  "temporal_limit": "Any newly observed bytes get their actual present-day download bound, never an earlier origin",
                  "working_storage": "Compressed originals plus small receipts; streaming projection, no bulk expansion or indices. Independent backup would require additional space.",
                  "model_calls": 0, "provider_spending_usd": 0, "payloads_downloaded": 0}
        saved = write_new(folder / "resolution.json", report)
        print(json.dumps({"resolution": saved, "queue": queue, "files": len(records),
                          "exact_payload_bytes": report["exact_payload_bytes"], "batch_id": batch}))
    except BaseException as error:
        write_new(folder / "failure.json", {"status": "failed_metadata_resolution", "error_type": type(error).__name__,
                                            "message": str(error), "payloads_downloaded": 0})
        raise


if __name__ == "__main__":
    main()
