"""Finite source-only top-one T6 tasks and single-use owned local execution.

Task selection never reads reference ratings or model outputs. Complete admitted
case worlds remain proofs; the task projection is an explicit separate layer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

from asof.chrono import EvidenceStore, load_snapshot
from asof.contracts import Case, Category, EvidenceStatus
from asof.ingest import peak_memory_bytes
from asof.journal import RunJournal
from asof.local_model import NoRedirect
from asof.retrieval import RetrievalPolicy
from asof.serde import ContractError, decode, encode, fingerprint, read_json, safe_child, sha256_file, write_json
from asof.workflow import Budget
from tools.science.comparison_workflow import _prepare, run_case, verify_case, default_role_policy
from tools.science.role_backend import RoleSelectionBackend
from tools.science.run_comparison import selected_store, pin, check_pin, verify_model, port_closed, _owned_listener

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'planning/protocols/t6-topone-development-v0.1.json'
PORT = 55582
ARMS = ['asof', 'adapted_virtual_biotech', 'lexical', 'provider_score']
SOURCE_BUNDLE = 'data/derived/science2-fresh-20261018T170501Z'
SOURCE_BUILD_SHA256 = 'b3f5b4352215bd571159f190799d4ce865999d8bf3d9e51712183d55979124f3'
CODE_FILES = ('tools/science/t6_challenge.py', 'tools/science/run_comparison.py',
              'tools/science/t6_reference.py', 'tools/science/t6_topone_evaluation.py',
              'tools/science/reference_packets.py', 'tools/framework/run_pilot.py',
              'tools/science/comparison_workflow.py', 'tools/science/role_backend.py') + tuple(
    p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/asof').glob('*.py')))


class PinnedRoleSelectionBackend(RoleSelectionBackend):
    """Guard the generated configuration before every quote and physical call."""
    def __init__(self, config_proof):
        self.config_proof = dict(config_proof)
        super().__init__(check_pin(self.config_proof))
        self.expected_config = fingerprint(self.provenance['config'])
        self._guard()

    def _guard(self):
        check_pin(self.config_proof)
        if (fingerprint(self.provenance['config']) != self.expected_config or
                self.provenance['config_sha256'] != self.config_proof['sha256']):
            raise ContractError('Top-one backend configuration changed before dispatch')

    def quote(self, request):
        self._guard()
        return super().quote(request)

    def select(self, request):
        self._guard()
        return super().select(request)


def task_store(case, full, category):
    """Project one category without discarding complete admission/source proofs."""
    category = Category(category)
    complete, selection = selected_store(case, full)
    records = tuple(complete.query(case, category))
    projected = EvidenceStore(full.snapshot, records, full.exclusions, full.source_proofs, full.catalog_policy)
    projected.snapshot_base = full.snapshot_base
    proof = {'category': category.value, 'parent_selection': selection,
             'parent_source_proofs_sha256': fingerprint(full.source_proofs),
             'projected_records': {r.observation.observation_id: fingerprint(r) for r in records}}
    return projected, proof


def freeze_tasks(case_stores, policy, retrieval, maximum_tasks=8, maximum_per_case=2, minimum_candidates=2):
    """Original case order, Category enum order, all dispositions, no replacement."""
    if (type(maximum_tasks) is not int or maximum_tasks != 8 or
            type(maximum_per_case) is not int or maximum_per_case != 2 or
            type(minimum_candidates) is not int or minimum_candidates != 2 or
            type(policy.get('selection_cap')) is not int or policy.get('selection_cap') != 1):
        raise ContractError('Top-one finite task recipe differs')
    tasks, dispositions = [], []
    for case, full in case_stores:
        selected_for_case = 0
        for category in Category:
            projected, projection = task_store(case, full, category)
            base, audit = _prepare(case, category, projected, policy, retrieval)
            ids = [r.observation_id for r in base.evidence]
            if len(ids) != len(set(ids)):
                raise ContractError('Duplicate offered candidate IDs')
            disposition = ('insufficient_offered_candidates' if len(ids) < minimum_candidates else
                           'beyond_total_cap' if len(tasks) >= maximum_tasks else
                           'beyond_case_cap' if selected_for_case >= maximum_per_case else 'selected')
            row = {'task_id': case.case_id+'--'+category.value, 'case_id': case.case_id,
                   'category': category.value, 'offered_candidate_ids': ids,
                   'offered_count': len(ids), 'disposition': disposition,
                   'retrieval': encode(audit), 'projection': projection,
                   'request': encode(base), 'request_sha256': fingerprint(base)}
            dispositions.append(row)
            if disposition == 'selected':
                tasks.append(row)
                selected_for_case += 1
    return {'schema_version': 1, 'role': 'source_only_task_manifest',
            'selection': 'original_case_order_then_Category_order_without_answers',
            'selection_cap': 1, 'maximum_tasks': maximum_tasks,
            'maximum_tasks_per_case': maximum_per_case,
            'minimum_offered_candidates': minimum_candidates,
            'tasks': tasks, 'dispositions': dispositions,
            'reference_answers_opened': False, 'model_outputs_opened': False}


def _output(path):
    path = Path(path).resolve()
    if not any(path.is_relative_to(ROOT/name) for name in ('runs', 'data/derived')):
        raise ContractError('Top-one output must be in ignored runs or derived tree')
    return path


def _load_sources(plan, protocol):
    bundle = safe_child(ROOT, protocol['source_bundle'])
    build = read_json(check_pin(plan['source_build']))
    if (check_pin(plan['source_build']) != bundle/'build-report.json' or
            plan['source_build']['sha256'] != protocol['source_build_report_sha256'] or
            build['status'] != 'built' or len(build['cases']) != 10 or
            [r['case_id'] for r in plan['cases']] != [r['case_id'] for r in build['cases']]):
        raise ContractError('Top-one complete ten-case parent build differs')
    loaded = []
    for row in plan['cases']:
        folder = safe_child(bundle, row['case_id'])
        for field, name in (('case', 'case.json'), ('snapshot', 'snapshot.json')):
            if check_pin(row[field]) != folder/name:
                raise ContractError('Top-one source path differs')
        case = decode(Case, read_json(check_pin(row['case'])))
        if case.case_id != row['case_id'] or case.task != 'T6':
            raise ContractError('Top-one parent case differs')
        full = load_snapshot(check_pin(row['snapshot']), case, check_pin(plan['catalog']))
        _, selection = selected_store(case, full)
        if (fingerprint(row['selection']) != fingerprint(selection) or
                fingerprint(row['source_proofs']) != fingerprint(full.source_proofs)):
            raise ContractError('Top-one complete parent world or source proofs differ')
        loaded.append((case, full))
    return loaded


def validate_plan(plan):
    output = _output(plan['root'])
    protocol = read_json(check_pin(plan['protocol']))
    if (Path(plan['protocol']['path']).resolve() != PROTOCOL.resolve() or
            protocol.get('protocol_id') != 't6-topone-source-bounded-development-v0.1' or
            type(plan.get('schema_version')) is not int or plan.get('schema_version') != 1 or
            type(plan.get('provider_spend_usd')) is not int or plan.get('provider_spend_usd') != 0 or
            plan.get('reference_answers_opened') is not False or plan.get('arms') != ARMS):
        raise ContractError('Top-one protocol or scientific boundary differs')
    if (protocol.get('source_bundle') != SOURCE_BUNDLE or
            protocol.get('source_build_report_sha256') != SOURCE_BUILD_SHA256):
        raise ContractError('Top-one protocol parent build differs')
    if any(type(protocol.get(k)) is not int or protocol.get(k) != v for k,v in {'selection_cap':1,'maximum_tasks':8,
            'maximum_tasks_per_case':2,'minimum_offered_candidates':2}.items()):
        raise ContractError('Top-one frozen task caps differ')
    for field, expected in (('arms', protocol['arms']), ('backend', protocol['local_backend']),
                            ('budget', protocol['budget_per_task_per_arm'])):
        if fingerprint(plan[field]) != fingerprint(expected):
            raise ContractError('Top-one fixed configuration differs: '+field)
    if (type(plan['backend'].get('selection_cap')) is not int or plan['backend'].get('selection_cap') != 1 or
            plan['backend'].get('retrieval') != {'max_records':12, 'max_request_bytes':12000,
                                                 'wire_format':'asof-shared-scientific-fields-v1'}):
        raise ContractError('Top-one packet/output bounds differ')
    for field, name in (('catalog','catalog-policy.json'), ('role_policy','role-policy.json'),
                        ('tasks','tasks.json'), ('model_receipt','model-acquisition.json')):
        if check_pin(plan[field]) != output/name:
            raise ContractError('Top-one local manifest path differs')
    policy = read_json(check_pin(plan['role_policy']))
    policy_source = safe_child(ROOT,protocol['role_policy']['path'])
    if sha256_file(policy_source) != protocol['role_policy']['sha256']:
        raise ContractError('Top-one upstream role policy source differs')
    expected_policy = default_role_policy()
    expected_policy['selection_cap'] = 1
    expected_policy['prioritization_question'] = protocol['reference_policy']['question']
    if fingerprint(policy) != fingerprint(expected_policy):
        raise ContractError('Top-one source role policy differs')
    if (plan['model_receipt']['sha256'] != protocol['local_backend']['acquisition_receipt_sha256'] or
            plan['original_model_receipt']['sha256'] != plan['model_receipt']['sha256']):
        raise ContractError('Top-one model receipt differs')
    check_pin(plan['original_model_receipt'])
    if ({Path(p['path']).resolve() for p in plan['code']} != {(ROOT/n).resolve() for n in CODE_FILES} or
            len(plan['code']) != len(CODE_FILES)):
        raise ContractError('Top-one code inventory differs')
    for proof in plan['code']:
        source = check_pin(proof)
        archived = output/'executed-code'/source.relative_to(ROOT)
        if not archived.is_file() or sha256_file(archived) != proof['sha256']:
            raise ContractError('Top-one code archive differs')
    sources = _load_sources(plan, protocol)
    frozen = freeze_tasks(sources, policy, RetrievalPolicy(**plan['backend']['retrieval']))
    if fingerprint(read_json(check_pin(plan['tasks']))) != fingerprint(frozen):
        raise ContractError('Top-one task projection or offered packet differs')
    expected_schedule = [{'task_id': t['task_id'], 'arms': ARMS[i%4:]+ARMS[:i%4]}
                         for i,t in enumerate(frozen['tasks'])]
    if plan['execution_order'] != expected_schedule:
        raise ContractError('Top-one arm rotation differs')
    Budget(**plan['budget']).validate()
    return sources, frozen


def prepare(output, protocol_path=PROTOCOL):
    output = _output(output)
    output.mkdir(parents=True, exist_ok=False)
    journal = RunJournal(output/'prepare', kind='build')
    try:
        protocol_path = Path(protocol_path).resolve()
        if protocol_path != PROTOCOL.resolve():
            raise ContractError('Top-one protocol must use the named versioned project contract')
        protocol = read_json(protocol_path)
        bundle = safe_child(ROOT, protocol['source_bundle'])
        if sha256_file(bundle/'build-report.json') != protocol['source_build_report_sha256']:
            raise ContractError('Top-one parent source build differs')
        build = read_json(bundle/'build-report.json')
        if build['status'] != 'built' or len(build['cases']) != 10:
            raise ContractError('Top-one requires the complete frozen ten-case parent build')
        (output/'catalog-policy.json').write_bytes((ROOT/'data/catalog/sources.json').read_bytes())
        policy = default_role_policy(); policy['selection_cap'] = 1
        policy['prioritization_question'] = protocol['reference_policy']['question']
        write_json(output/'role-policy.json', policy)
        pointer = read_json(ROOT/'data/derived/active-local-model-acquisition.json')
        original = check_pin({**pin(pointer['path']), 'sha256':pointer['sha256']})
        (output/'model-acquisition.json').write_bytes(original.read_bytes())
        plan = {'schema_version':1, 'root':str(output), 'created_at_utc':datetime.now(timezone.utc).isoformat(),
                'protocol':pin(protocol_path), 'source_build':pin(bundle/'build-report.json'),
                'catalog':pin(output/'catalog-policy.json'), 'role_policy':pin(output/'role-policy.json'),
                'model_receipt':pin(output/'model-acquisition.json'), 'original_model_receipt':pin(original),
                'arms':protocol['arms'], 'budget':protocol['budget_per_task_per_arm'],
                'backend':protocol['local_backend'], 'cases':[], 'code':[pin(ROOT/n) for n in CODE_FILES],
                'reference_answers_opened':False, 'provider_spend_usd':0}
        sources = []
        for entry in build['cases']:
            folder = safe_child(bundle, entry['case_id'])
            case = decode(Case, read_json(folder/'case.json'))
            full = load_snapshot(folder/'snapshot.json', case, output/'catalog-policy.json')
            _, selection = selected_store(case, full)
            plan['cases'].append({'case_id':case.case_id, 'case':pin(folder/'case.json'),
                'snapshot':pin(folder/'snapshot.json'), 'selection':selection, 'source_proofs':encode(full.source_proofs)})
            sources.append((case,full))
            journal.append('complete_source_world', case_id=case.case_id, selection=selection)
        frozen = freeze_tasks(sources, policy, RetrievalPolicy(**plan['backend']['retrieval']))
        write_json(output/'tasks.json', frozen); plan['tasks'] = pin(output/'tasks.json')
        plan['execution_order'] = [{'task_id':t['task_id'], 'arms':ARMS[i%4:]+ARMS[:i%4]}
                                   for i,t in enumerate(frozen['tasks'])]
        for name in CODE_FILES:
            archived = output/'executed-code'/name
            archived.parent.mkdir(parents=True, exist_ok=True)
            archived.write_bytes((ROOT/name).read_bytes())
        validate_plan(plan)
        write_json(output/'run-plan.json', plan)
        journal.append('tasks_frozen', tasks=len(frozen['tasks']), plan_sha256=sha256_file(output/'run-plan.json'))
        return {'status':'prepared_without_answers_or_inference', 'plan':pin(output/'run-plan.json'),
                'tasks':len(frozen['tasks']), 'task_manifest':pin(output/'tasks.json')}
    except BaseException as error:
        journal.fail(error,'preparation'); raise
    finally:
        journal.close()


def check_reference(proof, tasks_proof):
    """Read only seal metadata and hash child bytes; never deserialize ratings."""
    seal = read_json(check_pin(proof))
    if (seal.get('schema_version') != 1 or seal.get('role') != 'evaluation_only' or
            seal.get('status') != 'sealed_source_only_AI_reference' or
            seal.get('task_manifest') != tasks_proof or len(seal.get('reviews',[])) != 2 or
            not seal.get('limitations') or not seal.get('created_at_utc')):
        raise ContractError('Top-one execution requires sealed independent and reconciled reference')
    children = seal['reviews']+[seal['adjudication']]
    if len({str(Path(p['path']).resolve()) for p in children}) != 3:
        raise ContractError('Top-one independent reference artifacts must be distinct')
    approved = ROOT/'data/benchmark/gold_evidence/t6-topone-20261023'
    if not Path(proof['path']).resolve().is_relative_to(approved):
        raise ContractError('Top-one reference seal outside evaluator-only path')
    for child in children:
        if not check_pin(child).resolve().is_relative_to(approved):
            raise ContractError('Top-one reference child outside evaluator-only path')
    return seal


def execute(plan_path, expected_sha256, reference_manifest, reference_sha256):
    plan_path = Path(plan_path).resolve()
    if sha256_file(plan_path) != expected_sha256:
        raise ContractError('Top-one plan hash differs')
    plan = read_json(plan_path); output = _output(plan['root'])
    if plan_path != output/'run-plan.json':
        raise ContractError('Top-one plan moved outside its reservation')
    journal = RunJournal(output/'execution',kind='build')
    process = None; started = time.monotonic()
    report = {'schema_version':1, 'status':'running', 'plan':pin(plan_path), 'tasks':[],
              'provider_spend_usd':0, 'clinical_probabilities':None, 'reference_answers_opened':False}
    try:
        sources, frozen = validate_plan(plan)
        if not frozen['tasks']:
            raise ContractError('No eligible top-one tasks; no model dispatch')
        reference = {**pin(reference_manifest), 'sha256':reference_sha256}
        check_reference(reference,plan['tasks']); report['reference_seal'] = reference
        receipt = read_json(check_pin(plan['model_receipt']))
        journal.append('model_verification_started'); server, model = verify_model(receipt)
        with socket.socket() as check:
            check.bind(('127.0.0.1',PORT))
        argv = [str(server),'--model',str(model),'--host','127.0.0.1','--port',str(PORT),
                '--ctx-size','16384','--parallel','1','--n-gpu-layers','99','--threads','8',
                '--alias','asof-t6-topone','--no-webui','--offline']
        write_json(output/'server-command.json',{'argv':argv,'runtime_sha256':sha256_file(server)})
        with (output/'server.stdout.log').open('xb') as stdout,(output/'server.stderr.log').open('xb') as stderr:
            process = subprocess.Popen(argv,stdout=stdout,stderr=stderr,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        journal.append('server_started',pid=process.pid)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        deadline = time.monotonic()+180
        while time.monotonic()<deadline:
            if process.poll() is not None:
                raise ContractError('Owned top-one server exited; no retry')
            try:
                with opener.open(f'http://127.0.0.1:{PORT}/health',timeout=1) as response:
                    if response.status==200: break
            except OSError: time.sleep(1)
        else: raise TimeoutError('Top-one server startup deadline; no retry')
        if not _owned_listener(process.pid,PORT):
            raise ContractError('Top-one server listener not owned')
        settings = plan['backend']
        config = {'schema_version':1,'endpoint':f'http://127.0.0.1:{PORT}',
            'model_id':'Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'],
            'model_provenance':{'weights_sha256':{r['name']:r['sha256'] for r in receipt['items'] if r['name'].endswith('.gguf')},
                                'runtime_sha256':sha256_file(server),'acquisition_receipt_sha256':plan['model_receipt']['sha256']},
            **{key:settings[key] for key in ('retrieval','max_output_tokens','timeout_seconds','seed','selection_cap')}}
        write_json(output/'model-config.json',config)
        config_proof = pin(output/'model-config.json')
        report['model_config'] = config_proof
        policy = read_json(check_pin(plan['role_policy']))
        by_case = {case.case_id:(case,full) for case,full in sources}
        by_task = {row['task_id']:row for row in frozen['tasks']}
        for schedule in plan['execution_order']:
            task = by_task[schedule['task_id']]; case,full = by_case[task['case_id']]
            store,projection = task_store(case,full,Category(task['category']))
            if fingerprint(projection)!=fingerprint(task['projection']):
                raise ContractError('Top-one source projection changed')
            task_result = {'task_id':task['task_id'],'arms':[]}; report['tasks'].append(task_result)
            for arm in schedule['arms']:
                for proof in plan['code']: check_pin(proof)
                check_reference(reference,plan['tasks'])
                check_pin(config_proof)
                backend = PinnedRoleSelectionBackend(config_proof)
                folder = output/'arms'/task['task_id']/arm
                journal.append('arm_started',task_id=task['task_id'],arm=arm)
                result = run_case(case,store,backend,Budget(**plan['budget']),arm,folder,role_policy=policy)
                validation = verify_case(folder,case,store,backend_config=config,role_policy=policy)
                check_pin(config_proof)
                if result.get('probability') is not None or result.get('features')!={}:
                    raise ContractError('Top-one unqualified numerical prediction')
                selected = [r['observation_id'] for r in result['claims']]
                if len(selected)>1 or set(selected)-set(task['offered_candidate_ids']):
                    raise ContractError('Top-one output escaped frozen candidates or cap')
                write_json(folder.parent/(arm+'-verification.json'),validation)
                task_result['arms'].append({'arm':arm,'result':pin(folder/'result.json'),
                    'seal':pin(folder/'seal.json'),'verification':pin(folder.parent/(arm+'-verification.json')),
                    'status':result['status'],'calls':result['calls'],'usage':result['usage']})
                journal.append('arm_verified',task_id=task['task_id'],arm=arm,result_sha256=sha256_file(folder/'result.json'))
                print(json.dumps({'task_id':task['task_id'],'arm':arm,'status':result['status'],'calls':result['calls']}),flush=True)
                if result['status'] not in ('completed','budget_exhausted'):
                    raise ContractError('Top-one arm failed; retained without automatic repeat')
        validate_plan(plan); check_reference(reference,plan['tasks']); check_pin(config_proof)
        report['status']='all_topone_runs_verified'
    except BaseException as error:
        report.update(status='failed',error_class=type(error).__name__,error=str(error))
        journal.fail(error,'execution'); raise
    finally:
        cleanup_errors = []
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=10)
        except BaseException as cleanup_error:
            cleanup_errors.append({'error_class':type(cleanup_error).__name__,'error':str(cleanup_error)})
        try:
            stopped = process is None or process.poll() is not None
        except BaseException as cleanup_error:
            stopped = False
            cleanup_errors.append({'error_class':type(cleanup_error).__name__,'error':str(cleanup_error)})
        try:
            closed = port_closed(PORT)
        except BaseException as cleanup_error:
            closed = False
            cleanup_errors.append({'error_class':type(cleanup_error).__name__,'error':str(cleanup_error)})
        report.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,
            server_stopped=stopped,owned_loopback_port_closed=closed,cleanup_errors=cleanup_errors,
            peak_python_memory_bytes=peak_memory_bytes(),peak_native_memory_bytes=None,
            native_memory_reason='Not measured; no estimate inferred')
        if cleanup_errors or (report['status']=='all_topone_runs_verified' and not (
                report['server_stopped'] and report['owned_loopback_port_closed'])):
            report.update(status='failed',error_class='CleanupVerificationError',
                          error='Owned native process and loopback closure were not both verified')
            journal.append('cleanup_verification_failed',server_stopped=report['server_stopped'],
                           port_closed=report['owned_loopback_port_closed'])
        try:
            write_json(output/'execution-report.json',report)
            journal.append('execution_terminal',status=report['status'],server_stopped=report['server_stopped'])
        except BaseException as finalization_error:
            journal.fail(finalization_error,'terminal_record')
            raise
        finally:
            journal.close()
        if report['status']=='all_topone_runs_verified':
            write_json(output/'predictions-seal.json',{'schema_version':1,'role':'sealed_topone_predictions_before_answer_join',
                'plan':pin(plan_path),'report':pin(output/'execution-report.json'),'reference_seal':report['reference_seal'],
                'proofs':{name:pin(output/name) for name in ('execution/journal.jsonl','prepare/journal.jsonl',
                    'server-command.json','model-config.json','server.stdout.log','server.stderr.log')},
                'tasks':report['tasks'],'clinical_probabilities':None,'reference_answers_opened':False})
        write_json(output/'seal.json',{'schema_version':1,'files':[
            {'path':p.relative_to(output).as_posix(),'bytes':p.stat().st_size,'sha256':sha256_file(p)}
            for p in sorted(output.rglob('*')) if p.is_file() and p!=output/'seal.json']})
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='command',required=True)
    prep=commands.add_parser('prepare'); prep.add_argument('--output',type=Path,required=True)
    run=commands.add_parser('execute'); run.add_argument('--plan',type=Path,required=True)
    run.add_argument('--expected-sha256',required=True); run.add_argument('--reference-manifest',type=Path,required=True)
    run.add_argument('--reference-sha256',required=True)
    args=parser.parse_args(argv)
    result=prepare(args.output) if args.command=='prepare' else execute(args.plan,args.expected_sha256,args.reference_manifest,args.reference_sha256)
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
