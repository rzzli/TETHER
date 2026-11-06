"""Independent metadata-only SC02 lock/source check; no model or GPU import."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse, parse_qs

PARSER_ROOT = Path(__file__).resolve().parents[5] / "data/cache/tether-inspect-env-attempt02/environment/Lib/site-packages/pip/_vendor"
sys.path.insert(0, str(PARSER_ROOT))
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version


HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / "solver-feasibility"
OUTPUT = HERE / "metadata-review-attempt02"
read = lambda path: json.loads(path.read_text(encoding="utf-8"))


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def main():
    lock = read(BASE / "dependency-lock.json")
    manifest = read(BASE / "acquisition-manifest.json")
    target = default_environment()
    target["extra"] = ""
    assert target["python_version"] == "3.11" and target["sys_platform"] == "win32"
    packages = {canonicalize_name(p["name"]): p for p in lock["packages"]}
    assert len(packages) == len(lock["packages"]) == lock["package_count"]
    active_edges = []
    for package in packages.values():
        if package.get("requires_python"):
            assert Version(target["python_full_version"]) in SpecifierSet(package["requires_python"])
        _, wheel_version, _, tags = parse_wheel_filename(package["filename"])
        assert wheel_version == Version(package["version"])
        assert tags.intersection(set(sys_tags())), package["filename"]
        for raw in package["requires_dist"]:
            req = Requirement(raw)
            if req.marker is None or req.marker.evaluate(target):
                dep = packages[canonicalize_name(req.name)]
                assert Version(dep["version"]) in req.specifier, raw
                active_edges.append({"from": package["name"], "to": req.name, "requirement": raw, "version": dep["version"]})
    wheel_assets = {a["logical_id"]: a for a in manifest["assets"] if a["kind"] == "wheel"}
    assert set(wheel_assets) == {p["filename"] for p in packages.values()}
    for package in packages.values():
        asset = wheel_assets[package["filename"]]
        assert asset["expected_sha256"] == package["sha256"] and asset["expected_bytes"] == package["bytes"]
        assert asset["url"] == package["url"]
    req_lines = [x for x in (BASE / "requirements.lock.txt").read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
    assert len(req_lines) == len(packages)
    for line in req_lines:
        spec, hashpart = line.split(" --hash=sha256:")
        name, version = spec.split("==")
        package = packages[canonicalize_name(name)]
        assert Version(version) == Version(package["version"]) and hashpart == package["sha256"]
    assert sum(a["expected_bytes"] for a in manifest["assets"]) == manifest["total_payload_bytes"] <= manifest["maximum_total_payload_bytes"]
    assert len({a["logical_id"] for a in manifest["assets"]}) == len(manifest["assets"])
    for asset in manifest["assets"]:
        parsed = urlparse(asset["url"])
        assert parsed.scheme == "https" and parsed.hostname in manifest["allowed_source_hosts"]
        if asset["kind"] == "checkpoint":
            assert asset["logical_id"] == "fever_sci.ckpt"
            assert parse_qs(parsed.query)["versionId"] == [asset["expected_version_id"]]
            assert asset["local_sha256_required_before_deserialization"]
        elif asset["kind"] == "tokenizer_config":
            assert "/" + asset["expected_revision"] + "/" in parsed.path
            assert re.fullmatch("[0-9a-f]{40}", asset["expected_git_blob_sha1"])
            assert asset["local_sha256_required_before_use"]
    source_pins = []
    for recfile in ("source-receipt.json", "source-reference-addendum.json"):
        for source in read(BASE / recfile)["files"]:
            actual = pin(Path(source.get("local_path", source["path"])))
            assert actual["sha256"] == source["sha256"] and actual["bytes"] == source["bytes"]
            source_pins.append(actual)
    assert len({x["path"] for x in source_pins}) == len(source_pins)
    result = {"status": "PASS_metadata_only", "scope": "Independent manifest, active dependency edges, wheel tags and source byte identities; no acquisition, installation, checkpoint loading, tensor inference or GPU execution.",
              "packages": len(packages), "active_dependency_edges": active_edges, "target_marker_environment": target,
              "payload_bytes": manifest["total_payload_bytes"], "assets": len(manifest["assets"]), "source_files_verified": source_pins,
              "input_pins": {name: pin(BASE / name) for name in ("dependency-lock.json", "acquisition-manifest.json", "requirements.lock.txt", "source-receipt.json", "source-reference-addendum.json")},
              "reviewer": pin(Path(__file__)), "interpreter": str(Path(sys.executable).resolve()),
              "explicit_readonly_parser_dependency": [pin(path) for path in sorted((PARSER_ROOT / "packaging").rglob("*.py"))],
              "limitations": ["Payload byte integrity still requires acquisition receipts and local hashing.", "Metadata compatibility does not establish native CUDA or runtime compatibility.", "Modern-runtime legacy-source parity does not establish historical binary reproduction."]}
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT / "REVIEW.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "packages": len(packages), "active_edges": len(active_edges), "source_files": len(source_pins), "record": pin(OUTPUT / "REVIEW.json")}))


if __name__ == "__main__":
    main()
