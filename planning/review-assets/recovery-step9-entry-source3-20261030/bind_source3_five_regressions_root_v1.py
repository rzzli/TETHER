"""Bind only reviewed Source3 metadata; no subject execution or lineage crawl."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def pin(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('review asset outside repository')
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8'))


def main():
    peer = pin(sys.argv[1])
    if peer['sha256'] != sys.argv[2]:
        raise RuntimeError('independent harness peer changed')
    outline_path = HERE / 'ENTRY-SOURCE3-REGRESSION-BINDING-OUTLINE-v1.json'
    outline_pin = pin(outline_path)
    if outline_pin['sha256'] != '092f66634adff88ab9a8b15cc7d0270473adbb2a4ef1314353220eced568d072':
        raise RuntimeError('frozen outline changed')
    binding = json.loads(outline_path.read_bytes())
    for value in [binding['source_pause'], binding['inputs'], binding['preparation'],
                  *binding['source_map'].values(), *binding['harness'].values()]:
        if pin(value['path']) != value:
            raise RuntimeError('changed preparation pin: ' + value['path'])
    freeze = pin(HERE / 'ENTRY-SOURCE3-REGRESSION-FREEZE-v1.json')
    if freeze['sha256'] != 'fb8987fffc4074e9884b7e168a95c6e28c72be8f874d56ffce39c0306ae0d5f2':
        raise RuntimeError('frozen preparation changed')
    source_peer = pin(HERE / 'ENTRY-SOURCE3-CORRECTION-INDEPENDENT-STATIC-REVIEW-v1.json')
    if source_peer['sha256'] != '815b9c0729f876c2a58e982b366c26a39c3d49712a4126e1396f7c2242495261':
        raise RuntimeError('source correction peer changed')
    scope = dict(schema_version=1, status='ROOT_AUTHORIZED_SOURCE3_FIVE_REGRESSIONS_ONLY',
                 source_pause=binding['source_pause'], preparation=binding['preparation'],
                 freeze=freeze, outline=outline_pin, independent_harness_peer=peer,
                 independent_source_peer=source_peer, methods=binding['methods'],
                 execution='Run exact frozen five checks once in five fresh Source3 synthetic worlds. Preserve all first outcomes and raw facts; no old source replay or favorable retry.',
                 boundaries='One original real60s cooperative deadline; no hard callback-free guarantee. Actual pinned helpers total99000 bytes; Kernel121192 bytes is separate explicit pre-entry TCB. No native or physical authority.',
                 not_authorized=['frozen source edits', 'native/compiler/SDK/FFI/model execution',
                                 'original/protected targets', 'full32/53 or native25 run',
                                 'downloads/paid calls', 'application/default changes'],
                 provider_spend_usd=0, qualification=False)
    scope_path = HERE / 'ENTRY-SOURCE3-REGRESSION-EXECUTION-SCOPE-v1.json'
    save_new(scope_path, scope)
    binding['status'] = 'AUTHORIZED_SOURCE3_FIVE_REGRESSIONS_ONLY'
    binding['execution_scope'] = pin(scope_path)
    binding_path = HERE / 'ENTRY-SOURCE3-REGRESSION-BINDING-v1.json'
    save_new(binding_path, binding)
    print(json.dumps(dict(scope=pin(scope_path), binding=pin(binding_path))))


if __name__ == '__main__':
    main()
