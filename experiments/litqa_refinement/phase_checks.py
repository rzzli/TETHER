"""Read-only reconciliation of a completed refinement process envelope.

The caller first verifies the package inventory and child stage with their
external anchors. This helper checks the captured controls, process terminal,
worker journal and observed file grants. It neither executes model code nor
interprets biological sources or evaluator answers.
"""
from collections.abc import Mapping
from pathlib import Path
import math
import os
import sys
import time

from tether._process import ProcessLimits, validate_success_report
from tether_engine.serde import canonical, encode, fingerprint, freeze, parse_json
from tether_engine.study.stable_read import read_file
from . import contracts, projection, schedule


MODELS = ('critic', 'repair', 'removal')
LAUNCHER = ('import runpy,sys;sys.path[:0]=sys.argv[1:4];'
            'sys.argv=["tether-sc05-worker"]+sys.argv[4:];'
            'runpy.run_module("experiments.litqa_refinement.run",run_name="__main__")')


def _finite(value, label, *, minimum=0, maximum=None):
    contracts.need(type(value) in (int, float) and math.isfinite(value)
                   and value >= minimum and (maximum is None or value < maximum), label)
    return value


def _chain(raw):
    contracts.need(raw.endswith(b'\n'), 'Complete worker journal required')
    result = []
    previous = None
    for line in raw.splitlines():
        value = parse_json(line)
        contracts.need(set(value) == {'sequence', 'event', 'details', 'previous_sha256', 'sha256'},
                       'Worker journal fields')
        digest = value.pop('sha256')
        contracts.need(type(value['sequence']) is int and value['sequence'] == len(result)
                       and value['previous_sha256'] == previous and fingerprint(value) == digest,
                       'Worker journal hash chain')
        value['sha256'] = digest
        result.append(value)
        previous = digest
    contracts.need(bool(result), 'Empty worker journal')
    return result


class _Captured:
    def __init__(self, root, files, deadline):
        self.root, self.files, self.deadline = root, files, deadline
        self.checked = {}
        self.external_checked = {}

    def raw(self, name):
        contracts.need(name in self.files, 'Required phase artifact missing: ' + name)
        spec = self.files[name]
        projection._proof(spec)
        path = projection._path(spec['path'])
        contracts.need(path == self.root / name, 'Phase artifact location differs')
        raw = read_file(path, self.deadline, 128 * 1024**2)
        contracts.need(len(raw) == spec['bytes'] and contracts.codecs.digest(raw) == spec['sha256'],
                       'Phase artifact changed: ' + name)
        self.checked[name] = spec
        return raw

    def json(self, name):
        return parse_json(self.raw(name))

    def external(self, path, expected):
        path = projection._path(str(path))
        raw = read_file(path, self.deadline, 16 * 1024**2)
        contracts.need(contracts.codecs.digest(raw) == expected, 'External control anchor differs')
        prior = self.external_checked.get(path)
        contracts.need(prior is None or prior == expected, 'Contradictory external control anchor')
        self.external_checked[path] = expected
        return parse_json(raw)

    def recheck(self):
        for name in tuple(self.checked):
            self.raw(name)
        for path, expected in tuple(self.external_checked.items()):
            self.external(path, expected)


def _worker_journal(raw, terminal, config, phase):
    events = _chain(raw)
    expected = ['build_reserved']
    if phase in MODELS:
        expected += ['server_started', 'server_ready', 'server_terminal']
    expected += ['refinement_worker_completed']
    contracts.need([row['event'] for row in events] == expected, 'Exact worker completion journal')
    reserved = events[0]['details']
    contracts.need(type(config['worker_pid']) is int and config['worker_pid'] > 0
                   and reserved['owner_pid'] == config['worker_pid'], 'Worker owner identity')
    contracts.need(events[-1]['details'] == {'terminal_sha256': fingerprint(terminal)},
                   'Worker journal terminal fingerprint')
    server = terminal['server_terminal']
    if phase not in MODELS:
        contracts.need(server is None, 'Nonmodel phase cannot contain a native process')
        return
    fields = {'started', 'server_stopped', 'exit_code', 'secondary_failures',
              'peak_native_memory_bytes', 'peak_native_memory_reason', 'pid', 'elapsed_seconds'}
    contracts.need(isinstance(server, Mapping) and set(server) == fields
                   and server['started'] is True and server['server_stopped'] is True
                   and type(server['exit_code']) is int and not server['secondary_failures']
                   and type(server['pid']) is int and server['pid'] > 0,
                   'Native server success and cleanup declaration')
    contracts.need(events[1]['details'] == events[2]['details'] == {'pid': server['pid']}
                   and canonical(events[3]['details']) == canonical(server),
                   'Native process journal identity')
    _finite(server['elapsed_seconds'], 'Native elapsed time', maximum=terminal['wall_seconds'])
    memory = server['peak_native_memory_bytes']
    contracts.need((type(memory) is int and memory >= 0) or
                   (memory is None and isinstance(server['peak_native_memory_reason'], str)
                    and bool(server['peak_native_memory_reason'])), 'Native memory missingness')


def _audit(raw, *, root, frame, job, rows):
    """Rebuild every logged open decision and all ordered actor scopes."""
    contracts.need(not raw or raw.endswith(b'\n'), 'Complete I/O audit required')
    worker = root / 'worker'
    code = {str(projection._path(item['path']).resolve()).casefold() for item in frame['code_files']}
    models = {str(projection._path(path).resolve()).casefold() for path in job['model_bindings'].values()}
    inputs = {str(projection._path(item['path']).resolve()).casefold() for item in job['input_files']}
    inputs.update(str(p.resolve()).casefold() for p in
                  (root.parent/'FRAME.json', root/'JOB.json',
                   projection._path(frame['model_receipt']['path']),
                   projection._path(frame['model_license']['path'])))
    runtime = tuple(Path(p).resolve() for p in (sys.prefix, sys.base_prefix))
    expected_outputs = [worker/'phase/products'/f'{row["ordinal"]:04d}' for row in rows]
    phase = job['phase']
    role = 'coordinator'
    active = None
    cursor = 0
    opens = 0
    for line in raw.splitlines():
        row = parse_json(line)
        if 'event' in row:
            if row['event'] == 'actor_entered':
                contracts.need(set(row) == {'event', 'role', 'output', 'coordinator_inputs_granted'}
                               and row['coordinator_inputs_granted'] is False
                               and role == 'coordinator' and phase in MODELS
                               and row['role'] == phase and cursor < len(expected_outputs),
                               'Actor entry role and coordinator isolation')
                active = projection._path(row['output'])
                contracts.need(active == expected_outputs[cursor], 'Ordered actor output differs')
                role = phase
            else:
                contracts.need(row['event'] == 'actor_exited'
                               and set(row) == {'event', 'role', 'output'}
                               and role == phase and active is not None and row['role'] == role
                               and projection._path(row['output']) == active, 'Matching actor exit')
                role, active = 'coordinator', None
                cursor += 1
            continue
        opens += 1
        contracts.need(row.get('role') == role and row.get('allowed') is True,
                       'Observed denial or mismatched audit role')
        flags, mode = row.get('flags'), row.get('mode')
        contracts.need(type(flags) is int and flags >= 0 and (mode is None or isinstance(mode, str)),
                       'Open mode/flags required')
        if row.get('path') is None:
            contracts.need(set(row) == {'path','descriptor','mode','flags','allowed','basis','role'}
                           and type(row['descriptor']) is int and row['descriptor'] >= 0
                           and row['basis'] == 'existing_descriptor', 'Existing descriptor audit')
            continue
        contracts.need(set(row) == {'path','mode','flags','allowed','basis','role'}, 'Path open audit fields')
        path = projection._path(row['path']).resolve()
        key = str(path).casefold()
        write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if mode is not None:
            contracts.need(write == any(c in mode for c in 'wax+'), 'Open mode contradicts flags')
        target = worker if role == 'coordinator' else active
        own = path.is_relative_to(target)
        shared = key in code or key in models or any(path.is_relative_to(p) for p in runtime)
        explicit = role == 'coordinator' and key in inputs
        contracts.need(own or (not write and (shared or explicit)), 'Observed open lacks role authority')
        expected = 'role_output' if own else 'code_model_runtime' if shared else 'coordinator_input'
        contracts.need(row['basis'] == expected, 'Audit authority basis differs')
    contracts.need(role == 'coordinator' and active is None
                   and cursor == (len(rows) if phase in MODELS else 0), 'All actors must exit exactly once')
    contracts.need(opens > 0, 'An empty I/O log cannot establish file grants')
    return dict(observed_opens=opens, observed_denials=0, completed_actor_scopes=cursor)


def verify_phase(root, receipt, verified_stage, *, deadline=None):
    """Check a previously byte-verified package and semantically verified stage.

    This is bookkeeping validation, not source admission. It intentionally does
    not load reference answers, original source payloads or model weights.
    """
    root = projection._path(str(root))
    end = time.monotonic()+120 if deadline is None else deadline
    read = _Captured(root, receipt['files'], end)
    frame = read.external(root.parent/'FRAME.json', receipt['frame_sha256'])
    phase = receipt['phase']
    contracts.need(phase in schedule.PHASES and root == projection._path(frame['output'])/phase
                   and frame['kind'] == 'sc05_refinement_execution_v1'
                   and frame['provider_spend_usd'] == 0 and frame['automatic_retry'] is False,
                   'Phase/frame root and policy')
    job = read.json('JOB.json')
    config = read.json('worker/CONFIG.json')
    terminal = read.json('worker/COMPLETE.json')
    contracts.need(set(job) == {'phase','frame_sha256','parents','input_files','model_bindings','cutoff'}
                   and job['phase'] == phase and job['frame_sha256'] == receipt['frame_sha256']
                   and set(job['parents']) == set(schedule.PARENTS[phase]), 'Exact job phase and parents')
    contracts.need(set(config) == {'frame_sha256','job_sha256','phase','purpose','worker_pid','python_version','coordinator_grants'}
                   and config['frame_sha256'] == receipt['frame_sha256']
                   and config['job_sha256'] == receipt['files']['JOB.json']['sha256']
                   and config['phase'] == phase and config['purpose'] == frame['purpose']
                   and canonical(config['coordinator_grants']) == canonical(job['input_files']),
                   'Worker configuration and exact grants')
    for key in ('input_files',):
        paths = []
        for item in job[key]:
            projection._proof(item)
            paths.append(str(projection._path(item['path']).resolve()).casefold())
        contracts.need(len(paths) == len(set(paths)), 'Duplicate coordinator grant')
    for name, descriptor in job['parents'].items():
        contracts.need(set(descriptor) == {'root','package_sha256','stage_receipt_sha256'}
                       and projection._path(descriptor['root']) == root.parent/name, 'Parent role root differs')
        parent = read.external(root.parent/name/'PACKAGE-RECEIPT.json', descriptor['package_sha256'])
        parent_stage = parent['files']['worker/phase/STAGE-RECEIPT.json']
        contracts.need(parent['status'] == 'complete' and parent['phase'] == name
                       and parent['frame_sha256'] == receipt['frame_sha256']
                       and projection._path(parent_stage['path']) == root.parent/name/'worker/phase/STAGE-RECEIPT.json'
                       and parent_stage['sha256'] == descriptor['stage_receipt_sha256'],
                       'Parent package and child stage identity')
    if phase == 'removal':
        # Both paired runs must inherit the same pre-generation product. The
        # factual output itself must never be promoted to a removal parent.
        anchor = parse_json(read_file(root.parent/'repair-ANCHOR.json', end, 1024**2))
        contracts.need(projection._path(anchor['root']) == root.parent/'repair', 'Paired factual phase root')
        repair = read.external(root.parent/'repair/PACKAGE-RECEIPT.json', anchor['package_sha256'])
        spec = repair['files']['JOB.json']
        contracts.need(repair['status'] == 'complete' and repair['phase'] == 'repair'
                       and repair['frame_sha256'] == receipt['frame_sha256']
                       and projection._path(spec['path']) == root.parent/'repair/JOB.json',
                       'Paired factual package identity')
        other = read.external(root.parent/'repair/JOB.json', spec['sha256'])
        contracts.need(other['phase'] == 'repair' and other['frame_sha256'] == receipt['frame_sha256']
                       and canonical(other['parents']) == canonical(job['parents']),
                       'Paired runs must share exact frozen parent')
    model = read.json('worker/MODEL.json')
    contracts.need(set(model) == {'spec','bindings','provenance','alias'}
                   and canonical(model['spec']) == canonical(frame['model_spec'])
                   and canonical(model['provenance']) == canonical(frame['model_provenance'])
                   and model['bindings'] == job['model_bindings'] and model['alias'] == frame['alias'],
                   'Frozen native configuration differs')
    fields = {'status','phase','purpose','frame_sha256','stage_receipt','wall_seconds','worker_memory',
              'server_terminal','audit_denials','provider_cost_usd','reference_keys_read','scientific_scoring_performed'}
    contracts.need(set(terminal) == fields and terminal['status'] == 'complete'
                   and terminal['phase'] == phase and terminal['purpose'] == frame['purpose']
                   and terminal['frame_sha256'] == receipt['frame_sha256']
                   and terminal['audit_denials'] == 0 and terminal['provider_cost_usd'] == 0
                   and terminal['reference_keys_read'] is False and terminal['scientific_scoring_performed'] is False,
                   'Worker completion policy and identity')
    budget = frame['phase_seconds'][phase]
    contracts.need(type(budget) is int and 120 <= budget <= 43200, 'Phase deadline bound')
    _finite(terminal['wall_seconds'], 'Worker elapsed time', maximum=budget)
    stage_config, report = verified_stage['config'], verified_stage['report']
    contracts.need(canonical(read.json('worker/phase/CONFIG.json')) == canonical(stage_config)
                   and canonical(read.json('worker/phase/REPORT.json')) == canonical(report),
                   'Verified stage differs from retained stage bytes')
    contracts.need(tuple(stage_config['ids']) == tuple(frame['schedule']) and stage_config['phase'] == phase
                   and stage_config['purpose'] == frame['purpose'] and report['status'] == 'complete'
                   and report['scheduled'] == len(frame['schedule'])
                   and report['entered'] == report['scheduled'] and report['unexecuted'] == 0
                   and 0 < stage_config['seconds'] <= budget and report['wall_seconds'] <= terminal['wall_seconds'],
                   'Whole scheduled stage and worker timing')
    contracts.need(canonical(terminal['stage_receipt']) == canonical(receipt['files']['worker/phase/STAGE-RECEIPT.json'])
                   and verified_stage['receipt_sha256'] == terminal['stage_receipt']['sha256']
                   and projection._path(verified_stage['root']) == root/'worker/phase', 'Verified child stage identity')
    inputs = read.json('worker/phase/INPUTS.json')
    parents = {name:dict(root=str(root.parent/name/'worker/phase'),receipt_sha256=value['stage_receipt_sha256'])
               for name,value in job['parents'].items()}
    contracts.need(set(inputs) == {'baseline','parents','cutoff','model_provenance','reference_keys_available','scoring_performed'}
                   and canonical(inputs['baseline']) == canonical(frame['baseline'])
                   and canonical(inputs['parents']) == canonical(parents) and inputs['cutoff'] == job['cutoff']
                   and canonical(inputs['model_provenance']) == canonical(frame['model_provenance'])
                   and inputs['reference_keys_available'] is False and inputs['scoring_performed'] is False,
                   'Stage input parent/configuration projection')
    process = read.json('PROCESS.json')
    contracts.need(set(process) == {'returncode','supervision'} and type(process['returncode']) is int
                   and process['returncode'] == 0, 'Worker process did not exit successfully')
    validate_success_report(process['supervision'], ProcessLimits(budget+60,4*1024**2),
                            len(read.raw('stdout.bin')),len(read.raw('stderr.bin')))
    contracts.need(terminal['wall_seconds'] <= process['supervision']['execution_elapsed_seconds'],
                   'Worker elapsed exceeds supervised process')
    repository = Path(__file__).resolve().parents[2]
    command = [frame['interpreter']['path'],'-I','-B','-c',LAUNCHER,str(repository),str(repository/'src'),
               str(repository/'packages/tether/src'),'--worker','--frame',str(root.parent/'FRAME.json'),
               '--frame-sha256',receipt['frame_sha256'],'--job',str(root/'JOB.json'),
               '--job-sha256',receipt['files']['JOB.json']['sha256'],'--output',str(root/'worker')]
    contracts.need(read.json('COMMAND.json') == command, 'Actual worker command and authority differ')
    contracts.need(not any(Path(name).name in ('FAILURE.json','FINALIZATION-FAILED.json','DEADLINE.json')
                          for name in receipt['files']), 'Failure marker in completed phase')
    _worker_journal(read.raw('worker/journal.jsonl'),terminal,config,phase)
    audit = _audit(read.raw('worker/io-audit.jsonl'),root=root,frame=frame,job=job,rows=report['rows'])
    read.recheck()
    return freeze(dict(phase=phase,scheduled=report['scheduled'],accounting=report['accounting'],
                       process_reaped=True,audit=audit,scientific_source_validation=False))
