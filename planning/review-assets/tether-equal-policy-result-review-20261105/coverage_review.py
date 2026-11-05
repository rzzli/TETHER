"""Post-run read-only case-quality review. Never imports or invokes a validator."""
from __future__ import annotations
import copy
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
ROOT = PROJECT / 'data/benchmark/tether-equal-policy-20261102-attempt03'
OUT = Path(__file__).parent

def read(path):
    return json.loads(path.read_bytes())

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def pin(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(PROJECT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def parent_control(number):
    if number in (4, 6): return 'EP002'
    if 60 <= number <= 69: return 'EP059'
    if number == 77: return 'EP076'
    if 79 <= number <= 89: return 'EP078'
    if 90 <= number <= 92: return 'EP093'
    if number in (95, 96, 97, 98, 99, 100, 101, 102, 103, 104): return 'EP094'
    if number in (106, 107): return 'EP105'
    return 'EP001'

def expected_inputs(spec, baseline, local_config):
    """Independent in-memory application of the declarative input recipe.

    This deliberately starts with sealed valid baseline documents. It therefore
    detects EP023's unsealed cloned source rather than reproducing that defect.
    The producer and validator modules are not imported.
    """
    docs = copy.deepcopy(baseline)
    prep = spec['preparation']; recipe = prep['recipe']; base = prep['base']
    if base != 'core_t1':
        docs['case'].update(task='T6', endpoint=None)
        docs.pop('scorer')
    if base in ('real_t6', 'policy_t6'):
        docs['snapshot']['profile'] = 'contemporary_assessment'
    if recipe.get('local_config'):
        docs['local_model'] = copy.deepcopy(local_config)
    variant = recipe.get('observations')
    if variant:
        second = copy.deepcopy(docs['evidence']['observations'][0])
        if variant != 'duplicate_id': second['observation_id'] = 'obs-2'
        if variant in ('independent_second', 'shared_cohort'):
            second.update(study_id='FICTIONAL:STUDY-2', dependency_group='fictional-group-2')
        if variant == 'independent_second': second['context']['cohort_ids'] = ['FICTIONAL:COHORT-2']
        if variant in ('independent_second', 'same_group_conflict'): second['features']['genetic_support'] = 0.25
        docs['evidence']['observations'].append(second)
    if recipe.get('observation_lineage') == 'unrelated_source':
        extra = copy.deepcopy(docs['snapshot']['sources'][0]); extra['source_id'] = 'unrelated-source'
        docs['snapshot']['sources'].append(extra)
        docs['evidence']['observations'][0]['input_refs'] = ['unrelated-source']
    for change in prep['changes']:
        obj = docs[change['document']]
        for key in change['path'][:-1]: obj = obj[key]
        key = change['path'][-1]
        if change['op'] == 'set': obj[key] = copy.deepcopy(change['value'])
        elif change['op'] == 'delete': del obj[key]
        elif change['op'] == 'append': obj[key].append(copy.deepcopy(change['value']))
        else: raise ValueError(change['op'])
    if recipe.get('omit_scorer'): docs.pop('scorer', None)
    raw = canonical(docs['source']) + b'\n'
    docs['receipt'].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    for node in docs['snapshot']['sources']:
        if node['source_id'] == 'source-1':
            node.update(sha256=docs['receipt']['sha256'], receipt_sha256=hashlib.sha256(canonical(docs['receipt']) + b'\n').hexdigest())
        elif node['source_id'] == 'mapping-1':
            node['sha256'] = hashlib.sha256(canonical(docs['mapping']) + b'\n').hexdigest()
    docs['snapshot']['artifacts'][0]['sha256'] = hashlib.sha256(canonical(docs['evidence']) + b'\n').hexdigest()
    assert not prep['after_seal'], 'Review an added post-seal declarative recipe explicitly'
    return docs

def main():
    schedule = read(ROOT / 'case-preparation-schedule.json')['cases']
    baseline = {p.stem: read(p) for p in (ROOT/'bundles/EP001/input').glob('*.json')}
    local_config = read(ROOT/'bundles/EP094/input/local_model.json')
    rows, source_anomalies, input_mismatches, files = [], [], [], []
    input_groups = defaultdict(list)
    analysis = read(ROOT/'ANALYSIS.json')
    analysis_index = {(r['control_id'], r['implementation'], r['repetition']): r for r in analysis['rows']}
    for spec in schedule:
        cid = spec['control_id']; n = int(cid[2:]); bundle = ROOT/'bundles'/cid; recipe = spec['preparation']['recipe']
        expected = expected_inputs(spec, baseline, local_config)
        checks = []
        for name, value in expected.items():
            path = bundle/'input'/(name+'.json')
            fault = recipe.get('file_fault')
            if name == 'source' and fault == 'missing_raw': good = not path.exists()
            elif name == 'source' and fault == 'raw_is_directory': good = path.is_dir()
            elif name == 'source' and fault == 'raw_bytes_after_seal': good = path.read_bytes() == b'{"fictional":"changed after sealing"}\n'
            elif name == 'source' and recipe.get('sealed_mutation') == 'original_raw_bytes': good = path.read_bytes() == b'{"fictional":"altered original"}\n'
            elif name == 'case' and fault == 'duplicate_case_schema_key': good = path.read_bytes() == b'{"schema_version":2,' + (canonical(value)+b'\n')[1:]
            else: good = path.is_file() and canonical(read(path)) == canonical(value)
            checks.append(dict(document=name, matches_declared_recipe=good))
            if not good: input_mismatches.append(dict(control_id=cid, document=name))
        snapshot = read(bundle/'input/snapshot.json')
        for node in snapshot['sources']:
            relative = Path(node['path'])
            if '..' in relative.parts or relative.is_absolute(): continue
            source = bundle/'input'/relative
            if source.is_file():
                observed = hashlib.sha256(source.read_bytes()).hexdigest()
                if observed != node['sha256']:
                    source_anomalies.append(dict(control_id=cid, source_id=node['source_id'], declared_sha256=node['sha256'], actual_sha256=observed))
        inventory = {p.relative_to(bundle/'input').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (bundle/'input').rglob('*') if p.is_file()}
        input_groups[digest(inventory)].append(cid)
        arms = {}
        for arm in ('tether', 'independent'):
            results = []
            for repeat in (1,2,3):
                path = ROOT/'comparison'/f'{cid}-r{repeat}-{arm}'/'stdout.json'
                files.append(pin(path)); result = read(path)['result']
                results.append(result)
            stable = len({digest(result) for result in results}) == 1
            arms[arm] = dict(result=results[0], identical_result_across_three_repetitions=stable,
                frozen_oracle_decision_agreement=all(r['decision']==spec['oracle']['decision'] for r in results),
                frozen_observable_mismatches=[analysis_index[(cid,arm,r)]['observable_mismatches'] for r in (1,2,3)])
        verdict = 'intended_rejection_reason_reached' if spec['oracle']['decision']=='reject' else 'intended_acceptance_observables_present'
        limits = []
        if n in (75,77): verdict='separate_peer_review_required'; limits.append('Detailed EP075/EP077 review is assigned separately; frozen scores remain unchanged.')
        if n == 23:
            verdict='intended_rejection_reached_with_additional_fixture_fault'
            limits.append('The unrelated source has zero byte/receipt hashes. Its unused parent data should be correctly sealed in a future single-fault control; both arms currently reject the intended lineage escape first.')
        if n in (72,97):
            verdict='measured_overquote_verified_later_dispatch_prevention_not_isolated'
            plan=next(read_event['details'] for read_event in (json.loads(line) for line in (bundle/'run/trace.jsonl').read_bytes().splitlines()) if read_event['event']=='plan')
            limits.append('Only genetics is ready; no later eligible category exists. later_dispatches=0 is not alone a causal witness that overquote stops available later work.')
            checks.append(dict(ready_categories=[step['category'] for step in plan['steps'] if step['initial_status']=='ready']))
        if n in (1,25): limits.append('EP001 and EP025 have identical materialized input bytes; they are distinct policy annotations, not independent source constructions.')
        if n == 59: limits.append('The oracle has no extra numeric observable assertions; this is a valid archive acceptance control, not an independent scientific scorer assessment.')
        if n in (4,47,48,49,50): limits.append('This comparison invokes preparation only; before-dispatch execution ordering also relies on separately retained runtime tests.')
        if n in (70,71,72,73,74,94,95,96,97,102): limits.append('Archive verification observes a previously materialized fictional backend execution; it is not live model performance or an independently executed scheduler.')
        if n == 76: verdict='intended_inspection_observables_present'
        rows.append(dict(control_id=cid, title=spec['title'], operation=spec['operation'], expected=spec['oracle'],
            preparation=spec['preparation'], baseline_control=parent_control(n),
            baseline_relation='same fixture family; not a counterfactual rerun or necessarily byte-identical sealed archive',
            source_recipe_checks=checks, review_status=verdict, limitations=limits, arms=arms))
    duplicates=[ids for ids in input_groups.values() if len(ids)>1]
    document=dict(schema_version=1, status='REVIEW_COMPLETE_WITH_SCOPE_LIMITATIONS', reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Post-run read-only recipe, original-input, reason and retained-observable review of all108 controls and648 TETHER/independent cells. No validators/producers imported or run; no frozen sources/oracles edited.',
        exclusions=['Detailed EP075/EP077 and weaker hash-control diagnoses belong to the separately assigned peer review.'],
        counts=dict(cases=len(rows), reviewed_result_files=len(files), repeated_results_identical=sum(all(a['identical_result_across_three_repetitions'] for a in row['arms'].values()) for row in rows),
            review_status=dict(Counter(row['review_status'] for row in rows))),
        pins=[pin(ROOT/name) for name in ('FROZEN.json','case-preparation-schedule.json','oracle.json','ANALYSIS.json')]+[pin(Path(__file__))],
        unexpected_input_recipe_differences=input_mismatches, source_hash_anomalies=source_anomalies,
        repeated_input_inventory_groups=duplicates, reviewed_results=files, cases=rows,
        interpretation='First reported rejection reasons and explicit returned observables support reached checks; this is not instruction-level branch instrumentation or proof that disabling one check would make every mutant pass. Do not change frozen scores based on this review.')
    assert input_mismatches == [dict(control_id='EP023',document='snapshot')], input_mismatches
    assert len(rows)==108 and len(files)==648
    assert all(all(a['frozen_oracle_decision_agreement'] for a in row['arms'].values()) for row in rows)
    output=OUT/'coverage-review.json'
    with output.open('x',encoding='utf-8') as stream: json.dump(document,stream,ensure_ascii=False,indent=2); stream.write('\n')
    print(json.dumps(dict(status=document['status'],counts=document['counts'],input_mismatches=input_mismatches,
        source_hash_anomalies=source_anomalies,output_pin=pin(output)),indent=2))

if __name__=='__main__': main()
