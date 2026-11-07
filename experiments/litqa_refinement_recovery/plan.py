"""Metadata planning and permanent cross-output continuation reservation."""
from datetime import datetime,timezone
from pathlib import Path

from tether_engine.serde import canonical,encode,freeze
from . import contracts as c


def parent(descriptor):
    c.need(set(descriptor)=={'inspection','source_archive','baseline_acceptance'},'Exact original-parent descriptor')
    from . import original
    return original.reconstruct(descriptor['inspection'],descriptor['source_archive'],baseline_acceptance=descriptor['baseline_acceptance'])


def _sources():
    from .run import code_files
    return freeze(code_files())


def _revalidate(verified,sources):
    from . import original
    original.revalidate(verified)
    c.need(_sources()==sources,'Recovery admission source closure changed')


def _prepared(descriptor):
    """One semantic reconstruction, retaining its exact operation-scoped capability."""
    from . import original
    descriptor=freeze(encode(descriptor));sources=_sources()
    verified=parent(descriptor);payload=verified.payload
    parts=c.partition(payload);limits=c.budgets(payload,parts)
    value=freeze(dict(schema_version=2,kind='sc05_refinement_recovery_plan_v2',purpose=payload['frame']['purpose'],
        parent=descriptor,parent_identity=c.identity(payload['original_root'],payload['frame_proof']),
        original_root=payload['original_root'],original_frame=payload['frame_proof'],schedule=payload['schedule'],
        original_repair_slots=tuple(row['execution_id'] for row in payload['repair_rows']),authority_registry=str(c.authority_registry(original_root=payload['original_root'],purpose=payload['frame']['purpose'])),
        completed_phases=payload['completed_phases'],pair_prepare=payload['pair_prepare'],partition=parts,budgets=limits,
        automatic_retry=False,new_source_collection=False,reference_keys_available=False,
        original_failure_policy='Inherited failure stays error/not_run/null; authenticated new completion-limit failures may advance to the next untouched slot without retry.',
        failed_call=payload['failed_call']))
    _revalidate(verified,sources)
    return value,verified,sources


def prepare(descriptor):
    """No authority or calls; derive remaining sets and time from issued parent."""
    return _prepared(descriptor)[0]


def reserve(value,registry,output):
    """Permanent exclusive claim. Neither failure nor owner death releases it."""
    registry,output=c.path(registry),c.path(output)
    c.need(registry==c.authority_registry(original_root=value['original_root'],purpose=value['purpose']) and value['authority_registry']==str(registry),'One stable original-parent authority registry required')
    c.need(registry.is_dir() and output.parent.is_dir() and not output.exists(),'Existing registry and fresh planning output required')
    derived,verified,sources=_prepared(value['parent'])
    c.need(canonical(derived)==canonical(value),'Recovery plan no longer matches original parent')
    old=c.path(value['original_root'])
    for a,b in ((registry,old),(output,old),(output,registry)):
        c.need(not a.is_relative_to(b) and not b.is_relative_to(a),'Recovery authority/planning/original roots overlap')
    output.mkdir();authority=registry/value['parent_identity']
    try:
        plan_proof=c.write(output/'PLAN.json',value)
        c.write(output/'REQUEST.json',dict(kind='sc05_recovery_reservation_request_v2',created_at_utc=datetime.now(timezone.utc).isoformat(),
            plan=plan_proof,registry=str(registry),authority=str(authority),automatic_retry=False))
        authority.mkdir(exist_ok=False)
        claim=c.write(authority/'AUTHORITY.json',dict(schema_version=2,kind='sc05_refinement_recovery_authority_v2',
            parent_identity=value['parent_identity'],plan=plan_proof,allowed_dispatch=dict(repair=value['partition']['repair_dispatch'],
            removal=value['partition']['removal_dispatch']),permanent=True,automatic_retry=False))
        _revalidate(verified,sources)
        complete=c.write(output/'COMPLETE.json',dict(status='recovery_authority_reserved',plan=plan_proof,authority=claim,
            model_or_http_execution_performed=False))
        return freeze(dict(plan=plan_proof,authority=claim,complete=complete))
    except BaseException as error:
        c.write(output/'FAILURE.json',dict(stage='authority_reservation',error_type=type(error).__name__,message=str(error),
            authority_may_be_reserved=authority.exists(),automatic_retry=False))
        raise


def verify(plan_proof,authority_proof,*,return_parent=False):
    value=c.read(plan_proof);authority=c.read(authority_proof)
    c.need(value['kind']=='sc05_refinement_recovery_plan_v2' and value['schema_version']==2,'Recovery plan version')
    c.need(authority['kind']=='sc05_refinement_recovery_authority_v2' and authority['schema_version']==2 and
         authority['parent_identity']==value['parent_identity'] and authority['plan']==plan_proof and
         authority['permanent'] is True and authority['automatic_retry'] is False,'Permanent parent authority differs')
    c.need(Path(authority_proof['path']).parent.name==value['parent_identity'],'Authority parent identity location differs')
    registry=c.authority_registry(original_root=value['original_root'],purpose=value['purpose'])
    c.need(Path(authority_proof['path'])==registry/value['parent_identity']/'AUTHORITY.json' and
        value['authority_registry']==str(registry),'Stable authority registry binding differs')
    c.need(encode(authority['allowed_dispatch'])==dict(repair=list(value['partition']['repair_dispatch']),removal=list(value['partition']['removal_dispatch'])),
         'Authority dispatch set differs')
    derived,verified,_=_prepared(value['parent'])
    c.need(canonical(derived)==canonical(value),'Anchored plan no longer matches original')
    return (value,authority,verified) if return_parent else (value,authority)
