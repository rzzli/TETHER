import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tether_engine.serde import ContractError
from tools.science.registry_documents import select_document,verify_document
from tools.science.source_retrieval import registry_document_refs,fetch_control
from tests.test_science_source_retrieval_peer import FakeResponse


class RegistryDocumentTests(unittest.TestCase):
    nct='NCT01234001'
    filename='Prot_SAP_002.pdf'
    def fixture(self,root):
        body=b'%PDF-1.7\nProtocol fixture'
        source={'protocolSection':{'identificationModule':{'nctId':self.nct}},
         'resultsSection':{'later_outcomes':'DO_NOT_PROJECT'},'documentSection':{'largeDocumentModule':{'largeDocs':[
         {'filename':self.filename,'hasProtocol':True,'hasSap':True,'hasIcf':False,'size':len(body),
          'date':'2024-03-22','uploadDate':'2026-02-12T16:07'}]}}}
        raw=root/'api.json';raw.write_text(json.dumps(source),encoding='utf-8')
        api_url='https://clinicaltrials.gov/api/v2/studies/'+self.nct
        receipt={'nct_id':self.nct,'http_status':200,'requested_url':api_url,'response_url':api_url,
         'body':{'path':str(raw),'sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'bytes':raw.stat().st_size}}
        inspection={'registry_receipt':receipt,'projection':registry_document_refs(self.nct,source)}
        path=root/'inspection.json';path.write_text(json.dumps(inspection),encoding='utf-8')
        return path,hashlib.sha256(path.read_bytes()).hexdigest(),body
    def downloaded(self,root):
        path,digest,body=self.fixture(root);request=select_document(path,self.filename,digest,root)
        control={'nct_id':self.nct,'url':request['url'],'allowed_hosts':['cdn.clinicaltrials.gov'],
         'expected_sha256':None,'expected_format':'pdf','max_bytes':16777216}
        out=root/'download';fetch_control(control,out,open_response=lambda _:FakeResponse(body,url=request['url']))
        return request,out

    def test_exact_version_is_selected_without_later_outcome_or_historical_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,digest,_=self.fixture(Path(tmp));request=select_document(path,self.filename,digest,Path(tmp))
            self.assertFalse(request['historical_availability_qualified']);self.assertFalse(request['prospective_authenticity_qualified'])
            self.assertNotIn('later_outcomes',json.dumps(request))
            with self.assertRaises(ContractError):select_document(path,'Prot_SAP_003.pdf',digest,Path(tmp))

    def test_changed_registry_body_or_inspection_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,digest,_=self.fixture(root)
            path.write_text('{}',encoding='utf-8')
            with self.assertRaises(ContractError):select_document(path,self.filename,digest,root)
            path,digest,_=self.fixture(root);(root/'api.json').write_text('{}',encoding='utf-8')
            with self.assertRaises(ContractError):select_document(path,self.filename,digest,root)

    def test_projection_drift_and_consent_substitution_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,digest,_=self.fixture(root);d=json.loads(path.read_text())
            d['projection']['document_refs'][0]['filename']='ICF_003.pdf';path.write_text(json.dumps(d))
            with self.assertRaises(ContractError):select_document(path,self.filename,hashlib.sha256(path.read_bytes()).hexdigest(),root)
            path,digest,_=self.fixture(root);source=json.loads((root/'api.json').read_text())
            source['documentSection']['largeDocumentModule']['largeDocs'][0].update(hasProtocol=False,hasSap=False,hasIcf=True)
            raw=root/'api.json';raw.write_text(json.dumps(source));d=json.loads(path.read_text())
            d['registry_receipt']['body'].update(sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),bytes=raw.stat().st_size)
            d['projection']=registry_document_refs(self.nct,source);path.write_text(json.dumps(d))
            with self.assertRaises(ContractError):select_document(path,self.filename,hashlib.sha256(path.read_bytes()).hexdigest(),root)

    def test_new_source_bytes_seal_without_requiring_a_known_prior_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request,out=self.downloaded(root);result=verify_document(request,out,root)
            self.assertEqual('source_linked_original_received',result['status'])
            self.assertFalse(result['historical_availability_qualified']);self.assertFalse(result['clinical_label_contribution'])

    def test_request_size_body_and_final_version_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request,out=self.downloaded(root)
            forged=copy.deepcopy(request);forged['expected_bytes']+=1
            with self.assertRaises(ContractError):verify_document(forged,out,root)
            p=out/'receipt.json';original_receipt=p.read_bytes();receipt=json.loads(original_receipt);receipt['response_url']=request['url'].replace('_002','_003')
            p.write_text(json.dumps(receipt))
            with self.assertRaises(ContractError):verify_document(request,out,root)
            p.write_bytes(original_receipt)
            (out/'body.original').write_bytes(b'%PDF-changed')
            with self.assertRaises(ContractError):verify_document(request,out,root)

    def test_external_source_path_is_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,digest,_=self.fixture(root);allowed=root/'approved';allowed.mkdir()
            with self.assertRaises(ContractError):select_document(path,self.filename,digest,allowed)


if __name__=='__main__':unittest.main()
