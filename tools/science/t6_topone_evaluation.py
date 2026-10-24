"""Post-seal descriptive source prioritization; never clinical performance."""
from collections import Counter
from pathlib import Path

from asof.contracts import Category
from asof.journal import RunJournal, read_chain
from asof.serde import encode, fingerprint, read_json, safe_child, sha256_file, write_json
from tools.science.comparison_workflow import verify_case
from tools.science.run_comparison import check_pin, pin, verify_model
from tools.science.t6_challenge import task_store, validate_plan, check_reference, PORT
from tools.science.t6_reference import require, validate_review


def score_task(task, result, reference):
    offered = set(task['offered_candidate_ids'])
    selected = [claim['observation_id'] for claim in result['claims']]
    require(len(selected) <= 1 and not set(selected) - offered, 'Selection escapes top-one task')
    ratings = {r['observation_id']: r for r in reference['candidates']}
    best = set(reference['admissible_best_ids'])
    status = result['coverage'][task['category']]['status']
    applicable = status == 'completed'
    return {'task_id': task['task_id'], 'case_id': task['case_id'], 'category': task['category'],
            'arm': result['arm'], 'run_status': result['status'], 'category_status': status,
            'selected': selected, 'baseline_inapplicable': status == 'inapplicable',
            'admissible_best_ids': sorted(best), 'none_sufficient': reference['none_sufficient'],
            'reference_uncertainty': reference['reference_uncertainty'],
            'reference_tie': len(best) > 1, 'all_candidates_tied': best == offered,
            'abstained': applicable and not selected,
            'decision_agreement': (bool(set(selected) & best) if selected else not best) if applicable else None,
            'context_mismatch': (ratings[selected[0]]['applicability'] == 'context_mismatch') if selected else None,
            'calls': result['calls'], 'measured_usage': result['measured_usage'],
            'estimated_usage': result['estimated_usage'], 'elapsed_seconds': result['elapsed_seconds']}


def sealed_inventory(root):
    root = Path(root)
    seal = read_json(root/'seal.json')
    expected = {r['path']: r for r in seal['files']}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'seal.json'}
    require(len(expected) == len(seal['files']) and set(expected) == actual, 'Execution inventory differs')
    for name, row in expected.items():
        path = safe_child(root, name)
        require(path.stat().st_size == row['bytes'] and sha256_file(path) == row['sha256'], 'Execution bytes changed')


def verify_execution_transcript(events, execution):
    require(events[-1]['event'] == 'execution_terminal' and
            events[-1]['details']['status'] == execution['status'] and
            events[-1]['details']['server_stopped'] is True, 'Execution terminal journal differs')
    expected_events = ['build_reserved', 'model_verification_started', 'server_started']
    expected_arms = []
    for paired in execution['tasks']:
        for arm in paired['arms']:
            expected_events.extend(['arm_started', 'arm_verified'])
            expected_arms.append((paired['task_id'], arm))
    expected_events.append('execution_terminal')
    require([e['event'] for e in events] == expected_events, 'Launcher event schedule differs')
    require(type(events[2]['details'].get('pid')) is int and events[2]['details']['pid'] > 0,
            'Launcher native process identity missing')
    for (task_id, arm), start, finish in zip(expected_arms, events[3:-1:2], events[4:-1:2]):
        require(start['details'] == {'task_id': task_id, 'arm': arm['arm']} and
                finish['details'] == {'task_id': task_id, 'arm': arm['arm'], 'result_sha256': arm['result']['sha256']},
                'Launcher arm transcript differs')


def audit_originals(validated, by_case, plan, output):
    """Audit every distinct selected case/observation against physical originals."""
    from asof.ingest import _load_case_pack
    from asof.provenance import InputGraph, catalog_index
    from tools.framework.run_pilot import SourceAudit
    from tools.science.reference_packets import _mappings, audit_observation
    build = read_json(check_pin(plan['source_build']))
    bundle = Path(plan['source_build']['path']).parent
    definitions, _, _ = _load_case_pack(bundle/'case-pack.json', build['case_pack']['sha256'])
    definitions = {d.case_id: d for d in definitions}
    planned = {r['case_id']: r for r in plan['cases']}
    policy = catalog_index(read_json(check_pin(plan['catalog'])))
    audit, proofs, rows, mapped, seen = SourceAudit(), {}, [], {}, set()
    for task, result in validated:
        case, store = by_case[task['case_id']]
        folder = Path(planned[case.case_id]['case']['path']).parent
        if case.case_id not in mapped:
            graph = InputGraph(store.snapshot, folder, policy)
            nodes, refs, disease = _mappings(audit, folder,
                read_json(check_pin(planned[case.case_id]['case'])),
                read_json(check_pin(planned[case.case_id]['snapshot'])), definitions[case.case_id], graph, proofs)
            mapped[case.case_id] = (graph, nodes, refs, disease)
        graph, nodes, refs, disease = mapped[case.case_id]
        for claim in result['claims']:
            key = (case.case_id, claim['observation_id'])
            if key in seen:
                continue
            seen.add(key)
            row = audit_observation(audit, claim['evidence']['observation'], case=case,
                nodes=nodes, graph=graph, mapping_refs=refs, symbol=definitions[case.case_id].symbol,
                disease_name=disease, proofs=proofs)
            rows.append({'case_id': case.case_id, 'task_id': task['task_id'], 'audit': row})
    for proof in proofs.values():
        audit.source(proof, proof['raw_root'])
        require(sha256_file(safe_child(Path(proof['raw_root']), proof['receipt_path'])) == proof['receipt_sha256'],
                'Original source receipt changed')
    write_json(output/'original-row-audits.json', rows)
    return {'distinct_case_observations': len(rows), 'rows': pin(output/'original-row-audits.json'),
            'source_files_hashed': len(audit.hashes), 'source_proofs': list(proofs.values()),
            'scope': 'All distinct selected case/observation pairs across four arms; technical source fidelity, not biological truth.'}


def evaluate(predictions_proof, output):
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    try:
        code = pin(Path(__file__))
        (output/'executed-source.py').write_bytes(Path(__file__).read_bytes())
        predictions = read_json(check_pin(predictions_proof))
        require(predictions.get('role') == 'sealed_topone_predictions_before_answer_join' and
                predictions.get('reference_answers_opened') is False and
                predictions.get('clinical_probabilities') is None, 'Prediction boundary differs')
        plan = read_json(check_pin(predictions['plan']))
        sources, frozen = validate_plan(plan)
        root = Path(plan['root'])
        require(Path(predictions['plan']['path']).resolve() == root/'run-plan.json' and
                Path(predictions['report']['path']).resolve() == root/'execution-report.json', 'Launcher report paths differ')
        require(Path(predictions_proof['path']).resolve() == root/'predictions-seal.json', 'Prediction seal path differs')
        sealed_inventory(root)
        execution = read_json(check_pin(predictions['report']))
        require(execution['status'] == 'all_topone_runs_verified' and execution['server_stopped']
                and execution['owned_loopback_port_closed'], 'Execution or cleanup incomplete')
        require(predictions['tasks'] == execution['tasks'] and predictions['reference_seal'] == execution['reference_seal'],
                'Prediction and execution summaries differ')
        required_proofs = {'execution/journal.jsonl', 'prepare/journal.jsonl', 'server-command.json',
                           'model-config.json', 'server.stdout.log', 'server.stderr.log'}
        require(set(predictions['proofs']) == required_proofs, 'Launcher proof inventory differs')
        for name, proof in predictions['proofs'].items():
            require(Path(proof['path']).resolve() == root/name, 'Launcher proof path differs')
            check_pin(proof)
        events = read_chain(root/'execution/journal.jsonl')
        verify_execution_transcript(events, execution)
        config = read_json(root/'model-config.json')
        require(config.get('selection_cap') == 1, 'Backend selection cap differs')
        for key in ('retrieval', 'max_output_tokens', 'timeout_seconds', 'seed', 'selection_cap'):
            require(config[key] == plan['backend'][key], 'Backend settings differ')
        receipt = read_json(check_pin(plan['model_receipt']))
        server, model = verify_model(receipt)
        expected_argv = [str(server), '--model', str(model), '--host', '127.0.0.1', '--port', str(PORT),
                         '--ctx-size', '16384', '--parallel', '1', '--n-gpu-layers', '99', '--threads', '8',
                         '--alias', 'asof-t6-topone', '--no-webui', '--offline']
        require(read_json(root/'server-command.json') == {'argv': expected_argv, 'runtime_sha256': sha256_file(server)},
                'Native server command differs')
        require(config['endpoint'] == f'http://127.0.0.1:{PORT}' and
                config['model_id'] == 'Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'] and
                config['model_provenance']['acquisition_receipt_sha256'] == plan['model_receipt']['sha256'],
                'Model identity or transport differs')
        require(config['model_provenance']['runtime_sha256'] == sha256_file(server), 'Runtime provenance differs')
        require(config['model_provenance']['weights_sha256'] ==
                {r['name']: r['sha256'] for r in receipt['items'] if r['name'].endswith('.gguf')}, 'Weights provenance differs')
        policy = read_json(check_pin(plan['role_policy']))
        by_case = {case.case_id: (case, full) for case, full in sources}
        tasks = {t['task_id']: t for t in frozen['tasks']}
        require([t['task_id'] for t in execution['tasks']] == list(tasks), 'Executed task membership differs')
        validated = []
        for scheduled, paired in zip(plan['execution_order'], execution['tasks']):
            task = tasks[paired['task_id']]
            case, full = by_case[task['case_id']]
            store, _ = task_store(case, full, Category(task['category']))
            require([a['arm'] for a in paired['arms']] == scheduled['arms'], 'Arm order or membership differs')
            for arm in paired['arms']:
                folder = root/'arms'/task['task_id']/arm['arm']
                for key, path in [('result', folder/'result.json'), ('seal', folder/'seal.json'),
                                  ('verification', folder.parent/(arm['arm']+'-verification.json'))]:
                    require(Path(arm[key]['path']).resolve() == path, 'Arm path differs')
                    check_pin(arm[key])
                verification = verify_case(folder, case, store, backend_config=config, role_policy=policy)
                require(verification == read_json(check_pin(arm['verification'])), 'Saved arm verification differs')
                result = read_json(check_pin(arm['result']))
                require(all(result[k] == arm[k] for k in ('status', 'calls', 'usage')) and result['arm'] == arm['arm'],
                        'Arm summary differs')
                require(result['features'] == {} and result['probability'] is None, 'Numerical prediction forbidden')
                validated.append((task, result))
        journal.append('all_predictions_source_verified_before_answer_join', predictions=predictions_proof)
        original_audit = audit_originals(validated, by_case, plan, output)
        ref = check_reference(predictions['reference_seal'], plan['tasks'])
        reviews = [validate_review(read_json(check_pin(p)), frozen) for p in ref['reviews']]
        resolved = validate_review(read_json(check_pin(ref['adjudication'])), frozen)
        require(ref['reviews'][0]['sha256'] != ref['reviews'][1]['sha256'] and
                reviews[0]['reviewer_id'] != reviews[1]['reviewer_id'] and
                resolved['reviewer_id'] not in {r['reviewer_id'] for r in reviews}, 'Reference reviewer identity differs')
        require(resolved['task_manifest'] == plan['tasks'] and resolved['reviews'] == ref['reviews'], 'Reference parent binding differs')
        require(all(r['task_manifest'] == plan['tasks'] for r in reviews), 'Independent reference binding differs')
        answers = {r['task_id']: r for r in resolved['tasks']}
        rows = [score_task(task, result, answers[task['task_id']]) for task, result in validated]
        summaries = []
        for arm in plan['arms']:
            items = [r for r in rows if r['arm'] == arm]
            known = [r for r in items if r['decision_agreement'] is not None]
            summaries.append({'arm': arm, 'tasks': len(items), 'evaluable_decisions': len(known),
                'agreeing_decisions': sum(r['decision_agreement'] for r in known),
                'inapplicable': sum(r['baseline_inapplicable'] for r in items),
                'abstentions': sum(r['abstained'] for r in items),
                'context_mismatches': sum(r['context_mismatch'] is True for r in items),
                'statuses': dict(Counter(r['run_status'] for r in items)),
                'calls': sum(r['calls'] for r in items),
                'measured_usage': {k: sum(r['measured_usage'][k] for r in items) for k in ('input_tokens', 'output_tokens', 'cost_usd')},
                'elapsed_seconds': sum(r['elapsed_seconds'] for r in items)})
        check_pin(code)
        check_pin(predictions_proof)
        check_reference(predictions['reference_seal'], plan['tasks'])
        sealed_inventory(root)
        report = {'schema_version': 1, 'role': 'evaluation_only', 'status': 'postseal_topone_descriptive_evaluation_complete',
                  'predictions': predictions_proof, 'reference': predictions['reference_seal'], 'evaluator': code,
                  'tasks': len(tasks), 'cases': len({t['case_id'] for t in tasks.values()}),
                  'per_task_arm': rows, 'per_arm': summaries, 'provider_spend_usd': 0,
                  'reference_uncertainty': dict(Counter(r['reference_uncertainty'] for r in answers.values())),
                  'tied_reference_tasks': sum(len(r['admissible_best_ids']) > 1 for r in answers.values()),
                  'original_row_audit': original_audit,
                  'scientific_truth': 'not_established', 'clinical_metrics': None, 'probabilities': None,
                  'interpretation': 'Exposed AI-source-adjudicated development prioritization; no independent clinical truth, inferential superiority or explanation quality claim.'}
        write_json(output/'report.json', report)
        journal.append('evaluation_completed', report=pin(output/'report.json'))
        return report
    except BaseException as error:
        journal.fail(error, 'topone_evaluation')
        raise
    finally:
        journal.close()
