"""Typed generated control context for TETHER refinement; never source evidence."""
from collections.abc import Mapping
from datetime import datetime, timezone
import re

from tether_engine.serde import canonical, encode, fingerprint, freeze
from experiments.labbench import model as native_model
from experiments.labbench.native_contract import validate_query, validate_prediction
from experiments.litqa_comparison import codecs

SUPPORT = ('supported', 'contradicted', 'insufficient', 'not_assessable')
CANDIDATE_KIND = 'model_generated_candidate_context_v1'
CRITIQUE_KIND = 'model_generated_critique_context_v1'
need = codecs.need


def digest(value, label='digest'):
    need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), label)
    return value


def utc(value):
    need(isinstance(value, str), 'UTC timestamp required')
    stamp = datetime.fromisoformat(value)
    need(stamp.tzinfo is not None and stamp.utcoffset() == timezone.utc.utcoffset(stamp),
         'UTC timestamp required')
    return value


def raw_sources(query, sources):
    query, sources = native_model._inputs(query, sources)
    need(sum(len(s['text'].encode('utf-8')) for s in sources) <= 8000,
         'Selected raw-source byte cap')
    need(all(len(s['text'].encode('utf-8')) <= 1000 for s in sources),
         'Raw chunk byte cap')
    return query, sources


def candidate(query, prediction, *, producer_status, original_admission_status,
              native_call_sha256, generated_at_utc, offered_ids):
    query = validate_query(query)
    need(producer_status in ('produced', 'parse_failure', 'input_unavailable'), 'Original producer status')
    need(original_admission_status in ('accepted', 'rejected', 'not_run'), 'Original admission status')
    if producer_status == 'produced':
        prediction = validate_prediction(prediction, query, offered_ids)
        need(original_admission_status in ('accepted', 'rejected'), 'Produced original requires admission')
    else:
        need(prediction is None and original_admission_status == 'not_run', 'Failed original cannot invent a prediction')
    if native_call_sha256 is None:
        need(producer_status == 'input_unavailable' and generated_at_utc is None, 'Missing original native proof')
    else:
        digest(native_call_sha256, 'Original native proof digest')
        # Archived producers may bind the native bytes without recording an
        # exact generation timestamp. Do not relabel their reservation time.
        if generated_at_utc is not None:utc(generated_at_utc)
    return freeze(dict(kind=CANDIDATE_KIND, id=query['id'], query_sha256=fingerprint(query),
        prediction=prediction, producer_status=producer_status, original_admission_status=original_admission_status,
        native_call_sha256=native_call_sha256, generated_at_utc=generated_at_utc, is_scientific_evidence=False))


def validate_candidate(query, value, offered_ids=None):
    keys = {'kind','id','query_sha256','prediction','producer_status','original_admission_status',
            'native_call_sha256','generated_at_utc','is_scientific_evidence'}
    need(isinstance(value, Mapping) and set(value) == keys, 'Generated candidate fields')
    # Previously offered citations remain control context even if omitted by a
    # later selection. Initial projection must supply the actual original IDs.
    ids = offered_ids if offered_ids is not None else (
        value['prediction']['evidence_ids'] if isinstance(value['prediction'], Mapping) else ())
    rebuilt = candidate(query, value['prediction'], producer_status=value['producer_status'],
        original_admission_status=value['original_admission_status'], native_call_sha256=value['native_call_sha256'],
        generated_at_utc=value['generated_at_utc'], offered_ids=ids)
    need(canonical(value) == canonical(rebuilt), 'Generated candidate binding')
    return rebuilt


def query_terms(value):
    # Keep the established literal query parser and date/rights suffix builder;
    # SC05 applies tighter bounds before handing it structured lists.
    parsed = codecs.parse_expansion(canonical(dict(queries=value)))['queries']
    seen = set()
    for terms in parsed:
        need(1 <= len(terms) <= 2, 'Critic term count')
        for term in terms:
            need(len(term.encode('ascii')) <= 48, 'Critic term byte cap')
            need(not re.search(r'\b(?:AND|OR|NOT|DOI|PMID(?:\s*\d+)?|PMCID(?:\s*\d+)?|PMC\s*\d+)\b', term, re.I),
                 'Identifiers and search operators are forbidden')
            need(term.casefold() not in seen, 'Duplicate critic term')
            seen.add(term.casefold())
    return parsed


def parse_critic(raw, query, prior, sources):
    query, sources = raw_sources(query, sources)
    prior = validate_candidate(query, prior, [s['source_id'] for s in sources])
    value = codecs._strict_json(raw, 4096)
    need(isinstance(value, dict) and set(value) == {'support','evidence_ids','criticism','queries'}, 'Critic fields')
    need(value['support'] in SUPPORT, 'Critic support vocabulary')
    citations = value['evidence_ids']
    need(isinstance(citations, list) and len(citations) <= 2 and all(isinstance(s, str) for s in citations)
         and len(set(citations)) == len(citations) and set(citations) <= {s['source_id'] for s in sources},
         'Critic citations must be unique offered originals')
    need(value['support'] not in ('supported','contradicted') or bool(citations), 'Support assertion requires citation')
    need(prior['prediction'] is not None or value['support'] == 'not_assessable', 'Null prior is not assessable')
    need(isinstance(value['criticism'], str) and len(value['criticism'].encode('utf-8')) <= 160
         and not any(ord(c) < 32 for c in value['criticism']), 'Criticism UTF8/control bound')
    query_terms(value['queries'])
    return freeze(value)


def critique(query, prior, sources, decoded, *, native_status, native_call_sha256):
    query, sources = raw_sources(query, sources)
    prior = validate_candidate(query, prior, [s['source_id'] for s in sources])
    need(native_status in ('completed','codec_failure','capacity'), 'Critic native status')
    if native_status == 'completed':
        decoded = parse_critic(canonical(decoded), query, prior, sources)
    else:
        need(decoded is None, 'Unavailable critic cannot carry decoded control')
    if native_call_sha256 is None:
        need(native_status == 'capacity', 'Critic native proof missing')
    else:
        digest(native_call_sha256, 'Critic native proof digest')
    return freeze(dict(kind=CRITIQUE_KIND, query_sha256=fingerprint(query), candidate_sha256=fingerprint(prior),
        source_context_sha256=fingerprint(sources), decoded=decoded, native_status=native_status,
        native_call_sha256=native_call_sha256, is_scientific_evidence=False))


def validate_critique(query, prior, value, original_sources=None):
    keys = {'kind','query_sha256','candidate_sha256','source_context_sha256','decoded','native_status',
            'native_call_sha256','is_scientific_evidence'}
    need(isinstance(value, Mapping) and set(value) == keys, 'Critique context fields')
    prior = validate_candidate(query, prior)
    if original_sources is not None:
        expected = critique(query, prior, original_sources, value['decoded'], native_status=value['native_status'],
                            native_call_sha256=value['native_call_sha256'])
        need(canonical(expected) == canonical(value), 'Critique source/control binding')
        return expected
    need(value['kind'] == CRITIQUE_KIND and value['query_sha256'] == fingerprint(query)
         and value['candidate_sha256'] == fingerprint(prior) and value['is_scientific_evidence'] is False,
         'Critique control binding')
    digest(value['source_context_sha256'])
    # A repair can omit original citations; check the sealed critic's full
    # syntax using its own cited IDs, without treating them as current sources.
    need(value['native_status'] in ('completed','codec_failure','capacity'), 'Critic native status')
    if value['decoded'] is None:
        need(value['native_status'] != 'completed', 'Completed critic needs decoding')
    else:
        need(value['native_status'] == 'completed', 'Failed critic carries decoding')
        decoded = value['decoded']
        need(isinstance(decoded, Mapping) and set(decoded) == {'support','evidence_ids','criticism','queries'}, 'Critic fields')
        need(decoded['support'] in SUPPORT, 'Critic support vocabulary')
        ids = decoded['evidence_ids']
        need(isinstance(ids, (list,tuple)) and len(ids) <= 2 and all(isinstance(i,str) and i for i in ids)
             and len(set(ids)) == len(ids), 'Critic citation bounds')
        need(decoded['support'] not in ('supported','contradicted') or bool(ids), 'Support assertion requires citation')
        need(prior['prediction'] is not None or decoded['support']=='not_assessable', 'Null prior is not assessable')
        need(isinstance(decoded['criticism'],str) and len(decoded['criticism'].encode()) <= 160
             and not any(ord(c)<32 for c in decoded['criticism']), 'Criticism UTF8/control bound')
        query_terms(decoded['queries'])
    if value['native_call_sha256'] is None:
        need(value['native_status']=='capacity', 'Critic native proof missing')
    else: digest(value['native_call_sha256'])
    return freeze(encode(value))
