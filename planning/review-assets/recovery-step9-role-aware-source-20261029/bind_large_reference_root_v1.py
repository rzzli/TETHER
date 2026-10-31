"""Root's finite metadata-only binding for independent prefix preparation."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
P = H.parent / 'recovery-step9-role-aware-producer-20261029'
S = H.parent / 'recovery-step9-shared-owner-20261029'

def pin(path, expected=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None:
        assert digest == expected, path.name
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=digest)

helper = pin(H / 'prepare_role_aware_large_reference_v1.py', '773860bbc34e5c4b1e1ee9052da02f64f054ef930076e42c61262e49dabf484e')
peer = pin(H / 'ROLE-AWARE-LARGE-REFERENCE-INDEPENDENT-ALLOCATION-REVIEW-v1.json', '2bf0f301058745d6fdf23978e74b4e8ba1615d48d5ec463fe3100efd9d5561d4')
assert json.loads(Path(peer['path']).read_bytes())['material_blockers_reference_preparation'] == []
inputs = {
    'size_vector': pin(P / 'RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json', '3a7e00e9cc812f7fcf0676c70704c65ab35565cac4b6a652fe06fad42c890c75'),
    'tiny_cohort': pin(S / 'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json', 'eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8'),
    'implementation_slice': pin(P / 'ROLE-AWARE-PRODUCER-IMPLEMENTATION-SLICE-v1.json', '35484f8a35d29bc108712dc7279e1cbbcb4b76470d28a6c1241895bbc4fd3f9c'),
}
scope = dict(
    schema_version=1,
    status='ROOT_AUTHORIZED_REFERENCE_PREPARATION_ONLY',
    helper=helper, independent_code_peer=peer,
    small_acceptance=pin(H / 'ROLE-AWARE-PRODUCER-SMALL-GATE-ACCEPTANCE-v4.json', '096f5781b0c5d92208fcbd6a0da21528939f668be62ccd573c433ae7517b7445'),
    allocation_audit=pin(H / 'ROLE-AWARE-PRODUCER-ALLOCATION-LIFETIME-AUDIT-v4.json', '9d6f0240b9c2bf2cba533c64775109f8df58736cb1c2c332c307cac52faf7871'),
    execution='One exact helper invocation in a separate pinned Python process. Independent periodic SHA256 prefix references only; 213 historical size values and209 frozen fictional bytes form216 invented descriptors.',
    memory='One1MiB periodic block plus256B seed and bounded metadata. No whole-bulk bodies or source-owned values are used as an oracle. Actual heap/RSS remain unknown.',
    clock='Own original reference-main sample +300s, including metadata processing. Separate from future producer original entry clock; cooperative, no hard callback-free hang or persistence-time bound.',
    first_result='Exclusive attempt and result. Keep partial hashes on failure; descriptors None and no producer advancement. No timing retry.',
    outputs=['ROLE-AWARE-LARGE-REFERENCE-ATTEMPT-v1.json', 'ROLE-AWARE-LARGE-REFERENCE-PROOF-v1.json'],
    not_authorized=['producer source imports or calls', 'actual large producer run', 'original or protected targets', 'SDK/ctypes/Win32/compiler/native/model calls', 'downloads, paid calls, application/default changes'],
    provider_spend_usd=0,
)
scope_path = H / 'ROLE-AWARE-LARGE-REFERENCE-EXECUTION-SCOPE-v1.json'
binding_path = H / 'ROLE-AWARE-LARGE-REFERENCE-BINDING-v1.json'
for name in scope['outputs']:
    assert not (H / name).exists(), name
with scope_path.open('x', encoding='utf-8', newline='\n') as out:
    json.dump(scope, out, sort_keys=True, indent=2); out.write('\n')
binding = dict(schema_version=1, mode='INDEPENDENT_LARGE_PERIODIC_PREFIX_REFERENCE_V1',
               deadline_seconds=300, execution_scope=pin(scope_path), inputs=inputs, actual_runner=helper)
with binding_path.open('x', encoding='utf-8', newline='\n') as out:
    json.dump(binding, out, sort_keys=True, indent=2); out.write('\n')
print(json.dumps(dict(scope=pin(scope_path), binding=pin(binding_path))))
