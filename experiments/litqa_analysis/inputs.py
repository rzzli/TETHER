"""Evaluator-only independent joins to the original released LitQA2 rows."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import random
from uuid import UUID

from .native_records import canonical, decode, digest, need, read, verify_proof
from .sources import doi


def projection(raw, *, seed=20261106):
    need(len(raw)<=8*1024**2, 'Bounded original task file')
    rng=random.Random(seed); queries=[]; references=[]; hints=[]; seen=set(); doi_order=[]
    for line in raw.splitlines():
        row=decode(line); key=row['id']
        need(str(UUID(key))==key and key not in seen, 'Unique canonical original ID'); seen.add(key)
        need(isinstance(row['question'],str) and row['question'].strip() and isinstance(row['ideal'],str) and row['ideal'].strip(),
             'Original question and answer text')
        distractors=row['distractors']; unsure='Insufficient information to answer the question'
        need(isinstance(distractors,list) and 1<=len(distractors)<=24 and all(isinstance(d,str) and d.strip() for d in distractors),
             'Original distractor slots')
        need(row['ideal']!=unsure and row['ideal'] not in distractors and unsure not in distractors, 'Unambiguous key and unsure slot')
        values=[row['ideal'],unsure]+distractors; positions=list(range(len(values))); rng.shuffle(positions)
        queries.append(dict(id=key,question=row['question'],choices=[f'({chr(65+i)}) {values[j]}' for i,j in enumerate(positions)]))
        references.append(dict(id=key,answer_index=positions.index(0),unsure_index=positions.index(1)))
        need(isinstance(row['sources'],list) and 1<=len(row['sources'])<=2, 'Original paper annotations')
        ds=[doi(value) for value in row['sources']]
        need(all(ds) and len(set(ds))==len(ds), 'Unique resolved source annotations')
        hints.append(dict(id=key,question=row['question'],dois=ds))
        for d in ds:
            if d not in doi_order:doi_order.append(d)
    need(queries, 'Nonempty original projection')
    return dict(queries=queries,references=references,hints=hints,doi_schedule=doi_order)


def graph_groups(ids, hints):
    """Graph traversal rather than the frozen union-find implementation."""
    annotations={r['id']:r['dois'] for r in hints}; owners={}
    need(set(annotations)==set(ids), 'Complete grouping annotations')
    for key,ds in annotations.items():
        for d in ds:owners.setdefault(d,set()).add(key)
    visited=set(); groups=[]
    for root in ids:
        if root in visited:continue
        pending=[root]; group=set()
        while pending:
            key=pending.pop()
            if key in group:continue
            group.add(key)
            for d in annotations[key]:pending.extend(owners[d]-group)
        visited.update(group);groups.append([key for key in ids if key in group])
    return groups


def verify(path, external_sha, *, answer_started_at=None):
    raw=read(path);need(digest(raw)==external_sha, 'External frozen analysis input anchor'); manifest=decode(raw)
    need(manifest['kind']=='sc04_analysis_inputs_v1' and manifest['role']=='evaluation_only' and
         manifest['primary_answers_existed_at_freeze'] is False, 'Frozen evaluator-only input contract')
    need(manifest['questions']==199 and manifest['bootstrap_replicates']==10000 and manifest['seed']==20261106,
         'Original full-cohort analysis settings')
    frozen=datetime.fromisoformat(manifest['created_at_utc']);need(frozen.tzinfo is not None,'Aware analysis freeze')
    if answer_started_at is not None:
        started=datetime.fromisoformat(answer_started_at);need(started.tzinfo is not None and frozen<started,'Analysis frozen before answering')
    for key in ('specification','addendum','grouping_code','freeze_helper','native_scorer'): verify_proof(manifest[key])
    projected=decode(verify_proof(manifest['annotation_projection']))
    need(projected['role']=='diagnostic_selection_only' and projected['ordinary_retrieval_permitted'] is False and
         projected['answerer_may_read'] is False and projected['correct_answers_included'] is False and projected['key_passages_included'] is False,
         'Diagnostic selection isolation flags')
    original=verify_proof(projected['original']); rebuilt=projection(original,seed=manifest['seed'])
    for key,proof in (('queries',manifest['answer_queries']),('references',manifest['reference_keys']),
                      ('hints',projected['products']['hints']),('doi_schedule',projected['products']['doi_schedule'])):
        need(canonical(rebuilt[key])==canonical(decode(verify_proof(proof))), 'Original '+key+' reconstruction')
    ids=[q['id'] for q in rebuilt['queries']]
    need(len(ids)==199 and ids==manifest['question_schedule']==projected['schedule'] and
         len(rebuilt['doi_schedule'])==190 and sum(len(h['dois']) for h in rebuilt['hints'])==205, 'Original199/190/205 denominators')
    groups=decode(verify_proof(manifest['groups'])); expected=graph_groups(ids,rebuilt['hints'])
    need(groups==dict(kind='shared_annotated_doi_connected_components',role='evaluation_only',groups=expected,
        questions=199,components=len(expected),size_distribution={str(k):v for k,v in Counter(map(len,expected)).items()}),
        'Independent publication grouping')
    need(manifest['primary_metrics']==['raw_accuracy','correct_and_admitted_yield'] and
         manifest['primary_contrasts']==['expansion_at_lexical','ranking_at_lexical','combined_vs_lexical','interaction',
                                       'marginal_expansion','marginal_ranking'], 'Complete frozen analysis family')
    return dict(manifest=manifest,queries=rebuilt['queries'],references=rebuilt['references'],hints=rebuilt['hints'],
                doi_schedule=rebuilt['doi_schedule'],groups=expected,annotations={h['id']:h['dois'] for h in rebuilt['hints']})
