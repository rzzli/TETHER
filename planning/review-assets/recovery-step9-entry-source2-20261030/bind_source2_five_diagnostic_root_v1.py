"""Root metadata binding only; imports no subject and follows no data lineage."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def pin(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('review asset must stay in the repository')
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def exact(value):
    if pin(value['path']) != value:
        raise RuntimeError('changed exact pin: ' + value['path'])


def save_new(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8'))


def main():
    peer = pin(sys.argv[1])
    if peer['sha256'] != sys.argv[2]:
        raise RuntimeError('independent harness peer differs from reviewed hash')
    outline_path = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-BINDING-OUTLINE-v2.json'
    outline_pin = pin(outline_path)
    if outline_pin['sha256'] != 'c14ec0c0146a4395a0c3f8e706a473b315c3d0969ffbe7237bc0775e157752b1':
        raise RuntimeError('frozen outline changed')
    outline = json.loads(outline_path.read_bytes())
    for value in [outline['source_pause'], outline['inputs'], outline['preparation'],
                  *outline['source_map'].values(), *outline['harness'].values()]:
        exact(value)
    freeze = pin(HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-FREEZE-v2.json')
    if freeze['sha256'] != '09607fb5a47cd6813933fb5a315564a8172d135f4a3176c5d64772c0121040e3':
        raise RuntimeError('frozen diagnostic preparation changed')
    scope = dict(
        schema_version=1,
        status='ROOT_AUTHORIZED_ONE_SOURCE2_FIVE_CHECK_DIAGNOSTIC',
        source_pause=outline['source_pause'], preparation=outline['preparation'],
        freeze=freeze, outline=outline_pin, independent_harness_peer=peer,
        source_disposition='HOLD: accepted independent stopped-CloseHandle F2 finding',
        execution='Run only the exact five named methods once through the frozen runner. Retain all first outcomes, original failures, raw facts and cleanup evidence. An expected fifth FAIL is a failed source diagnostic, never source acceptance.',
        methods=outline['methods'], deadline_seconds=60,
        boundaries='One real cooperative deadline; fresh synthetic worlds and the actual pinned helper prefix. No callback-free hard-timeout guarantee. Kernel is explicit pre-entry trusted code.',
        not_authorized=['frozen source edits', 'native/compiler/SDK/FFI/model execution',
                        'original or protected data targets', 'full32/53 or native25 run',
                        'downloads or paid calls', 'application/default changes',
                        'replay of any retained actual experiment'],
        provider_spend_usd=0, qualification=False)
    scope_path = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-EXECUTION-SCOPE-v2.json'
    save_new(scope_path, scope)
    outline['status'] = 'AUTHORIZED_SOURCE2_FIVE_REGRESSIONS_WITH_STOPPED_CLOSE_DIAGNOSTIC'
    outline['execution_scope'] = pin(scope_path)
    binding_path = HERE / 'ENTRY-SOURCE2-DIAGNOSTIC-BINDING-v2.json'
    save_new(binding_path, outline)
    print(json.dumps(dict(scope=pin(scope_path), binding=pin(binding_path))))


if __name__ == '__main__':
    main()
