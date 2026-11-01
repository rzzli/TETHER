"""Tiny invented-bundle API probe; actual provider I/O is mocked to fail."""
import hashlib,json,platform,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
import pyarrow
from asof_p05_replay import audit_v1 as audit


def run():
    root=Path(__file__).resolve().parents[3]
    results=[]
    with tempfile.TemporaryDirectory(prefix="p09-fictional-cache-boundary-",dir=root/"data/cache") as temporary:
        base=Path(temporary)
        for has_caches in (False,True):
            bundle=base/("with-cache" if has_caches else "clean");bundle.mkdir()
            output=base/("empty-results-cache" if has_caches else "empty-results-clean");output.mkdir()
            payload=b"Invented metadata only.\n";(bundle/"README.md").write_bytes(payload)
            protocol=dict(schema_version=1,method="p09.public_reconstruction_protocol.v1",status="READY",actual_reconstruction_authorized=True,
                environment=dict(python=platform.python_version(),pyarrow=pyarrow.__version__,platform=sys.platform),
                files={"README.md":dict(path="README.md",sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload))})
            raw=audit.wire(protocol)+b"\n";(bundle/"protocol.json").write_bytes(raw)
            if has_caches:
                path=bundle/"source/replay/tests/__pycache__";path.mkdir(parents=True)
                for number in range(4):(path/("invented-"+str(number)+".pyc")).write_bytes(b"Invented excluded cache bytes")
            authority=dict(document=protocol,raw_bytes=raw,byte_sha256=hashlib.sha256(raw).hexdigest())
            with patch.object(audit,"native_projection",side_effect=AssertionError("Provider source access is forbidden in this probe")) as native, \
                 patch.object(audit,"_code_pins",side_effect=audit.AuditFailure("after_allowlist_marker")) as code:
                report=audit.audit_reconstruction(authority,bundle,base/"nonexistent-provider-root",output,time.monotonic()+30)
            expected="explicit_bundle_allowlist" if has_caches else "after_allowlist_marker"
            passed=report["unresolved_findings"]==[expected] and native.call_count==0 and code.call_count==(0 if has_caches else 1)
            results.append(dict(unlisted_cache_files=4 if has_caches else 0,passed=passed,findings=report["unresolved_findings"],
                provider_projection_calls=native.call_count,code_pin_calls=code.call_count,source_inclusive=report["source_inclusive"],
                logical_original_compressed_bytes_scanned=report["resources"]["logical_original_compressed_bytes_scanned"]))
    return dict(schema="p09.bytecache_allowlist_boundary_probe.v1",status="PASS" if all(x["passed"] for x in results) else "FAIL",results=results,
        interpretation="Four invented unlisted pyc files fail the explicit whole-bundle allowlist before code pins, report/reference processing or provider source projection. Clean metadata passes that boundary and deliberately stops at a mocked next-stage marker.",
        actual_original_reads=0,actual_source_audit_runs=0,production_mutations=0)


if __name__=="__main__":
    report=run();path=Path(__file__).with_name("BYTECACHE-ALLOWLIST-BOUNDARY-PROBE-v1.json")
    with path.open("xb") as stream:stream.write(json.dumps(report,indent=2).encode()+b"\n")
    print(json.dumps(report,indent=2))
