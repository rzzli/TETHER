"""Shared balanced article allocation and exact raw-passage candidate pool."""
from __future__ import annotations

from itertools import zip_longest
import re
from collections.abc import Mapping

from tether_engine.serde import freeze
from experiments.labbench.retrieval import question_tokens
from .codecs import digest, need, question_view, validate_pool


def balanced_candidates(branch_results):
    """Alternate query ranks, deduplicate identities, retain query/rank provenance.

    A branch is one search strategy (lexical or expanded), with two query slots.
    This function does not infer access rights: inputs must be qualified metadata.
    """
    need(isinstance(branch_results,(tuple,list)) and len(branch_results) == 2, 'Two search result lists required')
    need(all(isinstance(x,(tuple,list)) and len(x) <= 10 for x in branch_results), 'Search hit bound')
    seen, output = set(), []
    for pair in zip_longest(*branch_results):
        for item in pair:
            if item is None:
                continue
            need(isinstance(item, Mapping) and isinstance(item.get('candidate'), Mapping), 'Candidate record')
            key = item['candidate'].get('pmcid')
            need(isinstance(key, str) and re.fullmatch(r'PMC[0-9]+',key), 'Candidate identity')
            if key not in seen:
                output.append(item)
                seen.add(key)
    return freeze(output)


def build_pool(question, sources):
    question = question_view(question)
    need(isinstance(sources,(list,tuple)) and len(sources) <= 3, 'Source cap')
    tokens = set(question_tokens(question['question']))
    chunks, seen_sources, seen_spans = [], set(), set()
    for source in sources:
        sid = source['source_id']
        need(sid not in seen_sources, 'Duplicate source')
        seen_sources.add(sid)
        for span in source['spans']:
            text = span['text']
            need(isinstance(text,str) and text.strip() and digest(text.encode()) == span['text_sha256'], 'Parent paragraph hash')
            need(span['evidence_id'] not in seen_spans, 'Duplicate span identity')
            seen_spans.add(span['evidence_id'])
            start = 0
            while start < len(text):
                end = min(len(text),start+1000)
                while len(text[start:end].encode()) > 1000:
                    end -= 1
                need(end > start,'Invalid UTF8 boundary')
                if end < len(text):
                    boundary = text.rfind(' ',start,end)
                    if boundary > start:
                        end = boundary+1
                chunk = text[start:end]
                key = span['evidence_id']+f':c{start}-{end}'
                words = set(re.findall(r'[a-z][a-z0-9-]{2,}',chunk.casefold()))
                chunks.append(dict(task=dict(source_id=key,text=chunk,sha256=digest(chunk.encode())),
                    score=len(tokens & words), binding=dict(source_id=key,document_id=sid,
                        span_id=span['evidence_id'],character_start=start,character_end=end,
                        parent_text_sha256=span['text_sha256'],original_sha256=source['original']['sha256'])))
                start=end
    ordered = sorted(enumerate(chunks),key=lambda x:(-x[1]['score'],x[0]))
    pool, bindings, used = [], [], 0
    for _, chunk in ordered:
        size = len(chunk['task']['text'].encode())
        if len(pool) >= 16 or used+size > 10000:
            continue
        pool.append(dict(rank_id=f'p{len(pool):02d}',**chunk['task']))
        bindings.append(chunk['binding'])
        used += size
    pool = validate_pool(pool)
    return freeze(dict(pool=pool,bindings=bindings,
        coverage=dict(available_chunks=len(chunks),pool_chunks=len(pool),pool_text_bytes=used,
                      excluded_chunks=len(chunks)-len(pool),
                      available_text_bytes=sum(len(c['task']['text'].encode()) for c in chunks),
                      scope='bounded raw paragraph chunks; no absence-of-evidence claim'),
        question_sha256=digest(question['question'].encode())))
