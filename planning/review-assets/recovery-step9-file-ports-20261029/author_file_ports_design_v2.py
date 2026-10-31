"""Versioned design metadata only; no platform binding or file-port implementation."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE / 'FILE-PORTS-DESIGN-CONTRACT-v1.json'
OUT = HERE / 'FILE-PORTS-DESIGN-CONTRACT-v2.json'
FREEZE = HERE / 'FILE-PORTS-DESIGN-FREEZE-v2.json'

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')

def main():
    assert not OUT.exists() and not FREEZE.exists(), 'Preserve design versions'
    old_pin = pin(OLD)
    assert old_pin['sha256'] == 'bc73427712614a6652e37924a6ff91646c1b8a881e5928cd98b200516bce7a05'
    old = json.loads(OLD.read_text(encoding='utf-8'))
    peer_path = HERE / 'FILE-PORTS-INDEPENDENT-DESIGN-REVIEW-v1.json'
    assert pin(peer_path)['sha256'] == '08f7d4c0b4f73fa59398f14e8789b6b2f8bda5e10ac986523e0e8236f94bc196'
    semantic = copy.deepcopy(old['semantic_contract'])
    semantic['port_design_id'] = 'finite-original-file-and-exclusive-sink-v2'
    semantic['admitted_paths']['metadata_directory_nodes'] = dict(
        union=['ordinary_admitted_directory', 'CanonicalDriveRoot'],
        ordinary='Existing strict canonical admitted directory spelling with at least one component; no leaf/role grammar relaxation.',
        drive_root=dict(
            exact_record_shape=dict(kind='canonical_drive_root', path='approved uppercase drive letter, colon, one backslash'),
            path_regex=r'^[A-Z]:\\$', utf16_units=3,
            derivation='Purely derive the uppercase drive root from already admitted canonical ancestor paths; preserve original source spelling separately. Only roots of the exact approved C/D roster may occur. No discovery, extra drive authority or filesystem normalization.',
            identity='Use the existing ASCII-only case/slash collision key and count each distinct canonical root once in U.',
            permitted_operation='One existing GetFileAttributesExW/GetFileExInfoStandard0 ancestor attribute observation, included in U.',
            required_result='Known TRUE, directory attribute set and reparse attribute clear. Failed/undefined/late/unknown prevents ancestry completion; no fallback or hidden extra attempt.',
            prohibited_uses=['original FileSpec', 'output file leaf', 'output namespace leaf', 'scan root', 'FindFirst/FindNext traversal', 'scan-discovered authority', 'arbitrary drive discovery'],
        ),
    )
    semantic['admitted_paths']['ancestor_index'] += ' CanonicalDriveRoot metadata-only nodes explicitly represent the approved drive-root ancestors; each counts once inside U and is never a file leaf or scan root.'
    semantic['admitted_paths']['long_path_limit'] = '4096 units is an admission/buffer ceiling, not proof of Windows long-path policy support. Documented failure remains negative; no prefix, registry, OS-policy or spelling fallback.'
    semantic['metadata_scans']['ancestor_calls'] += ' The U term explicitly includes each unique CanonicalDriveRoot; roots receive attributes only, never enumeration. No additional root-call allowance is introduced.'
    semantic['metadata_scans']['iterator'] += ' A CanonicalDriveRoot is never an admitted scan directory; no root enumeration is permitted.'
    semantic['output']['registry_only_observations'] = 'Per-output API/write/flush/close attempts and returns are finite owner-registry records only. They do not append additional journal events beyond the declared K/F_fixed/failure plan; no recursive journal logging.'
    semantic['output']['late_known_write'] = 'A late returned successful positive count remains known-written evidence at its retained offset. Preserve the prepared immutable record and returned slice; its hash may remain pending. No post-hard-cutoff hashing, completed artifact pin or positive publication is inferred.'
    semantic['admission_formulas']['symbols']['U'] = 'Unique admitted directorynodes incl each CanonicalDriveRoot and prospectiveoutputleaf, <=1024; roots are attributes-only and counted once'
    semantic['required_fake_vectors'] += [
        'Approved C:\\ and D:\\ CanonicalDriveRoot ancestors each count once in U; duplicate ancestor references add no extra attribute attempt',
        'CanonicalDriveRoot rejected as original/output leaf, scan root or scan-discovered new authority; existing leaf grammar remains unchanged',
        'Bare-drive, lowercase noncanonical root descriptor, relative, UNC, device or unapproved root rejected without fallback',
        'Failed/undefined/unknown root attributes block ancestry completion under the existing U budget',
        'Output port registry observations consume no recursive journal events; late known write retains immutable bytes/offset with hash pending and no positive pin',
    ]
    unchanged_top_fields = []
    changed_top_fields = []
    for key in old['semantic_contract']:
        (unchanged_top_fields if semantic[key] == old['semantic_contract'][key] else changed_top_fields).append(key)
    assert sorted(changed_top_fields) == sorted(['port_design_id', 'admitted_paths', 'metadata_scans', 'output', 'admission_formulas', 'required_fake_vectors'])
    assert semantic['admitted_paths']['grammar'] == old['semantic_contract']['admitted_paths']['grammar']
    assert semantic['admitted_paths']['roles'] == old['semantic_contract']['admitted_paths']['roles']
    for key in ('events', 'event_meaning', 'API_total', 'mini_plan', 'full_plan'):
        assert semantic['admission_formulas'][key] == old['semantic_contract']['admission_formulas'][key]
    assert semantic['ABI'] == old['semantic_contract']['ABI']
    assert semantic['slots'] == old['semantic_contract']['slots']
    assert semantic['trusted_origin'] == old['semantic_contract']['trusted_origin']
    assert semantic['output']['quota'] == old['semantic_contract']['output']['quota']
    semantic_hash = hashlib.sha256(canonical(semantic)).hexdigest()
    basis = dict(old['basis'])
    for name in ('FILE-PORTS-DESIGN-CONTRACT-v1.json', 'FILE-PORTS-DESIGN-FREEZE-v1.json',
                 'FILE-PORTS-INDEPENDENT-DESIGN-REVIEW-v1.json', 'FILE-PORTS-DESIGN-DELTA-v2.md'):
        basis[name] = pin(HERE / name)
    record = dict(
        schema_version=2, status='CORRECTED_DESIGN_FOR_ROOT_AND_INDEPENDENT_REVIEW_BEFORE_CODE',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(), semantic_contract=semantic,
        semantic_sha256=semantic_hash, basis=basis, author=pin(Path(__file__)),
        root_authorization='Delivered root message authorizes separately versioned design-v2 only: metadata DriveRoot attributes-only counted U; leaf/output/scan grammar unchanged; preserve v1; no fileport/API implementation.',
        exact_delta_scope='One required metadata-directory grammar correction plus previously reviewed normative registry/late-write/long-path clarifications.',
        source_and_docs_activity='This writer reads retained design/review metadata only and writes new design metadata. No new source qualification, documentation/network read, API/SDK/ctypes construction, original-input or payload operation.',
    )
    write(OUT, record)
    write(FREEZE, dict(
        schema_version=2, status='DESIGN_FROZEN_FOR_REVIEW_NO_PORT_IMPLEMENTATION',
        contract=pin(OUT), author=pin(Path(__file__)), semantic_sha256=semantic_hash,
        prior_contract=old_pin, peer_basis=pin(peer_path),
        changed_semantic_top_fields=changed_top_fields, unchanged_semantic_top_fields=unchanged_top_fields,
        leaf_grammar_and_roles_unchanged=True, typed_API_structures_flags_unchanged=True,
        event_API_formulas_and_output_quotas_unchanged=True, original_clock_and_slot_ownership_unchanged=True,
        direct_file_exports=14, Win32_API_calls=0, old_original_or_source_qualification=0,
        CPU_GGUF_oldpack_operations=0, implementation_authorized=False, execution_authorized=False,
    ))
    print(json.dumps(dict(contract=pin(OUT), freeze=pin(FREEZE), semantic_sha256=semantic_hash)))

if __name__ == '__main__':
    main()
