"""Dependency-free input and integrity contracts for the MultiVerS adapter."""
from __future__ import annotations

import hashlib
from pathlib import Path


class ContractError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ContractError(message)


def identifier(value):
    return type(value) is int and value >= 0


def capture_asset_bytes(root, expected, *, max_total_bytes=8_000_000):
    """Hash precisely the bytes returned to the caller; never follow an escape."""
    root = Path(root).resolve()
    captured = {}
    total = 0
    for name, spec in expected.items():
        need(isinstance(name, str) and name == Path(name).name and name not in ('', '.', '..'),
             'Asset logical ID must be a plain filename')
        path = (root / name).resolve()
        need(path.parent == root, 'Asset escapes the declared directory')
        need(type(spec.get('bytes')) is int and 0 <= spec['bytes'] <= max_total_bytes,
             'Invalid asset size')
        total += spec['bytes']
        need(total <= max_total_bytes, 'Asset capture byte cap exceeded')
        with path.open('rb') as stream:
            raw = stream.read(spec['bytes'] + 1)
        need(len(raw) == spec['bytes'], 'Asset length mismatch: ' + name)
        need(hashlib.sha256(raw).hexdigest() == spec.get('sha256'), 'Asset SHA256 mismatch: ' + name)
        captured[name] = raw
    return captured


def prepare_entries(claims, corpus):
    documents = {}
    for doc in corpus:
        need(isinstance(doc, dict) and identifier(doc.get('doc_id')), 'Invalid corpus document ID')
        did = doc['doc_id']
        need(did not in documents, 'Duplicate corpus document ID')
        need(isinstance(doc.get('title'), str), 'Document title must be a string')
        need(isinstance(doc.get('abstract'), list) and doc['abstract'] and
             all(isinstance(s, str) and s.strip() for s in doc['abstract']), 'Invalid abstract sentences')
        documents[did] = doc
    seen = set()
    entries = []
    for claim in claims:
        need(isinstance(claim, dict) and set(claim) == {'id', 'claim', 'doc_ids'},
             'Prediction claims require only id, claim, doc_ids; annotations are forbidden')
        cid = claim['id']
        need(identifier(cid) and cid not in seen, 'Invalid or duplicate claim ID')
        seen.add(cid)
        need(isinstance(claim['claim'], str) and claim['claim'].strip(), 'Invalid claim text')
        ids = claim['doc_ids']
        need(isinstance(ids, list) and all(identifier(x) for x in ids) and len(set(ids)) == len(ids),
             'Invalid or duplicate retrieved document IDs')
        for did in ids:
            need(did in documents, 'Retrieved document is absent from corpus')
            doc = documents[did]
            entries.append(dict(claim_id=cid, abstract_id=did, claim=claim['claim'],
                                title=doc['title'], sentences=list(doc['abstract'])))
    return entries


def native_predictions(claim_ids, pairs):
    need(all(identifier(x) for x in claim_ids) and len(set(claim_ids)) == len(claim_ids),
         'Invalid or duplicate output claim IDs')
    result = {cid: {} for cid in claim_ids}
    seen = set()
    for pair in pairs:
        cid, did = pair['claim_id'], pair['abstract_id']
        need(cid in result and identifier(did), 'Unknown prediction claim or document ID')
        need((cid, did) not in seen, 'Duplicate claim/document prediction')
        seen.add((cid, did))
        label, sentences = pair['predicted_label'], pair['predicted_rationale']
        need(label in ('CONTRADICT', 'NEI', 'SUPPORT'), 'Unknown predicted label')
        need(isinstance(sentences, list) and all(identifier(x) for x in sentences) and
             sentences == sorted(set(sentences)), 'Rationale indices must be unique ascending integers')
        if label != 'NEI':
            result[cid][str(did)] = {'label': label, 'sentences': list(sentences)}
    return [{'id': cid, 'evidence': evidence} for cid, evidence in result.items()]


def require_complete_pairs(entries, pairs):
    expected = [(x['claim_id'], x['abstract_id']) for x in entries]
    actual = [(x['claim_id'], x['abstract_id']) for x in pairs]
    need(actual == expected, 'Scheduled prediction pairs were lost, duplicated, reordered, or replaced')
    for entry, pair in zip(entries, pairs):
        need(all(type(i) is int and 0 <= i < len(entry['sentences']) for i in pair['predicted_rationale']),
             'Predicted rationale escapes the supplied abstract')
