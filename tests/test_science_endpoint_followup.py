"""Retained execution verification without database, network or credentials."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError,read_json,write_json,sha256_file
from tools.science.endpoint_followup import join_snapshot,verify_extraction,ROOT
from tools.science.outcome_inputs import validate_study_rows
from tools.science.outcome_results import validate_result_rows
from tests import test_science_endpoint_followup_peer as fixture


class EndpointExecutionTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixture.EndpointFollowupPeerTests();self.helper.setUp()

    def make_output(self,root,change=None):
        out=root/'output';journal=RunJournal(out,kind='build')
        plan=self.helper.plan(root);plan['parents']=[]
        code=['tools/science/outcome_extract.py','tools/science/endpoint_followup.py','tools/science/outcome_inputs.py',
            'tools/science/outcome_results.py','tools/science/ascertainment_policy.py','tools/science/origin_programs.py',
            'tools/science/reference_panel.py','src/tether_engine/serde.py','src/tether_engine/journal.py']
        plan['executed_code']=[{'path':str(ROOT/n),'sha256':sha256_file(ROOT/n)} for n in code]
        archives=[]
        for source in plan['executed_code']:
            path=Path(source['path']);archived=out/'executed-code'/path.relative_to(ROOT)
            archived.parent.mkdir(parents=True,exist_ok=True);archived.write_bytes(path.read_bytes())
            archives.append({'source':source,'archive_path':str(archived),'sha256':source['sha256']})
        write_json(out/'executed-code-proofs.json',archives)
        (out/'executed-runner.py').write_bytes((ROOT/'tools/science/outcome_extract.py').read_bytes())
        snapshots=[]
        for job in plan['jobs']:
            day=job['snapshot_date'];job['restore_root']=str(root/('restore-'+day))
            folder=out/day;folder.mkdir();studies,results,sq,rq=self.helper.rows(day)
            meta={'database':'aact_snapshot','read_only':'on','studies':job['expected_studies'],
                'directory':str(Path(job['restore_root'])/'pgdata'),'port':str(job['port'])}
            if change=='database':meta['database']='other'
            if change=='writable':meta['read_only']='off'
            write_json(folder/'metadata.stdout.log',meta)
            life={'ownership_acquired':True,'server_stopped':True,'port':job['port'],'automatic_retry':False}
            if change=='port':life['port']+=1
            if change=='retry':life['automatic_retry']=True
            write_json(folder/'lifecycle.json',life);queries=[]
            for name,rows,request in [('studies',studies,sq),('results',results,rq)]:
                first=folder/(name+'-first.stdout.log');repeat=folder/(name+'-repeat.stdout.log')
                first.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8');repeat.write_bytes(first.read_bytes())
                validation=(validate_study_rows(rows,request) if name=='studies' else validate_result_rows(rows,request))
                if change=='validation':validation['clinical_label']=1
                write_json(folder/(name+'-validation.json'),validation)
                queries.append({'name':name,'path':str(first),'sha256':sha256_file(first),'bytes':first.stat().st_size,'repeat_identical':True})
            snapshots.append({'snapshot_date':day,'queries':queries,'metadata':meta})
        write_json(out/'effective-plan.json',plan)
        report={'status':'source_reads_complete_pending_scientific_validation','role':'evaluation_only',
            'phase':'endpoint_followup','protocol_sha256':sha256_file(out/'effective-plan.json'),
            'provider_spend_usd':0,'clinical_labels_assigned':0,'clinical_activation':False,'snapshots':snapshots}
        if change=='role':report['role']='agent_evidence'
        if change=='spend':report['provider_spend_usd']=1
        write_json(out/'report.json',report);journal.append('build_completed',report_sha256=sha256_file(out/'report.json'));journal.close()
        return out,sha256_file(out/'effective-plan.json'),sha256_file(out/'report.json')

    def verify(self,*args):
        with patch('tools.science.endpoint_followup.validate_endpoint_binding'):
            return verify_extraction(*args)

    def test_complete_retained_empty_results_are_context_not_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.make_output(Path(tmp));joined=self.verify(*args)
            self.assertEqual(2,len(joined))
            self.assertTrue(all(m['clinical_label'] is None and m['absence_claim'] is False
                for snapshot in joined for m in snapshot['members']))

    def test_coherent_report_cannot_bless_wrong_identity_or_saved_validation(self):
        for change in ('database','writable','port','retry','validation','role','spend'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                args=self.make_output(Path(tmp),change)
                with self.assertRaises(ContractError):self.verify(*args)

    def test_changed_repeat_and_archived_code_are_rejected(self):
        for change in ('repeat','code','report','plan'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                args=self.make_output(Path(tmp));out=args[0]
                path={'repeat':out/'2026-01-01/results-repeat.stdout.log',
                    'code':out/'executed-code/tools/science/endpoint_followup.py','report':out/'report.json',
                    'plan':out/'effective-plan.json'}[change]
                path.write_bytes(path.read_bytes()+b' ')
                with self.assertRaises(ContractError):self.verify(*args)

    def test_mutation_during_reconstruction_fails_final_input_recheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.make_output(Path(tmp));original=join_snapshot;calls=0
            def mutate(*rows):
                nonlocal calls
                result=original(*rows);calls+=1
                if calls==2:
                    path=args[0]/'2026-01-01/studies-first.stdout.log';path.write_bytes(path.read_bytes()+b' ')
                return result
            with patch('tools.science.endpoint_followup.join_snapshot',side_effect=mutate):
                with self.assertRaises(ContractError):self.verify(*args)


if __name__=='__main__':unittest.main()
