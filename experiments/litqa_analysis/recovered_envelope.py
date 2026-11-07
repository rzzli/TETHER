"""Independent v2 recovery envelopes and supervised execution records.

Only independent analysis readers are imported. Certificate evidence is bound as
an external prospective input; this checker does not declare a new producer
equivalent, redo model inference, or turn source citations into scientific truth.
"""
import os
from pathlib import Path
import sys

from . import envelopes, native_records, recovered_run, source_archive
from .native_records import canonical, decode, digest, journal, load, need

REPO = Path(__file__).resolve().parents[2]
same = recovered_run._same


def _code_names():
    folders = ('src/tether_engine', 'packages/tether/src/tether', 'experiments/labbench',
               'experiments/litqa_comparison', 'experiments/litqa_supplied',
               'experiments/litqa_analysis', 'experiments/litqa_recovery')
    names = {p.relative_to(REPO).as_posix() for folder in folders for p in (REPO/folder).rglob('*.py')
             if not p.name.startswith('test_')}
    for name in tuple(names):
        for parent in (REPO/name).parents:
            if parent == REPO: break
            if (parent/'__init__.py').is_file(): names.add((parent/'__init__.py').relative_to(REPO).as_posix())
    return names


def _memory(value):
    if value is None: return None
    need(set(value)=={'working_set_bytes','process_peak_working_set_bytes','cpu_seconds'}, 'Captured process sample fields')
    for item in value.values():
        if item is not None: envelopes.nonnegative(item,'Captured process resource')
    return value


def _model(value, inputs):
    need(set(value) == {'model_receipt','model_license','port','alias','model_spec','model_provenance'}, 'Frozen model metadata fields')
    raw = inputs.bound(value['model_receipt']); receipt = decode(raw); inputs.bound(value['model_license'])
    root = source_archive._absolute(receipt['root'])
    entries, bindings = [], {}
    for item in receipt['items']:
        name = item['name']
        need(Path(name).name == name and '/' not in name and '\\' not in name, 'Model item basename')
        entries.append(dict(logical_id=name, sha256=item['sha256'], bytes=item['bytes'])); bindings[name] = str(root/name)
    for item in receipt['runtime_files']:
        name = item['path'].replace('\\','/')
        need(name.startswith('runtime/') and ':' not in name and all(p not in ('','.','..') for p in name.split('/')), 'Model runtime path')
        entries.append(dict(logical_id=name, sha256=item['sha256'], bytes=item['bytes'])); bindings[name] = str(root/name)
    entries.append(dict(logical_id='acquisition.json', sha256=value['model_receipt']['sha256'], bytes=len(raw)))
    bindings['acquisition.json'] = value['model_receipt']['path']
    need(len(bindings) == len(entries), 'Unique model asset identities')
    executables = [e for e in entries if e['logical_id'] == 'runtime/llama-server.exe']
    weights = sorted(e['logical_id'] for e in entries if e['logical_id'].endswith('.gguf'))
    need(len(executables) == 1 and weights and type(value['port']) is int and 1 <= value['port'] <= 65535,
         'Single pinned local model executable and bounded port')
    executable = executables[0]; alias = value['alias']
    need(isinstance(alias,str) and alias and len(alias)<=128, 'Frozen model alias')
    argv = [bindings[executable['logical_id']], '--model', bindings[weights[0]], '--host','127.0.0.1',
        '--port',str(value['port']), '--alias',alias,'--ctx-size','16384','--parallel','1',
        '--threads','8','--n-gpu-layers','99','--offline','--no-webui']
    spec = dict(argv=argv, executable=executable, required_inputs=[e for e in entries if e is not executable],
                host='127.0.0.1', port=value['port'], startup_seconds=180, terminate_seconds=30, kill_seconds=10)
    provenance = dict(weights_sha256={e['logical_id']:e['sha256'] for e in entries if e['logical_id'] in weights},
        runtime_sha256=executable['sha256'], asset_manifest_sha256=value['model_receipt']['sha256'],
        model_id=receipt['model_id'], revision=receipt['revision'])
    need(same(spec,value['model_spec']) and same(provenance,value['model_provenance']), 'Model receipt/specification/provenance differs')
    return dict(spec=spec, bindings=bindings, provenance=provenance, alias=alias)


def _transition(frame, parent, original, inputs):
    cert = inputs.json(frame['transition_certificate'])
    need(set(cert) == {'schema_version','kind','status','purpose','original_supplied_frame','primary','primary_acceptance',
        'source_archive','original_repository_root','current_code_pins','parity_proof','qualification'} and
        cert['schema_version'] == 2 and cert['kind'] == 'sc04_recovery_transition_certificate_v2' and
        cert['status'] == 'PASS' and cert['purpose'] == frame['purpose'] and cert['original_supplied_frame'] == parent['original_frame'] and
        cert['current_code_pins'] == frame['code_pins'], 'Prospective transition certificate binding')
    q = inputs.json(cert['qualification']); inputs.bound(cert['parity_proof'])
    need(q['schema_version'] == 2 and q['kind'] == 'sc04_recovery_controller_qualification_v2' and q['status'] == 'PASS' and
         type(q['tests']) is int and q['tests'] > 0 and all(type(q[k]) is int and q[k]==0 for k in ('failures','errors','skipped')) and
         q['code_pins'] == frame['code_pins'], 'Frozen controller qualification identity')
    archive = cert['source_archive']
    resolver = source_archive.load_archive(archive['path'], archive['sha256'], original['code_pins'], cert['original_repository_root'])
    inputs.bound(resolver.manifest_proof)
    for name in resolver.logical_names: inputs.bound(resolver.proof(name))
    primary = cert['primary']; root = Path(primary['root']); proof = inputs.proof(root/'ROOT-RECEIPT.json')
    need(proof['sha256'] == primary['root_receipt_sha256'], 'Sealed primary anchor')
    receipt = inputs.json(proof)
    # The accepted primary run owns nested phase receipts. Do not accidentally
    # reinterpret its root inventory as a recursive v2 inventory.
    files = envelopes.inventory(root, omit=('ROOT-RECEIPT.json',), recursive=False)
    need(receipt['status'] == 'primary_execution_complete' and receipt['files'] == files, 'Original primary root inventory')
    for value in files.values(): inputs.bound(value)
    complete = inputs.json(files['COMPLETE.json']); acceptance = inputs.json(cert['primary_acceptance'])
    need(complete['status'] == 'primary_execution_complete' and complete['purpose'] == frame['purpose'] and
         acceptance['status'] == 'passed' and acceptance['primary_execution_anchor'] == primary['root_receipt_sha256'] and
         acceptance['scientific_correctness_scored'] is False, 'Primary acceptance identity')
    inputs.bound(acceptance['primary_replay'])
    if frame['purpose'] == 'production':
        need(acceptance['questions'] == 199 and acceptance['answers'] == 796 and
             original['primary_execution']['root'] == str(root) and
             original['primary_execution']['receipt']['sha256'] == primary['root_receipt_sha256'], 'Full original primary parent')
    return cert


def _supervision(root, frame, phase, job_proof, frame_proof, inputs):
    records = {}; events = []
    for mode,label in (('worker','execution'), ('review-worker','review')):
        seconds = frame['phase_seconds'][phase] if mode=='worker' else frame['replay_seconds']
        output = root/('worker' if mode=='worker' else 'review')
        cache = REPO/'data/cache'/('sc04-recovery-'+frame_proof['sha256']+'-'+phase+('-review' if mode=='review-worker' else ''))
        command = [frame['environment']['executable']['path'], '-I','-B','-X','pycache_prefix='+str(cache),
            str(REPO/'experiments/litqa_recovery/run.py'),mode,'--frame',frame_proof['path'],
            '--frame-sha256',frame_proof['sha256'],'--job',job_proof['path'],
            '--job-sha256',job_proof['sha256'],'--output',str(output)]
        limits = dict(timeout_seconds=seconds,max_output_bytes=4194304)
        need(same(load(root/(label+'-COMMAND.json')),dict(command=command,limits=limits)), 'Exact supervised command and deadline')
        wrapper = load(root/(label+'-SUPERVISION.json')); report = wrapper['supervision']
        need(type(wrapper['returncode']) is int and wrapper['returncode']==0 and report['schema_version']==1 and
             report['method']=='tether.process_envelope.v1' and same(report['limits'],limits) and report['termination_reason']=='exited' and
             report['process_started'] is True and report['process_reaped'] is True and
             report['pipe_eof']==dict(stdout=True,stderr=True) and report['cleanup_errors']==[] and
             report['observed_counts_are_lower_bounds'] is False, 'Successful bounded process supervision')
        for stream in ('stdout','stderr'):
            n = inputs.proof(root/(label+'-'+stream+'.txt'))['bytes']
            need(type(report['retained_'+stream+'_bytes']) is int and
                 n == report['retained_'+stream+'_bytes'] == report['observed_'+stream+'_bytes'], 'Retained/observed child stream bytes')
        need(report['observed_stdout_bytes']+report['observed_stderr_bytes']<=4194304 and
             envelopes.nonnegative(report['execution_elapsed_seconds'],'Child execution elapsed')<=seconds and
             envelopes.nonnegative(report['total_elapsed_seconds'],'Child total elapsed')>=report['execution_elapsed_seconds'],
             'Supervision timing and stream limits')
        records[label] = report
        events.extend([('child_dispatched',dict(role=mode,command_sha256=digest(canonical(command)))), ('child_reaped',dict(role=mode))])
    return records,events


def _audit(root, phase, role, frame, frame_proof, parent, planning, cert, job_proof, job, model, inputs):
    allowed = {frame_proof['path'],job_proof['path']}
    def add(proof): inputs.bound(proof); allowed.add(proof['path'])
    for proof in (frame['planning_frame'],frame['planning_authority'],frame['transition_certificate'],parent['interrupted_snapshot'],
                  parent['original_frame'],frame['collection_frame']['qualification'],planning['registry_policy'],planning['prospective_contract']): add(proof)
    allowed.update(str(p) for p in Path(planning['output']).iterdir() if p.is_file())
    for proof in inputs.json(parent['interrupted_snapshot'])['original_inventory'].values(): add(proof)
    for proof in inputs.json(parent['original_frame'])['products'].values(): add(proof)
    for key in ('primary_acceptance','parity_proof','qualification'): add(cert[key])
    add(inputs.json(cert['primary_acceptance'])['primary_replay'])
    primary = Path(cert['primary']['root']); add(inputs.proof(primary/'ROOT-RECEIPT.json'))
    for proof in load(primary/'ROOT-RECEIPT.json')['files'].values(): add(proof)
    add(inputs.proof(cert['source_archive']['path']))
    for proof in load(cert['source_archive']['path'])['files'].values(): add(proof)
    for key in ('collection_frame','answer_claim'):
        if job[key] is not None: add(job[key])
    if job['collection'] is not None:
        allowed.update(str(p) for p in Path(job['collection']['root']).rglob('*') if p.is_file())
    authority = Path(planning['authority'])
    # A collection worker only had its collection claim. The later answer claim
    # may be present during replay but cannot retrospectively grant that read.
    for name in ('collection-execution/CLAIM.json','answer-execution/CLAIM.json'):
        path = authority/name
        if path.is_file() and (phase=='answer' or role=='review' or name.startswith('collection-')): allowed.add(str(path))
    allowed.update(str(REPO/name) for name in frame['code_pins'])
    allowed.add(frame['environment']['executable']['path'])
    allowed.update(frame['model'][key]['path'] for key in ('model_receipt','model_license'))
    if phase=='answer' and role=='worker': allowed.update(model['bindings'].values())
    if role=='review': allowed.update(str(p) for p in (root.parent/'worker').rglob('*') if p.is_file())
    cache = Path(job['import_cache']+('-review' if role=='review' else ''))
    code_roots = (REPO/'src',REPO/'packages/tether/src',REPO/'experiments',Path(sys.prefix),Path(sys.base_prefix),cache)
    raw = native_records.read(root/'io-audit.jsonl'); records = [decode(line) for line in raw.splitlines()]
    need(raw.endswith(b'\n') and records, 'Nonempty complete worker/review access audit')
    special = [record for record in records if record.get('basis')=='exclusive_collection_claim']
    for record in special:
        need(phase=='collect' and role=='worker' and set(record)=={'path','mode','flags','allowed','basis'} and
             record['path']==str(authority/'collection-execution/CLAIM.json') and record['allowed'] is True and
             type(record['flags']) is int, 'Exclusive collection claim audit role')
        flags = record['flags']; writing = flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
        need(not writing or flags & os.O_EXCL and flags & os.O_CREAT and not flags & (os.O_TRUNC|os.O_APPEND),
             'Claim cannot be rewritten or appended')
    ordinary = [record for record in records if record not in special]
    need(ordinary, 'Worker/review audit has no ordinary input events')
    result = envelopes.audit_records(b''.join(canonical(x)+b'\n' for x in ordinary), inputs=allowed, output=root, code_roots=code_roots)
    result['exclusive_claim_events'] = len(special)
    return result


def _verify_run(root, expected_root_sha256, inputs):
    """Verify the upper envelope and return arguments for independent reconstruction."""
    root = recovered_run.safe_path(root)
    proof = inputs.proof(root/'ROOT-RECEIPT.json'); receipt = inputs.json(proof)
    need(proof['sha256']==expected_root_sha256 and set(receipt)=={'schema_version','kind','frame','files'} and
         receipt['schema_version']==2 and receipt['kind']=='sc04_recovered_root_receipt_v2', 'External v2 root anchor/schema')
    files = inputs.inventory(root,omit=('ROOT-RECEIPT.json',)); need(files==receipt['files'],'Exact recovered root inventory')
    frame_proof = receipt['frame']; frame = inputs.json(frame_proof)
    need(set(frame)=={'schema_version','kind','purpose','created_at_utc','output','common_root','planning_frame','planning_authority',
         'transition_certificate','collection_frame','model','generation_configuration','code_pins','environment','phase_seconds',
         'replay_seconds','call_seconds','maximum_answer_calls','ordinary_retrieval','automatic_retry','provider_cost_usd'} and
         inputs.bound(frame_proof)==inputs.bound(files['FRAME.json']) and frame['kind']=='sc04_supervised_recovery_execution_v2' and
         frame['schema_version']==2 and frame['purpose'] in ('production','fictional_qualification') and frame['output']==str(root) and
         frame['ordinary_retrieval'] is False and frame['automatic_retry'] is False and frame['provider_cost_usd']==0,
         'Frozen recovery frame identity/role')
    envelopes.utc(frame['created_at_utc']); planning = inputs.json(frame['planning_frame']); parent = planning['plan']
    original = inputs.json(parent['original_frame'])
    need(frame['planning_authority']['path']==str(Path(planning['authority'])/'AUTHORITY.json') and
         frame['common_root']==str(Path(parent['original_root']).parent) and frame['model']==original['model'] and
         frame['generation_configuration']==original['generation_configuration'] and frame['purpose']==original['purpose'],
         'Original parent/model configuration')
    need(root!=Path(frame['common_root']) and root.is_relative_to(Path(frame['common_root'])), 'Declared common recovery root')
    need(set(frame['code_pins'])==_code_names(),'Complete recovery source closure')
    code = {name:inputs.proof(envelopes.child(REPO,name)) for name in frame['code_pins']}
    need(all(p['sha256']==frame['code_pins'][name] for name,p in code.items()),'Current frozen producer source bytes')
    cf = frame['collection_frame']
    need(cf['planning_frame']==frame['planning_frame'] and cf['planning_authority']==frame['planning_authority'] and
         cf['output']==str(root/'collect/worker/phase') and cf['limits']['phase_seconds']==frame['phase_seconds']['collect']-60,
         'Embedded collection authority/output/deadline')
    for p in (Path(parent['original_root']),Path(planning['registry']),Path(planning['output'])):
        need(not root.is_relative_to(p) and not p.is_relative_to(root),'Protected recovery output overlap')
    need(set(frame['phase_seconds'])=={'collect','answer'} and type(frame['phase_seconds']['collect']) is int and
         180<=frame['phase_seconds']['collect']<=21600 and type(frame['phase_seconds']['answer']) is int and
         240<=frame['phase_seconds']['answer']<=43200 and type(frame['replay_seconds']) is int and 60<=frame['replay_seconds']<=3600 and
         frame['call_seconds']==120 and frame['maximum_answer_calls']==len(parent['answer_queries']), 'Bounded recovered execution schedule')
    for key in ('executable','engine_initializer','facade_initializer'): inputs.bound(frame['environment'][key])
    cert = _transition(frame,parent,original,inputs); model = _model(frame['model'],inputs)
    complete = inputs.json(files['COMPLETE.json'])
    need(same(complete,dict(status='recovered_diagnostic_complete',purpose=frame['purpose'],frame=frame_proof,
         phases=complete['phases'],answer_claim=complete['answer_claim'],wall_seconds=complete['wall_seconds'],provider_cost_usd=0,
         ordinary_retrieval=False,scientific_scoring_performed=False,sc04_complete=False)) and set(complete['phases'])=={'collect','answer'},
         'Exact recovered root completion')
    envelopes.nonnegative(complete['wall_seconds'],'Controller elapsed')
    claim = complete['answer_claim']; expected_claim = dict(schema_version=2,kind='sc04_answer_execution_claim_v2',
        frame=frame_proof,output=str(root),parent_identity=parent['parent_identity'],question_ids=[q['id'] for q in parent['answer_queries']],
        maximum_calls=len(parent['answer_queries']),automatic_retry=False)
    need(claim['path']==str(Path(planning['authority'])/'answer-execution/CLAIM.json') and same(inputs.json(claim),expected_claim),
         'Permanent answer authority and full denominator')
    results = {}; resources = {}; jobs = {}
    for phase in ('collect','answer'):
        phase_root = root/phase; descriptor = complete['phases'][phase]; phase_files = inputs.inventory(phase_root,omit=('PACKAGE-RECEIPT.json',))
        top_names = {'JOB.json','journal.jsonl','REPLAY.json','PACKAGE-RECEIPT.json'} | {
            label+suffix for label in ('execution','review') for suffix in
            ('-COMMAND.json','-SUPERVISION.json','-stdout.txt','-stderr.txt')}
        if phase=='collect': top_names.add('COLLECTION-FRAME.json')
        need({p.name for p in phase_root.iterdir() if p.is_file()}==top_names and
             {p.name for p in phase_root.iterdir() if p.is_dir()}=={'worker','review'}, 'Exact phase artifact membership')
        for role in ('worker','review'):
            role_root = phase_root/role
            names = {'REPORT.json','journal.jsonl','io-audit.jsonl'} if role=='review' else {'CONFIG.json','COMPLETE.json','journal.jsonl','io-audit.jsonl'}
            directories = set() if role=='review' else {'phase'}
            if phase=='answer' and role=='worker':
                names.update(('MODEL.json','SERVER-RESOURCE-SAMPLES.json')); directories.add('server')
            need({p.name for p in role_root.iterdir() if p.is_file()}==names and
                 {p.name for p in role_root.iterdir() if p.is_dir()}==directories, 'Exact worker/review artifact membership')
        if phase=='answer':
            need({p.name for p in (phase_root/'worker/server').iterdir()}==
                 {'server-command.json','server.stdout.log','server.stderr.log'}, 'Exact owned-server artifacts')
        need(descriptor['root']==str(phase_root) and descriptor['receipt']==files[phase+'/PACKAGE-RECEIPT.json'] and
             inputs.json(descriptor['receipt'])==dict(schema_version=2,phase=phase,frame=frame_proof,files=phase_files), 'Phase package ancestry')
        job_proof = files[phase+'/JOB.json']; job = inputs.json(job_proof); jobs[phase] = job
        cache = str(REPO/'data/cache'/('sc04-recovery-'+frame_proof['sha256']+'-'+phase))
        expected_job = dict(schema_version=2,phase=phase,frame=frame_proof,collection=complete['phases']['collect'] if phase=='answer' else None,
            collection_frame=files['collect/COLLECTION-FRAME.json'] if phase=='collect' else None,
            answer_claim=claim if phase=='answer' else None,cutoff=job['cutoff'] if phase=='answer' else None,import_cache=cache)
        need(same(job,expected_job),'Exact phase predecessor/job/claim binding')
        if phase=='collect': need(inputs.json(job['collection_frame'])==cf,'Embedded collection frame bytes')
        else: envelopes.utc(job['cutoff'])
        supv, expected_events = _supervision(phase_root,frame,phase,job_proof,frame_proof,inputs)
        worker_root = phase_root/'worker'; worker = load(worker_root/'COMPLETE.json')
        need(set(worker)=={'status','phase','frame','job','stage_receipt','accounting','wall_seconds','worker_memory',
             'server_terminal','audit_denials','provider_cost_usd'} and
             same(load(worker_root/'CONFIG.json'),dict(frame=frame_proof,job=job,purpose=frame['purpose'])) and
             worker['status']=='complete' and worker['phase']==phase and worker['frame']==frame_proof and worker['job']==job_proof and
             worker['audit_denials']==0 and worker['provider_cost_usd']==0 and
             envelopes.nonnegative(worker['wall_seconds'],'Worker elapsed')<frame['phase_seconds'][phase], 'Worker completion/configuration')
        stage_name = 'RECEIPT.json' if phase=='collect' else 'STAGE-RECEIPT.json'
        stage = files[phase+'/worker/phase/'+stage_name]
        need(worker['stage_receipt']==descriptor['stage_receipt']==stage,'Phase/worker original stage anchor')
        if phase=='collect':
            need(worker['server_terminal'] is None and worker['accounting']==load(worker_root/'phase/MANIFEST.json')['accounting'], 'Source worker resource accounting')
            expected_summary = dict(unique_dois=len(parent['doi_schedule']),accounting=worker['accounting'])
        else:
            terminal = worker['server_terminal']
            need(same(load(worker_root/'MODEL.json'),model) and terminal['server_stopped'] is True and terminal['started'] is True and
                 type(terminal['pid']) is int and terminal['pid']>0 and type(terminal['exit_code']) is int and
                 terminal['secondary_failures']==[] and 'error_class' not in terminal, 'Owned model launch/cleanup identity')
            envelopes.nonnegative(terminal['elapsed_seconds'],'Model elapsed')
            need(load(worker_root/'server/server-command.json')==model['spec'],'Owned server original command')
            usage,cells=envelopes._native_resources(worker_root/'phase')
            expected_accounting=dict(scheduled=len(parent['answer_queries']),entered=len(parent['answer_queries']),unexecuted=0,
                generation_calls=usage['generation_calls'],
                measured_usage=dict(input_tokens=usage['measured_input_tokens'],output_tokens=usage['measured_output_tokens'],cost_usd=0.0),
                conservative_reservations=dict(input_tokens=usage['reserved_input_tokens'],output_tokens=usage['reserved_output_tokens']),
                maximum_calls=frame['maximum_answer_calls'])
            need(len(cells)==len(parent['answer_queries']) and usage['generation_calls']<=frame['maximum_answer_calls'] and
                 usage['reserved_output_tokens']<=256*frame['maximum_answer_calls'] and same(worker['accounting'],expected_accounting),
                 'Whole answer schedule accounting')
            expected_summary = dict(status='verified',questions=len(parent['answer_queries']),diagnostic_only=True,ordinary_retrieval=False,
                recovery_contract='sc04_recovered_source_context_v2',scientific_correctness='Not evaluated by maintained replay')
        report = dict(status='verified',phase=phase,frame=frame_proof,stage_receipt=stage,summary=expected_summary,
                      model_or_http_execution_performed=False,scientific_support_verified=False)
        need(same(load(phase_root/'REPLAY.json'),report) and same(load(phase_root/'review/REPORT.json'),report), 'Retained review declarative report')
        expected_events = [('phase_reserved',dict(phase=phase,frame=frame_proof))]+expected_events+[
            ('phase_verified',dict(report=files[phase+'/REPLAY.json']))]
        need([(e['event'],e['details']) for e in journal(phase_root/'journal.jsonl')]==expected_events,'Exact phase dispatch/reap journal')
        we = [('worker_reserved',dict(frame=frame_proof,job=job_proof))]
        if phase=='answer': we += [('server_started',dict(pid=terminal['pid'])),('server_ready',dict(pid=terminal['pid'])),('server_terminal',terminal)]
        we += [('worker_completed',dict(complete=files[phase+'/worker/COMPLETE.json']))]
        need([(e['event'],e['details']) for e in journal(worker_root/'journal.jsonl')]==we,'Worker/server event bijection')
        need([(e['event'],e['details']) for e in journal(phase_root/'review/journal.jsonl')]==[
            ('review_reserved',dict(frame=frame_proof,job=job_proof)),('review_completed',dict(report=files[phase+'/review/REPORT.json']))], 'Independent review event binding')
        audits = {role:_audit(phase_root/role,phase,role,frame,frame_proof,parent,planning,cert,job_proof,job,model,inputs)
                  for role in ('worker','review')}
        results[phase] = dict(stage_root=str(worker_root/'phase'),stage_receipt=stage,worker=worker,job=job,report=report)
        resources[phase] = dict(supervision=supv,worker_wall_seconds=worker['wall_seconds'],worker_memory=_memory(worker['worker_memory']),io_audit=audits)
        if phase=='answer':
            samples=load(worker_root/'SERVER-RESOURCE-SAMPLES.json'); values=[]
            need(isinstance(samples,list) and 0<len(samples)<=100000, 'Bounded process resource sample series')
            for sample in samples:
                need(set(sample)=={'monotonic','value','error_class'} and
                     (sample['error_class'] is None or isinstance(sample['error_class'],str)), 'Process sample schema')
                envelopes.nonnegative(sample['monotonic'],'Sample clock'); value=_memory(sample['value'])
                if sample['error_class'] is None and value is not None: values.append(value)
            peaks=[v['process_peak_working_set_bytes'] for v in values if v['process_peak_working_set_bytes'] is not None]
            resources[phase].update(server_peak_working_set_bytes=max(peaks,default=None),
                server_cpu_seconds_last_sample=values[-1]['cpu_seconds'] if values else None,
                server_resource_sample_errors=sum(s['error_class'] is not None for s in samples),
                server_resource_unknown_samples=sum(s['value'] is None for s in samples))
    expected = [('controller_reserved',dict(frame=frame_proof)),('controller_verified',dict(frame=frame_proof,parent_identity=parent['parent_identity'])),
        ('phase_accepted',dict(phase='collect',descriptor=complete['phases']['collect'])),('answers_claimed',dict(claim=claim)),
        ('phase_accepted',dict(phase='answer',descriptor=complete['phases']['answer'])),('controller_completed',dict(complete=files['COMPLETE.json']))]
    need([(e['event'],e['details']) for e in journal(root/'journal.jsonl')]==expected,'Root event order and authority binding')
    need({p.name for p in root.iterdir() if p.is_dir()}=={'collect','answer'} and
         {p.name for p in root.iterdir() if p.is_file()}=={'FRAME.json','COMPLETE.json','journal.jsonl','ROOT-RECEIPT.json'}, 'Exact root artifact membership')
    args = dict(common_root=frame['common_root'],cutoff=jobs['answer']['cutoff'],model_provenance=model['provenance'],alias=model['alias'],
        owner_pid=results['answer']['worker']['server_terminal']['pid'],configuration=frame['generation_configuration'],
        code_proof=code['experiments/litqa_comparison/codecs.py'],catalog_proof=code['experiments/labbench/tether_adapter.py'],
        expected_endpoint=f'http://127.0.0.1:{model["spec"]["port"]}')
    inputs.unchanged(); need(inputs.inventory(root,omit=('ROOT-RECEIPT.json',))==files,'Root changed during envelope analysis')
    return dict(root=str(root),root_sha256=expected_root_sha256,frame=frame,frame_sha256=frame_proof['sha256'],phases=results,
        reconstruction_arguments=args,resources=resources,executed_source_proofs=code,transition_evidence_bound=True,
        original_supplied_frame=dict(proof=parent['original_frame'],value=original),
        transition_certificate=dict(proof=frame['transition_certificate'],value=cert),parent_identity=parent['parent_identity'],
        producer_equivalence_independently_adjudicated=False,source_lineage_checked=False,native_calls_checked=False,
        scope='Independent sealed root, process supervision, original model/claims and recorded access classification. Source and native answer reconstruction is a separate required gate; transition evidence is bound, not newly approved here.')


def verify_run(root, expected_root_sha256):
    """Check the supervised envelope with a private, operation-scoped tracker."""
    return _verify_run(root, expected_root_sha256, recovered_run._Inputs())


def reconstruct(root, expected_root_sha256):
    """Join independent upper-envelope and source/native reconstruction gates."""
    inputs = recovered_run._Inputs()
    envelope = _verify_run(root,expected_root_sha256,inputs); phases = envelope['phases']
    result = recovered_run.reconstruct(phases['collect']['stage_root'],phases['collect']['stage_receipt']['sha256'],
        phases['answer']['stage_root'],phases['answer']['stage_receipt']['sha256'],**envelope['reconstruction_arguments'])
    result.update(root=envelope['root'],root_sha256=expected_root_sha256,frame_sha256=envelope['frame_sha256'],
        frame=envelope['frame'],supervised_root_verified=True,executed_source_proofs=envelope['executed_source_proofs'],executed_source_archive=None,
        original_supplied_frame=envelope['original_supplied_frame'],transition_certificate=envelope['transition_certificate'],
        parent_identity=envelope['parent_identity'],
        transition_evidence_bound=True,producer_equivalence_independently_adjudicated=False)
    result['resources']['supervised_phases'] = envelope['resources']
    inputs.unchanged()
    return result
