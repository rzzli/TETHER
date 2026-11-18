"""Prepare the exact IL6R/RA example from existing pinned originals.

Invoking this recipe registers a new local, narrowly scoped example use. It does
not change existing policies or grant permission to unrelated/evaluation data.
Review the source terms and use only originals you are authorized to process.
No network access, downloads, model calls or scientific validation are performed.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time

from tether import _catalog_policy as policy
from tether_engine.contracts import (Artifact, Availability, Case, Category, EvidencePacket,
    EvidenceStatus, Hypothesis, Method, Observation, Polarity, Profile, QuantitativeResult,
    ScientificContext, Snapshot, SourceNode, TemporalClass, validate_observation)
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, encode, fingerprint, sha256_file, write_json, ContractError
from tether_engine.stable_read import checked_path, read_file

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
CANDIDATE_SHA='c2b58694416c3d355cff63d07ea30246051dd1948edffbae36f3304fe68cd0f4'


def require(condition, message):
    if not condition:
        raise ContractError(message)


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise ContractError('Example output collision')
    write_json(path,value)


def build(output, raw_root, catalog_path):
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '21.0.0':
        raise ContractError('Example intake requires pyarrow==21.0.0')
    candidate_bytes=(HERE/'il6r_ot2509.json').read_bytes()
    require(hashlib.sha256(candidate_bytes).hexdigest()==CANDIDATE_SHA, "Pinned example contract differs")
    candidate=json.loads(candidate_bytes)
    output=Path(output).absolute()
    checked_path(output.parent.parent,output.parent.name)
    if os.path.lexists(output):
        raise ContractError('Refusing to reuse example output')
    started=time.monotonic()
    deadline=started+300
    journal=RunJournal(output,kind='build')
    stage='source_copy'
    try:
        now=datetime.now(timezone.utc)
        sources, rows, inspected=[],[],[]
        raw_root=Path(raw_root).absolute()
        for item in candidate['sources']:
            receipt_bytes=read_file(raw_root/item['receipt_path'],deadline,1024*1024)
            raw=read_file(raw_root/item['relative_path'],deadline,32*1024*1024)
            require(hashlib.sha256(raw).hexdigest()==item['sha256'] and len(raw)==item['bytes'], "Pinned example contract differs")
            require(hashlib.sha256(receipt_bytes).hexdigest()==item['receipt_sha256'], "Pinned example contract differs")
            receipt=json.loads(receipt_bytes)
            require(receipt['relative_path'].replace('\\','/')==item['relative_path'], "Pinned example contract differs")
            require(receipt['sha256']==item['sha256'] and receipt['status']=='completed', "Pinned example contract differs")
            require(receipt['url']==item['source_url'] and receipt['release_id']=='25.09', "Pinned example contract differs")
            completed=datetime.fromisoformat(receipt['completed_at_utc'])
            availability=Availability(None,None,None,None,completed.date(),'public_download_receipt',
                'Contemporary upper availability bound; earliest publication and annotation history unknown',
                completed,item['receipt_sha256'])
            require(availability.exclusion(now) is None, "Pinned example contract differs")
            for relative,payload in ((item['relative_path'],raw),(item['receipt_path'],receipt_bytes)):
                path=output/'raw'/relative
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(payload)
            file=pq.ParquetFile(io.BytesIO(raw))
            require(file.metadata.num_rows==item['physical_rows_scanned'], "Pinned example contract differs")
            for row in candidate['rows']:
                if row['source_id']!=item['source_id']:
                    continue
                table=file.read_row_group(row['row_group'],columns=item['projected_columns'])
                value=table.slice(row['row_in_group'],1).to_pylist()[0]
                require(value==row['values'], "Pinned example contract differs")
                require(sum(file.metadata.row_group(i).num_rows for i in range(row['row_group']))+row['row_in_group']==row['physical_row'], "Pinned example contract differs")
                rows.append(row)
            sources.append(SourceNode(item['source_id'],item['dataset_id'],'25.09',item['relative_path'],
                item['sha256'],'reference',availability,TemporalClass.CONTEMPORARY,item['source_url'],
                receipt_path=item['receipt_path'],receipt_sha256=item['receipt_sha256']))
            inspected.append(dict(source_id=item['source_id'],bytes=len(raw),sha256=item['sha256'],
                source_file_rows=item['physical_rows_scanned'],selected_rows=item['selected_rows']))
            journal.append('build_progress',source_id=item['source_id'],bytes=len(raw),selected_rows=item['selected_rows'])
        stage='contracts'
        by_dataset={item['dataset_id']:source for item,source in zip(candidate['sources'],sources,strict=True)}
        evidence=next(row for row in rows if row['source_id']==by_dataset['ot_evidence'].source_id)
        values=evidence['values']
        target=next(row for row in rows if row['source_id']==by_dataset['ot_target'].source_id)['values']
        disease=next(row for row in rows if row['source_id']==by_dataset['ot_disease'].source_id)['values']
        require(target==dict(id='ENSG00000160712',approvedSymbol='IL6R'), "Pinned example contract differs")
        require(disease==dict(id='EFO_0000685',name='rheumatoid arthritis'), "Pinned example contract differs")
        require(values['targetId']==target['id'] and values['diseaseId']==disease['id'], "Pinned example contract differs")
        require(values['datasourceId']=='gwas_credible_sets' and values['datatypeId']=='genetic_association', "Pinned example contract differs")
        latest=max(sources,key=lambda source:source.availability.known_public_by).availability
        hypothesis=Hypothesis(target['id'],disease['id'],'OT25.09:target:'+by_dataset['ot_target'].sha256,
            'OT25.09:disease:'+by_dataset['ot_disease'].sha256,'inhibit','antibody',None,latest)
        case=Case(2,'il6r-ra-ot2509-one-annotation','T6',now.date(),hypothesis,None,None,now)
        case.validate()
        refs=tuple(s.source_id for s in sources)
        missing={key:'Not established by this selected provider annotation' for key in
                 ('species','ancestry','tissue','intervention_direction','study_identity','effect_scale','sample_size','therapeutic_relevance')}
        missing.update({key:'Source value is null' for key,value in values.items() if value is None})
        limitations=('One fixed-shard annotation, not a complete evidence review',
            'Source score is descriptive, not a validated effect size or clinical probability',
            'No HGNC crosswalk: identifiers and labels validated against the selected same-release OT originals',
            'Parquet row projection separately replayed; no registered Parquet normalization derivation',
            'No clinical benefit, drug direction or biological absence is inferred')
        observation=Observation('ot2509-'+values['id'],target['id'],disease['id'],None,Category.GENETICS,'integrated',
            'Open Targets 25.09 reports one genetic-association annotation linking IL6R (ENSG00000160712) '
            'and rheumatoid arthritis (EFO_0000685) in the selected shard. Therapeutic relevance is not assessed.',
            EvidenceStatus.OBSERVED,Polarity.UNCERTAIN,'uncertain',None,None,
            ScientificContext(None,None,None,None,None,None,()),QuantitativeResult(None,None,None,None,None,None,None),
            Method('tether.example.ot2509_fixed_row','1',{'projection_sha256':fingerprint(evidence),
                'source_semantics':'provider_annotation_only'},'passed',limitations),latest,{},None,refs,None,
            {k:evidence[k] for k in ('source_id','row_group','row_in_group','physical_row')},values,missing,
            date.fromisoformat(values['publicationDate']),None)
        validate_observation(observation)
        save(output/'snapshot/evidence.json',EvidencePacket(2,(observation,)))
        release='p10-'+now.strftime('%Y%m%dT%H%M%SZ')
        artifact=Artifact('p10-il6r-annotation','tether_normalized_packets',release,'evidence.json',
            sha256_file(output/'snapshot/evidence.json'),'agent_evidence',True,TemporalClass.CONTEMPORARY,latest,
            by_dataset['ot_evidence'].source_url,refs)
        coverage=dict(scope='one_fixed_shard_selected_subset',source_file_rows=candidate['sources'][0]['physical_rows_scanned'],
            selection_basis='fixed previously inspected locator; no new complete matching-row search',
            selected_evidence_rows=1,identifier_rows=2,unobserved_sources='Not collected in this example',
            absent_evidence_inference=False,conflicting_evidence='Not established; subset cannot exclude conflicts',
            prediction_features='empty',clinical_probability=None,scientific_validation='not_established',
            computed_at=now.isoformat(),normalization_replay='separate_original_row_check_not_registered_runtime_derivation')
        snapshot=Snapshot(2,release,Profile.CONTEMPORARY,now.date(),False,(artifact,),tuple(sources),
            str(output/'raw'),coverage,now)
        save(output/'case.json',case)
        save(output/'snapshot/snapshot.json',snapshot)
        provenance=dict(schema_version=1,status='exact_selected_rows_replayed',rows=rows,inspected=inspected,
            candidate_sha256=CANDIDATE_SHA,permission_basis='explicit_recipe_invocation_for_exact_pinned_inputs',
            computed_at=now.isoformat(),scientific_validation='not_established',limitations=limitations,
            terms=dict(product='Open Targets Platform 25.09',current_terms='CC0-1.0',
                url='https://platform-docs.opentargets.org/licence',checked_date='2026-11-16',
                historical_terms_verified=False),normalization_replay='separate_from_runtime_semantic_verifier')
        save(output/'reports/source-projection.json',provenance)
        stage='artifact_policy'
        catalog_bytes=read_file(Path(catalog_path).absolute(),deadline,16*1024*1024)
        catalog_path=output/'data/catalog/sources.json'
        catalog_path.parent.mkdir(parents=True)
        catalog_path.write_bytes(catalog_bytes)
        document=policy.migrate_catalog(catalog_bytes,source_path='data/catalog/sources.json',
            policy_id='p10-il6r-three-originals-v1',created_at_utc=now.isoformat())
        for product in document['products']:
            if product['dataset_id'] in ('ot_target','ot_disease','ot_evidence','tether_normalized_packets'):
                product['dependency_review_status']='reviewed_for_selected_frame'
            if product['dataset_id']=='tether_normalized_packets':
                product['input_dependencies']=['ot_target','ot_disease','ot_evidence']
        records,by_node=[],{}
        for entry,kind,alias in [(encode(s),'raw','raw') for s in sources]+[(encode(artifact),'packet','snapshot')]:
            location=output/('raw' if kind=='raw' else 'snapshot')/entry['path']
            parents=entry.get('parents',entry.get('input_refs',[]))
            receipt=json.loads((output/'raw'/entry['receipt_path']).read_bytes()) if kind=='raw' else None
            record=policy.artifact_record(dataset_id=entry['dataset_id'],release_id=entry['release_id'],root_alias=alias,
                relative_path=entry['path'],sha256=entry['sha256'],bytes=location.stat().st_size,kind=kind,
                parents=[by_node[parent]['artifact_id'] for parent in parents],availability=entry['availability'],
                temporal_classification=entry['temporal_classification'],source_url=entry['source_url'],
                provenance=dict(kind='download_receipt' if kind=='raw' else 'generated',
                    evidence=[dict(path='reports/source-projection.json',sha256=sha256_file(output/'reports/source-projection.json'))],
                    receipt=dict(root_alias='raw',relative_path=entry['receipt_path'],sha256=entry['receipt_sha256'],
                                 receipt_id=receipt['receipt_id'],url=entry['source_url']) if receipt else None),
                scope='Exact-three-original contemporary IL6R/RA example; no other use granted',scientific_validation='not_established')
            records.append(record)
            by_node[entry.get('source_id',entry.get('artifact_id'))]=record
        document['artifacts']=records
        frame=dict(hypothesis=encode(hypothesis),rows=rows,scope='fixed_one_annotation_no_effect_inference')
        frame_sha=fingerprint(frame)
        document['uses']=[dict(use_id='p10-il6r-example',kind='contemporary_evidence',status='allowed',
            profile=snapshot.profile.value,origin_at=now.isoformat(),frame_sha256=frame_sha,
            case_fingerprint=fingerprint(case),snapshot_fingerprint=fingerprint(snapshot),
            raw_root_alias='raw',snapshot_root_alias='snapshot',
            grants=[dict(artifact_id=r['artifact_id'],role='reference' if r['kind']=='raw' else 'agent_evidence') for r in records],blockers=[])]
        roots=dict(raw=str(output/'raw'),snapshot=str(output/'snapshot'),metadata=str(output))
        policy.authorize_snapshot(document,encode(snapshot),case=encode(case),use_id='p10-il6r-example',root_aliases=roots)
        save(output/'policy.json',document)
        save(output/'roots.json',dict(schema_version=1,roots=roots))
        save(output/'frame.json',dict(frame=frame,sha256=frame_sha))
        journal.append('build_completed',selected_evidence_rows=1,identifier_rows=2,frame_sha256=frame_sha,
                       elapsed_seconds=time.monotonic()-started)
        report=dict(status='built_with_exact_use_grant',output=str(output),frame_sha256=frame_sha,
            elapsed_seconds=time.monotonic()-started,original_bytes=candidate['original_bytes'],
            provider_spending_usd=0,scientific_validation='not_established')
        save(output/'build-report.json',report)
        return report
    except BaseException as error:
        journal.fail(error,stage)
        raise
    finally:
        journal.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument("--source-root",type=Path,required=True,help="Existing originals and receipts root; read-only")
    parser.add_argument("--catalog",type=Path,default=ROOT/"data/catalog/sources.json")
    args=parser.parse_args()
    print(json.dumps(build(args.output,args.source_root,args.catalog),indent=2))
