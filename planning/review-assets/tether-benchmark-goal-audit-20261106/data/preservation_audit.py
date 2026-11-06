"""Read-only five-stage preservation audit; no product imports or inference."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
CACHE = {}
CHECKS = []
INVENTORIES = []
OMISSIONS = []
MUTABLE = {"README.md", "memory/MEMORY.md", "memory/project-goals.md",
           "planning/TETHER Inspect Comparison Results 2026-11-06.md"}


def absolute(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT/path


def digest(path):
    path = absolute(path)
    before = path.stat()
    signature = (before.st_size, before.st_mtime_ns)
    cached = CACHE.get(str(path))
    if cached and cached[0] == signature:
        return cached[1]
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while raw := stream.read(1024*1024):
            h.update(raw)
    after = path.stat()
    assert signature == (after.st_size, after.st_mtime_ns), str(path)
    pin = {"bytes": before.st_size, "sha256": h.hexdigest()}
    CACHE[str(path)] = (signature, pin)
    return pin


def check(path, expected, scope):
    path = absolute(path)
    expected = {"sha256": expected} if isinstance(expected, str) else {k: expected[k] for k in ("sha256", "bytes") if k in expected}
    try:
        actual = digest(path)
        passed = all(actual[k] == v for k, v in expected.items())
        row = {"path": str(path), "scope": scope, "expected": expected, "actual": actual,
               "status": "pass" if passed else "mismatch"}
    except OSError as exc:
        passed = False
        row = {"path": str(path), "scope": scope, "status": "missing_or_unreadable", "error": type(exc).__name__}
    CHECKS.append(row)
    return passed


def load(path, expected=None, scope="selected anchor"):
    path = absolute(path)
    if expected is not None:
        assert check(path, expected, scope), str(path)
    return json.loads(path.read_bytes())


def mapping(pins, base, scope):
    for name, pin in pins.items():
        check(Path(base)/name, pin, scope)


def inventory(root, expected, scope, exclusions=()):
    root = absolute(root)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}-set(exclusions)
    expected = {str(p).replace("\\", "/") for p in expected}
    INVENTORIES.append({"scope": scope, "root": str(root), "expected_files": len(expected), "actual_files": len(actual),
                        "added": sorted(actual-expected), "missing": sorted(expected-actual), "status": "pass" if actual == expected else "mismatch"})


def sealed(root, name, sha, scope, key="outputs"):
    root = absolute(root)
    record = load(root/name, sha, scope+" anchor")
    mapping(record[key], root, scope+" outputs")
    inventory(root, record[key], scope, exclusions=(name,))
    return record


def tracked(path, commit, scope):
    data = subprocess.check_output(["git", "show", commit+":"+path.replace("\\", "/")], cwd=ROOT)
    expected = hashlib.sha256(data).hexdigest()
    # Git blobs may use LF while the retained Windows checkout uses CRLF.
    current = absolute(path).read_bytes()
    same = current == data
    CHECKS.append({"path": str(absolute(path)), "scope": scope, "status": "pass" if same else
        ("line_endings_only" if current.replace(b"\r\n",b"\n") == data.replace(b"\r\n",b"\n") else "mismatch"),
        "git_commit": commit, "git_blob_sha256": expected, "actual": digest(path), "exact_git_bytes": same})


def main():
    started = time.perf_counter()
    assert not (HERE/"PRESERVATION-MANIFEST-01.json").exists()
    bg1 = load("planning/review-assets/tether-ce-fixes-20261102/VALIDATION.json",
               "1792d94ed55e806dc0f3fdcbf8c08684b899ad5ddd6c8e420bde4aba63a4b90d", "BG01")
    mapping(bg1["inputs"], ROOT, "BG01 retained qualification inputs")
    check("planning/review-assets/tether-replay-correction-20261105/RELEASE-AGGREGATE-FINAL01.json",
          "d966fa3f74fa5ace029a041642a279bcacef346aa70df65f7bc048733835b01e", "BG02 corrected release")
    for version, attempt, frozen_sha, reconstruction_sha in (
        ("original", "02", "f7b4b09f4b144d84761e565452a19082dba16c778e81e422b314880aec531bc7", "aa6f39df533d65d7a8377e0b5ded5777fc04d7fa64f5f7477d3b4c7fdb69b50f"),
        ("patched", "01", "3ec7625fa601a517d8e2dd302228f9f465f35e877f79cd1a587a3a63b394a4fc", "db43e00ad671c74029a3954a56766a47f0e79085629764815fe895bac2e170c3")):
        root = ROOT/f"data/benchmark/tether-equal-policy-v2-{version}-20261105-attempt{attempt}"
        frozen = load(root/"FROZEN.json", frozen_sha, "BG02 "+version)
        mapping(frozen["bundles"], root/"bundles", "BG02 "+version+" candidates/sources")
        inventory(root/"bundles", frozen["bundles"], "BG02 "+version+" bundle files")
        dirs = {p.relative_to(root/"bundles").as_posix() for p in (root/"bundles").rglob("*") if p.is_dir()}
        assert dirs == set(frozen["bundle_directories"])
        mapping(frozen["sources"], ROOT, "BG02 "+version+" frozen sources")
        check(root/"oracle.json", frozen["oracle_pin"], "BG02 oracle")
        check(root/"trusted-runtime.json", frozen["trusted_runtime_pin"], "BG02 original runtime authority")
        recon = load(root/"INDEPENDENT-RECONSTRUCTION.json", reconstruction_sha, "BG02 independent reconstruction")
        execution = load(root/"comparison/EXECUTION.json")
        assert len(execution["records"]) == execution["terminal_cells"] == 1308
        for row in execution["records"]:
            check(root/"comparison"/row["cell"]/"RESULT.json", row, "BG02 "+version+" retained terminal cell")
        for family in frozen["installed_runtime"].values():
            mapping(family["files"], family["root"], "BG02 "+version+" historical installed payload")
    print("BG01/BG02 retained anchors and cells checked", flush=True)
    scifact = ROOT/"data/benchmark/scifact/native-20261105T234805Z-attempt01"
    sealed(scifact, "RECEIPT.json", "3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968", "BG03 native")
    sealed(ROOT/"data/benchmark/scifact/reconstruction-20261105-attempt01", "RECEIPT.json",
           "07e9d33fa0d8d989c458edd1a956b3a9e7b4701f5665e10e3fcdc0cf5fa30bed", "BG03 reconstruction")
    frozen = load(scifact/"FROZEN.json")
    mapping(frozen["runtime"]["task_code"], ROOT, "BG03 current task source equality")
    site = Path(frozen["runtime"]["executables"]["executable"]["path"]).parent.parent/"Lib/site-packages"
    for package in frozen["runtime"]["packages"].values():
        mapping(package["files"], site, "BG03 qualified installed RECORD payload")
    for field in ("protocol", "evaluator"):
        p = frozen[field];check(p["path"],p,"BG03 "+field)
    acquisition = load("planning/review-assets/tether-scifact-20261105/ACQUISITION-20261105.json")
    for item in acquisition["originals"]:
        check(item["file"], item, "BG03 original acquisition")
        check(item["receipt_file"], item["receipt_sha256"], "BG03 original transport receipt")
    for item in acquisition["selected_code_license_member_pins"]:
        with zipfile.ZipFile(ROOT/"data/raw/scifact_public/20261105-attempt01"/item["archive"]) as archive:
            raw = archive.read(item["member"])
        assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    generation_root = ROOT/"data/benchmark/labbench/generation-20261106T011303Z-attempt01"
    sealed(generation_root,"SEALED.json","46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447","BG04 generation")
    sealed(ROOT/"data/benchmark/labbench/evaluation-20261106T011303Z-attempt01","SEALED.json",
           "118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f","BG04 evaluation")
    generation = load(generation_root/"manifest.json")
    mapping(generation["code_pins"], ROOT, "BG04 generation source equality")
    collection_root = Path(generation["collection"]["path"])
    collection = load(collection_root/"manifest.json", generation["collection"]["manifest_sha256"], "BG04 collection manifest")
    mapping(collection["outputs"],collection_root,"BG04 complete retained collection outputs")
    inventory(collection_root,collection["outputs"],"BG04 collection",exclusions=("manifest.json","COMPLETE.json","SEALED.json"))
    mapping(collection["code_pins"],ROOT,"BG04 collection source equality")
    raw_root=ROOT/"data/raw/labbench_public/20261106-attempt01"
    acquisition=load(raw_root/"ACQUISITION.json")
    for item in acquisition["files"]:
        check(raw_root/item["path"],item,"BG04 original acquisition")
    model=generation["model_receipt"]
    check(model["path"],model["sha256"],"BG04 model acquisition receipt only")
    OMISSIONS.append("Model weight payloads and the broader D:/E: biological raw stores were not rehashed; the model receipt and all selected benchmark originals/outputs were checked.")
    print("BG03/BG04 native/source artifacts checked",flush=True)
    primary_root=ROOT/"data/benchmark/tether-inspect-20261106-attempt01"
    sealed(primary_root/"run","SEALED.json","d0ea739f5e4cf004cb37802df3ffe25dcf97e1756c0ca0a1c52293a147bf1f9c","BG05 primary")
    primary=load(primary_root/"freeze/FROZEN.json","dd2e5e3d07cac7e966a02bff34b9b2e2fb1ea30507d6d861630d76b57244e6b4","BG05 freeze")
    mapping(primary["input_pins"],ROOT,"BG05 full frozen input preservation")
    runtime_root=ROOT/"data/cache/tether-inspect-runtime-witnesses-20261106-attempt01"
    sealed(runtime_root/"runtime-stage","SEALED.json","92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f","BG05 runtime",key="files")
    runtime=load(runtime_root/"freeze/FROZEN.json","532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5","BG05 runtime freeze")
    mapping(runtime["code_pins"],ROOT,"BG05 runtime full frozen inputs")
    result=load(runtime_root/"runtime-stage/result.json")
    mapping(result["witness_outputs"],runtime_root,"BG05 native witness outputs")
    installed=ROOT/"data/cache/tether-inspect-env-attempt02/environment/Lib/site-packages"
    product=load("planning/review-assets/tether-inspect-20261106/environment/attempt02/PROJECT-SOURCE-COMPARISON.json")
    for item in product["sources"]:
        check(installed/item["path"],item,"current installed 85 product sources")
        repo=ROOT/("src" if item["path"].startswith("asof/") else "packages/tether/src")/item["path"]
        check(repo,item,"current maintained 85 product sources")
    legacy=load("planning/review-assets/tether-ce-fixes-20261102/legacy-preservation/PRESERVATION-20261102T192818Z.json")
    for item in legacy["checks"]:
        if item["name"] == "retained_hash":check(item["path"],item["expected_sha256"],"earlier release/downloader preservation")
    for name in ("paper/release/tether/RELEASE-RECORD.json","paper/release/WORKING-PACKET-RECORD.json"):
        record=load(name);check(record["archive"]["workspace_path"],record["archive"],"earlier immutable review packet")
    catalog=load("data/catalog/sources.json")
    providers=[p["provider_id"] for p in catalog["providers"]];datasets=[d["dataset_id"] for d in catalog["datasets"]]
    assert len(set(providers))==len(providers)==83 and len(set(datasets))==len(datasets)==178
    assert all(d["provider_id"] in providers and all(p in datasets for p in d["dependencies"]) for d in catalog["datasets"])
    for path in ("data/catalog/sources.json","tools/data/Start-DownloadBatch.ps1","tools/data/Watch-DownloadBatch.ps1",
                 "tools/data/Get-DownloadStatus.ps1","tools/data/Sync-DownloadCatalog.ps1"):
        tracked(path,"114fecf","baseline tracked catalog/worker/monitor")
    monitor=load("data/manifests/private/storage-config.json")
    monitor_observation={k:monitor.get(k) for k in ("monitor_enabled","monitor_process_id","monitor_session_id")}
    assert monitor_observation == {"monitor_enabled":False,"monitor_process_id":None,"monitor_session_id":None}
    # Acceptance/report history is preserved by Git, but mutable current documents
    # are not expected to match obsolete earlier acceptance-document hashes.
    selected_records=[
      "planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json",
      "planning/review-assets/tether-equal-policy-v2-20261105/completion/CLOSURE-20261105.json",
      "planning/review-assets/tether-inspect-20261106/stage/STAGE-ACCEPTANCE-01.json"]
    for path in selected_records:tracked(path,"eda8118","committed earlier acceptance records")
    mismatches=[r for r in CHECKS if r["status"] not in ("pass","line_endings_only")]
    report={"schema_version":1,"status":"pass_scoped_preservation" if not mismatches and all(i['status']=='pass' for i in INVENTORIES) else "findings_require_review",
      "at_utc":datetime.now(timezone.utc).isoformat(),"checks":CHECKS,"inventories":INVENTORIES,
      "mismatches":mismatches,"unique_files_hashed":len(CACHE),"unique_logical_bytes_hashed":sum(v[1]['bytes'] for v in CACHE.values()),
      "catalog":{"providers":83,"datasets":178,"references_resolve":True,"benchmark_families_not_in_biological_catalog":["SciFact","LAB-Bench LitQA2"],"inventory_authority":"separate experiment-specific acquisition/projection manifests"},
      "monitor_configuration_observation":monitor_observation,"monitor_scope":"Read-only configuration, not live or historical process attestation",
      "excluded_mutable_documents":sorted(MUTABLE),"omissions":OMISSIONS,
      "tests":"No tests, validators, providers or models reexecuted. Prior test counts remain version-specific retained evidence.",
      "audit_seconds":time.perf_counter()-started,"helper":digest(__file__)}
    payload=json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    with (HERE/"PRESERVATION-MANIFEST-01.json").open('xb') as stream:stream.write(payload)
    print(json.dumps({"status":report['status'],"checks":len(CHECKS),"unique_files":len(CACHE),"mismatches":len(mismatches),"inventory_mismatches":sum(x['status']!='pass' for x in INVENTORIES),"report_sha256":hashlib.sha256(payload).hexdigest()}))


if __name__ == '__main__':main()
