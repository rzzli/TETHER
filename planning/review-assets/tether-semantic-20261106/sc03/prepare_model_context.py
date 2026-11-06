"""Create and qualify the external-checkpoint policy context before production."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from asof.serde import encode, fingerprint
from experiments.scifact_comparison.policy import CONFIGURATION, build_external_context
from experiments.scifact_comparison.prepare import pin, read, write

ASSETS = ROOT/'planning/review-assets/tether-semantic-20261106'
OUTPUT = ASSETS/'sc03/external-model-context-attempt01'


def main():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    try:
        acquisition = ROOT/'data/cache/tether-multivers-acquisition-20261106-attempt01/RECEIPT.json'
        assets = read(acquisition)
        accepted_freeze = read(ASSETS/'solver-qualification/full-freeze-attempt02/MANIFEST.json')
        model = dict(schema_version=1,kind='sc03_external_pretrained_model',configuration=CONFIGURATION,
            acquisition_receipt=pin(acquisition),
            acquisition_payloads=[{k:r[k] for k in ('path','bytes','sha256')} for r in assets['files']
                                  if r['kind'] in ('checkpoint','tokenizer_config')],
            qualification_acceptance=pin(ASSETS/'sc02-acceptance-attempt01/ROOT-ACCEPTANCE.json'),
            runtime_source_pins=accepted_freeze['pins'],
            producer_code=pin(ROOT/'experiments/scifact_comparison/worker.py'),
            exposure='Pre-SciFact-finetuning release; pretraining/model-development exposure not excluded.',
            local_fitting_performed=False)
        write(OUTPUT/'MODEL-MANIFEST.json',model)
        cutoff = datetime.now(timezone.utc).isoformat()
        context = build_external_context(ROOT/'data/benchmark/scifact/preparation-20261105-attempt03',
            OUTPUT/'MODEL-MANIFEST.json',pin(OUTPUT/'MODEL-MANIFEST.json')['sha256'],OUTPUT/'proofs',
            cutoff=cutoff,workspace_root=ROOT)
        write(OUTPUT/'CONTEXT.json',dict(cutoff=cutoff,policy_sha256=context.policy_sha256,
            container_admission=encode(context.container_admission),
            corpus_document_hashes=encode(context.document_hashes),
            model=pin(OUTPUT/'MODEL-MANIFEST.json'),source_preparation_sha256=context.preparation_manifest_sha256))
        result = dict(status='PASS',model=pin(OUTPUT/'MODEL-MANIFEST.json'),context=pin(OUTPUT/'CONTEXT.json'),
            policy_code=pin(ROOT/'experiments/scifact_comparison/policy.py'),queries=len(context.queries),
            corpus_documents=len(context.corpus),native_candidate_execution=False,
            actual_model_inference=False,cutoff=cutoff)
        write(OUTPUT/'PREFLIGHT.json',result)
        print(json.dumps(result))
    except BaseException as error:
        write(OUTPUT/'FAILED.json',dict(status='FAIL',error_type=type(error).__name__,error=str(error)))
        raise


if __name__ == '__main__':
    main()
