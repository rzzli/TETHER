"""Bounded fictional qualification; never opens SciFact reference labels.

CLI requires a completed acquisition receipt hash and an unused output folder.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.scifact_multivers.contracts import ContractError, native_predictions, need
from experiments.scifact_multivers.data import collate, tensorize_pair
from experiments.scifact_multivers.runtime import (
    configure_device, hard_deadline, load_components, offline_environment, process_memory,
)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, indent=2)+'\n').encode()


def tensor_record(tensor):
    def safe(value):
        if isinstance(value, list):
            return [safe(x) for x in value]
        if isinstance(value, float) and not math.isfinite(value):
            return 'NaN' if math.isnan(value) else ('+Infinity' if value > 0 else '-Infinity')
        return value
    return dict(dtype=str(tensor.dtype), shape=list(tensor.shape), values=safe(tensor.detach().cpu().tolist()))


def expanded_case(case, recipe, tokenizer):
    case = dict(case, sentences=list(case['sentences']))
    if 'target_tokens' not in case:
        return case
    def candidate(repeats):
        filler = recipe['prefix'] + recipe['repeat_word']*repeats + recipe['suffix']
        sentences = [filler, *case['sentences']]
        context = tokenizer.eos_token.join(sentences)
        if case['title'] is not None:
            context = case['title'] + tokenizer.eos_token + context
        count = len(tokenizer(case['claim']+tokenizer.eos_token+context)['input_ids'])
        return sentences, count
    low, high = 0, 6000
    while low < high:
        mid = (low+high+1)//2
        if candidate(mid)[1] <= case['target_tokens']:
            low = mid
        else:
            high = mid-1
    case['sentences'], count = candidate(low)
    need(case['target_tokens']-3 <= count <= case['target_tokens'], 'Fictional length construction failed')
    case['constructed_token_count'] = count
    return case


def run(args):
    offline_environment()
    import torch
    import transformers
    import tokenizers
    from experiments.scifact_multivers.model import decode, load_state_strict
    from experiments.scifact_multivers.reference import build_reference, capture_reference_sources, reference_tensorizer
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cpu_started = time.process_time()
    events = (output/'events.jsonl').open('xb', buffering=0)
    def event(kind, **values):
        events.write((json.dumps(dict(event=kind, monotonic_seconds=time.monotonic(),
            elapsed_seconds=time.perf_counter()-started, **values), allow_nan=False)+'\n').encode())
    event('started', acquisition_receipt_sha256=args.receipt_sha256)
    controls_path = Path(__file__).with_name('fictional-controls.json')
    raw_controls = controls_path.read_bytes()
    controls = json.loads(raw_controls)
    (output/'controls.json').write_bytes(raw_controls)
    need(controls['force_rationale'] is False, 'Qualification must use release-default decoding')
    with hard_deadline(controls['maximum_process_seconds']):
        device_info = configure_device(args.device)
        load_started = time.perf_counter()
        event('model_load_started', device=device_info)
        model, tokenizer, state, checkpoint, captured = load_components(args.acquisition_root, args.receipt_sha256)
        model_load_seconds = time.perf_counter()-load_started
        sources = capture_reference_sources(args.reference_bundle)
        reference, original_decode = build_reference(model.encoder.config, sources,
            label_threshold=model.label_threshold, rationale_threshold=model.rationale_threshold)
        load_state_strict(reference, state)
        reference.eval().requires_grad_(False)
        del state
        gc.collect()
        original_tensorizer = reference_tensorizer(tokenizer, sources)
        model.to(args.device); reference.to(args.device)
        event('models_loaded', model_load_seconds=model_load_seconds, checkpoint=checkpoint,
              memory=process_memory(), device=device_info)
        results = []
        for index, raw_case in enumerate(controls['cases']):
            case = expanded_case(raw_case, controls['long_context_recipe'], tokenizer)
            event('case_started', case_id=case['id'], input_sha256=hashlib.sha256(json_bytes(case)).hexdigest())
            (output/f'{index:02d}-{case["id"]}.input.json').write_bytes(json_bytes(case))
            if case.get('expected_rejection'):
                try:
                    tensorize_pair(tokenizer, case['claim'], case['sentences'], case['title'])
                except ContractError as exc:
                    need('4096' in str(exc), 'Overflow control failed for the wrong reason')
                    row = dict(case_id=case['id'], rejected=True, reason=str(exc),
                               token_count=case['constructed_token_count'])
                    (output/f'{index:02d}-{case["id"]}.result.json').write_bytes(json_bytes(row))
                    results.append(row); event('case_completed', **row)
                    continue
                raise ContractError('Overflow input was not rejected')
            with hard_deadline(controls['maximum_case_seconds']):
                tensorized = tensorize_pair(tokenizer, case['claim'], case['sentences'], case['title'])
                original = original_tensorizer._tensorize(case['claim'], case['sentences'], case['title'])
                need(dict(original['tokenized']) == tensorized['tokenized'] and
                     original['abstract_sent_idx'] == tensorized['abstract_sent_idx'], 'Released tensorizer parity failed')
                batch = collate([dict(tensorized, claim_id=index+1, abstract_id=index+101)], tokenizer)
                batch = {k: ({f: v.to(args.device) for f,v in value.items()} if k == 'tokenized' else value.to(args.device))
                         for k,value in batch.items()}
                if args.device.startswith('cuda'):
                    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
                forward_started = time.perf_counter()
                with torch.inference_mode():
                    actual = model(batch['tokenized'], batch['abstract_sent_idx'])
                if args.device.startswith('cuda'):
                    torch.cuda.synchronize()
                forward_seconds = time.perf_counter()-forward_started
                reference_started = time.perf_counter()
                with torch.inference_mode():
                    expected = reference(batch['tokenized'], batch['abstract_sent_idx'])
                if args.device.startswith('cuda'):
                    torch.cuda.synchronize()
                reference_seconds = time.perf_counter()-reference_started
                # Preserve the exact inputs and both outputs before assertions;
                # failed parity must leave evidence for independent reconstruction.
                tensors = dict(case_id=case['id'],
                    tokenized={k:tensor_record(v) for k,v in batch['tokenized'].items()},
                    abstract_sent_idx=tensor_record(batch['abstract_sent_idx']),
                    claim_id=tensor_record(batch['claim_id']), abstract_id=tensor_record(batch['abstract_id']),
                    actual={k:tensor_record(v) for k,v in actual.items()},
                    reference={k:tensor_record(v) for k,v in expected.items()})
                (output/f'{index:02d}-{case["id"]}.tensors.json').write_bytes(json_bytes(tensors))
                predicted = decode(actual, batch, force_rationale=False)
                reference_predicted = original_decode(expected, batch, False)
                reference_plain = [{**{k:r[k] for k in ('claim_id','abstract_id','predicted_label','predicted_rationale')},
                                    'label_probs':r['label_probs'].tolist(),
                                    'rationale_probs':r['rationale_probs'].tolist()} for r in reference_predicted]
                (output/f'{index:02d}-{case["id"]}.decoded.json').write_bytes(json_bytes(
                    dict(actual=predicted,reference=reference_plain)))
                differences = {}
                for field in ('label_logits','rationale_logits','label_probs','rationale_probs'):
                    torch.testing.assert_close(actual[field], expected[field], atol=controls['parity_atol'], rtol=controls['parity_rtol'])
                    differences[field] = float((actual[field]-expected[field]).abs().max())
                for field in ('predicted_labels','predicted_rationales'):
                    need(torch.equal(actual[field], expected[field]), 'Discrete prediction parity failed')
                need([(x['claim_id'], x['abstract_id']) for x in predicted] == [(index+1,index+101)],
                     'A scheduled prediction pair was lost or duplicated')
                for a,b in zip(predicted,reference_predicted):
                    for field in ('claim_id','abstract_id','predicted_label','predicted_rationale'):
                        need(a[field] == b[field], 'Released decode parity failed: '+field)
                row = dict(case_id=case['id'], token_count=len(tensorized['tokenized']['input_ids']),
                           sentence_offsets=tensorized['abstract_sent_idx'], prediction=predicted[0],
                           native_prediction=native_predictions([index+1], predicted)[0],
                           expected_label_diagnostic=case.get('expected_label_diagnostic'),
                           semantic_diagnostic_match=predicted[0]['predicted_label'] == case.get('expected_label_diagnostic'),
                           source_level_parity=True, maximum_absolute_differences=differences,
                           forward_seconds=forward_seconds, reference_seconds=reference_seconds,
                           memory=process_memory(),
                           cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated() if args.device.startswith('cuda') else None,
                           cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved() if args.device.startswith('cuda') else None)
                results.append(row)
                (output/f'{index:02d}-{case["id"]}.result.json').write_bytes(json_bytes(row))
                event('case_completed', **row)
        report = dict(schema='multivers-fictional-qualification-v1', status='passed',
                      qualification='archived_source_level_numerical_parity_not_historical_binary_parity',
                      original_tokenizers_binary_parity=False,
                      versions={'torch':torch.__version__, 'transformers':transformers.__version__, 'tokenizers':tokenizers.__version__},
                      checkpoint=checkpoint, device=device_info,
                      controls_sha256=hashlib.sha256(raw_controls).hexdigest(),
                      model_load_seconds=model_load_seconds, wall_seconds=time.perf_counter()-started,
                      cpu_seconds=time.process_time()-cpu_started, memory=process_memory(), cases=results,
                      semantic_diagnostics_are_not_a_pass_gate=True, dev_or_calibration_data_used=False)
        (output/'QUALIFICATION.json').write_bytes(json_bytes(report))
        event('completed', status='passed')
    events.close()
    print(json.dumps({'status':'passed','output':str(output),'wall_seconds':report['wall_seconds']}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--acquisition-root', required=True)
    parser.add_argument('--receipt-sha256', required=True)
    parser.add_argument('--reference-bundle', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device', default='cuda:0')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
