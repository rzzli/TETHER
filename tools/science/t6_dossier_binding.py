"""Evaluator-only dossier/claim binding with replayed Open Targets originals.

No model calls or scientific judgments. Draft source statements are deliberately
not marked atomically complete. A digest alone never substitutes for source replay.
"""
from pathlib import Path
import hashlib
import re
import time
from types import SimpleNamespace

from asof.artifacts import verify_run
from asof.chrono import required_source_proofs
from asof.contracts import Case, Snapshot
from asof.journal import RunJournal
from asof.provenance import InputGraph, catalog_index
from asof.serde import (ContractError, canonical, decode, fingerprint, read_json, read_ledger_json,
                        safe_child, sha256_file, write_json)
from tools.framework.run_pilot import SourceAudit
from tools.science.reference_packets import _mappings, audit_observation
from tools.science.run_comparison import check_pin, pin
from tools.science.t6_claim_audit import (HYPOTHESIS_FIELDS, MAX_SOURCE_BYTES,
    _summarize_review, require, validate_claims)


def _approved(path, roots):
    path = Path(path).resolve()
    require(bool(roots) and any(path.is_relative_to(Path(root).resolve()) for root in roots),
            'Dossier/source path outside explicitly approved roots')
    return path


def _dossier_bytes(path):
    with path.open('rb') as stream:
        payload = stream.read(MAX_SOURCE_BYTES + 1)
    require(len(payload) <= MAX_SOURCE_BYTES, 'Dossier exceeds bounded audit input size')
    return payload


def _collect(receipt_proof, approved_roots):
    try:
        import pyarrow
    except ImportError as error:
        raise ContractError('Original Open Targets audit requires the pinned ingest extra') from error
    require(pyarrow.__version__ == '21.0.0', 'Original Open Targets audit requires pyarrow 21.0.0')
    receipt_path = _approved(receipt_proof['path'], approved_roots)
    require(receipt_path.name == 'receipt.json', 'Expected a native v2 run receipt')
    check_pin(receipt_proof)
    run = receipt_path.parent
    receipt = read_json(receipt_path)
    require(type(receipt.get('schema_version')) is int and receipt['schema_version'] == 2,
            'Dossier binding requires v2 semantic verification; v1 remains archival')
    inputs = read_json(run / 'inputs.json')
    case, snapshot = decode(Case, inputs['case']), decode(Snapshot, inputs['snapshot'])
    require(case.task == 'T6', 'This audit binding is scoped to T6 dossiers')
    base = _approved(inputs['snapshot_base'], approved_roots)
    _approved(snapshot.raw_root, approved_roots)
    # Check complete path capability before any raw-source verification reads.
    proofs = required_source_proofs(snapshot, case, base, inputs['catalog_policy'])
    for proof in proofs:
        _approved(proof['path'], approved_roots)
        if proof.get('receipt_path'):
            _approved(proof['receipt_path'], approved_roots)
    verification = verify_run(run, receipt_proof['sha256'], verify_sources=True)
    require(verification['semantic_consistency'] == 'verified' and
            verification['source_binding'] == 'current_originals', 'Run/source semantics not verified')
    prediction, features = read_json(run / 'prediction.json'), read_json(run / 'features.json')
    require(prediction['probability'] is None and
            all(value['value'] is None for value in features['values'].values()),
            'This real-data development binding requires withheld probabilities/features')
    dossier_path = run / 'dossier.md'
    require(dossier_path.stat().st_size <= MAX_SOURCE_BYTES, 'Dossier exceeds bounded audit input size')
    dossier = _dossier_bytes(dossier_path)
    require(hashlib.sha256(dossier).hexdigest() == receipt['outputs']['dossier.md'], 'Dossier changed during read')
    headers = list(re.finditer(rb'(?m)^##(?:#)? [^\r\n]+', dossier))
    sections = {}
    for index, match in enumerate(headers):
        sections.setdefault(match.group(), []).append((match.start(),
            headers[index + 1].start() if index + 1 < len(headers) else len(dossier)))
    mapping_path = _approved(base / 'identifier-validation.json', approved_roots)
    mapping_pin = pin(mapping_path)
    mapping = read_json(mapping_path)
    recorded = mapping['hgnc'][0]
    definition = SimpleNamespace(symbol=recorded['symbol'], target_id=case.hypothesis.target_id,
                                 disease_id=case.hypothesis.indication_id,
                                 hgnc_id=recorded['hgnc_id'])
    audit, source_proofs = SourceAudit(), {}
    graph = InputGraph(snapshot, base, catalog_index(inputs['catalog_policy']))
    nodes, refs, disease = _mappings(audit, base, inputs['case'], inputs['snapshot'],
                                    definition, graph, source_proofs)
    ledger = read_ledger_json(run / 'ledger.json')
    units, physical, seen = [], set(), set()
    for claim in ledger['claims']:
        observation = claim['evidence']['observation']
        require(observation['observation_id'] not in seen, 'Duplicate selected source observation')
        seen.add(observation['observation_id'])
        original = audit_observation(audit, observation, case=case, nodes=nodes, graph=graph,
            mapping_refs=refs, symbol=definition.symbol, disease_name=disease, proofs=source_proofs)
        location = original['physical_locator']
        key = (original['source']['sha256'], location['row_group'], location['row'])
        require(key not in physical, 'Duplicate physical original row in selected source inventory')
        physical.add(key)
        quote = ('> ' + observation['statement'].replace('\n', '\n> ')).encode('utf-8')
        header = ('### ' + claim['claim_id'] + ' (' + claim['specialist'] + ')').encode('utf-8')
        require(len(sections.get(header, [])) == 1, 'Selected ledger claim has no unique dossier section')
        start, section_end = sections[header][0]
        # Native write_text can serialize LF or Windows CRLF; compare exact
        # renderer variants, retaining actual bytes rather than normalizing input.
        variants = tuple(dict.fromkeys((quote, quote.replace(b'\n', b'\r\n'))))
        matches = [(dossier.find(value, start, section_end), value) for value in variants
                   if dossier.find(value, start, section_end) >= 0]
        require(len(matches) == 1, 'Dossier quote differs or has ambiguous native line endings')
        quote_start, quote = matches[0]
        require(dossier.find(quote, quote_start + len(quote), section_end) < 0,
                'Repeated source quote in one claim section is ambiguous')
        citation = claim['evidence']['citation']
        source_line = (f"Source: {citation['dataset_id']}/{citation['release_id']}; "
            f"artifact {citation['artifact_id']}; observation {observation['observation_id']}.").encode('utf-8')
        section_lines = dossier[start:section_end].splitlines()
        require([line for line in section_lines if line.startswith(b'Source: ')] == [source_line] and
                [line for line in section_lines if line.startswith(b'SHA-256: ')] ==
                [f"SHA-256: `{citation['artifact_sha256']}`.".encode('utf-8')],
                'Dossier citation differs from the sealed source claim')
        units.append(dict(ledger_claim_id=claim['claim_id'], observation_id=observation['observation_id'],
            statement=observation['statement'], quoted_span=dict(start=quote_start, end=quote_start + len(quote)),
            section_span=dict(start=start, end=section_end),
            source_audit=original))
    for proof in source_proofs.values():
        require(sha256_file(audit.source(proof, proof['raw_root'])) == proof['sha256'],
                'Original source changed during dossier binding')
        require(sha256_file(safe_child(Path(proof['raw_root']), proof['receipt_path'])) == proof['receipt_sha256'],
                'Original source receipt changed during dossier binding')
    check_pin(mapping_pin)
    check_pin(receipt_proof)
    # Recheck all sealed output bytes after lengthy original-row work.
    for name, digest in {**receipt['outputs'], **receipt.get('auxiliary_outputs', {})}.items():
        require(sha256_file(safe_child(run, name)) == digest, 'Sealed run changed during source binding')
    return dict(schema_version=1, role='evaluation_only', kind='native_v2_OT_dossier_binding',
        run_receipt=receipt_proof, dossier=pin(dossier_path), identifier_validation=mapping_pin,
        question={name: getattr(case.hypothesis, name) for name in sorted(HYPOTHESIS_FIELDS)},
        source_units=units, source_proofs=list(source_proofs.values()),
        claims_inventory_scope='source_units_only_not_atomic_or_complete',
        scientific_validity='not_established', clinical_probability=None)


def build_binding(receipt_proof, output, *, approved_roots):
    """Reserve before reading; retain failures and never overwrite or restart."""
    output = Path(output).resolve()
    require(not output.is_relative_to(Path(receipt_proof['path']).resolve().parent),
            'Binding output must be outside the sealed run directory')
    journal = RunJournal(output, kind='build')
    started = time.monotonic()
    try:
        journal.append('dossier_binding_started', run_receipt=receipt_proof,
                       approved_roots=[str(Path(root).resolve()) for root in approved_roots])
        binding = _collect(receipt_proof, approved_roots)
        require(len(canonical(binding)) <= MAX_SOURCE_BYTES, 'Binding exceeds 64 MiB audit limit; no rows dropped')
        write_json(output / 'binding.json', binding)
        report = dict(status='source_inclusive_dossier_binding_completed', role='evaluation_only',
            binding=pin(output / 'binding.json'), source_units=len(binding['source_units']),
            source_files=len(binding['source_proofs']), elapsed_seconds=time.monotonic() - started,
            code=[pin(Path(__file__))], atomic_inventory_complete=False, scientific_validity='not_established')
        write_json(output / 'report.json', report)
        journal.append('build_completed', report=pin(output / 'report.json'))
        return report
    except BaseException as error:
        journal.fail(error, 'dossier_source_binding')
        raise
    finally:
        journal.close()


def verify_binding(binding_proof, *, approved_roots):
    _approved(binding_proof['path'], approved_roots)
    binding = read_json(check_pin(binding_proof))
    current = _collect(binding['run_receipt'], approved_roots)
    require(fingerprint(current) == fingerprint(binding), 'Dossier/source binding replay differs')
    return binding


def bind_manifest(manifest, binding):
    """Check exact UTF-8 source spans. Completeness remains explicitly attested."""
    validate_claims(manifest)
    require(manifest.get('dossier_binding_sha256') == fingerprint(binding) and
            manifest['dossier_sha256'] == binding['dossier']['sha256'] and
            manifest['question'] == binding['question'], 'Claim inventory differs from bound dossier/question')
    data = _dossier_bytes(Path(check_pin(binding['dossier'])))
    require(hashlib.sha256(data).hexdigest() == binding['dossier']['sha256'], 'Dossier changed during span read')
    available = {u['observation_id'] for u in binding['source_units']}
    for claim in manifest['claims']:
        spans = claim.get('dossier_spans')
        require(isinstance(spans, list) and len(spans) == 1,
                'Version 1 requires one contiguous exact dossier byte span per claim')
        pieces, last = [], -1
        for span in spans:
            require(isinstance(span, dict) and type(span.get('start')) is int and type(span.get('end')) is int
                    and 0 <= span['start'] < span['end'] <= len(data) and span['start'] >= last,
                    'Invalid, overlapping or unordered dossier spans')
            try:
                pieces.append(data[span['start']:span['end']].decode('utf-8'))
            except UnicodeError as error:
                raise ContractError('Dossier span cuts a UTF-8 character') from error
            last = span['end']
        require(''.join(pieces) == claim['statement'], 'Inventoried claim text is absent from dossier spans')
        require(not set(claim['cited_source_ids']) - available, 'Claim cites an unselected dossier source')
        cited_here = {u['observation_id'] for u in binding['source_units'] if
                      u['section_span']['start'] <= spans[0]['start'] < spans[0]['end'] <= u['section_span']['end']}
        require(set(claim['cited_source_ids']) == cited_here,
                'Inventoried citations differ from this actual dossier section')
    return manifest


def audit_bound_claims(manifest, review, binding_proof, *, approved_roots):
    binding = verify_binding(binding_proof, approved_roots=approved_roots)
    bind_manifest(manifest, binding)
    sources = [dict(source_id=u['observation_id'], format='verified_opentargets_parquet',
                    source_audit=u['source_audit']) for u in binding['source_units']]
    originals = {u['observation_id']: u['source_audit']['projected_original_row']
                 for u in binding['source_units']}
    report = _summarize_review(manifest, review, sources, originals)
    report.update(dossier_binding=binding_proof, original_source_replay=True,
                  dossier_span_binding=True, atomic_inventory_completeness='reviewer_attestation_only')
    return report
