"""Read-only comparison of two retained simulated cases; no execution/replay."""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / 'recovery-step9-native-integration-20261027'
INPUTS = {}
guards = []


def audit(event, args):
    if event in ('subprocess.Popen', 'socket.connect', 'socket.__new__', 'socket.getaddrinfo', 'os.system'):
        guards.append(event)
        raise RuntimeError('Read-only retained-metadata audit')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        if '\\data\\benchmark\\' in os.path.normcase(os.path.abspath(os.fsdecode(args[0]))):
            raise RuntimeError('Protected payloads excluded')


sys.addaudithook(audit)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, *, parse=True):
    raw = path.read_bytes()
    key = path.relative_to(ROOT).as_posix()
    proof = dict(sha256=sha(raw), bytes=len(raw))
    assert key not in INPUTS or INPUTS[key] == proof
    INPUTS[key] = proof
    return json.loads(raw) if parse else raw


def inspect(phase, version):
    qualification = read(phase / 'SIMULATION-QUALIFICATION.json')
    assert qualification['version'] == version
    assert qualification['status'] == 'qualified_real_inputs_simulated_native_case'
    run = Path(qualification['output'])
    receipt = read(run / 'receipt.json')
    assert INPUTS[(run / 'receipt.json').relative_to(ROOT).as_posix()]['sha256'] == qualification['result']['receipt_sha256']
    events = [json.loads(line) for line in read(run / 'journal.jsonl', parse=False).splitlines()]
    summary = read(run / 'summary.json')
    by_name = {}
    for event in events:
        by_name.setdefault(event['event'], []).append(event['details'])
    def one(name):
        assert len(by_name[name]) == 1
        return by_name[name][0]
    anchors = {n: one(n)['elapsed_seconds'] for n in
        ('source_ready', 'retrieval_ready', 'tokenizer_ready', 'native_preparing',
         'native_context_qualified', 'native_stopped')}
    anchors['summary'] = summary['elapsed_seconds']
    anchors['sealed'] = receipt['sealed_elapsed_seconds']
    quotes = {d['cell']: d['elapsed_seconds'] for d in by_name['quote_ready']}
    accepts = {d['cell']: d['elapsed_seconds'] for d in by_name['cell_accepted']}
    cells = []
    previous = anchors['native_context_qualified']
    for i in range(6):
        quote = read(run / f'quotes/{i:02d}/quote.json')
        report = read(run / f'cells/{i:02d}/report.json')
        wrapper = read(run / f'cells/{i:02d}/raw-response.bin')
        configuration = read(run / f'cells/{i:02d}/configuration.json')
        prompt = read(run / f'quotes/{i:02d}/prompt.bin', parse=False)
        assert sha(prompt) == quote['prompt_sha256']
        assert previous <= quotes[i] <= accepts[i]
        native, reported, cap = wrapper['elapsed_seconds'], report['elapsed_seconds'], configuration['budget']['max_seconds']
        assert 0 <= native < cap and 0 <= reported < cap and native <= reported + 1e-6
        cells.append(dict(cell=i, quote_ready_seconds=quotes[i], accepted_seconds=accepts[i],
            prior_anchor_to_quote_ready_seconds=quotes[i]-previous,
            quote_ready_to_acceptance_seconds=accepts[i]-quotes[i],
            recorded_quote_interval_seconds=quote['elapsed_seconds'],
            recorded_tokenizer_child_seconds=quote['child']['elapsed_seconds'],
            recorded_child_report_seconds=reported, simulated_transport_seconds=native,
            allocated_seconds=cap, prompt_sha256=quote['prompt_sha256'], token_count=quote['token_count']))
        previous = accepts[i]
    anchors['last_cell_accepted'] = accepts[5]
    ordered = [('through_source_ready', 0.0, anchors['source_ready']),
        ('source_ready_to_retrieval_ready', anchors['source_ready'], anchors['retrieval_ready']),
        ('retrieval_ready_to_tokenizer_ready', anchors['retrieval_ready'], anchors['tokenizer_ready']),
        ('tokenizer_ready_to_native_preparing', anchors['tokenizer_ready'], anchors['native_preparing']),
        ('native_preparing_to_context_ready', anchors['native_preparing'], anchors['native_context_qualified']),
        ('context_ready_to_last_cell_accepted', anchors['native_context_qualified'], accepts[5]),
        ('last_cell_accepted_to_summary', accepts[5], anchors['summary']),
        ('summary_to_sealed', anchors['summary'], anchors['sealed'])]
    partition = {name: end-start for name, start, end in ordered}
    assert all(value >= 0 for value in partition.values())
    assert math.isclose(sum(partition.values()), anchors['sealed'], abs_tol=1e-6)
    # Confirm selected metadata bytes against the existing root receipt, without
    # repeating source/model-inclusive semantic verification.
    for name, proof in receipt['artifacts'].items():
        key = (run / name).relative_to(ROOT).as_posix()
        if key in INPUTS:
            assert INPUTS[key] == dict(sha256=proof['sha256'], bytes=proof['bytes'])
    return dict(version=version, run=run.relative_to(ROOT).as_posix(), receipt_sha256=qualification['result']['receipt_sha256'],
        outer_execution_seconds=qualification['execution_seconds'],
        reported_replay_and_postcheck_seconds=qualification['replay_seconds'],
        sealed_seconds=anchors['sealed'], headroom_seconds=300-anchors['sealed'],
        headroom_fraction=(300-anchors['sealed'])/300,
        anchors=anchors, additive_anchor_partition_seconds=partition, cells=cells,
        summed_quote_recorded_intervals_seconds=sum(c['recorded_quote_interval_seconds'] for c in cells),
        summed_tokenizer_child_seconds=sum(c['recorded_tokenizer_child_seconds'] for c in cells),
        summed_quote_ready_to_acceptance_seconds=sum(c['quote_ready_to_acceptance_seconds'] for c in cells),
        summed_child_report_seconds=sum(c['recorded_child_report_seconds'] for c in cells),
        receipt_timings=receipt['timings'],
        overlapping_fake_process_lifetime_seconds=one('server_terminal')['elapsed_seconds'],
        parent_peak_working_set_bytes=qualification['peak_parent_working_set_bytes'],
        child_peak_memory_bytes=qualification['child_peak_memory_bytes'],
        source_authority_sha256=summary['source_authority_sha256'],
        input_reserved=summary['input_reserved'], output_reserved=summary['output_reserved'],
        coverage=qualification['coverage'], actual_model_calls=summary['actual_model_calls'],
        actual_native_servers=qualification['actual_native_servers'])


old, new = inspect(OLD, '0.3.9'), inspect(HERE, '0.3.10')
assert old['source_authority_sha256'] == new['source_authority_sha256']
assert old['coverage'] == new['coverage']
assert old['input_reserved'] == new['input_reserved'] == 24558
assert old['output_reserved'] == new['output_reserved'] == 6144
assert all(a['prompt_sha256'] == b['prompt_sha256'] and a['token_count'] == b['token_count'] for a, b in zip(old['cells'], new['cells']))
assert old['actual_model_calls'] == new['actual_model_calls'] == 0
assert old['actual_native_servers'] == new['actual_native_servers'] == 0
assert all(dict(sha256=sha((ROOT/name).read_bytes()), bytes=(ROOT/name).stat().st_size) == proof for name, proof in INPUTS.items())
assert not guards
result = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='retained_metadata_timing_comparison_complete',
    scope='One retained simulated case per version; no rerun or full source/model replay',
    versions=[old,new], partition_deltas_seconds={k: new['additive_anchor_partition_seconds'][k]-v for k,v in old['additive_anchor_partition_seconds'].items()},
    outer_execution_delta_seconds=new['outer_execution_seconds']-old['outer_execution_seconds'],
    outer_execution_ratio=new['outer_execution_seconds']/old['outer_execution_seconds'],
    causal_attribution='Not established: nonrandomized single observations, no controlled resource/load/cache measurements',
    original_files_unchanged=INPUTS, metadata_files_checked=len(INPUTS),
    actual_model_calls=0, native_servers_started=0, tokenizer_children_started=0,
    process_dispatches=0, network_calls=0, guard_scope='This analysis process only',
    helper_sha256=sha(Path(__file__).read_bytes()), native_integrated_case_fit='Not established')
with (HERE/'STAGE-TIMING-AUDIT.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(dict(status=result['status'],metadata_files_checked=result['metadata_files_checked'],
    outer_seconds=[old['outer_execution_seconds'],new['outer_execution_seconds']],
    headroom_seconds=[old['headroom_seconds'],new['headroom_seconds']],
    partitions=[old['additive_anchor_partition_seconds'],new['additive_anchor_partition_seconds']])))
