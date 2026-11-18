"""Check exact original-row links and render a source-bound example reading view.

Requires the optional pinned ingestion dependency for original Parquet replay.
The new reading view has its own manifest; it never changes the sealed dossier.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import time

from tether.api import RunArtifacts, verify_run
from tether_engine.serde import ContractError
from tether_engine.stable_read import read_file, checked_path
from tether_engine.journal import RunJournal


def need(condition, message):
    if not condition:
        raise ContractError('Example audit: '+message)


def render(model):
    """HTML-escape every source-derived value; no Markdown/HTML interpretation."""
    esc=lambda value: html.escape(str(value),quote=True)
    facts=''.join('<tr><th>'+esc(key)+'</th><td>'+esc(value)+'</td></tr>' for key,value in model['facts'].items())
    def source_link(row):
        url=row['source_url']
        need(isinstance(url,str) and url.startswith('https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/'),
             'unexpected source URL')
        return '<a href="'+esc(url)+'">'+esc(row['source_id'])+'</a>'
    rows=''.join('<li>'+source_link(row)+' · row group '+esc(row['row_group'])+
                 ', row '+esc(row['row_in_group'])+'</li>' for row in model['rows'])
    missing=''.join('<li>'+esc(key)+': '+esc(value)+'</li>' for key,value in model['missingness'].items())
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">'
        '<title>TETHER · IL6R / rheumatoid arthritis</title><style>'
        'body{font:17px/1.65 system-ui,sans-serif;max-width:900px;margin:3rem auto;padding:0 1.5rem;color:#183047;background:#fbfcfe}'
        'h1,h2{line-height:1.2}h2{margin-top:2rem}table{border-collapse:collapse;width:100%}'
        'th,td{padding:.6rem;border-bottom:1px solid #dce3ed;text-align:left;vertical-align:top;overflow-wrap:anywhere}'
        '.notice{padding:1rem;border-left:5px solid #176b9d;background:#eaf5fb}.small{font-size:.9rem;color:#456}'
        '</style><main><p class="small">TETHER · source-linked example</p><h1>IL6R &amp; rheumatoid arthritis</h1>'
        '<p class="notice">Proposed hypothesis: inhibit IL6R with an antibody; tissue unspecified. '
        'This example does not establish therapeutic benefit. Clinical probability is withheld.</p>'
        '<h2>What this source reports</h2><p>'+esc(model['statement'])+'</p><table>'+facts+'</table>'
        '<h2>What remains unknown</h2><p>One selected annotation is not a complete review. '
        'Other specialist sources were not collected here. Missing inputs do not mean biological absence; '
        'conflicts are not established or excluded.</p><ul>'+missing+'</ul>'
        '<h2>Where the facts came from</h2><ul>'+rows+'</ul>'
        '<p>Release: Open Targets 25.09. The reported publication date is separate from the later verified '
        'download availability bound. Source metrics are descriptive, not validated prediction features.</p>'
        '<p class="small">See reading-view.json for exact source URLs, original hashes and locators; '
        'audit.json records the machine checks. Native dossier and receipts remain unchanged. '
        'No article interpretation, causal effect or scientific truth is certified.</p></main></html>')


def audit(inputs, run_dir, receipt_sha256, engine_receipt_sha256, output):
    import pyarrow
    import pyarrow.parquet as pq
    need(pyarrow.__version__=='21.0.0','requires pyarrow==21.0.0')
    inputs,run_dir,output=(Path(p).absolute() for p in (inputs,run_dir,output))
    checked_path(output.parent.parent,output.parent.name)
    deadline=time.monotonic()+300
    started=time.monotonic()
    verification=verify_run(RunArtifacts(run_dir,receipt_sha256,engine_receipt_sha256),source_roots=(inputs,))
    need(verification['artifact_policy']['status']=='artifact_policy_consistency_verified','policy verification unavailable')
    def read(path):
        return json.loads(read_file(path,deadline,32*1024*1024))
    pinned_bytes=read_file(Path(__file__).with_name('il6r_ot2509.json').absolute(),deadline,1024*1024)
    need(hashlib.sha256(pinned_bytes).hexdigest()=='c2b58694416c3d355cff63d07ea30246051dd1948edffbae36f3304fe68cd0f4','pinned manifest changed')
    pinned=json.loads(pinned_bytes)
    rows=[]
    for source in pinned['sources']:
        original=read_file(inputs/'raw'/source['relative_path'],deadline,32*1024*1024)
        need(hashlib.sha256(original).hexdigest()==source['sha256'],'original hash changed')
        parquet=pq.ParquetFile(io.BytesIO(original))
        for row in pinned['rows']:
            if row['source_id']!=source['source_id']:
                continue
            offset=sum(parquet.metadata.row_group(i).num_rows for i in range(row['row_group']))+row['row_in_group']
            need(offset==row['physical_row'],'locator differs')
            value=parquet.read_row_group(row['row_group'],columns=source['projected_columns']).slice(row['row_in_group'],1).to_pylist()[0]
            need(value==row['values'],'row projection differs')
            rows.append(dict(**row,source_url=source['source_url'],original_sha256=source['sha256']))
    ledger=read(run_dir/'engine/ledger.json')
    need(len(ledger['claims'])==1,'expected exactly one selected annotation')
    observation=ledger['claims'][0]['evidence']['observation']
    source_values=pinned['rows'][0]['values']
    expected_statement=('Open Targets 25.09 reports one genetic-association annotation linking '
        +pinned['rows'][1]['values']['approvedSymbol']+' ('+source_values['targetId']+') and '
        +pinned['rows'][2]['values']['name']+' ('+source_values['diseaseId']+') in the selected shard. '
        'Therapeutic relevance is not assessed.')
    need(observation['statement']==expected_statement,'statement differs from the qualified source-only template')
    need(observation['publication_date']==source_values['publicationDate'],'publication date differs')
    need(observation['source_metrics']==source_values,'claim metadata differs from original row')
    need(observation['source_locator']=={k:pinned['rows'][0][k] for k in ('source_id','row_group','row_in_group','physical_row')},'claim locator differs')
    case=read(inputs/'case.json')
    hypothesis=case['hypothesis']
    need(hypothesis['target_id']==source_values['targetId'] and hypothesis['indication_id']==source_values['diseaseId'],'hypothesis identity differs')
    need(hypothesis['intended_action']=='inhibit' and hypothesis['modality']=='antibody' and hypothesis['tissue'] is None,'hypothesis context differs')
    need(observation['features']=={},'unvalidated numerical feature present')
    features=read(run_dir/'engine/features.json')
    need(all(row['value'] is None for row in features['values'].values()),'numerical features not withheld')
    prediction=read(run_dir/'engine/prediction.json')
    need(prediction['probability'] is None and prediction['status']=='audit_only','clinical prediction present')
    need(observation['mechanism_direction']=='uncertain' and observation['polarity']=='uncertain','unqualified direction asserted')
    need(all(value is None or value==[] for value in observation['context'].values()),'unreported biological context inferred')
    for key,value in source_values.items():
        if value is None:
            need(observation['missingness'].get(key)=='Source value is null','missingness differs from source')
    record=read(run_dir/'engine/run.json')
    need(record['calls']==1 and record['usage']['cost_usd']==0,'unexpected calls or spending')
    model=dict(schema_version=1,statement=observation['statement'],
        facts={'Target':pinned['rows'][1]['values']['approvedSymbol']+' / '+source_values['targetId'],
               'Indication':pinned['rows'][2]['values']['name']+' / '+source_values['diseaseId'],
               'Reported evidence type':source_values['datatypeId'],'Provider score (descriptive)':source_values['score'],
               'Source-reported PMID':', '.join(source_values['literature']),
               'Source-reported publication date':source_values['publicationDate']},
        rows=rows,missingness=observation['missingness'],hypothesis=hypothesis,
        clinical_probability=None,scientific_validation='not_established',
        source_selection='One fixed annotation plus two identifier rows; no exhaustive coverage',
        native_receipt_sha256=engine_receipt_sha256,outer_receipt_sha256=receipt_sha256)
    # Reserve only after checks; a validation failure does not create a success artifact.
    journal=RunJournal(output,kind='build')
    try:
        payloads={'reading-view.json':(json.dumps(model,indent=2,ensure_ascii=False)+'\n').encode(),
                  'reading-view.html':render(model).encode()}
        for name,payload in payloads.items():
            (output/name).write_bytes(payload)
        report=dict(status='passed',exact_original_rows=3,selected_claims=1,numerical_features='withheld',
            clinical_probability=None,elapsed_seconds=time.monotonic()-started,
            source_projection_replay='independent_original_row_group_check',scientific_validation='not_established',
            artifacts={name:hashlib.sha256(payload).hexdigest() for name,payload in payloads.items()})
        journal.append('build_completed',**report)
        (output/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        return report
    except BaseException as error:
        journal.fail(error,'reading_view')
        raise
    finally:
        journal.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','run-dir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('receipt-sha256','engine-receipt-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.inputs,args.run_dir,args.receipt_sha256,args.engine_receipt_sha256,args.output),indent=2))
