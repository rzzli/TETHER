"""Root metadata binding: exact finite suite, no subject import or data crawl."""
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
        stream.write((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def main():
    peer = pin(sys.argv[1])
    if peer['sha256'] != sys.argv[2]:
        raise RuntimeError('reviewed peer hash changed')
    outline_path = HERE / 'ENTRY-CONTRACT-SUITE-BINDING-OUTLINE-v2.json'
    outline_pin = pin(outline_path)
    if outline_pin['sha256'] != '5222a23a30a8ac6c61e2c331e3570bb8a693092aa2c39a403b4763b5b5d24b0c':
        raise RuntimeError('frozen outline changed')
    binding = json.loads(outline_path.read_bytes())
    for value in [binding['source_pause'], binding['inputs'], binding['preparation'],
                  *binding['source_map'].values(), *binding['harness'].values()]:
        if pin(value['path']) != value:
            raise RuntimeError('changed frozen pin: ' + value['path'])
    if binding['source_pause']['sha256'] != '225e8baf3aea76240e934eb1f80ad85478ba404a1e38a0a26cba5d65bd11973a':
        raise RuntimeError('accepted Source3 anchor required')
    freeze = pin(HERE / 'ENTRY-CONTRACT-SUITE-FREEZE-v2.json')
    if freeze['sha256'] != '2116ed80a148a8df9b81c65cd785e1db8666d276a7cda464d567736bc9ee4694':
        raise RuntimeError('frozen preparation changed')
    for path in binding['consumed_paths']:
        if Path(path).exists():
            raise RuntimeError('suite already consumed; no replay')
    scope = dict(
        schema_version=1, status='ROOT_AUTHORIZED_ONE_SOURCE3_ENTRY32_53_SUITE',
        source_pause=binding['source_pause'], preparation=binding['preparation'],
        inputs=binding['inputs'], freeze=freeze, outline=outline_pin,
        independent_harness_peer=peer,
        execution='Run the exact frozen v2 runner once over the53 ordered branches of32 named controls. Use actual unchanged Source3 objects; retain first action/cleanup/evidence outcomes and genuine earlier/final snapshots. No old subject experiment replay.',
        deadline_seconds=60,
        deadline_boundary='One real cooperative timer from runner setup through per-world evidence retention and final veto. Final proof JSON persistence follows the reported elapsed and is unmeasured. No hard callback-free timeout, physical durability or whole-process startup claim.',
        generated_large_input=dict(authorized=True, case='E32', bulk_bytes=3991999872,
                                  recipe='procedural periodic bytes00..ff, reset at offset0',
                                  sha256='5321e7c0efc028f133e7a6690e5c5bdf0344dded80904eb416fddb7ed0c2b1fb',
                                  read_buffer_limit_bytes=1048576,
                                  geometry=dict(N=5,B=3,M=3,Q=3812,R=3892,C=3922,E=234),
                                  original_payload_reads=False, bulk_capture_assembly=False),
        coverage='E08 external manifest policy and two E16 historical factory invocations remain explicitly deferred after their limited checks. E29 is metadata-only. Expected defer never completes the entry gate or becomes runtime PASS. E32 may claim actual procedural streaming only from retained actual execution.',
        source_boundary='Kernel121192B is separate pre-entry trusted code; actual captured helper prefix99000B. Numeric labels/fixture expectations are harness-only. All native, physical, real-roster, integrated-resource and scientific qualification flags remain false.',
        not_authorized=['subject or frozen harness edits', 'original/protected data or model payload reads',
                        'native/compiler/SDK/FFI/model execution', 'native25 execution',
                        'new capability/profile/cap', 'downloads or paid calls',
                        'application/default changes', 'downloader/periodic-monitor changes'],
        provider_spend_usd=0, qualification=False)
    scope_path = HERE / 'ENTRY-CONTRACT-SUITE-EXECUTION-SCOPE-v2.json'
    save_new(scope_path, scope)
    binding['status'] = binding['required_execution_status']
    binding['execution_scope'] = pin(scope_path)
    binding['allow_large_stream'] = True
    binding['allow_large_stream_reason'] = 'Root explicitly authorizes the one prospective E32 procedural stream in the exact execution scope.'
    binding['freeze'] = freeze
    binding_path = HERE / 'ENTRY-CONTRACT-SUITE-BINDING-v2.json'
    save_new(binding_path, binding)
    print(json.dumps(dict(scope=pin(scope_path), binding=pin(binding_path))))


if __name__ == '__main__':
    main()
