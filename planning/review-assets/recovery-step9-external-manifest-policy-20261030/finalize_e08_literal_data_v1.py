"""Bind unchanged independent literal DATA to final contract pins, no subject."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def save(path,value):
    with path.open('xb')as f:f.write((json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8'))
    return pin(path)


def vectors_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')


def main():
    draft_path=HERE/'E08-INDEPENDENT-LITERAL-CORPUS-DRAFT-v1.json';draft_pin=pin(draft_path)
    assert draft_pin['sha256']=='c10c24468f0877a7536e1549296038172b0a3610e5a2ffd1f998d04123f8b3ae'
    draft=json.loads(draft_path.read_bytes().decode('utf-8'))
    contract=pin(HERE/'E08-EXTERNAL-MANIFEST-POLICY-CONTRACT-v1.json')
    schema=pin(HERE/'E08-EXTERNAL-MANIFEST-POLICY-SCHEMA-v1.json')
    assert contract['sha256']=='a55b839b5b1fb038e8f0348d7fc5570abc36415db9a8f94ff6cb32269071f656'
    assert schema['sha256']=='6553a874cb34f4d312d5d1c5068c6a625ad9a6ae7cb56a050f3116bfa26b708a'
    framing_path=HERE/'E08-INDEPENDENT-LITERAL-FRAMING-PROOF-DRAFT-v1.json';framing_pin=pin(framing_path)
    assert framing_pin['sha256']=='05bc8e60b9685cfd3048e118e347f3c7283c4a54e0b5c4540a0dee9b5ba18246'
    framing=json.loads(framing_path.read_bytes().decode('utf-8'))
    assert framing['corpus']==draft_pin and framing['groups_passed']==6
    corpus=dict(draft)
    corpus.update(status='FROZEN_INDEPENDENT_PRECODE_LITERAL_DATA_NO_SUBJECT',
                  effective_contract=[contract,schema],preserved_readable_draft=draft_pin,
                  mutual_readiness='Both authors declared FINAL_READY on literal values and effective contract semantics before final named publication. Only metadata references/status change here.')
    assert vectors_bytes(corpus['vectors'])==vectors_bytes(draft['vectors'])
    assert corpus['vector_count']==len(corpus['vectors'])==52
    final_path=HERE/'E08-INDEPENDENT-LITERAL-CORPUS-v1.json'
    final_pin=save(final_path,corpus)
    reread=json.loads(final_path.read_bytes().decode('utf-8'))
    assert vectors_bytes(reread['vectors'])==vectors_bytes(draft['vectors'])
    report_count=sum(v['expected']['kind']=='REPORT'for v in corpus['vectors'])
    assert report_count==10
    provenance=dict(schema_version=1,status='FROZEN_LITERAL_PROVENANCE_NO_IMPLEMENTATION_OR_EXECUTION',
                    corpus=final_pin,contract=contract,schema=schema,preserved_draft=draft_pin,
                    author_helper=pin(HERE/'author_e08_literal_data_v1.py'),
                    framing_checker=pin(HERE/'check_e08_literal_framing_v1.py'),framing_proof=framing_pin,
                    finalizer=pin(__file__),authoring_scope=corpus['authoring_scope'],
                    vector_count=52,expected_report_count=10,expected_refusal_count=42,
                    exact_vector_data_unchanged=True,
                    vector_data_ascii_json_sha256=hashlib.sha256(vectors_bytes(corpus['vectors'])).hexdigest(),
                    construction_boundary='All 52 binding values satisfy the selected bounded immutable constructor shell: correct 6 named fields, four exact lists <=256, exact pin entry keys, JSON scalar leaves. Semantic/domain/length/duplicate/role/graph refusals therefore prospectively reach Core policy after original sample. No typed object was forged or executed.',
                    independent_expectations='Statuses/refusal codes manually assigned by the independent fixture author; no graph solver, policy implementation or reference admission engine exists. Automation is standard JSON framing/hashes and declared field counts only.',
                    canonical_context='Only request.binding+request.envelope contribute to canonical bytes/digests. Harness-only entry_basis_pins independently fixes future valid/mismatched FileSpec vectors; it never substitutes for genuine typed EntryPlan ownership.',
                    framing_groups_passed=6,
                    coverage=['Allowed external TCB/prior metadata and downstream current provenance; current-ID root spoof refusal.',
                              'Acyclic direct/transitive/nonbasis current ancestry; self/mutual/transitive/static and current-output cycles.',
                              'Unknown/identical/conflicting nodes, duplicate edges, duplicate/conflicting/cross-role pins and binding role/list mismatch.',
                              'AUTHORING planned/unbuilt descendants versus EXECUTION refusal, including an unselected unbuilt node.',
                              'All seven metadata bounds at equality and one over; exact 131072/131073 canonical bytes and 4096/4097 declared edges.',
                              'Two independently declared valid-but-unequal EntryPlan basis count/pin vectors.',
                              'No approved flag, no report fields capable of minting live owner/ref/lease/child/actual admission.'],
                    excluded_claims=['No actual constructor/Core/clock/callback/file/native/physical behavior was exercised.',
                                     'Reports retain 12 declared data fields, not launcher authentication, file admission or runtime permission.',
                                     'Prepared-versus-issued late report, source identity/foreign namespace, first-open barrier and cleanup compatibility need actual later integration tests.',
                                     'E16 historical factories/native25/full roster/new84/resources/science/humans remain pending.'],
                    activity=dict(subject_implementation=False,subject_imports=0,subject_runs=0,
                                  original_targets_followed=False,native_activity=False),qualification=False)
    provenance_pin=save(HERE/'E08-INDEPENDENT-LITERAL-PROVENANCE-v1.json',provenance)
    print(json.dumps(dict(corpus=final_pin,provenance=provenance_pin,vectors=52,reports=10,refusals=42)))


if __name__=='__main__':main()
