"""Acquire exact public CPU wheels for the declared CPython 3.11 Windows baseline."""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PACKAGES = {"numpy": "2.3.5", "scipy": "1.16.3", "scikit-learn": "1.7.2",
            "joblib": "1.5.2", "threadpoolctl": "3.6.0"}


def read(url, cap):
    with urlopen(Request(url, headers={"User-Agent": "TETHER-benchmark-environment/1"}), timeout=60) as r:
        if not r.geturl().startswith("https://"):
            raise ValueError("Non-HTTPS redirect")
        raw = r.read(cap + 1)
        if len(raw) > cap:
            raise ValueError("Acquisition exceeds limit")
        return raw


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = []
    status = "failed"
    try:
        for name, version in PACKAGES.items():
            url = f"https://pypi.org/pypi/{name}/{version}/json"
            raw = read(url, 2 * 1024 * 1024)
            with (out / (name + ".pypi.json")).open("xb") as f:
                f.write(raw)
            meta = json.loads(raw)
            choices = [x for x in meta["urls"] if x["filename"].endswith(
                ("-cp311-cp311-win_amd64.whl", "-py3-none-any.whl")) and not x.get("yanked")]
            if len(choices) != 1:
                raise ValueError(f"Ambiguous or unavailable pinned wheel: {name}")
            item = choices[0]
            payload = read(item["url"], 64 * 1024 * 1024)
            digest = hashlib.sha256(payload).hexdigest()
            if digest != item["digests"]["sha256"] or len(payload) != item["size"]:
                raise ValueError("Wheel length or PyPI digest mismatch")
            with (out / item["filename"]).open("xb") as f:
                f.write(payload)
            record = {"package": name, "version": version, "filename": item["filename"],
                      "url": item["url"], "sha256": digest, "bytes": len(payload),
                      "metadata_url": url, "metadata_sha256": hashlib.sha256(raw).hexdigest(),
                      "requires_python": item.get("requires_python"),
                      "license_metadata": meta["info"].get("license"),
                      "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
            records.append(record)
            print(json.dumps({k: record[k] for k in ("package", "version", "filename", "sha256", "bytes")}), flush=True)
        status = "downloaded_hash_verified_installation_pending"
    finally:
        with (out / "WHEELS.json").open("x", encoding="utf-8", newline="\n") as f:
            json.dump({"status": status, "target": "CPython3.11-win_amd64", "wheels": records}, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
