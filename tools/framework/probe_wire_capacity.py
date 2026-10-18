"""Probe exact normalized-record wire capacity, without model calls or raw admission.

Uses packet hashes and admitted-record fingerprints from completed source-verified
runs. This validates transport only, not a new scientific ingestion or feature.
"""
from dataclasses import replace
from pathlib import Path
import argparse
import re

from asof.agents import make_request
from asof.contracts import Case, Category, Citation, EvidencePacket, EvidenceStatus, GroundedObservation
from asof.serde import ContractError, decode, fingerprint, read_json, safe_child, sha256_file, write_json
from asof.wire import request_bytes, FORMAT
import asof.wire as wire_module


def probe(pilot):
    report = read_json(pilot / 'pilot-report.json'); rows = []
    for case_result in report['cases']:
        if case_result['verification']['source_binding'] != 'current_originals':
            raise ContractError('Transport probe requires a source-verified parent run')
        old = safe_child(pilot, case_result['case_id'])
        if sha256_file(old / 'receipt.json') != case_result['receipt_sha256']:
            raise ContractError('Parent run receipt changed')
        inputs, receipt = read_json(old / 'inputs.json'), read_json(old / 'receipt.json')
        case = decode(Case, inputs['case']); records = []
        for artifact in inputs['snapshot']['artifacts']:
            path = safe_child(Path(inputs['snapshot_base']), artifact['path'])
            if sha256_file(path) != artifact['sha256']:
                raise ContractError('Normalized packet changed')
            packet = decode(EvidencePacket, read_json(path))
            citation = Citation(artifact['artifact_id'], artifact['dataset_id'], artifact['release_id'], artifact['sha256'], artifact['source_url'])
            for obs in packet.observations:
                record = GroundedObservation(obs, citation)
                if obs.observation_id not in receipt['admitted_fingerprints']:
                    continue
                if fingerprint(record) != receipt['admitted_fingerprints'][obs.observation_id]:
                    raise ContractError('Admitted normalized record changed')
                if obs.status == EvidenceStatus.OBSERVED and case.permits_program(obs.program_id):
                    records.append(record)
        for category in Category:
            group = tuple(r for r in records if r.observation.category == category)
            if not group:
                continue
            request = make_request(case, category, group)
            tokens = set(re.findall(r'[a-z0-9_]{3,}', request.case_json.casefold()))
            ranked = sorted(request.evidence, key=lambda r: (
                -len(tokens & set(re.findall(r'[a-z0-9_]{3,}', r.statement.casefold()))), r.observation_id))
            formats = {}
            for fmt in ['canonical', FORMAT]:
                selected = []
                for item in ranked:
                    if len(selected) < 12 and len(request_bytes(replace(request, evidence=tuple(selected + [item])), fmt, verify=False)) <= 12000:
                        selected.append(item)
                formats[fmt] = {'candidates': len(selected),
                    'wire_bytes': len(request_bytes(replace(request, evidence=tuple(selected)), fmt))}
            rows.append({'case_id': case.case_id, 'category': category.value, 'available': len(group), 'formats': formats})
    return {'status': 'exact_normalized_record_roundtrip_and_capacity_probe', 'model_calls': 0,
        'probe_code_sha256': sha256_file(Path(__file__)), 'wire_code_sha256': sha256_file(Path(wire_module.__file__)),
        'completed_parent_cases': len(report['cases']), 'rows': rows,
        'input_basis': 'Packet hashes and used admitted-record fingerprints checked against completed source-inclusive runs',
        'scientific_validation': 'not_established', 'raw_current_bytes_rehashed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ContractError('Refusing to overwrite transport probe')
    write_json(args.report, probe(args.pilot))
