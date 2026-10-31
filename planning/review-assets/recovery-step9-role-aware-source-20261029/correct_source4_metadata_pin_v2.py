"""Retain and correct one metadata filename error; no source/test execution."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
def pin(p):
    b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

old=H/'freeze_role_aware_v4_extension_correction_v1.py'
assert pin(old)['sha256']=='53e1716ba89e627eb9ffbed2baf810d77fab7374780b07ba7287c4b0c85acfbb'
actual=pin(H/'ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v1.json')
assert actual['sha256']=='321524454289ad0202672d359228fee5591e2946566fb5ca70cda8e5c3488bd8'
failure=dict(schema_version=1,status='METADATA_FREEZE_STOPPED_BEFORE_PUBLICATION',helper=pin(old),
    error_class='FileNotFoundError',attempted_basename='ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v3.json',
    verified_actual=actual,reason='Native localization record version is1, not3. This was a metadata path transcription error, not a source/test result.',
    preparation_outputs_published_before_failure=0,subject_imports=0,subject_runs=0,
    unchanged_test=pin(H/'role_aware_producer_extension_tests_v2.py'),unchanged_runners=[pin(H/'run_role_aware_independent_v8.py'),pin(H/'run_role_aware_extensions_v5.py')])
p=H/'ROLE-AWARE-SOURCE4-PREPARATION-FAILURE-v1.json'
with p.open('xb') as f:f.write((json.dumps(failure,sort_keys=True,indent=2)+'\n').encode())
t=old.read_text(encoding='utf-8')
assert t.count('ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v3.json')==1
t=t.replace('ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v3.json','ROLE-AWARE-EXTENSIONS-FIRST-INDEPENDENT-LOCALIZATION-v1.json')
t=t.replace("root_choice=choice,source_pause=pause,source_pins_metadata=src,old_test=before", "root_choice=choice,preserved_metadata_helper_failure=pin(H/'ROLE-AWARE-SOURCE4-PREPARATION-FAILURE-v1.json'),source_pause=pause,source_pins_metadata=src,old_test=before")
with (H/'freeze_role_aware_v4_extension_correction_v2.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print(json.dumps(dict(failure=pin(p),corrected_helper=pin(H/'freeze_role_aware_v4_extension_correction_v2.py'))))
