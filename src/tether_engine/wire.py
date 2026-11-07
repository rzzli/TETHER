"""Lossless, readable factoring of repeated scientific fields for local model prompts.

This is a transport representation, never an evidence transformation. Every field,
including nulls, arrays, method parameters and contexts, reconstructs exactly.
"""
from collections.abc import Mapping
from functools import lru_cache

from .agents import SpecialistRequest
from .serde import ContractError, canonical, decode, encode, freeze, parse_json


FORMAT = 'tether-shared-scientific-fields-v1'
_MISSING = object()


def same_json(left, right):
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(same_json(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    if type(left) is not type(right):
        return False
    # Preserve JSON numeric spelling, including -0.0 versus 0.0.
    return canonical(left) == canonical(right) if isinstance(left, float) else left == right


def parse_scientific(text):
    record = parse_json(text)
    if not isinstance(record, dict) or text != canonical(record).decode('utf-8'):
        raise ContractError('Scientific records require canonical JSON objects')
    return freeze(record)


_cached_scientific = lru_cache(maxsize=64)(parse_scientific)


def shared(values):
    first = values[0]
    if all(same_json(value, first) for value in values[1:]):
        return first
    if all(isinstance(value, Mapping) for value in values):
        keys = set(first).intersection(*(set(value) for value in values[1:]))
        result = {}
        for key in sorted(keys):
            common = shared([value[key] for value in values])
            if common is not _MISSING:
                result[key] = common
        return result if result else _MISSING
    return _MISSING


def difference(value, common):
    if same_json(value, common):
        return _MISSING
    if isinstance(common, Mapping) and isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            delta = difference(item, common[key]) if key in common else item
            if delta is not _MISSING:
                result[key] = delta
        return result
    return value


def merge(common, delta):
    if isinstance(common, Mapping) and isinstance(delta, Mapping):
        result = dict(common)
        for key, value in delta.items():
            result[key] = merge(common[key], value) if key in common else value
        return result
    return delta


def encode_wire(request: SpecialistRequest):
    value = encode(request)
    records = [(_cached_scientific if len(item.scientific_record_json) <= 64000 else parse_scientific)(item.scientific_record_json)
               for item in request.evidence]
    # The envelope already displays these fields. Reference them instead of sending
    # two identical copies; reconstruct them before comparing canonical requests.
    identity = [key for key in ('observation_id', 'statement') if records and all(
        key in record and same_json(record[key], getattr(item, key))
        for item, record in zip(request.evidence, records))]
    records = [{k: v for k, v in record.items() if k not in identity} for record in records]
    common = shared(records) if records else {}
    if common is _MISSING:
        common = {}
    evidence = []
    for item, record in zip(value['evidence'], records):
        delta = difference(record, common)
        evidence.append({key: item[key] for key in ('observation_id', 'statement', 'source_ref')} |
                        {'scientific_record_fields': {} if delta is _MISSING else encode(delta)})
    return {key: value[key] for key in ('case_json', 'category', 'instructions', 'feedback')} | {
        'wire_format': FORMAT, 'identity_fields_from_evidence': identity,
        'common_scientific_fields': encode(common), 'evidence': evidence}


def decode_wire(value):
    if set(value) != {'case_json', 'category', 'instructions', 'feedback', 'wire_format',
                     'identity_fields_from_evidence', 'common_scientific_fields', 'evidence'} or value['wire_format'] != FORMAT:
        raise ContractError('Invalid scientific wire format')
    common = value['common_scientific_fields']
    identity = value['identity_fields_from_evidence']
    if (not isinstance(identity, list) or any(k not in ('observation_id', 'statement') for k in identity) or
            len(identity) != len(set(identity))):
        raise ContractError('Invalid referenced identity fields')
    if not isinstance(common, dict) or not isinstance(value['evidence'], list):
        raise ContractError('Invalid shared scientific fields')
    evidence = []
    for item in value['evidence']:
        if set(item) != {'observation_id', 'statement', 'source_ref', 'scientific_record_fields'} or not isinstance(item['scientific_record_fields'], dict):
            raise ContractError('Invalid wire evidence fields')
        record = merge(common, item['scientific_record_fields'])
        if any(k in record for k in identity):
            raise ContractError('Conflicting referenced scientific identity')
        record = {**record, **{k: item[k] for k in identity}}
        evidence.append({key: item[key] for key in ('observation_id', 'statement', 'source_ref')} |
            {'scientific_record_json': canonical(record).decode('utf-8')})
    return decode(SpecialistRequest, {key: value[key] for key in ('case_json', 'category', 'instructions', 'feedback')} |
                  {'evidence': evidence})


def request_bytes(request, wire_format='canonical', *, verify=True):
    if wire_format == 'canonical':
        return canonical(request)
    if wire_format != FORMAT:
        raise ContractError('Unsupported local model wire format')
    payload = encode_wire(request)
    if verify and canonical(decode_wire(payload)) != canonical(request):
        raise ContractError('Wire transport failed exact reconstruction')
    return canonical(payload)
