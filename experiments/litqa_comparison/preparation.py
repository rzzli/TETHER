"""Reverify the original LitQA2 release and publish role-separated SC04 inputs.

This parent-side preparation reads reference-bearing originals only to verify
the old projection. It writes no answer keys, DOI hints or key passages into
the new predictor products. Model/retrieval workers consume only those products.
"""
from pathlib import Path

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,freeze,parse_json,safe_child
from experiments.labbench.data_views import verify_views,load_queries
from experiments.labbench.native_contract import validate_query
from .codecs import question_view,need,digest

SOURCE_MANIFEST_SHA='7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b'


def project(queries,expected_count=199):
    need(isinstance(queries,(list,tuple)) and len(queries)==expected_count,'Full declared task count required')
    answer=[];source=[];seen=set()
    for query in queries:
        query=validate_query(query)
        need(query['id'] not in seen,'Duplicate task identity')
        seen.add(query['id']);answer.append(query)
        source.append(question_view({k:query[k] for k in ('id','question')}))
    return freeze(dict(source_queries=source,answer_queries=answer,schedule=[q['id'] for q in answer]))


def prepare(original_preparation,output):
    journal=RunJournal(Path(output),kind='build');root=journal.output
    try:
        original=Path(original_preparation).resolve()
        verified=verify_views(original,SOURCE_MANIFEST_SHA)
        parent=verified['products']['queries']
        queries=load_queries(safe_child(original,parent['path']),parent['sha256'])
        projected=project(queries)
        products={}
        for name in ('source_queries','answer_queries'):
            raw=canonical(projected[name])+b'\n';path=root/(name+'.json')
            publish_bytes(path,raw)
            products[name]=dict(path=str(path.resolve()),sha256=digest(raw),bytes=len(raw),
                                role='question_only_input' if name=='source_queries' else 'answerer_input')
        manifest=freeze(dict(kind='sc04_task_products_v1',scheduled=199,schedule=projected['schedule'],products=products,
            parent_preparation=dict(path=str(original/'manifest.json'),sha256=SOURCE_MANIFEST_SHA),
            parent_queries=dict(path=str(original/parent['path']),sha256=parent['sha256'],bytes=parent['bytes']),
            source_reconstruction='Original released bytes and prior projection reverified by retained data_views.verify_views',
            preparation_code_sha256=digest(Path(__file__).read_bytes()),
            workers_may_read_reference_originals=False,reference_fields_in_predictor_products=False))
        publish_bytes(root/'MANIFEST.json',canonical(manifest))
        journal.append('input_products_completed',manifest_sha256=digest(canonical(manifest)),scheduled=199)
        publish_bytes(root/'RECEIPT.json',canonical(dict(manifest_sha256=digest(canonical(manifest)),journal_terminal_sha256=journal.events[-1]['sha256'])))
        return manifest
    except BaseException as error:
        journal.fail(error,'task_preparation')
        publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,stage='original_reconstruction_or_projection')))
        raise
    finally:journal.close()


def load_product(manifest,kind):
    need(kind in ('source_queries','answer_queries'),'Unknown product role')
    need(manifest['kind']=='sc04_task_products_v1' and manifest['scheduled']==199,'Expected full-cohort manifest')
    product=manifest['products'][kind];raw=Path(product['path']).read_bytes()
    need(product['role']==('question_only_input' if kind=='source_queries' else 'answerer_input'),'Product role differs')
    need(len(raw)==product['bytes'] and digest(raw)==product['sha256'],'Input product anchor differs')
    values=parse_json(raw)
    need(isinstance(values,list) and len(values)==199 and tuple(v['id'] for v in values)==tuple(manifest['schedule']),
         'Full ordered product schedule')
    checker=question_view if kind=='source_queries' else validate_query
    return tuple(checker(v) for v in values)
