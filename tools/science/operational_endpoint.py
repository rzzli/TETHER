"""Pure evaluator-only finite-source event candidates for P12 development.

No I/O or source qualification is performed here. Candidate labels require an
enclosing complete-source audit; qualified, clinical and programme labels remain
null. The endpoint reports a source's phase/start observation, not actual dosing.
"""
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
import re


def _need(ok, reason):
    if not ok: raise ValueError('Operational endpoint: '+reason)


def _day(value):
    _need(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value), 'Exact calendar day required')
    return date.fromisoformat(value)


def _interval(value):
    if type(value) is not str or not re.fullmatch(r'[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?',value): return None
    try:
        parts=list(map(int,value.split('-')));year=parts[0]
        low=date(year,parts[1] if len(parts)>1 else 1,parts[2] if len(parts)>2 else 1)
        if len(parts)==3:high=low+timedelta(days=1)
        elif len(parts)==2:high=date(year+int(parts[1]==12),parts[1]%12+1,1)
        else:high=date(year+1,1,1)
        return low,high
    except (ValueError,OverflowError):return None


def _text(value): return type(value) is str and bool(value.strip())


def _identity(row):
    # Typed representations keep booleans distinct from integer phase values.
    fields=('id','datasourceId','datatypeId','targetId','diseaseId','drugId','clinicalPhase','studyStartDate')
    return tuple((key,type(row.get(key)).__name__,repr(row.get(key))) for key in fields)


def reduce_endpoint(units, rows, *, origin, horizon, observation_freeze, source_complete):
    """Apply the fixed observation window to an explicitly supplied finite frame.

    The caller must prove source completeness, original row identity, field types
    and exposure restrictions. Rows outside the declared frame are rejected.
    Registration before origin is intentionally not an event exclusion.
    """
    origin,horizon,freeze=map(_day,(origin,horizon,observation_freeze))
    _need(origin<horizon,'Empty or reversed event window')
    _need(type(source_complete) is bool,'Boolean completeness required')
    _need(type(units) is list and 0<len(units)<=10000,'Bounded unit frame required')
    by_pair={};by_id={}
    for u in units:
        _need(type(u) is dict and all(_text(u.get(k)) for k in ('unit_id','target_id','disease_id')),'Invalid unit')
        pair=u['target_id'],u['disease_id']
        _need(pair not in by_pair and u['unit_id'] not in by_id,'Duplicate unit')
        _need(type(u.get('policy_holds')) is list and all(_text(x) for x in u['policy_holds']),'Explicit policy holds required')
        by_pair[pair]=u;by_id[u['unit_id']]=u
    selected=defaultdict(list);groups=defaultdict(list);parent={key:key for key in by_id}
    drug_links=defaultdict(set);trial_links=defaultdict(set);count=0
    for r in rows:
        count+=1;_need(count<=1000000,'Row budget exceeded')
        _need(type(r) is dict and r.get('datasourceId')=='chembl' and r.get('datatypeId')=='known_drug','Forbidden source or datatype')
        _need(_text(r.get('targetId')) and _text(r.get('diseaseId')),'Cannot assign malformed pair')
        pair=r['targetId'],r['diseaseId'];_need(pair in by_pair,'Row outside declared frame')
        uid=by_pair[pair]['unit_id']
        _need(type(r.get('nct_ids')) is list and all(type(n) is str and re.fullmatch(r'NCT[0-9]{8}',n) for n in r['nct_ids']),
              'Exact trial link list required')
        selected[uid].append(r)
        if _text(r.get('id')):groups[r['id']].append((uid,r))
        if _text(r.get('drugId')):drug_links[r['drugId']].add(uid)
        for nct in r['nct_ids']:trial_links[nct].add(uid)
    conflicting={key for key,group in groups.items() if len({_identity(r) for _,r in group})>1}
    duplicates=sum(len(group)-1 for key,group in groups.items() if key not in conflicting)
    def root(key):
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    for linked in list(drug_links.values())+list(trial_links.values()):
        ordered=sorted(linked)
        for key in ordered[1:]:
            a,b=sorted((root(ordered[0]),root(key)));parent[b]=a
    components=defaultdict(list)
    for key in sorted(by_id):components[root(key)].append(key)
    component_ids={key:hashlib.sha256(json.dumps(members,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
                   for key,members in components.items()}
    results=[]
    for uid in sorted(by_id):
        u=by_id[uid];holds=set();uncertain=set();uncertain_high=set();events=set();higher=set();seen=set();limits=set()
        if not source_complete:holds.add('source_coverage_incomplete')
        for r in selected[uid]:
            if not _text(r.get('drugId')):limits.add('drug_link_missing')
            if not r['nct_ids']:limits.add('trial_link_missing')
            identity=r.get('id')
            if not _text(identity):holds.add('evidence_id_missing');continue
            if identity in conflicting:holds.add('conflicting_evidence_id');continue
            if identity in seen:continue
            seen.add(identity)
            phase=r.get('clinicalPhase');period=_interval(r.get('studyStartDate'))
            valid=type(phase) in (int,float) and phase in (0,0.5,1,1.5,2,2.5,3,4)
            if not valid:
                uncertain.add('phase_unresolved');uncertain_high.add('phase_unresolved');continue
            if phase<2.5:continue
            outside=period is not None and (period[1]<=origin or period[0]>=horizon)
            if outside:continue
            within=period is not None and origin<=period[0]<period[1]<=horizon
            if phase==2.5:
                uncertain.add('combined_phase_component_unknown');uncertain_high.add('combined_phase_component_unknown')
            elif not within:
                uncertain_high.add('phase'+str(int(phase))+'_date_unresolved')
                if phase==3:uncertain.add('phase3_date_unresolved')
            else:
                higher.add(identity)
                if phase==3:events.add(identity)
        if not selected[uid]:limits.add('no_observed_linkage')
        mature=freeze>=horizon
        def state(observed,ambiguity):
            if not mature:return 'right_censored'
            if holds:return 'unresolved'
            if observed:return 'recorded_event'
            if ambiguity:return 'unresolved'
            return 'no_record_in_complete_source'
        primary=state(events,uncertain);sensitivity=state(higher,uncertain_high)
        policy=sorted(set(u['policy_holds']))
        def label(value):
            if policy:return None
            return {'recorded_event':1,'no_record_in_complete_source':0}.get(value)
        results.append(dict(unit_id=uid,target_id=u['target_id'],disease_id=u['disease_id'],source_state=primary,
                            candidate_operational_label=label(primary),at_least_phase3_state=sensitivity,
                            at_least_phase3_candidate_label=label(sensitivity),qualified_label=None,clinical_label=None,programme_label=None,
                            event_ids=sorted(events),at_least_phase3_event_ids=sorted(higher),holds=sorted(holds),policy_holds=policy,
                            uncertainty=sorted(uncertain),at_least_phase3_uncertainty=sorted(uncertain_high),
                            component_id=component_ids[root(uid)],dependence_limits=sorted(limits),physical_rows=len(selected[uid])))
    return dict(schema_version=1,endpoint_id='ot-reported-phase3-start-window.v1',role='evaluation_only',
                chronology=dict(origin=origin.isoformat(),horizon=horizon.isoformat(),observation_freeze=freeze.isoformat()),
                agent_visible=False,source_qualification='required_before_label_release',units=results,physical_rows=count,
                duplicate_rows=duplicates,conflicting_evidence_ids=sorted(conflicting),
                source_states=dict(sorted(Counter(r['source_state'] for r in results).items())),
                dependence=dict(basis='all_observed_development_drug_and_trial_links_including_outcomes',
                                components=[dict(component_id=component_ids[k],unit_ids=v) for k,v in sorted(components.items())],
                                component_sizes=sorted((len(x) for x in components.values()),reverse=True),
                                shared_drugs=sum(len(v)>1 for v in drug_links.values()),shared_trials=sum(len(v)>1 for v in trial_links.values()),
                                effective_sample_size=None),scientific_validation='not_established')
