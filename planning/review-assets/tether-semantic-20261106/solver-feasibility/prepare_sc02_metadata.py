"""Fetch only official small source text/metadata, never wheels or model payloads."""
from __future__ import annotations

import concurrent.futures
import email.parser
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
PINS = {
    "transformers": "4.57.1", "tokenizers": "0.22.1",
    "huggingface-hub": "0.36.0", "safetensors": "0.6.2",
    "filelock": "3.19.1", "typing-extensions": "4.15.0", "sympy": "1.13.3",
    "networkx": "3.5", "jinja2": "3.1.6", "fsspec": "2025.9.0",
    "numpy": "2.3.5", "packaging": "25.0", "pyyaml": "6.0.3",
    "regex": "2025.9.18", "requests": "2.32.5", "tqdm": "4.67.1",
    "charset-normalizer": "3.4.4", "idna": "3.11", "urllib3": "2.5.0",
    "certifi": "2025.10.5", "markupsafe": "3.0.3", "mpmath": "1.3.0",
    "colorama": "0.4.6", "hf-xet": "1.2.0",
}


def get_small(url, cap):
    req = urllib.request.Request(url, headers={"User-Agent": "MultiVerS-source-metadata-preparation"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(cap + 1)
    if len(data) > cap:
        raise ValueError(f"Metadata/source exceeds byte cap: {url}")
    return data


def put_exclusive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"Existing preparation differs: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(data)


def put_json(path, data):
    put_exclusive(path, (json.dumps(data, indent=2, ensure_ascii=True) + "\n").encode())


def inspect_package(item):
    name, version = item
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    raw = get_small(url, 1_500_000)
    data = json.loads(raw)
    # Prefer the exact CPython 3.11 Windows wheel; otherwise use a compatible ABI3
    # or universal wheel. There is exactly one selected payload per distribution.
    suffixes = ("cp311-cp311-win_amd64.whl", "cp311-abi3-win_amd64.whl",
                "cp39-abi3-win_amd64.whl", "cp38-abi3-win_amd64.whl",
                "cp37-abi3-win_amd64.whl", "py3-none-any.whl", "py2.py3-none-any.whl")
    chosen = None
    for suffix in suffixes:
        matches = [row for row in data["urls"] if row["filename"].endswith(suffix)]
        if matches:
            if len(matches) != 1:
                raise ValueError(f"Ambiguous wheel for {name}")
            chosen = matches[0]
            break
    if chosen is None:
        raise ValueError(f"No Python 3.11 Windows wheel for {name}")
    info = data["info"]
    return dict(name=name, version=version, filename=chosen["filename"],
                url=chosen["url"], bytes=chosen["size"], sha256=chosen["digests"]["sha256"],
                requires_python=info.get("requires_python"), requires_dist=info.get("requires_dist") or [],
                license_expression=info.get("license_expression"), license=info.get("license"),
                license_classifiers=[row for row in info.get("classifiers", []) if row.startswith("License ::")],
                metadata_url=url, metadata_sha256=hashlib.sha256(raw).hexdigest())


def main():
    prior = json.loads((ROOT / "metadata.json").read_text())
    source_rows = []
    for row in prior["source_files"]:
        url = prior["source_raw_url_prefix"] + row["path"]
        raw = get_small(url, 250_000)
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"Pinned source mismatch: {row['path']}")
        local = ROOT / "source" / row["path"]
        put_exclusive(local, raw)
        source_rows.append(dict(row, url=url, local_path=str(local)))
    extra_sources = {
        "multivers/allennlp_feedforward.py": prior["source_raw_url_prefix"] + "multivers/allennlp_feedforward.py",
        "multivers/allennlp_nn_util.py": prior["source_raw_url_prefix"] + "multivers/allennlp_nn_util.py",
        "multivers/util.py": prior["source_raw_url_prefix"] + "multivers/util.py",
        "reference-transformers-4.2.2/modeling_longformer.py": "https://raw.githubusercontent.com/huggingface/transformers/v4.2.2/src/transformers/models/longformer/modeling_longformer.py",
        "reference-transformers-4.2.2/configuration_longformer.py": "https://raw.githubusercontent.com/huggingface/transformers/v4.2.2/src/transformers/models/longformer/configuration_longformer.py",
        "reference-transformers-4.2.2/LICENSE": "https://raw.githubusercontent.com/huggingface/transformers/v4.2.2/LICENSE",
        "reference-transformers-4.57.1/modeling_longformer.py": "https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/src/transformers/models/longformer/modeling_longformer.py",
        "reference-transformers-4.57.1/LICENSE": "https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/LICENSE",
    }
    for path, url in extra_sources.items():
        raw = get_small(url, 250_000)
        local = ROOT / "source" / path
        put_exclusive(local, raw)
        source_rows.append(dict(path=path, url=url, local_path=str(local), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    put_json(ROOT / "source-receipt.json", dict(schema="small-source-receipt-v1", files=source_rows))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        packages = list(pool.map(inspect_package, PINS.items()))
    torch = prior["candidate_torch_wheel"]
    raw = get_small(torch["url"] + ".metadata", 100_000)
    parsed = email.parser.BytesParser().parsebytes(raw)
    if parsed["Version"] != "2.7.1+cu128":
        raise ValueError("Wrong CUDA wheel metadata")
    packages.append(dict(name="torch", version="2.7.1+cu128",
                         filename="torch-2.7.1+cu128-cp311-cp311-win_amd64.whl",
                         url=torch["url"], bytes=3273066072, sha256=torch["sha256"],
                         requires_python=parsed["Requires-Python"], requires_dist=parsed.get_all("Requires-Dist"),
                         license=parsed["License"], metadata_url=torch["url"] + ".metadata",
                         metadata_sha256=hashlib.sha256(raw).hexdigest()))
    packages.sort(key=lambda row: row["name"])
    lock = dict(schema="candidate-cp311-win-amd64-lock-v1", status="metadata_only_not_installed_or_qualified",
                target=dict(python="3.11", implementation="CPython", os="Windows", architecture="AMD64", cuda="12.8"),
                packages=packages, package_count=len(packages), wheel_bytes=sum(row["bytes"] for row in packages),
                note="hf-xet included explicitly for either AMD64 marker spelling; all inference network fallback disabled")
    put_json(ROOT / "dependency-lock.json", lock)
    reqs = "# Candidate runtime; install only after SC01 and acquisition integrity checks.\n"
    reqs += "\n".join(f"{row['name']}=={row['version']} --hash=sha256:{row['sha256']}" for row in packages) + "\n"
    put_exclusive(ROOT / "requirements.lock.txt", reqs.encode())

    assets = []
    for row in packages:
        assets.append(dict(kind="wheel", logical_id=row["filename"], url=row["url"], expected_bytes=row["bytes"], expected_sha256=row["sha256"]))
    ckpt = prior["checkpoints"][0]
    assets.append(dict(kind="checkpoint", logical_id="fever_sci.ckpt", url=ckpt["version_pinned_url"],
                       expected_bytes=ckpt["bytes"], expected_sha256=None, expected_version_id=ckpt["version_id"],
                       expected_etag=ckpt["etag"], local_sha256_required_before_deserialization=True))
    revision = prior["tokenizer_config"]["revision"]
    for name, size, git_blob in [
        ("config.json", 803, "586f829492f0d3ac19113a594321d30ed0dee5a2"),
        ("vocab.json", 898823, "5606f48548d99a9829d10a96cd364b816b02cd21"),
        ("merges.txt", 456318, "226b0752cac7789c48f0cb3ec53eda48b7be36cc"),
        ("tokenizer.json", 1355863, "ad0bcbeb288f0d1373d88e0762e66357f55b8311"),
    ]:
        assets.append(dict(kind="tokenizer_config", logical_id=name,
                           url=f"https://huggingface.co/allenai/longformer-large-4096/resolve/{revision}/{name}",
                           expected_bytes=size, expected_sha256=None, expected_revision=revision,
                           expected_git_blob_sha1=git_blob, local_sha256_required_before_use=True))
    put_json(ROOT / "acquisition-manifest.json", dict(schema="bounded-sc02-acquisition-v1",
              status="planned_only_no_payloads_downloaded", assets=assets,
              total_payload_bytes=sum(row["expected_bytes"] for row in assets),
              maximum_total_payload_bytes=9_000_000_000,
              preserve_existing_downloader=True, unique_attempt_directory_required=True,
              receipt_fields=["logical_id", "source_url", "final_url", "started_utc", "completed_utc", "bytes", "sha256", "http_etag", "http_version_id", "http_repo_commit", "status"],
              stop_conditions=["unexpected_length", "hash_mismatch", "version_or_revision_mismatch", "aggregate_cap_exceeded", "redirect_outside_source_host_allowlist"],
              allowed_source_hosts=["download-r2.pytorch.org", "download.pytorch.org", "files.pythonhosted.org", "scifact.s3.us-west-2.amazonaws.com", "huggingface.co"] ))
    print(json.dumps(dict(source_files=len(source_rows), wheel_count=len(packages),
                          wheel_bytes=lock["wheel_bytes"], payload_bytes=sum(row["expected_bytes"] for row in assets))))


if __name__ == "__main__":
    main()
