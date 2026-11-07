"""External-checkpoint context and paired primary-candidate checks.

Reuse the frozen native source/request checker without claiming the external
model was fitted by the baseline. Transformer measurements remain explicit in
an additional resource record; the old non-generative envelope is a compatibility
projection, not the authoritative token accounting.
"""
import hashlib
import math
from pathlib import Path

from tether_engine.serde import encode, fingerprint, freeze
from experiments.scifact.data_views import verify_preparation, load_product
from experiments.scifact.tether_adapter import (
    NativeContext, admit_container, authorize_products, make_request, verify_candidate,
)
from experiments.scifact_comparison.inputs import digest, encoded, need
from experiments.scifact_comparison.prepare import pin, read, write, PREPARATION_SHA

ACQUISITION_SHA = 'a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610'
CONFIGURATION = dict(method='multivers_fever_sci_zero_shot', precision='float32',
                     force_rationale=False, max_tokens=4096, retrieval='retained_baseline_top5',
                     label_threshold=None, rationale_threshold=.5,
                     label_order=['CONTRADICT','NEI','SUPPORT'])


def validate_external_manifest(model):
    need(set(model) == {'schema_version','kind','configuration','acquisition_receipt',
                       'acquisition_payloads','qualification_acceptance','runtime_source_pins',
                       'producer_code','exposure','local_fitting_performed'}, 'External model manifest fields differ')
    need(model['schema_version'] == 1 and model['kind'] == 'sc03_external_pretrained_model', 'External model kind differs')
    need(model['configuration'] == CONFIGURATION and model['local_fitting_performed'] is False,
         'External model may not masquerade as locally fitted baseline')
    authority = model['acquisition_receipt']
    need(authority['sha256'] == ACQUISITION_SHA and pin(authority['path']) == authority, 'Acquisition authority differs')
    acquired = read(authority['path'])
    need(acquired['status'] == 'PASS', 'Acquisition not complete')
    expected = [{k:row[k] for k in ('path','bytes','sha256')} for row in acquired['files']
                if row['kind'] in ('checkpoint','tokenizer_config')]
    need(model['acquisition_payloads'] == expected, 'Model payload inventory differs')
    need(sum(Path(p['path']).name == 'fever_sci.ckpt' for p in expected) == 1, 'Wrong external checkpoint')
    accepted = model['qualification_acceptance']
    need(accepted['sha256'] == 'bb21dfe9c08f01796457dcf634dcc9a9bc9082c9aec711e765d1b71b5a974ef4'
         and pin(accepted['path']) == accepted and read(accepted['path'])['status'] == 'PASS', 'SC02 acceptance differs')
    need(model['exposure'] == 'Pre-SciFact-finetuning release; pretraining/model-development exposure not excluded.', 'Exposure declaration differs')
    proofs = expected + model['runtime_source_pins'] + [model['producer_code']]
    need(model['runtime_source_pins'] and len({p['path'] for p in model['runtime_source_pins']}) == len(model['runtime_source_pins']),
         'Missing/duplicate qualified runtime source pins')
    # The acceptance's verified file inventory fixes the eligible runtime identities.
    accepted_files = {p['path']:p for p in read(accepted['path'])['verified_files']}
    accepted_freezes = [p for p in accepted_files.values() if
        p['sha256'] == 'fbcff0a79e7054fdb3e128a3ad038ff03b6dc1ced9411e2ee7ed1a83becf64e6']
    need(len(accepted_freezes) == 1 and pin(accepted_freezes[0]['path']) == accepted_freezes[0], 'Qualified runtime freeze missing')
    need(model['runtime_source_pins'] == read(accepted_freezes[0]['path'])['pins'], 'Incomplete qualified runtime inventory')
    need(Path(model['producer_code']['path']).resolve() == Path(__file__).with_name('worker.py').resolve(), 'Wrong producer entrypoint')
    for proof in model['runtime_source_pins']:
        need(accepted_files.get(proof['path']) == proof, 'Runtime proof not in accepted SC02 inventory')
    for proof in proofs:
        need(pin(proof['path']) == proof, 'External model/source bytes changed')
    return freeze(model)


def validate_pair_decode(pair, sentence_count):
    """Reconstruct the qualified release-default decode from retained probabilities."""
    labels = CONFIGURATION['label_order']
    probabilities = pair['label_probs']
    rationale = pair['rationale_probs']
    need(type(probabilities) is list and len(probabilities) == 3 and
         all(type(x) in (int,float) and math.isfinite(x) and 0 <= x <= 1 for x in probabilities)
         and abs(sum(probabilities)-1) <= 1e-5, 'Invalid label probabilities')
    need(type(rationale) is list and len(rationale) == sentence_count and
         all(type(x) in (int,float) and math.isfinite(x) and 0 <= x <= 1 for x in rationale),
         'Invalid rationale probabilities')
    need(pair['predicted_label'] == labels[max(range(3), key=probabilities.__getitem__)], 'Label/probability mismatch')
    need(pair['predicted_rationale'] == [i for i,p in enumerate(rationale) if p >= .5], 'Rationale/probability mismatch')


def build_external_context(preparation_root, model_path, model_sha256, proof_directory, *, cutoff, workspace_root):
    prepared, model_path = Path(preparation_root), Path(model_path)
    need(pin(model_path)['sha256'] == model_sha256, 'External manifest anchor differs')
    model = validate_external_manifest(read(model_path))
    manifest = verify_preparation(prepared, PREPARATION_SHA)
    authorize_products(manifest, ['corpus','queries_dev'], 'predict')
    archive = manifest['archive']
    admission = admit_container(archive['path'], archive['receipt_path'],
        Path(proof_directory)/'normalized-container-receipt.json', workspace_root=workspace_root,
        cutoff=cutoff, expected_archive_sha256=archive['sha256'], expected_receipt_sha256=archive['receipt_sha256'])
    corpus = {r['doc_id']:r for r in load_product(prepared, manifest, 'corpus','predict')}
    queries = {r['id']:r for r in load_product(prepared, manifest, 'queries_dev','predict')}
    doc_hashes = {k:fingerprint(v) for k,v in corpus.items()}
    sentence_hashes = {(k,i):hashlib.sha256(s.encode()).hexdigest() for k,d in corpus.items() for i,s in enumerate(d['abstract'])}
    scope = dict(policy='sc03_external_model_native_primary_v1', model_sha256=model_sha256,
                 preparation_manifest_sha256=PREPARATION_SHA, cutoff=cutoff,
                 container_sha256=fingerprint(admission), policy_code_sha256=pin(__file__)['sha256'])
    return NativeContext(prepared, PREPARATION_SHA, model_path.parent, model_sha256, model_path.name,
        Path(workspace_root), cutoff, manifest, model, corpus, queries, doc_hashes, sentence_hashes,
        admission, fingerprint(scope))


def check_primary(context, input_request, claim, pairs, retrieved):
    """Bind the actual five-pair primary result before applying frozen native checks."""
    cid = input_request['id']
    need(claim['condition'] == 'primary' and claim['id'] == cid and claim['status'] == 'produced', 'Primary produced claim required')
    need(claim['input_sha256'] == digest(input_request), 'Worker input binding differs')
    need(input_request['claim'] == context.queries[cid]['claim'], 'Claim text differs from original query')
    expected_ids = [r['doc_id'] for r in retrieved]
    need([d['doc_id'] for d in input_request['documents']] == expected_ids and len(expected_ids) == 5,
         'Fixed primary retrieval differs')
    need([p['abstract_id'] for p in pairs] == expected_ids, 'Pair coverage/order differs')
    predicted = []
    observations = []
    for doc, pair in zip(input_request['documents'], pairs):
        did = doc['doc_id']
        need(digest(doc) == context.document_hashes[did] and pair['input_document_sha256'] == digest(doc), 'Original source/input document differs')
        need(pair['claim_id'] == cid and pair['status'] == 'completed' and pair['model_dispatch'] is True, 'Pair not completed')
        p = pair['prediction']
        need(p['claim_id'] == cid and p['abstract_id'] == did, 'Predicted pair identity differs')
        validate_pair_decode(p, len(doc['abstract']))
        need(type(pair['observations']['token_count']) is int and 0 < pair['observations']['token_count'] <= 4096,
             'Measured input tokens invalid')
        predicted.append(p)
        observations.append(pair['observations'])
    from experiments.scifact_multivers.contracts import native_predictions, require_complete_pairs
    require_complete_pairs([dict(claim_id=cid, abstract_id=d['doc_id'], sentences=d['abstract'])
                            for d in input_request['documents']], predicted)
    need(native_predictions([cid], predicted)[0] == claim['prediction'], 'Claim does not assemble retained pair predictions')
    prediction = claim['prediction']
    request = make_request(context, cid, context.model['configuration'])
    source_bindings = [dict(doc_id=int(did), sentence_id=i, text_sha256=context.sentence_hashes[(int(did),i)])
                       for did, item in prediction['evidence'].items() for i in item['sentences']]
    # This view preserves the frozen non-generative schema only. Measured input
    # token counts are retained below and must not be inferred from these nulls.
    resources = dict(wall_seconds=claim['wall_seconds'], cpu_seconds=claim['cpu_seconds'],
        peak_memory_bytes=max(o['memory']['peak_working_set_bytes'] for o in observations),
        memory_method='windows_process_lifetime_peak', input_bytes=len(encoded(input_request)),
        output_bytes=len(encoded(claim)), examples=1, model_input_tokens=None, model_output_tokens=None,
        tokenizer_identity=None, provider_usage=None, token_usage_reason='not_applicable_non_llm', provider_cost_usd=0)
    envelope = dict(request_sha256=fingerprint(request), prediction_sha256=fingerprint(prediction),
        retrieved=retrieved, source_bindings=source_bindings,
        producer_code_sha256=context.model['producer_code']['sha256'], resources=resources)
    accepted = verify_candidate(context, request, prediction, envelope, configuration=context.model['configuration'])
    return freeze(dict(candidate=accepted, input_sha256=claim['input_sha256'],
        measured_transformer_resources=dict(input_tokens=sum(o['token_count'] for o in observations),
            tokenizer_assets_receipt_sha256=ACQUISITION_SHA, generated_output_tokens=0,
            mode='non_autoregressive_sequence_and_sentence_classification', pair_observations=observations),
        compatibility_scope='Legacy non-generative envelope validates source/request obligations; transformer token accounting is in measured_transformer_resources.'))
