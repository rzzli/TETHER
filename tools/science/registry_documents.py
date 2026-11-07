"""Exact-version evaluator-only document retrieval from a retained registry listing."""
from pathlib import Path
import hashlib
from tether_engine.serde import ContractError,read_json,sha256_file,parse_json
from tether_engine.journal import read_chain
from tools.science.source_retrieval import registry_document_refs


def require(condition,message):
    if not condition:raise ContractError(message)


def contained(path,root):
    path=Path(path).resolve();root=Path(root).resolve()
    require(path.is_relative_to(root) and path.is_file(),'Source outside approved local root')
    return path


def select_document(inspection_path,filename,inspection_sha256,approved_root):
    inspection_path=contained(inspection_path,approved_root)
    require(sha256_file(inspection_path)==inspection_sha256,'Registry inspection changed')
    inspection=read_json(inspection_path);receipt=inspection['registry_receipt']
    require(receipt.get('http_status')==200,'Successful retained registry response required')
    api_url='https://clinicaltrials.gov/api/v2/studies/'+receipt['nct_id']
    require(receipt.get('requested_url')==receipt.get('response_url')==api_url,'Registry resource URL differs from requested trial')
    source=contained(receipt['body']['path'],approved_root)
    require(sha256_file(source)==receipt['body']['sha256'] and source.stat().st_size==receipt['body']['bytes'],
        'Original registry body differs from receipt')
    projection=registry_document_refs(receipt['nct_id'],read_json(source))
    require(projection==inspection['projection'],'Document projection differs from original registry bytes')
    selected=[r for r in projection['document_refs'] if r['filename']==filename]
    require(len(selected)==1,'Exact requested document version is not listed; no automatic replacement')
    ref=selected[0]
    require(ref['has_protocol'] is True and ref['has_sap'] is True and ref['has_icf'] is False,
        'Requested combined protocol/SAP flags are not satisfied')
    require(type(ref['reported_bytes']) is int and 0<ref['reported_bytes']<=16*1024*1024,'Explicit selected document size required')
    return {'schema_version':1,'role':'evaluation_only','nct_id':ref['nct_id'],'filename':filename,'url':ref['url'],
        'expected_bytes':ref['reported_bytes'],'reported_document_date':ref['source_reported_date'],
        'reported_upload_date':ref['source_reported_upload_date'],'document_ref_pointer':ref['source_json_pointer'],
        'inspection':{'path':str(inspection_path),'sha256':inspection_sha256},'api_body':dict(receipt['body']),
        'temporal_classification':'contemporary_only','historical_availability_qualified':False,
        'prospective_authenticity_qualified':False,'clinical_label_contribution':False,
        'automatic_version_replacement':False,'expected_sha256':None}


def verify_document(request,output,approved_root):
    """Verify transport/lineage only, never infer authenticity from upload dates."""
    current=select_document(request['inspection']['path'],request['filename'],request['inspection']['sha256'],approved_root)
    require(current==request,'Selected document request differs from frozen source projection')
    output=Path(output).resolve()
    require((output/'journal.jsonl').is_file(),'Retained transport journal required')
    events=read_chain(output/'journal.jsonl')
    require(events[0]['event']=='build_reserved' and events[-1]['event']=='build_completed','Transport did not reach sealed completion')
    receipt_bytes=(output/'receipt.json').read_bytes();control_bytes=(output/'control.json').read_bytes()
    require(hashlib.sha256(receipt_bytes).hexdigest()==events[-1]['details'].get('receipt_sha256'),
        'Transport receipt differs from committed journal')
    receipt=parse_json(receipt_bytes);control=parse_json(control_bytes)
    require(receipt['nct_id']==control['nct_id']==request['nct_id'],'Downloaded trial differs from selected trial')
    require(receipt['requested_url']==control['url']==request['url'],'Downloaded URL differs from selected version')
    require(receipt.get('response_url')==request['url'],'Final PDF URL differs from selected version')
    require(control.get('allowed_hosts')==['cdn.clinicaltrials.gov'],'Unexpected selected-document host policy')
    require(control.get('expected_sha256') is None and control.get('expected_format')=='pdf' and
        type(control.get('max_bytes')) is int and control['max_bytes']==16*1024*1024 and
        type(control.get('max_elapsed_seconds',120)) is int and control.get('max_elapsed_seconds',120)==120 and
        type(control.get('request_timeout_seconds',40)) is int and control.get('request_timeout_seconds',40)==40,
        'Download recipe differs from frozen new-source policy')
    require(hashlib.sha256(control_bytes).hexdigest()==receipt['control_sha256'],'Download control changed')
    require(receipt['http_status']==200 and receipt['pdf_signature_matches'] is True,'Original PDF transport failed')
    path=contained(receipt['body']['path'],output)
    require(path.stat().st_size==receipt['body']['bytes']==request['expected_bytes'],'Selected PDF size differs from registry listing')
    require(sha256_file(path)==receipt['body']['sha256'],'Downloaded PDF differs from receipt')
    with path.open('rb') as stream:require(stream.read(5)==b'%PDF-','Invalid original PDF signature')
    return {'status':'source_linked_original_received','role':'evaluation_only','nct_id':request['nct_id'],
        'filename':request['filename'],'body':dict(receipt['body']),'source_inspection':dict(request['inspection']),
        'identity_basis':'Exact selected registry document reference, URL and reported size; new body SHA sealed on retrieval',
        'historical_availability_qualified':False,'prospective_authenticity_qualified':False,
        'clinical_scope_qualified':False,'clinical_label_contribution':False,'automatic_version_replacement':False}
