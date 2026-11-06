"""Reusable receipt-bound solver; callers provide their frozen retrieval schedule.

No search, gold-label access, model selection, retry, or training is performed.
Scientific scheduling belongs to the separately frozen experiment controller.
"""
from __future__ import annotations

import gc
import time
from contextlib import contextmanager

from .contracts import native_predictions, prepare_entries, require_complete_pairs
from .data import collate, tensorize_pair
from .runtime import configure_device, hard_deadline, load_components, offline_environment, process_memory


@contextmanager
def record_pair_failure(event, entry):
    try:
        yield
    except Exception as exc:
        event(event='pair_failed', claim_id=entry['claim_id'], abstract_id=entry['abstract_id'],
              monotonic_seconds=time.monotonic(), status='failed', error_type=type(exc).__name__,
              error=str(exc)[:2000])
        raise


class LoadedSolver:
    def __init__(self, acquisition_root, receipt_sha256, *, device='cuda:0'):
        offline_environment()
        started=time.perf_counter()
        self.device=device
        self.device_info=configure_device(device)
        self.model,self.tokenizer,state,self.metadata,_=load_components(acquisition_root,receipt_sha256)
        del state
        gc.collect()
        self.model.to(device)
        self.load_seconds=time.perf_counter()-started

    def predict(self, claims, corpus, *, pair_deadline_seconds=120, event=lambda **unused: None):
        import torch
        from .model import decode
        entries=prepare_entries(claims,corpus)
        predictions=[]
        observations=[]
        for entry in entries:
            event(event='pair_started',claim_id=entry['claim_id'],abstract_id=entry['abstract_id'],monotonic_seconds=time.monotonic())
            with record_pair_failure(event,entry), hard_deadline(pair_deadline_seconds):
                encoded=tensorize_pair(self.tokenizer,entry['claim'],entry['sentences'],entry['title'])
                batch=collate([dict(encoded,claim_id=entry['claim_id'],abstract_id=entry['abstract_id'])],self.tokenizer)
                batch={k:({f:v.to(self.device) for f,v in value.items()} if k=='tokenized' else value.to(self.device))
                       for k,value in batch.items()}
                if self.device.startswith('cuda'):
                    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
                started=time.perf_counter()
                with torch.inference_mode():
                    output=self.model(batch['tokenized'],batch['abstract_sent_idx'])
                if self.device.startswith('cuda'):
                    torch.cuda.synchronize()
                seconds=time.perf_counter()-started
                pairs=decode(output,batch,force_rationale=False)
                require_complete_pairs([entry],pairs)
                predictions.extend(pairs)
                record=dict(claim_id=entry['claim_id'],abstract_id=entry['abstract_id'],
                            token_count=len(encoded['tokenized']['input_ids']),sentence_offsets=encoded['abstract_sent_idx'],
                            forward_seconds=seconds,memory=process_memory(),
                            cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated() if self.device.startswith('cuda') else None,
                            cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved() if self.device.startswith('cuda') else None)
                observations.append(record)
                event(event='pair_completed',status='completed',prediction=pairs[0],
                      monotonic_seconds=time.monotonic(),**record)
        require_complete_pairs(entries,predictions)
        return dict(status='completed',predictions=native_predictions([x['id'] for x in claims],predictions),
                    pair_predictions=predictions,observations=observations,
                    model_receipt=self.metadata,load_seconds=self.load_seconds,force_rationale=False)
