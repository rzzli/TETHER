"""Explicit invented acquisition/probe envelopes for lossless-cache engineering tests.

OS/process records are authored fixtures. Source metadata and every public plan,
layout, bit comparison and cache authority check remain real.
"""
from pathlib import Path
import sys

from tether_engine.serde import canonical,encode
from experiments.alce import derived_checkpoint as d
from tests.test_alce_derived_checkpoint import checkpoint,original_rows,proof,put


def process(root,stdout=b'',*,seconds=930):
    (root/'stdout.bin').write_bytes(stdout);(root/'stderr.bin').write_bytes(b'')
    return put(root/'PROCESS.json',dict(returncode=0,supervision=dict(schema_version=1,method='tether.process_envelope.v1',
        limits=dict(timeout_seconds=seconds,max_output_bytes=4*1024**2),termination_reason='exited',
        execution_elapsed_seconds=.1,total_elapsed_seconds=.2,retained_stdout_bytes=len(stdout),retained_stderr_bytes=0,
        observed_stdout_bytes=len(stdout),observed_stderr_bytes=0,observed_counts_are_lower_bounds=False,
        pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[])))


def parent_fixture(root,deadline,writer=checkpoint):
    """Five tiny originals, adjacent alias, exact 12 original model members."""
    inputs=root/'inputs';inputs.mkdir();acq=inputs/'acquisition';source=acq/'payloads/models/true_nli';source.mkdir(parents=True)
    names=sorted(n for n in d.runtime.FILES['true_nli'] if n.endswith('.bin'))
    keymap={};tensors=[];shards=[];aliases={}
    for i,name in enumerate(names):
        keys=['shared.weight','encoder.embed_tokens.weight'] if i==0 else [f'layer.{i}.weight']
        bits=bytes.fromhex('000000800100c07f0000807f01000000')
        writer(source/name,[(k,'0',[4],[1]) for k in keys],{'0':bits})
        rows,meta=original_rows(source/name,deadline);tensors.extend(rows)
        shards.append(dict(file=name,state_dict_metadata=None,storage_members=list(meta['storages'].values())))
        for row in rows:
            keymap[row['key']]=name;aliases.setdefault(name+'@'+str(row['checkpoint_offset']),[]).append(row['key'])
    for name in sorted(d.runtime.FILES['true_nli']-set(names)-{'pytorch_model.bin.index.json'}):
        (source/name).write_bytes(b'{}\n' if name.endswith('.json') else b'invented metadata only\n')
    index=put(source/'pytorch_model.bin.index.json',dict(metadata=dict(total_size=len(tensors)*16),weight_map=keymap))
    meta=put(inputs/'SOURCE-METADATA.json',dict(invented=True,process_captures='explicitly authored'))
    rows=[];observed=[]
    for i,name in enumerate(sorted(d.runtime.FILES['true_nli'])):
        fp=proof(source/name)
        row=dict(id=f'file-{i}',product_id='true_nli',destination='models/true_nli/'+name,expected_bytes=fp['bytes'],
            revision=dict(kind='git_commit',value=d.runtime.MODELS['true_nli'][1]),
            digest=dict(kind='content',algorithm='sha256',value=fp['sha256']),metadata_proof=meta,rights_reference='invented')
        rows.append(row);observed.append(dict(row,path=fp['path'],bytes=fp['bytes'],sha256=fp['sha256'],status='completed',attempts=1))
    manifest=put(inputs/'MANIFEST.json',dict(kind='alce_acquisition_manifest_v1',assets=rows,limits=dict(total_seconds=930)))
    worker=put(acq/'WORKER.json',dict(kind='alce_acquisition_worker_receipt_v1',status='completed',hard_parent_supervision=True,manifest=manifest,files=observed))
    ap=process(acq)
    acquisition=put(acq/'RECEIPT.json',dict(kind='alce_acquisition_receipt_v1',status='verified',worker_receipt=worker,
        manifest=manifest,process=ap,automatic_retries=0,range_resume=False,payload_hashes_rechecked=True))
    child=inputs/'metadata-child';child.mkdir();outer=inputs/'metadata-outer';outer.mkdir()
    inventory=put(child/'INVENTORY.json',dict(original_index=index,original_config=proof(source/'config.json'),
        shards=shards,tensors=tensors,same_storage_aliases=aliases))
    helper=proof(Path(__file__).resolve());interpreter=proof(Path(sys.executable).resolve())
    pins=put(inputs/'PROBE-PINS.json',dict(acquisition=acquisition,helper=helper,interpreter=interpreter))
    request=put(child/'REQUEST.json',dict(pins=pins,helper=helper,inference=False,model_instantiation=False,numeric_storage_access_authorized=False))
    result=put(child/'RESULT.json',dict(status='metadata_inventory_complete',inventory=inventory,denied_numeric_reads=[],
        model_instantiated=False,inference=False,weights_rehashed=False,elapsed_seconds=.05,key_count=len(tensors),shard_count=len(names)))
    resources=put(child/'RESOURCES.json',dict(scope='Invented process records; no measured model work.'))
    child_receipt=put(child/'RECEIPT.json',dict(kind='true_fp32_metadata_probe_receipt_v1',
        files={'REQUEST.json':request,'RESULT.json':result,'INVENTORY.json':inventory,'RESOURCES.json':resources}))
    command=put(outer/'COMMAND.json',dict(helper=helper,limits=dict(timeout_seconds=930,max_output_bytes=4*1024**2),
        argv=[interpreter['path'],'-I','-B','-X','utf8',helper['path'],'--execute','--pins',pins['path'],
              '--pins-sha256',pins['sha256'],'--output',str(child)]))
    op=process(outer,canonical(dict(receipt=child_receipt)))
    supervision=put(outer/'RECEIPT.json',dict(kind='supervised_true_fp32_metadata_receipt_v1',status='metadata_inventory_complete',
        inference=False,child=child_receipt,files={'COMMAND.json':command,'PROCESS.json':op,
          'stdout.bin':proof(outer/'stdout.bin'),'stderr.bin':proof(outer/'stderr.bin')}))
    plan=d.prepare_plan(acquisition,inventory,supervision,deadline=deadline)
    pp=put(inputs/'PLAN.json',plan)
    return dict(plan=encode(plan),plan_proof=pp,acquisition=acquisition,inventory=inventory,supervision=supervision,
                inputs=inputs,source=source)
