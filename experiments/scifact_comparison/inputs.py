"""Pure, reference-separated input construction and explicit sentence lineage."""
from copy import deepcopy
import hashlib
import json
import math

CONDITIONS = ('primary', 'rationale_only', 'evidence_removal',
              'irrelevant_context', 'constructed_conflict')
IRRELEVANT = ('In a fictional observatory, the blue telescope was stored beside '
              'an unused wooden cabinet.')
CONFLICT = 'For this constructed counterfactual, the following statement is false: '


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def text_digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def identifier(value):
    return type(value) is int and value >= 0


def validate_requests(requests, *, expected_schedule=None, expected_k=5):
    need(type(requests) is list and requests, 'Nonempty request list required')
    ids = []
    for request in requests:
        need(type(request) is dict and set(request) == {'id', 'claim', 'documents'},
             'Request fields must exclude annotations and evaluator metadata')
        cid = request['id']
        need(identifier(cid) and cid not in ids, 'Invalid or duplicate claim ID')
        ids.append(cid)
        need(type(request['claim']) is str and request['claim'].strip(), 'Claim text required')
        docs = request['documents']
        need(type(docs) is list and len(docs) == expected_k, 'Fixed retrieval count differs')
        doc_ids = set()
        for doc in docs:
            need(type(doc) is dict and set(doc) == {'doc_id', 'title', 'abstract'}, 'Document projection differs')
            did = doc['doc_id']
            need(identifier(did) and did not in doc_ids, 'Invalid or duplicate document ID')
            doc_ids.add(did)
            need(type(doc['title']) is str, 'Title text required')
            need(type(doc['abstract']) is list and
                 all(type(s) is str and s.strip() for s in doc['abstract']), 'Invalid abstract text')
    need(expected_schedule is None or ids == expected_schedule, 'Request schedule differs')
    return ids


def build_primary(queries, corpus, candidates, schedule, *, expected_k=5):
    """No reference argument: retain only original query and fixed retrieval text."""
    need(type(schedule) is list and schedule and all(identifier(x) for x in schedule)
         and len(schedule) == len(set(schedule)), 'Invalid schedule')
    need([q['id'] for q in queries] == schedule, 'Query membership/order differs')
    need(all(set(q) == {'id', 'claim'} for q in queries), 'Queries must be label-free')
    documents = {}
    for doc in corpus:
        need(identifier(doc.get('doc_id')) and doc['doc_id'] not in documents, 'Duplicate corpus ID')
        documents[doc['doc_id']] = doc
    need(len(candidates) == len(schedule), 'Candidate count differs')
    requests, retrieval = [], []
    for query, candidate in zip(queries, candidates):
        need(candidate['cell_id'] == str(query['id']) and candidate['status'] == 'completed',
             'Baseline candidate identity/status differs')
        selected = candidate['result']['retrieved']
        need(type(selected) is list and len(selected) == expected_k, 'Retained top-k differs')
        docs = []
        for rank, item in enumerate(selected, 1):
            need(set(item) == {'doc_id', 'rank', 'score', 'document_sha256'}, 'Retrieval fields differ')
            did = item['doc_id']
            need(identifier(did) and did in documents and type(item['rank']) is int and item['rank'] == rank,
                 'Retrieved source identity/rank differs')
            need(type(item['score']) in (int, float) and math.isfinite(item['score']), 'Invalid retrieval score')
            source = documents[did]
            need(item['document_sha256'] == digest(source), 'Original document fingerprint differs')
            need(source['abstract'], 'Original abstract is empty')
            docs.append({key: deepcopy(source[key]) for key in ('doc_id', 'title', 'abstract')})
        requests.append(dict(id=query['id'], claim=query['claim'], documents=docs))
        retrieval.append(dict(id=query['id'], retrieved=deepcopy(selected)))
    validate_requests(requests, expected_schedule=schedule, expected_k=expected_k)
    return requests, retrieval


def build_condition(primary, condition, *, references=None, expected_k=5):
    """Keep reference-derived masks out of primary/constructed-context routes."""
    need(condition in CONDITIONS, 'Unknown condition')
    schedule = validate_requests(primary, expected_k=expected_k)
    informed = condition in ('rationale_only', 'evidence_removal')
    need(informed == (references is not None), 'References required only for the two reference-informed conditions')
    reference_map = {}
    if informed:
        need(type(references) is list and [r['id'] for r in references] == schedule,
             'Reference membership/order differs')
        reference_map = {r['id']: r for r in references}
    requests, lineages = [], []
    for original in primary:
        query = dict(id=original['id'], claim=original['claim'], documents=[])
        lineage = dict(id=original['id'], condition=condition,
                       primary_request_sha256=digest(original), documents=[])
        for doc in original['documents']:
            indices = list(range(len(doc['abstract'])))
            annotated = False
            mask = set()
            if informed:
                rationales = reference_map[original['id']]['evidence'].get(str(doc['doc_id']), [])
                annotated = bool(rationales)
                for rationale in rationales:
                    need(type(rationale['sentences']) is list and rationale['sentences'], 'Empty rationale set')
                    for index in rationale['sentences']:
                        need(type(index) is int and 0 <= index < len(doc['abstract']), 'Reference index out of bounds')
                        mask.add(index)
                if annotated:
                    indices = [i for i in indices if (i in mask) == (condition == 'rationale_only')]
            sentences = [doc['abstract'][i] for i in indices]
            origins = [dict(input_index=j, original_index=i, origin='source', text_sha256=text_digest(text))
                       for j, (i, text) in enumerate(zip(indices, sentences))]
            if condition in ('irrelevant_context', 'constructed_conflict'):
                added = IRRELEVANT if condition == 'irrelevant_context' else CONFLICT + original['claim']
                origins.append(dict(input_index=len(sentences), original_index=None,
                                    origin='synthetic_' + condition, text_sha256=text_digest(added)))
                sentences.append(added)
            transformed = dict(doc_id=doc['doc_id'], title=doc['title'], abstract=sentences)
            query['documents'].append(transformed)
            lineage['documents'].append(dict(doc_id=doc['doc_id'], source_document_sha256=digest(doc),
                input_document_sha256=digest(transformed), title_sha256=text_digest(doc['title']),
                sentences=origins, annotated_rationale_applicable=annotated if informed else None,
                disposition='input_unavailable' if not sentences else 'ready',
                reason='No abstract sentences remain after intervention' if not sentences else
                       'unchanged_no_annotated_evidence' if informed and not annotated else None))
        lineage['request_sha256'] = digest(query)
        requests.append(query)
        lineages.append(lineage)
    validate_requests(requests, expected_schedule=schedule, expected_k=expected_k)
    return requests, lineages


def map_rationale(pair, lineage):
    """Separate genuine source locators from synthetic selections; never drop either."""
    need(pair['abstract_id'] == lineage['doc_id'], 'Pair/document lineage mismatch')
    indices = pair['predicted_rationale']
    need(type(indices) is list and all(type(i) is int for i in indices) and
         indices == sorted(set(indices)), 'Invalid predicted rationale indices')
    need(all(0 <= i < len(lineage['sentences']) for i in indices), 'Rationale escapes transformed input')
    selected = [deepcopy(lineage['sentences'][i]) for i in indices]
    return dict(original_sentence_indices=[r['original_index'] for r in selected if r['origin'] == 'source'],
                synthetic_selections=[r for r in selected if r['origin'] != 'source'])
