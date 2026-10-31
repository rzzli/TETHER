"""Record the exact v2 source/pure resolution; no reviewed code is executed."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
REPORT=HERE/'VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v2.json'
NOTE=HERE/'VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v2.md'
EXPECTED={
    'deterministic_verifier_v2.py':'98ef68ee1bd0a5bb8fd2cf2c780a0dd0c294f7f24654d169280831cca5d4b725',
    'check_deterministic_verifier_v2.py':'17ab0c8f9f5254dc88cb440d7fa8c992b03af170733a47cd2f9f0a1794f4c55a',
    'VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v2.json':'f6ddcadf030230dc24672836b2a1d430286148fc06169b6210a5f3af79ba6a10',
    'VERIFIER-RECOVERY-IMPLEMENTATION-v2.md':'d431620487b31c90c33a989fcfad236a85aaa2a4887c348611e3ff4bf9f9441a',
    'VERIFIER-OPEN-RETURN-REGRESSION-BEFORE-v2.json':'7cd1ab36c772256e982d8e766aad8ab4792be6def2161b7fef83482e7b034085',
    'VERIFIER-RECOVERY-INDEPENDENT-HOLD-SUPPLEMENT-v1.json':'b61dc485f5cae14499658a4cc22deced68fad3f95476c44028edf02daa5dca2c',
    'VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v1.json':'cdc450bd151d87251117e64491ff5850af90eb231b970c22d9b8225d2f04f1e8',
    'deterministic_verifier_v1.py':'b15142efac14d8beafc19f9c71b5d594737063303f5096f627e08e7f04adac4b',
    'VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v1.json':'4ac3271c3b488fae45ed266585164aed700e1486f344d6eb2bc1f6f719e2ce65',
    'VERIFIER-RECOVERY-DESIGN-CONTRACT-v2.json':'7bff14386239d908ca33fd1a11214e95d90010b312aed3d23ac07b9fd69e3c6f',
    'retain_verifier_pure_proofs_v2.py':'4d7c572c6640ce1a557eae1916db3a9766bbec59dd35e9bccd25446ee8ea7638',
}
def pin(path):
    path=Path(path);assert path.parent==HERE,'New-phase source/evidence only'
    raw=path.read_bytes();raw.decode('utf-8','strict')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def tree(name):return ast.parse((HERE/name).read_text(encoding='utf-8'))
def owner_methods(parsed):
    cls=next(n for n in parsed.body if isinstance(n,ast.ClassDef) and n.name=='_Owner')
    return {n.name:ast.dump(n) for n in cls.body if isinstance(n,ast.FunctionDef)}
def assigned(parsed,name):return next(ast.dump(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))

def main():
    assert not REPORT.exists() and not NOTE.exists(),'Preserve previous review'
    artifacts={}
    for name,expected in EXPECTED.items():
        row=pin(HERE/name);assert row['sha256']==expected;artifacts[name]=row
    proof=load('VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v2.json')
    assert proof['result']['methods']==23 and proof['result']['failures']==proof['result']['errors']==0 and proof['result']['passed'] is True
    for key in ('source','checker','retention_writer','previous_source','previous_proof','initial_ownership_witness','independent_hold','contract'):
        assert proof[key]==pin(Path(proof[key]['path']))
    before=load('VERIFIER-OPEN-RETURN-REGRESSION-BEFORE-v2.json')
    assert before['result']['methods']==4 and before['result']['failures']==3 and before['result']['errors']==0
    assert before['source']==artifacts['deterministic_verifier_v1.py']
    assert before['checker']==pin(Path(before['checker']['path']))
    old,new=tree('deterministic_verifier_v1.py'),tree('deterministic_verifier_v2.py')
    old_methods,new_methods=owner_methods(old),owner_methods(new)
    unchanged=sorted(name for name in new_methods if name in old_methods and new_methods[name]==old_methods[name])
    changed=sorted(name for name in new_methods if name not in old_methods or new_methods[name]!=old_methods[name])
    assert unchanged==proof['owner_AST_unchanged_methods'] and changed==proof['owner_AST_changed_methods']
    assert assigned(old,'GATES')==assigned(new,'GATES') and assigned(old,'CHECKS')==assigned(new,'CHECKS')
    checker_tree=tree('check_deterministic_verifier_v2.py')
    methods=[n.name for c in checker_tree.body if isinstance(c,ast.ClassDef) and c.name=='Checks'
        for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    assert len(methods)==23
    assert {'test_open_return_explicit_ownership_only','test_open_failure_known_no_transferred_handle',
        'test_owned_metadata_failure_still_closed_once','test_factories_have_reserved_and_return_witnesses'}<=set(methods)
    source=(HERE/'deterministic_verifier_v2.py').read_text(encoding='utf-8');lines=source.splitlines()
    at=lambda text:next(i+1 for i,line in enumerate(lines) if text in line)
    result=dict(schema_version=1,status='CLEAR_V2_SOURCE_PURE_ORCHESTRATION_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        review_type='Independent AI engineering source/evidence review; no scientist or live-profile qualification',
        artifacts=artifacts,
        resolution=[dict(hold_id='malformed_open_cannot_transfer_ownership',source_line=at('if type(opened) is OpenReturn and opened.owned is True'),
            finding='Resolved: exact explicit owned-success with nonnull handle alone transfers a lease before later metadata/time checks. Exact OpenFailure transfers no handle. Null, foreign, typed-null and invalid ownership flags remain unknown without a guessed close.',
            evidence='Four ownership-focused latest methods pass. Preserved v1before-witness has3unsafe-close failures and1late-valid-owned control pass.'),
            dict(hold_id='durable_factory_stage_attempts',source_line=at('authority = owner.stage('),
            finding='Resolved: all3post-reservation factories use existing stage reservations and return/unknown observations under the same owner clock. Late observed factory returns remain visible without a gate; throwing factories keep prior durable attempt.',
            evidence='test_factories_have_reserved_and_return_witnesses covers all3factories with throwing/late and complete paths. Six added events stay inside fixed64allowance.')],
        prior_limited_clear_and_hold_preserved=True,remaining_material_source_blockers=[],
        AST_checks=dict(unchanged_owner_methods=unchanged,changed_owner_methods=changed,gate_and_checker_order_unchanged=True),
        evidence=dict(author_methods_passed=23,author_failures=0,author_errors=0,reviewer_reruns=0,
            old_witness_methods=4,old_witness_failures=3,old_witness_errors=0,
            pure_test_timing='Measured elapsed0.0 is clock-resolution output; runnertext0.015s. No real-time resource-fit inference.'),
        owner_bounds=dict(total_seconds=300,work_seconds=295,finalization_reserve_seconds=5,files=256,events=2048,joint_reservation=1728),
        retained_conditions=['Original clock/gates/immutable context/streamed capture/late-return bookkeeping/once-only cleanup/final-seal veto mechanics retain the completed v1source review.',
            'Malformed ownership may conceal an untransferred resource; unknown is preserved and never represented as successful cleanup or no side effects.',
            'The platform-neutral engine trusts its source-bound port to validate native invalid-handle sentinels before minting an owned-success acknowledgment.',
            'Owner-issued proofs/context block accidental or serialized cross-run reuse, not malicious in-process Python code.'],
        remaining_unimplemented=['First-clock real bootstrap before component/source imports','Exact approved live authority and original-file adapter',
            'Real archive/journal/raw-resource/core checker implementations','Bounded real complete-profile verification and resource feasibility'],
        scientific_and_historical_limits='No old failed experiment, incomplete external verifier, native conformance gate or scientific outcome is reclassified. No clinical probabilities/full-mask/inference claim.',
        approval_basis='Delivered root source/pure v2 instruction, as transparently recorded by proof.root_approval; no separate root decision file is invented.',
        activity=dict(reviewed_source_tests_or_helpers_executed=0,old_original_or_payload_reads=0,SDK_target_compiler_calls=0,source_test_edits=0),
        execution_authorized=False,real_profile_qualified=False,scientific_validation='not_established',recorder=pin(Path(__file__)))
    with REPORT.open('x',encoding='utf-8') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
    text='''# Verifier recovery v2: independent source/pure resolution

**Clear within source/pure orchestration scope.** The [machine review](VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v2.json) binds source `98ef68ee…a5d4b725`, checker `17ab0c8f…94f4c55a` and the retained 23-method passing proof. The earlier [limited review](VERIFIER-RECOVERY-INDEPENDENT-PEER-REVIEW-v1.json) and [HOLD supplement](VERIFIER-RECOVERY-INDEPENDENT-HOLD-SUPPLEMENT-v1.json) remain unchanged. No reviewed source, helper or test was executed by this reviewer.

Both held boundaries are resolved. Only an exact `OpenReturn` with `owned is True` and a nonnull handle transfers ownership; it is registered before deadline or identity checks. Exact `OpenFailure` means known failure with no transferred handle. Malformed/null/unowned observations remain unknown, create no guessed lease and trigger no close. A later metadata failure or late valid-owned return still closes once. The saved v1 witness retains three unsafe-close failures and one passing late-valid-owned control; the v2 suite passes these boundaries and the remaining earlier regressions.

Authority, file-port and checker factories now have durable reserved/returned-or-unknown stages after exclusive reservation. These six added events fit the existing 64-event allowance. AST comparison confirms eleven owner methods and fixed gate/checker order are unchanged; the four changed methods contain only ownership/I/O outcome bookkeeping and reporting. The 300/295/5-second clock, 256-file/2,048-event caps, immutable owner-local captured bytes, no ready-marker authority, once-only cleanup and final-clock/seal veto remain in scope.

This is not a live verifier acceptance. A future source-bound port must validate native handle sentinels before issuing its ownership acknowledgment. The actual first-clock bootstrap, fixed live authority/original-file adapter and real archive/journal/resource/core checkers are still unimplemented and require review. Synthetic timing establishes no real 300-second fit. Unknown ownership may conceal an untransferred resource; it is never treated as successful cleanup or proof of no side effects.

No old originals, source inputs or CPU/GGUF/pack payloads were opened or rehashed. No SDK, target, compiler or native operation occurred. The failed recognition run and incomplete external verifier remain unchanged. Scientific validity, numerical predictions and full-mask/inference qualification are outside this review.
'''
    for target in re.findall(r'\]\(([^)]+)\)',text):assert (HERE/target).is_file()
    with NOTE.open('x',encoding='utf-8',newline='\n') as out:out.write(text)
    print(json.dumps(dict(status=result['status'],report=pin(REPORT),note=pin(NOTE),author_methods=23,reviewer_reruns=0)))
if __name__=='__main__':main()
