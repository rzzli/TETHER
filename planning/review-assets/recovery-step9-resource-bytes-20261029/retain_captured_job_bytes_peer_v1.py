"""Publish the bounded independent source/pure review; no runtime artifact input."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'CAPTURED-JOB-BYTES-INDEPENDENT-PEER-v1.json'
MD=HERE/'CAPTURED-JOB-BYTES-INDEPENDENT-PEER-v1.md'
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    assert not OUT.exists() and not MD.exists(),'Preserve peer review'
    proof_path=HERE/'CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    assert pin(proof_path)['sha256']=='cda50dd118215386fc29a97e28b9a1680b91da2e89fb404b14f1ae241755662f'
    assert proof['status']=='passed' and proof['methods']==7 and proof['counts']==dict(literal_captures=16,literal_phases=18,independent_vectors=49)
    for item in proof['inputs'].values():assert pin(Path(item['path']))==item,'Frozen component/evidence changed'
    text='''# Captured Job bytes: independent source and pure review

The exact decoder `fd655c8b…` has no material blocker within the frozen contract's narrow byte/selected-phase scope. This is not a live Job, source-provenance, process-ownership or resource qualification.

I read the complete component, contract, fixture expectations and author checker/proof. My [separate checker](check_captured_job_bytes_peer_v1.py) passed seven methods: all 16 frozen captures and 18 phase expectations, plus 49 independent vectors. The [retained proof](CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json) binds the exact source/evidence and confirms no changes to the author's files.

The independent vectors construct bytes with explicit little-endian `int.to_bytes` fields. They check signed64 time extremes, unsigned32 counter maximum, unsigned64 PID extremes, byte offsets, reverse-endian corruption, 16-PID capacity, variable returned lengths and nonzero unused tails. An empty list may report eight bytes; a one-PID list may report 16. The contract permits other lengths within the complete-prefix/allocated-frame range; this review does not assert which lengths an OS will produce.

False API returns retain undefined fields despite plausible bytes/error0. Missing queries remain missing; an independently valid other query remains decoded. Bad flags/hex/lengths stay bounded and malformed. Source summary booleans cannot match integer fields through Python coercion. Invalid query windows retain decoded data while blocking raw completeness. Valid sequential-but-inconsistent accounting/PID tuples remain mismatches with race/unknown-cause scope.

The selected-phase checker requires the exact decoder-result type, a declared phase and a strict PID. It retains immutable state with fresh detached dictionaries/lists. Its matched result is only a match to the selected tuple; resource qualification is always false, atomic-snapshot evidence is always false, and non-atomic race possibility remains true. Public Python dataclasses are ordinary API types, not hostile-Python isolation or source-authentication capabilities.

There was no actual SDK/OS query, child, native/model call, original payload or old-report replay. A future report gate must still bind captured bytes to source/owner/journal/phase chronology, raw limits/peaks, output accounting, reaping, cleanup, clock and terminal seals. Existing negative experiments and incomplete external verification remain unchanged.
'''
    with MD.open('x',encoding='utf-8') as out:out.write(text)
    value=dict(schema_version=1,status='CLEAR_SOURCE_PURE_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        source=proof['inputs']['captured_job_bytes_v1.py'],contract=proof['inputs']['CAPTURED-JOB-BYTES-CONTRACT-v2.json'],
        independent_checker=proof['checker'],independent_proof=pin(proof_path),author_inputs=proof['inputs'],note=pin(MD),recorder=pin(Path(__file__)),
        checks=proof['counts'],methods=7,material_findings=[],source_pins_unchanged=True,
        source_review=['Exact48byte <qqqqIIII signed64/unsigned32 layout','Exact136byte allocated PID frame; complete variable returned prefix; unsigned64 IDs; unused tail retained but not extraPIDs',
            'Undefined/missing/malformed separated; strict bool/counter/source-view handling','Non-atomic phase tuple mismatch retained, not normalized','Ordinary immutable result/fresh serialization/strict typed phase boundary'],
        resource_qualified=False,original_source_qualification=False,actual_old_report_replay=False,SDK_OS_native_calls=0,CPU_GGUF_oldpack_operations=0,
        runtime_or_execution_authority=False,hostile_Python_security_claim=False,
        remaining='Actual original-source/owner provenance, journal/report binding, limits/peaks, captures/reaping, cleanup/seals and one-clock full external verification remain separate gates.')
    with OUT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(review=pin(OUT),note=pin(MD))))
if __name__=='__main__':main()
