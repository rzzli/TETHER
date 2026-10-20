"""Source-derived role workflow and fresh bounded T6 ablations, never probabilities.

This reimplements a restricted role pattern from pinned Virtual Biotech sources.
It does not import the original SDK/orchestrator or expose tools to the model.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import re
import time

from asof.agents import Selection, SpecialistRequest, Usage, make_request
from asof.contracts import Category, EvidenceStatus, Profile
from asof.journal import RunJournal, read_chain
from asof.local_model import LocalSelectionBackend, parse_selection, selection_payload
from asof.retrieval import RetrievalPolicy, bounded_request
from asof.serde import ContractError, canonical, decode, encode, fingerprint, parse_json, read_json, safe_child, sha256_file, write_json
from asof.workflow import Budget, BudgetMeter, add_usage, over_quote


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT/'planning/review-assets/science-prerequisites-20261018/item7/adapter-role-policy.json'
ARMS = ('asof', 'adapted_virtual_biotech', 'lexical', 'provider_score', 'no_literature', 'no_perturbation')
STAGES = ('chief_of_staff', 'coordinator_delegate', 'mapped_specialist', 'scientific_reviewer', 'coordinator_synthesize')
DEFAULT_RETRIEVAL = {'max_records': 12, 'max_request_bytes': 12000, 'wire_format': 'asof-shared-scientific-fields-v1'}


def default_role_policy():
    policy = read_json(POLICY)
    source = Path(policy['source_root'])
    if sha256_file(source/'manifest.json') != policy['source_manifest_sha256']:
        raise ContractError('Upstream role source manifest differs')
    for row in policy['source_files']:
        if sha256_file(safe_child(source, row['path'])) != row['sha256']:
            raise ContractError('Upstream role source bytes differ')
    return policy


def _policy(value):
    value = parse_json(canonical(value))
    if (value.get('schema_version') != 1 or tuple(value.get('stage_order', ())) != STAGES or
            set(value.get('stage_guidance', {})) != set(STAGES) or
            set(value.get('specialists', {})) != {c.value for c in Category} or
            value.get('control_reserve_bytes') != 2048):
        raise ContractError('Invalid source-derived role policy')
    if any(not isinstance(x, str) or not x.strip() for x in value['stage_guidance'].values()):
        raise ContractError('Role instructions must be explicit')
    return value


def _stage_instructions(base, stage, category, policy):
    return base.instructions + '\nRole: ' + stage + '; mapped upstream specialist: ' + policy['specialists'][category.value] + '.\n' + policy['stage_guidance'][stage]


def _prepare(case, category, store, policy, retrieval):
    records = tuple(r for r in store.query(case, category) if r.observation.status == EvidenceStatus.OBSERVED)
    base = make_request(case, category, records)
    # All arms reserve the same worst-case role/control overhead, then receive the
    # exact same whole-record candidate packet. No role silently truncates fields.
    longest = max((_stage_instructions(base, s, category, policy) for s in STAGES), key=lambda x: len(x.encode('utf-8')))
    envelope = replace(base, instructions=longest + '\n' + ' ' * policy['control_reserve_bytes'])
    prepared, audit = bounded_request(envelope, retrieval)
    return replace(base, evidence=prepared.evidence), audit


def _request(base, stage, category, policy, prior):
    feedback = (json.dumps({'prior_role_choices': prior}, sort_keys=True, separators=(',', ':')), ) if prior else ()
    if len(canonical(feedback)) > policy['control_reserve_bytes']:
        raise ContractError('Role feedback exceeds frozen control reservation')
    return replace(base, instructions=_stage_instructions(base, stage, category, policy), feedback=feedback)


def _baseline(request, arm):
    if arm == 'lexical':
        tokens = set(re.findall(r'[a-z0-9_]{3,}', request.case_json.casefold()))
        rows = sorted(request.evidence, key=lambda r: (-len(tokens & set(re.findall(r'[a-z0-9_]{3,}', r.statement.casefold()))), r.observation_id))
    else:
        records = [(r, parse_json(r.scientific_record_json)) for r in request.evidence]
        providers = {r.get('source_locator', {}).get('datasource_id') for _, r in records}
        scores = [r.get('source_metrics', {}).get('score') for _, r in records]
        if len(providers) != 1 or None in providers:
            return [], 'inapplicable', 'incomparable_or_unknown_datasource_scales'
        if any(type(s) not in (int, float) or not math.isfinite(s) for s in scores):
            return [], 'inapplicable', 'missing_or_nonfinite_provider_score'
        rows = [r for r, _ in sorted(zip(request.evidence, scores), key=lambda pair: (-pair[1], pair[0].observation_id))]
    return [r.observation_id for r in rows[:3]], 'completed', None


def _claim(store, category, identity):
    record = store.lookup(identity)
    if record.observation.category != category:
        raise ContractError('Claim category differs from its admitted source')
    return {'category': category.value, 'observation_id': identity, 'evidence': encode(record), 'source_claim_sha256': fingerprint(record)}


def _seal(output):
    write_json(output/'seal.json', {'schema_version': 1, 'files': [
        {'path': p.relative_to(output).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
        for p in sorted(output.rglob('*')) if p.is_file() and p != output/'seal.json']})


def run_case(case, store, backend, budget, arm, output, role_policy=None):
    case.validate()
    budget.validate()
    if store.snapshot.origin != case.origin or store.snapshot.origin_at != case.origin_at:
        raise ContractError('Comparison case/store temporal context differs')
    if arm not in ARMS or case.task != 'T6':
        raise ContractError('Unsupported matched T6 arm')
    policy = _policy(role_policy if role_policy is not None else default_role_policy())
    provenance = encode(getattr(backend, 'provenance', {}))
    if arm not in ('lexical', 'provider_score') and store.snapshot.profile != Profile.DEMO and backend.backend_id != 'local-structured-selection-v1':
        raise ContractError('Real scientific comparison requires the pinned local backend')
    retrieval = RetrievalPolicy(**provenance.get('config', {}).get('retrieval', DEFAULT_RETRIEVAL))
    output = Path(output).resolve()
    journal = RunJournal(output)
    meter = BudgetMeter(budget)
    result = {'schema_version': 1, 'engine_id': 'science7-source-derived-role-workflow-v1',
        'case_id': case.case_id, 'case_sha256': fingerprint(case), 'hypothesis_sha256': case.hypothesis.key,
        'arm': arm, 'status': 'running', 'features': {}, 'probability': None, 'claims': [],
        'selections': {}, 'coverage': {}, 'calls': 0, 'usage': encode(Usage(0, 0, 0)),
        'measured_usage': encode(Usage(0, 0, 0)), 'estimated_usage': encode(Usage(0, 0, 0)),
        'source_proofs_sha256': fingerprint(store.source_proofs), 'scientific_validation': 'not_established',
        'source_coverage': encode(store.snapshot.coverage),
        'configuration': {'budget': encode(budget), 'retrieval': encode(retrieval), 'backend_id': backend.backend_id,
                          'backend_provenance': provenance, 'role_policy_sha256': fingerprint(policy)},
        'provider_spend_usd': 0, 'clinical_metrics': None}
    backend_records = []
    try:
        (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        write_json(output/'role-policy.json', policy)
        write_json(output/'case.json', encode(case))
        journal.append('comparison_plan', case_sha256=fingerprint(case), arm=arm,
                       configuration=result['configuration'], source_proofs_sha256=result['source_proofs_sha256'])
        exhausted = failed = interrupted = False
        disabled = Category.LITERATURE if arm == 'no_literature' else Category.PERTURBATION if arm == 'no_perturbation' else None
        for category in Category:
            all_rows = store.query(case, category)
            available = sum(r.observation.status == EvidenceStatus.OBSERVED for r in all_rows)
            coverage = {'available_in_collected_case_world': available, 'selected': 0,
                'nonobserved': [{'observation_id': r.observation.observation_id, 'status': r.observation.status.value} for r in all_rows if r.observation.status != EvidenceStatus.OBSERVED],
                'interpretation': 'Collected-source scope only; missing or excluded records are not biological absence'}
            result['coverage'][category.value] = coverage
            if category == disabled:
                coverage['status'] = 'disabled_before_retrieval'
                journal.append('category_disabled', category=category.value)
                continue
            if not available:
                coverage['status'] = 'no_observed_evidence_in_collected_scope'
                continue
            if exhausted or failed or interrupted:
                coverage['status'] = 'not_run_after_budget_or_failure'
                continue
            base, audit = _prepare(case, category, store, policy, retrieval)
            coverage['retrieval'] = audit
            journal.append('bounded_candidates', category=category.value, audit=audit)
            if not base.evidence:
                coverage['status'] = 'no_whole_records_within_budget'
                continue
            if arm in ('lexical', 'provider_score'):
                selected, status, reason = _baseline(base, arm)
                coverage.update(status=status, reason=reason)
                journal.append('baseline_selection', category=category.value, arm=arm, selected=selected, status=status, reason=reason)
            else:
                stages = STAGES if arm == 'adapted_virtual_biotech' else ('mapped_specialist',)
                prior = []
                selected = []
                complete = True
                for stage in stages:
                    request = _request(base, stage, category, policy, prior)
                    quote = backend.quote(request)
                    quote.validate()
                    if not meter.can_reserve(quote):
                        journal.append('budget_denied', category=category.value, role=stage, quote=encode(quote), elapsed_seconds=time.monotonic()-meter.started)
                        exhausted, complete = True, False
                        break
                    attempt_id = f'{category.value}:{stage}'
                    journal.append('dispatch', attempt_id=attempt_id, category=category.value, role=stage,
                        request=encode(request), request_sha256=fingerprint(request), reserved=encode(quote),
                        elapsed_seconds=time.monotonic()-meter.started)
                    selection = None
                    usage, measured = quote, False
                    try:
                        selection = backend.select(request)
                        if not isinstance(selection, Selection):
                            raise ContractError('Malformed selection object')
                        selection.usage.validate()
                        usage, measured = selection.usage, True
                        ids = list(selection.observation_ids)
                        allowed = {r.observation_id for r in request.evidence}
                        if len(ids) > 3 or len(ids) != len(set(ids)) or set(ids)-allowed:
                            raise ContractError('Role selected outside the exact supplied IDs/cap')
                        if stage in ('scientific_reviewer', 'coordinator_synthesize') and set(ids)-set(prior[-1]['observation_ids']):
                            raise ContractError('Review/synthesis added an unreviewed source ID')
                        if over_quote(usage, quote):
                            raise ContractError('Backend exceeded its reservation')
                    except KeyboardInterrupt:
                        interrupted, complete = True, False
                        journal.append('call_failed', attempt_id=attempt_id, error_class='KeyboardInterrupt')
                    except Exception as error:
                        failed, complete = True, False
                        journal.append('call_failed', attempt_id=attempt_id, error_class=type(error).__name__)
                    finally:
                        meter.account(usage, measured)
                        journal.append('attempt_accounted', attempt_id=attempt_id, usage=encode(usage),
                                       basis='adapter_reported' if measured else 'quoted_upper_bound_not_measured')
                        records = getattr(backend, 'records', None)
                        record = encode(records[-1]) if records else {'kind': 'synthetic_test_backend', 'request_sha256': fingerprint(request)}
                        backend_records.append({'attempt_id': attempt_id, 'record': record})
                        write_json(output/'backend-execution.json', {'schema_version': 1, 'attempts': backend_records})
                    if not complete:
                        break
                    selected = list(selection.observation_ids)
                    prior.append({'role': stage, 'observation_ids': selected})
                    journal.append('role_selection', attempt_id=attempt_id, category=category.value, role=stage,
                                   selected=selected, usage=encode(usage))
                    if time.monotonic()-meter.started >= budget.max_seconds:
                        exhausted, complete = True, False
                        journal.append('wall_time_exhausted', category=category.value, role=stage, elapsed_seconds=time.monotonic()-meter.started)
                        break
                coverage['status'] = 'completed' if complete else 'interrupted' if interrupted else 'failed' if failed else 'budget_exhausted'
                if not complete:
                    selected = []
            committed = []
            for identity in selected:
                if time.monotonic()-meter.started >= budget.max_seconds:
                    exhausted = True
                    coverage['status'] = 'budget_exhausted'
                    journal.append('wall_time_exhausted', category=category.value, stage='claim_commit', elapsed_seconds=time.monotonic()-meter.started)
                    break
                claim = _claim(store, category, identity)
                result['claims'].append(claim)
                journal.append('claim_committed', claim=claim)
                committed.append(identity)
            result['selections'][category.value] = committed
            coverage['selected'] = len(committed)
        result['status'] = 'interrupted' if interrupted else 'failed' if failed else 'budget_exhausted' if exhausted else 'completed'
    except BaseException as error:
        result.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error_class=type(error).__name__, error=str(error))
        journal.fail(error, 'comparison')
        raise
    finally:
        result.update(calls=meter.calls, usage=encode(meter.used), measured_usage=encode(meter.measured),
                      estimated_usage=encode(meter.estimated), elapsed_seconds=time.monotonic()-meter.started,
                      provider_spend_usd=meter.used.cost_usd)
        if not (output/'backend-execution.json').exists():
            write_json(output/'backend-execution.json', {'schema_version': 1, 'attempts': backend_records})
        write_json(output/'result.json', result)
        journal.append('comparison_finalized', status=result['status'], result_sha256=sha256_file(output/'result.json'))
        journal.close()
        _seal(output)
    return result


def verify_case(output, case, store, backend_config=None, role_policy=None):
    output = Path(output)
    seal = read_json(output/'seal.json')
    listed = {r['path']: r for r in seal['files']}
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p != output/'seal.json'}
    required = {'journal.jsonl', 'result.json', 'role-policy.json', 'case.json', 'backend-execution.json', 'executed-source.py'}
    if len(listed) != len(seal['files']) or set(listed) != actual or not required <= actual:
        raise ContractError('Comparison sealed output inventory differs')
    for name, proof in listed.items():
        p = safe_child(output, name)
        if p.stat().st_size != proof['bytes'] or sha256_file(p) != proof['sha256']:
            raise ContractError('Comparison output bytes differ')
    result = read_json(output/'result.json')
    if backend_config is not None:
        configuration = result['configuration']
        if (configuration['backend_provenance'].get('config') != backend_config or
                configuration['retrieval'] != backend_config['retrieval'] or
                configuration['backend_id'] != LocalSelectionBackend.backend_id):
            raise ContractError('Comparison expected backend/retrieval configuration differs')
    policy = _policy(read_json(output/'role-policy.json'))
    if role_policy is not None and fingerprint(policy) != fingerprint(role_policy):
        raise ContractError('Comparison role policy differs')
    if (result['case_id'] != case.case_id or result['case_sha256'] != fingerprint(case) or
            read_json(output/'case.json') != encode(case) or result['hypothesis_sha256'] != case.hypothesis.key or
            result['source_proofs_sha256'] != fingerprint(store.source_proofs) or
            result['source_coverage'] != encode(store.snapshot.coverage) or
            result['configuration']['role_policy_sha256'] != fingerprint(policy) or
            result['features'] != {} or result['probability'] is not None or result['provider_spend_usd'] != 0):
        raise ContractError('Comparison source/case/prediction contract differs')
    events = encode(read_chain(output/'journal.jsonl'))
    if events[-1]['event'] != 'comparison_finalized' or events[-1]['details']['result_sha256'] != sha256_file(output/'result.json'):
        raise ContractError('Comparison final journal binding differs')
    plan = next(e['details'] for e in events if e['event'] == 'comparison_plan')
    if (fingerprint(plan['configuration']) != fingerprint(result['configuration']) or plan['arm'] != result['arm'] or
            plan['case_sha256'] != fingerprint(case) or plan['source_proofs_sha256'] != result['source_proofs_sha256']):
        raise ContractError('Comparison journal identity differs')
    if result['arm'] not in ARMS or set(result['coverage']) != {c.value for c in Category}:
        raise ContractError('Comparison arm/category inventory differs')
    if result['scientific_validation']!='not_established' or result['clinical_metrics'] is not None:
        raise ContractError('Comparison scientific validation overclaimed')
    budget = decode(Budget,result['configuration']['budget']);budget.validate()
    disabled = Category.LITERATURE if result['arm'] == 'no_literature' else Category.PERTURBATION if result['arm'] == 'no_perturbation' else None
    category_order={c.value:i for i,c in enumerate(Category)}
    last_category=-1
    halted_at=None
    pending = None
    seen_attempts = set()
    ready = set()
    completed_roles = {}
    baseline_choices = {}
    trace_usage = Usage(0,0,0)
    trace_calls = 0
    trace_elapsed = 0.0
    halted = False
    chronological_bases = {}
    if (len(events)<3 or events[0]['event']!='run_reserved' or events[1]['event']!='comparison_plan' or
            sum(e['event']=='comparison_plan' for e in events)!=1):
        raise ContractError('Comparison journal plan grammar differs')
    for index,event in enumerate(events[2:],2):
        kind,d = event['event'],event['details']
        if kind=='bounded_candidates':
            if halted or pending is not None or d['category'] in ready:
                raise ContractError('Comparison source ordering/uniqueness differs')
            ordinal=category_order[d['category']]
            if ordinal<=last_category or not any(r.observation.status==EvidenceStatus.OBSERVED for r in store.query(case,Category(d['category']))):
                raise ContractError('Comparison category visitation/source eligibility differs')
            last_category=ordinal
            ready.add(d['category'])
            chronological_bases[d['category']]=_prepare(case,Category(d['category']),store,policy,RetrievalPolicy(**result['configuration']['retrieval']))[0]
        elif kind=='dispatch':
            identity=d['attempt_id'];category=d['category']
            stages=STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
            prior=completed_roles.get(category,[])
            if halted or pending is not None or identity in seen_attempts or category not in ready or len(prior)>=len(stages) or d['role']!=stages[len(prior)]:
                raise ContractError('Comparison dispatch ordering differs')
            seen_attempts.add(identity)
            pending={'id':identity,'category':category,'role':d['role'],'state':'dispatched','failed':False}
            trace_calls+=1
            elapsed=d.get('elapsed_seconds')
            if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<trace_elapsed:
                raise ContractError('Comparison dispatch time ordering differs')
            trace_elapsed=elapsed
        elif kind=='call_failed':
            if pending is None or pending['state']!='dispatched' or pending['id']!=d['attempt_id']:
                raise ContractError('Comparison failure ordering differs')
            pending['failed']=True;pending['state']='failed'
        elif kind=='attempt_accounted':
            if pending is None or pending['state'] not in ('dispatched','failed') or pending['id']!=d['attempt_id']:
                raise ContractError('Comparison accounting ordering differs')
            trace_usage=add_usage(trace_usage,decode(Usage,d['usage']))
            if pending['failed']:
                halted=True
                halted_at=category_order[pending['category']]
                pending=None
            else:
                pending['state']='accounted'
        elif kind=='role_selection':
            if (pending is None or pending['state']!='accounted' or pending['id']!=d['attempt_id'] or
                    pending['category']!=d['category'] or pending['role']!=d['role']):
                raise ContractError('Comparison selection ordering differs')
            completed_roles.setdefault(d['category'],[]).append({'role':d['role'],'observation_ids':d['selected']})
            pending=None
        elif kind=='baseline_selection':
            if halted or pending is not None or d['category'] not in ready or d['category'] in baseline_choices or result['arm'] not in ('lexical','provider_score'):
                raise ContractError('Comparison baseline ordering differs')
            computed,status,reason=_baseline(chronological_bases[d['category']],result['arm'])
            if d['arm']!=result['arm'] or d['selected']!=computed or d['status']!=status or d['reason']!=reason:
                raise ContractError('Comparison baseline journal differs from deterministic recipe')
            baseline_choices[d['category']]=d
        elif kind=='claim_committed':
            claim=d['claim'];category=claim['category']
            if halted or pending is not None:
                raise ContractError('Comparison claim precedes completed call')
            if result['arm'] in ('lexical','provider_score'):
                selected=baseline_choices.get(category,{}).get('selected',[])
            else:
                roles=completed_roles.get(category,[])
                required_stages=STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
                if tuple(r['role'] for r in roles)!=required_stages:
                    raise ContractError('Comparison claim precedes complete review chain')
                selected=roles[-1]['observation_ids']
            if claim['observation_id'] not in selected:
                raise ContractError('Comparison claim precedes selected source')
        elif kind=='budget_denied':
            quote=decode(Usage,d['quote']);quote.validate()
            elapsed=d.get('elapsed_seconds')
            if (pending is not None or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<trace_elapsed or
                    (trace_calls<budget.max_calls and trace_usage.input_tokens+quote.input_tokens<=budget.max_input_tokens and
                     trace_usage.output_tokens+quote.output_tokens<=budget.max_output_tokens and
                     trace_usage.cost_usd+quote.cost_usd<=budget.max_cost_usd and elapsed<budget.max_seconds)):
                raise ContractError('Comparison budget denial was not justified')
            category=d['category'];prior=completed_roles.get(category,[])
            stages=STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
            if halted or category not in ready or len(prior)>=len(stages) or d['role']!=stages[len(prior)]:
                raise ContractError('Comparison denied an unplanned role')
            if backend_config is not None:
                req=_request(chronological_bases[category],d['role'],Category(category),policy,prior)
                payload=selection_payload(req,backend_config['max_output_tokens'],backend_config['seed'],backend_config['retrieval'].get('wire_format','canonical'))
                if encode(quote)!=encode(Usage(len(payload['prompt'].encode('utf-8'))+32,backend_config['max_output_tokens'],0)):
                    raise ContractError('Comparison denial quote differs from actual planned request')
            trace_elapsed=elapsed
            halted=True
            halted_at=category_order[category]
        elif kind=='wall_time_exhausted':
            elapsed=d.get('elapsed_seconds')
            if pending is not None or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<max(trace_elapsed,budget.max_seconds):
                raise ContractError('Comparison wall-time abstention differs')
            trace_elapsed=elapsed
            halted=True
            halted_at=category_order[d['category']]
        elif kind=='comparison_finalized':
            if pending is not None or index!=len(events)-1:
                raise ContractError('Comparison finalized an unresolved/duplicate attempt')
        elif kind in ('category_disabled','run_failed','run_interrupted'):
            if pending is not None:
                raise ContractError('Comparison terminal/category event ordering differs')
            if kind in ('run_failed','run_interrupted'):
                halted=True
                halted_at=last_category
            else:
                if disabled is None or d['category']!=disabled.value or category_order[d['category']]<=last_category:
                    raise ContractError('Comparison category disable event differs')
                last_category=category_order[d['category']]
        else:
            raise ContractError('Comparison journal contains an unknown/duplicate event')
    if type(result['elapsed_seconds']) not in (int,float) or not math.isfinite(result['elapsed_seconds']) or result['elapsed_seconds']<trace_elapsed:
        raise ContractError('Comparison elapsed time contradicts trace')
    for category in Category:
        records = store.query(case,category)
        cov = result['coverage'][category.value]
        expected_nonobserved = [{'observation_id':r.observation.observation_id,'status':r.observation.status.value}
                                for r in records if r.observation.status != EvidenceStatus.OBSERVED]
        count = sum(r.observation.status == EvidenceStatus.OBSERVED for r in records)
        if cov['available_in_collected_case_world'] != count or cov['nonobserved'] != expected_nonobserved:
            raise ContractError('Comparison source coverage differs from admission')
        if category == disabled and (cov['status'] != 'disabled_before_retrieval' or cov['selected'] != 0):
            raise ContractError('Comparison ablation did not disable before retrieval')
        if category!=disabled and not count and (cov['status']!='no_observed_evidence_in_collected_scope' or cov['selected']!=0):
            raise ContractError('Comparison empty-category status differs')
        if category!=disabled and count and category.value not in ready and (not halted or halted_at is None or category_order[category.value]<=halted_at or cov['status']!='not_run_after_budget_or_failure' or cov['selected']!=0):
            raise ContractError('Comparison omitted an eligible category without a stop')
        if ('retrieval' in cov)!=(category.value in ready):
            raise ContractError('Comparison retrieval coverage inventory differs')
        if cov['interpretation']!='Collected-source scope only; missing or excluded records are not biological absence':
            raise ContractError('Comparison biological absence overclaimed')
    failures = [e for e in events if e['event'] in ('call_failed','run_failed','run_interrupted')]
    interrupted = any(e['event']=='run_interrupted' or e['details'].get('error_class')=='KeyboardInterrupt' for e in failures)
    exhausted = any(e['event'] in ('budget_denied','wall_time_exhausted') for e in events)
    expected_status = 'interrupted' if interrupted else 'failed' if failures else 'budget_exhausted' if exhausted else 'completed'
    if result['status'] != expected_status or events[-1]['details']['status'] != result['status']:
        raise ContractError('Comparison terminal status differs from execution')
    retrieval = RetrievalPolicy(**result['configuration']['retrieval'])
    bases = {}
    for e in events:
        if e['event'] == 'bounded_candidates':
            d = e['details']; category = Category(d['category'])
            if category == disabled or category.value in bases:
                raise ContractError('Comparison retrieved an ablated or duplicate category')
            base, audit = _prepare(case, category, store, policy, retrieval)
            if fingerprint(audit) != fingerprint(d['audit']):
                raise ContractError('Comparison retrieval differs from admitted sources')
            if fingerprint(result['coverage'][category.value]['retrieval'])!=fingerprint(audit):
                raise ContractError('Comparison result retrieval coverage differs from journal/source')
            bases[category.value] = base
    dispatches = [e['details'] for e in events if e['event'] == 'dispatch']
    accounts = [e['details'] for e in events if e['event'] == 'attempt_accounted']
    execution = read_json(output/'backend-execution.json')['attempts']
    if len(dispatches) != len(accounts) or len(dispatches) != len(execution) or len(dispatches) != result['calls']:
        raise ContractError('Comparison physical call accounting differs')
    summed = measured = estimated = Usage(0, 0, 0)
    role_counts = {}
    previous_elapsed = 0.0
    priors = {}
    choices = {e['details']['attempt_id']: e['details'] for e in events if e['event'] == 'role_selection'}
    call_failures = {e['details']['attempt_id']:e['details'] for e in events if e['event']=='call_failed'}
    for dispatch, account, executed in zip(dispatches, accounts, execution):
        category = Category(dispatch['category']); role = dispatch['role']; prior = priors.setdefault(category.value, [])
        expected_request = _request(bases[category.value], role, category, policy, prior)
        request = decode(SpecialistRequest, dispatch['request'])
        attempt_id = dispatch['attempt_id']
        stages = STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
        role_index = role_counts.get(category.value,0)
        if (result['arm'] in ('lexical','provider_score') or role_index >= len(stages) or role != stages[role_index] or
                attempt_id != category.value+':'+role):
            raise ContractError('Comparison physical role order differs')
        role_counts[category.value] = role_index+1
        if fingerprint(request) != fingerprint(expected_request) or dispatch['request_sha256'] != fingerprint(request) or account['attempt_id'] != attempt_id or executed['attempt_id'] != attempt_id:
            raise ContractError('Comparison role request/attempt binding differs')
        usage = decode(Usage, account['usage']); usage.validate()
        quote = decode(Usage, dispatch['reserved']); quote.validate()
        elapsed = dispatch['elapsed_seconds']
        if (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed < previous_elapsed or
                elapsed >= budget.max_seconds or sum(role_counts.values())>budget.max_calls or
                summed.input_tokens+quote.input_tokens>budget.max_input_tokens or
                summed.output_tokens+quote.output_tokens>budget.max_output_tokens or
                summed.cost_usd+quote.cost_usd>budget.max_cost_usd):
            raise ContractError('Comparison dispatch exceeded its reservation/budget')
        previous_elapsed=elapsed
        record = executed['record']
        if record['request_sha256'] != fingerprint(request):
            raise ContractError('Comparison native request binding differs')
        if backend_config is not None:
            if result['configuration']['backend_provenance'].get('config') != backend_config:
                raise ContractError('Comparison local model configuration differs')
            payload = selection_payload(request, backend_config['max_output_tokens'], backend_config['seed'], backend_config['retrieval'].get('wire_format', 'canonical'))
            expected_quote = Usage(len(payload['prompt'].encode('utf-8'))+32,backend_config['max_output_tokens'],0)
            if encode(expected_quote) != encode(quote):
                raise ContractError('Comparison quote differs from bounded native request')
            if (fingerprint(record.get('request')) != fingerprint(request) or fingerprint(record.get('payload')) != fingerprint(payload) or
                    record.get('payload_sha256') != fingerprint(payload)):
                raise ContractError('Comparison model payload differs')
            if record['status'] == 'completed':
                selected, actual_usage = parse_selection(record['response'], [r.observation_id for r in request.evidence])
                if (over_quote(usage,quote) or account['basis']!='adapter_reported' or
                        encode(decode(Usage,record['measured_usage']))!=encode(actual_usage) or
                        fingerprint(record['response']) != record['response_sha256'] or list(selected) != record['selection'] or encode(actual_usage) != encode(usage)):
                    raise ContractError('Comparison native response/accounting differs')
                if attempt_id not in choices:
                    invalid_subset = role in ('scientific_reviewer','coordinator_synthesize') and bool(set(selected)-set(prior[-1]['observation_ids']))
                    if attempt_id not in call_failures or not invalid_subset or account['basis']!='adapter_reported':
                        raise ContractError('Comparison dropped a successful native selection without justified role failure')
            elif record['status'] not in ('failed','timeout'):
                raise ContractError('Comparison native attempt state differs')
            elif attempt_id not in call_failures or attempt_id in choices or account['basis']!='quoted_upper_bound_not_measured':
                raise ContractError('Comparison native failure/accounting event differs')
            elif record.get('error_class')!=call_failures[attempt_id]['error_class']:
                raise ContractError('Comparison native failure reason differs from journal')
        if attempt_id in choices:
            selected = list(choices[attempt_id]['selected'])
            if encode(decode(Usage,choices[attempt_id]['usage']))!=encode(usage):
                raise ContractError('Comparison role-reported usage differs from accounting')
            allowed = {r.observation_id for r in request.evidence}
            if len(selected) > 3 or len(selected) != len(set(selected)) or set(selected)-allowed:
                raise ContractError('Comparison role selected invalid IDs')
            if role in ('scientific_reviewer', 'coordinator_synthesize') and (not prior or set(selected)-set(prior[-1]['observation_ids'])):
                raise ContractError('Comparison bypassed critical review')
            if backend_config is not None and list(parse_selection(record['response'], allowed)[0]) != selected:
                raise ContractError('Comparison journal/native selection differs')
            prior.append({'role': role, 'observation_ids': selected})
        summed = add_usage(summed, usage)
        if account['basis'] == 'adapter_reported':
            measured = add_usage(measured, usage)
        elif account['basis'] == 'quoted_upper_bound_not_measured' and fingerprint(usage) == fingerprint(quote):
            estimated = add_usage(estimated, usage)
        else:
            raise ContractError('Comparison accounting basis differs')
    if any(encode(v) != result[k] for k,v in (('usage',summed),('measured_usage',measured),('estimated_usage',estimated))):
        raise ContractError('Comparison total usage differs')
    selection_categories={category for category,base in bases.items() if base.evidence}
    if set(result['selections'])!=selection_categories:
        raise ContractError('Comparison terminal selection category inventory differs')
    for category,base in bases.items():
        cov=result['coverage'][category]
        if not base.evidence:
            if cov['status']!='no_whole_records_within_budget' or cov['selected']!=0:
                raise ContractError('Comparison empty retrieval disposition differs')
            continue
        local_failures=[d for identity,d in call_failures.items() if identity.split(':',1)[0]==category]
        local_exhaustion=any(e['event'] in ('budget_denied','wall_time_exhausted') and e['details'].get('category')==category for e in events)
        if any(d['error_class']=='KeyboardInterrupt' for d in local_failures):
            status='interrupted'
        elif local_failures:
            status='failed'
        elif local_exhaustion:
            status='budget_exhausted'
        elif result['arm'] in ('lexical','provider_score'):
            status=_baseline(base,result['arm'])[1]
        else:
            stages=STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
            if tuple(r['role'] for r in priors.get(category,[]))!=stages:
                raise ContractError('Comparison role chain missing without a failure/exhaustion')
            status='completed'
        if cov['status']!=status:
            raise ContractError('Comparison coverage disposition differs from actual calls')
    expected_claims = []
    for category, selected in result['selections'].items():
        cov = result['coverage'][category]
        if cov['selected'] != len(selected):
            raise ContractError('Comparison coverage count differs')
        if cov['status'] == 'completed':
            if result['arm'] in ('lexical', 'provider_score'):
                computed, status, _ = _baseline(bases[category], result['arm'])
                if computed != selected or status != 'completed':
                    raise ContractError('Comparison baseline differs')
            else:
                prior = priors.get(category, [])
                expected_stages = STAGES if result['arm'] == 'adapted_virtual_biotech' else ('mapped_specialist',)
                if tuple(r['role'] for r in prior) != expected_stages or prior[-1]['observation_ids'] != selected:
                    raise ContractError('Comparison incomplete role chain committed claims')
        elif selected:
            roles=priors.get(category,[])
            if result['arm'] in ('lexical','provider_score'):
                terminal=_baseline(bases[category],result['arm'])[0]
            else:
                expected_stages=STAGES if result['arm']=='adapted_virtual_biotech' else ('mapped_specialist',)
                if tuple(r['role'] for r in roles)!=expected_stages:
                    raise ContractError('Comparison incomplete category committed claims')
                terminal=roles[-1]['observation_ids']
            if (cov['status']!='budget_exhausted' or terminal[:len(selected)]!=selected or not any(
                    e['event']=='wall_time_exhausted' and e['details'].get('category')==category and e['details'].get('stage')=='claim_commit' for e in events)):
                raise ContractError('Comparison partial claim commit lacks timed source proof')
        elif cov['status']=='inapplicable':
            if result['arm']!='provider_score' or _baseline(bases[category],result['arm'])[1:] != ('inapplicable',cov.get('reason')):
                raise ContractError('Comparison provider-score abstention differs')
        expected_claims += [_claim(store, Category(category), identity) for identity in selected]
    journal_claims = [e['details']['claim'] for e in events if e['event'] == 'claim_committed']
    if fingerprint(expected_claims) != fingerprint(result['claims']) or fingerprint(journal_claims) != fingerprint(expected_claims):
        raise ContractError('Comparison journal/source claims differ')
    return {'status': 'verified', 'byte_integrity': 'passed', 'semantic_consistency': 'passed',
        'source_binding': 'passed_against_supplied_admission', 'scientific_validation': 'not_established',
        'calls': len(dispatches), 'claims': len(expected_claims), 'result_sha256': sha256_file(output/'result.json')}
