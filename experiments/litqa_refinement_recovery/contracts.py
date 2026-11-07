"""Version-two recovery identities, budgets and immutable metadata contracts."""
from collections.abc import Mapping
import hashlib
import math
import os
from pathlib import Path
import re

from tether_engine.serde import canonical, encode, freeze, parse_json

SCHEMA_VERSION=2
PHASES=('repair','removal')
TERMINAL_STATUSES=('completed','codec_failure','capacity','authenticated_limit_failure')
ORIGINAL_TERMINAL=('completed','codec_failure','capacity')
CELL_LIMITS=dict(generation_calls=1,reserved_input_tokens=16128,reserved_output_tokens=256,
                 source_http_requests=0,provider_cost_usd=0,seconds=120)
MAX_METADATA_BYTES=64*1024**2
ROOT=Path(__file__).resolve().parents[2]


def authority_registry(*,original_root=None,purpose='production'):
    need(purpose in ('production','fictional_qualification'),'Explicit authority purpose')
    if purpose=='fictional_qualification':
        need(original_root is not None,'Invented authority requires its original parent root')
        return path(original_root).parent/'recovery-authorities'
    return ROOT/'data/benchmark/litqa_refinement_recovery/authorities'


def need(ok,message):
    if not ok:raise ValueError(message)


def fingerprint(value):return hashlib.sha256(canonical(encode(value))).hexdigest()


def path(value):
    result=Path(value)
    need(result.is_absolute() and result==result.resolve(),'Canonical absolute recovery path required')
    need(not str(result).startswith(('\\\\','//')),'Local recovery paths required')
    for item in (result,*result.parents):
        if item.exists() or item.is_symlink():
            info=item.lstat()
            need(not item.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,'Linked/reparse recovery path rejected')
    return result


def proof(value):
    need(isinstance(value,Mapping) and set(value)=={'path','sha256','bytes'},'Exact immutable byte proof required')
    path(value['path'])
    need(type(value['bytes']) is int and value['bytes']>=0,'Nonnegative proof size')
    need(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']),'Lowercase SHA256 proof')
    return freeze(encode(value))


def capture(value,expected=None,maximum=MAX_METADATA_BYTES):
    target=path(value)
    if expected is not None:expected=proof(expected);need(Path(expected['path'])==target,'Proof location differs')
    need(type(maximum) is int and maximum>=0,'Nonnegative integer recovery byte cap')
    from experiments.litqa_analysis.native_records import read as stable_read
    raw=stable_read(target,maximum)
    actual=dict(path=str(target),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    need(expected is None or actual==encode(expected),'Recovery proof bytes changed')
    return freeze(actual),raw


def read(value):
    expected=proof(value)
    return freeze(parse_json(capture(expected['path'],expected)[1]))


def write(target,value):
    target=path(target)
    with target.open('xb') as stream:
        stream.write(canonical(encode(value))+b'\n');stream.flush();os.fsync(stream.fileno())
    return capture(target)[0]


def finite(value,label):
    need(type(value) in (int,float) and math.isfinite(value) and value>=0,'Finite nonnegative '+label)
    return value


def schedule(ids,purpose):
    from uuid import UUID
    ids=tuple(ids)
    need(purpose in ('production','fictional_qualification'),'Explicit recovery purpose')
    need(len(ids)==(199 if purpose=='production' else 2) and len(set(ids))==len(ids),'Full original recovery schedule')
    need(all(type(v) is str and str(UUID(v))==v for v in ids),'Canonical recovery query identities')
    return ids


def identity(original_root,frame_proof):
    original=path(original_root);frame=proof(frame_proof)
    need(Path(frame['path'])==original/'FRAME.json','Original frame identity differs')
    # The same physical parent cannot obtain a new authority by changing an
    # inspection timestamp, output path, or equivalent Windows casing.
    return fingerprint(dict(original_root=os.path.normcase(str(original)),frame_sha256=frame['sha256']))


def partition(parent):
    frame=parent['frame'];ids=schedule(parent['schedule'],frame['purpose'])
    need(tuple(frame['schedule'])==ids,'Original frame/query order differs')
    rows=parent['repair_rows'];failed=parent['failed_ordinal']
    need(type(failed) is int and 0<=failed<len(ids),'One inherited failure ordinal required')
    need(len(rows)==len(ids),'Original repair records cover full schedule')
    for i,row in enumerate(rows):
        need(row['ordinal']==i and row['id']==ids[i],'Original repair ordinal/identity differs')
        allowed=ORIGINAL_TERMINAL if i<failed else ('failed',) if i==failed else ('unexecuted',)
        need(row['status'] in allowed,'Original repair prefix/reservation partition differs')
    repair=tuple(range(failed+1,len(ids)));removal=tuple(range(len(ids)))
    need(tuple(parent['untouched_repair_ordinals'])==repair and tuple(parent['untouched_removal_ordinals'])==removal,
         'Untouched dispatch set differs from original reservation audit')
    need(set(parent['completed_phases'])=={'critic','refinement_collect','pair_prepare'},'Exactly three adopted complete phases')
    if frame['purpose']=='production':
        need(failed==184 and sum(r['status']=='completed' for r in rows)==183 and
             sum(r['status']=='codec_failure' for r in rows)==1 and len(repair)==14,'Frozen production stopping partition differs')
    return freeze(dict(repair_adopted=tuple(range(failed)),repair_inherited_failed=(failed,),
        repair_dispatch=repair,removal_dispatch=removal))


def budgets(parent,parts):
    frame=parent['frame'];elapsed=parent['elapsed'];original=parent['budgets']
    phase=frame['phase_seconds']
    need(original['outer_seconds']==43200 and all(type(phase[p]) is int and 120<=phase[p]<=7200 for p in PHASES),'Original phase/outer caps differ')
    if frame['purpose']=='production':need(phase['repair']==phase['removal']==7200,'Frozen production phase caps differ')
    stage=finite(original['repair_stage_seconds'],'original repair stage allowance')
    need(0<stage<=phase['repair'],'Original stage allowance exceeds phase')
    repair_spent=max(finite(elapsed['repair_process_total_seconds'],'repair process elapsed'),
                     finite(elapsed['repair_worker_wall_seconds'],'repair worker elapsed'))
    stage_spent=finite(elapsed['repair_stage_seal_elapsed_seconds'],'repair sealed elapsed')
    outer_spent=finite(elapsed['outer_process_total_seconds'],'original outer elapsed')
    need(stage_spent<=repair_spent<=outer_spent,'Original nested elapsed order differs')
    remaining=dict(repair=math.floor(phase['repair']-repair_spent),removal=phase['removal'])
    stage_remaining=math.floor(stage-stage_spent);outer_remaining=math.floor(original['outer_seconds']-outer_spent)
    need(remaining['repair']>120 and remaining['removal']>120 and stage_remaining>0 and outer_remaining>120,
         'Insufficient carried recovery time; no budget reset')
    count=len(parts['repair_dispatch'])+len(parts['removal_dispatch'])
    return freeze(dict(original_phase_seconds={k:phase[k] for k in PHASES},original_outer_seconds=original['outer_seconds'],
        charged_repair_seconds=repair_spent,charged_repair_stage_seconds=stage_spent,charged_outer_seconds=outer_spent,
        phase_remaining_seconds=remaining,repair_stage_remaining_seconds=stage_remaining,outer_remaining_seconds=outer_remaining,
        max_new_generation_calls=count,max_new_source_http_requests=0,max_new_reserved_input_tokens=count*16128,
        max_new_reserved_output_tokens=count*256,cell_limits=CELL_LIMITS,provider_spend_usd=0,
        clock_scope='Conservative original elapsed carry-forward; nested clocks are not summed; new startup/verification/cleanup consume remaining bounds.'))
