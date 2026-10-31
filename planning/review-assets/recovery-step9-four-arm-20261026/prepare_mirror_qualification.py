"""Declare one storage-only second qualification after the preserved terminal failure."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


mirror=json.loads((HERE/'MODEL-MIRROR.json').read_bytes())
closed=json.loads((HERE/'QUALIFICATION-FAILURE-CLOSEOUT-v1.json').read_bytes())
assert mirror['status']=='verified_identical_local_mirror' and len(mirror['items'])==35
assert closed['status']=='verified_partial_cells_not_completed_case' and closed['prior_tokenizer_children']==2
assert closed['new_tokenizer_children']==closed['actual_model_calls']==0
text=(HERE/'qualify_four_arm.py').read_text(encoding='utf-8')
text=text.replace('QUALIFICATION-PROTOCOL-v1.json','QUALIFICATION-PROTOCOL-v2.json')
text=text.replace('QUALIFICATION-FAILURE-v1.json','QUALIFICATION-FAILURE-v2.json')
old="allowed={normalized(a['path']) for a in assets}|{normalized(model/'acquisition.json')}\ndirectories={normalized(model),normalized(model/'runtime')}"
assert text.count(old)==1
text=text.replace(old,"allowed=set()  # The verified mirror is entirely on D; deny every E open.\ndirectories=set()")
old="          'protocol_sha256':"  # No match is used; report replacement below is exact.
old="    protected_payloads_read=False,scientific_validation='not_attempted')"
assert text.count(old)==1
text=text.replace(old,"    protected_payloads_read=False,scientific_validation='not_attempted',\n    qualification_attempt=2,prior_failed_attempt_tokenizer_children=2,\n    storage_mirror_sha256=protocol['mirror_sha256'],model_root=str(model))")
old="    assert state['children']==6 and result==replay"
assert text.count(old)==1
text=text.replace(old,old+"\n    assert len(state['E_files'])==0")
old="    report.update(status='failed',error_class=type(error).__name__,message=str(error),"
assert text.count(old)==1
text=text.replace(old,"    report.update(status='failed',error_class=type(error).__name__,message=str(error),\n        execution_outer_seconds=time.monotonic()-started,")
helper=HERE/'qualify_four_arm_v2.py'
with helper.open('x',encoding='utf-8') as stream:
    stream.write(text)
protocol=json.loads((HERE/'QUALIFICATION-PROTOCOL-v1.json').read_bytes())
protocol.update(created_at_utc=datetime.now(timezone.utc).isoformat(),qualification_attempt=2,
    helper_sha256=sha(helper),model_root=mirror['target'],
    mirror_sha256=sha(HERE/'MODEL-MIRROR.json'),
    previous_failed_protocol_sha256=sha(HERE/'QUALIFICATION-PROTOCOL-v1.json'),
    previous_failure_sha256=sha(HERE/'QUALIFICATION-FAILURE-v1.json'),
    previous_partial_closeout_sha256=sha(HERE/'QUALIFICATION-FAILURE-CLOSEOUT-v1.json'),
    storage_remediation_sha256=sha(HERE/'STORAGE-REMEDIATION.md'),
    prior_failed_attempt_tokenizer_children=2,maximum_new_tokenizer_children=6,
    maximum_children_across_these_two_qualification_attempts=8,
    factor_changed='Physical model asset root only; all35 mirrored files verified byte-identical',
    E_reads_during_second_attempt=0,no_third_attempt_authorized=True)
with (HERE/'QUALIFICATION-PROTOCOL-v2.json').open('x',encoding='utf-8') as stream:
    json.dump(protocol,stream,indent=2)
print(json.dumps(dict(status='storage_only_second_protocol_sealed',helper_sha256=sha(helper),
    protocol_sha256=sha(HERE/'QUALIFICATION-PROTOCOL-v2.json'),model_root=mirror['target'])))
