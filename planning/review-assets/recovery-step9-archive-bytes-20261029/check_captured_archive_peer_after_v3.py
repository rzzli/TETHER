"""Independent probes of new synthetic bytes only; no original archive replay."""
import copy
from dataclasses import replace
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'captured_archive_v3.py'
PROOF=HERE/'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-AFTER-PROBES-v3.json'


def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')+b'\n'
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=digest(raw))


def main():
    assert not PROOF.exists()
    original=pin(SOURCE)
    spec=importlib.util.spec_from_file_location('captured_archive_independent_after_v3',SOURCE)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    roster=json.loads((HERE/'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json').read_text(encoding='utf-8'))['cases']
    by={case['id']:case for case in roster};observations=[];probes=[]
    def convert(case):
        c=case['captured'];b=case['bindings'];p=lambda row:m.MetadataPin(**row)
        archive=m.CapturedArchive(bytes.fromhex(c['protocol_hex']),bytes.fromhex(c['authority_hex']),tuple((row['locator'],bytes.fromhex(row['raw_hex'])) for row in c['run_files']))
        binding=m.ArchiveBindings(b['policy_id'],b['run_root'],p(b['protocol_pin']),p(b['authority_pin']),p(b['helper_pin']),tuple(map(p,b['static_software_pins'])),tuple(m.DynamicPin(row['role'],p(row['pin'])) for row in b['dynamic_pins']),tuple(map(p,b['payload_descriptors'])))
        return archive,binding
    base,binding=convert(by['complete_positive_captured_graph'])
    def rebind(files,b):
        # Rebind only known synthetic late metadata after a deliberately altered
        # early leaf. Does not constitute a general archive-validation routine.
        files=dict(files)
        def short(raw):return dict(bytes=len(raw),sha256=digest(raw))
        def full(name):return dict(path=b.run_root+'\\'+name.replace('/','\\'),**short(files[name]))
        receipt=json.loads(files['receipt.json']);receipt['outputs']={name:short(files[name]) for name in receipt['outputs']};files['receipt.json']=encoded(receipt)
        cleanup=json.loads(files['post-lease-cleanup.json']);cleanup['earlier_receipt']=full('receipt.json');files['post-lease-cleanup.json']=encoded(cleanup)
        seal=json.loads(files['terminal-seal.json']);seal['earlier_receipt']=full('receipt.json');seal['cleanup_artifact']=full('post-lease-cleanup.json');seal['outputs']={name:short(files[name]) for name in seal['outputs']};files['terminal-seal.json']=encoded(seal)
        return replace(base,run_files=tuple(files.items()))
    def observed(identity,c,b=binding):
        try:
            result=m.check_archive(c,b,check=lambda:None).to_dict()
            row=dict(id=identity,result=result)
        except BaseException as error:
            row=dict(id=identity,exception_class=type(error).__name__,error=str(error)[:512])
        probes.append(row);return row

    class Checks(unittest.TestCase):
        def test_frozen32_projections_remain_observational(self):
            for case in roster:
                result=m.check_archive(*convert(case),check=lambda:None).to_dict()
                for key,value in case['expected_projection'].items():self.assertIs(type(result[key]),type(value));self.assertEqual(result[key],value)
            observations.append(dict(id='all32_authored_projection_comparisons',passed=True))

        def test_source_already_closed_lease_has_null_close_success(self):
            files=dict(base.run_files);cleanup=json.loads(files['post-lease-cleanup.json'])
            cleanup['outcomes'][0].update(closed_before=True,close_attempted=False,close_return_observed=False,close_success=None,close_error=None,closed_after=True)
            files['post-lease-cleanup.json']=encoded(cleanup)
            row=observed('already_closed_source_null_success',rebind(files,binding))
            self.assertIn('result',row)
            self.assertEqual(row['result']['captured_graph_status'],'consistent_captured_graph')
            self.assertEqual(row['result']['source_terminal_disposition'],'source_positive_observations_pending')

        def test_bounded_invalid_large_integer_is_not_uncaught_numeric_conversion(self):
            files=dict(base.run_files);config=json.loads(base.protocol_bytes);config['periodic_job_seconds']=10**1000
            raw=encoded(config);new_pin=replace(binding.protocol_pin,bytes=len(raw),sha256=digest(raw));b=replace(binding,protocol_pin=new_pin)
            files['effective-protocol.json']=raw
            journal=[json.loads(row) for row in files['execution/journal.jsonl'].splitlines()]
            journal[1]['details']['protocol_sha256']=digest(raw)
            journal[1]['sha256']=digest(encoded({k:v for k,v in journal[1].items() if k!='sha256'})[:-1])
            files['execution/journal.jsonl']=b''.join(encoded(row) for row in journal)
            receipt=json.loads(files['receipt.json']);receipt['protocol_sha256']=digest(raw);files['receipt.json']=encoded(receipt)
            c=replace(rebind(files,b),protocol_bytes=raw)
            row=observed('bounded_large_integer_periodic_interval',c,b)
            self.assertIn('result',row)
            self.assertEqual(row['result']['captured_graph_status'],'inconsistent_captured_graph')

        def test_fully_rebound_malformed_marker_still_vetoes_by_filename(self):
            files=dict(base.run_files);files['failure.json']=b'{"authoritative":false,"authoritative":true}\n'
            seal=json.loads(files['terminal-seal.json']);seal['outputs']['failure.json']=dict(bytes=len(files['failure.json']),sha256=digest(files['failure.json']));files['terminal-seal.json']=encoded(seal)
            row=observed('malformed_known_marker',rebind(files,binding))['result']
            self.assertEqual(row['captured_graph_status'],'inconsistent_captured_graph');self.assertEqual(row['source_terminal_disposition'],'source_negative');self.assertIn('failure.json',row['failure_vetoes'])

        def test_callback_identity_from_JSON_data_catch_and_final_freeze(self):
            markers=[ValueError('synthetic'),UnicodeError('synthetic'),UnicodeDecodeError('utf-8',b'\xff',0,1,'synthetic'),RecursionError('synthetic'),RuntimeError('synthetic'),KeyboardInterrupt('synthetic'),SystemExit('synthetic'),m._Bad('synthetic')]
            for marker in markers:
                fired=[False];actual=None
                def check():
                    frame=sys._getframe(2)
                    if not fired[0] and frame.f_code.co_name=='json' and 'value' in frame.f_locals:
                        fired[0]=True;raise marker
                try:m.check_archive(base,binding,check=check)
                except BaseException as error:actual=error
                self.assertTrue(fired[0]);self.assertIs(actual,marker)
            total=[0]
            def count():total[0]+=1
            m.check_archive(base,binding,check=count)
            for target in (1,total[0]//2,total[0]):
                marker=UnicodeError('synthetic late stop');calls=[0]
                def stop():
                    calls[0]+=1
                    if calls[0]==target:raise marker
                try:m.check_archive(base,binding,check=stop)
                except BaseException as error:self.assertIs(error,marker)
                else:self.fail('Callback converted to summary')
            observations.append(dict(id='eleven_callback_identity_probes',passed=True))

        def test_returned_summary_deep_detachment_and_early_absence(self):
            result=m.check_archive(base,binding,check=lambda:None)
            first=result.to_dict();first['node_digests']['receipt.json']['bytes']=0;first['failure_vetoes'].append('synthetic')
            second=result.to_dict();self.assertNotEqual(second['node_digests']['receipt.json']['bytes'],0);self.assertNotIn('synthetic',second['failure_vetoes'])
            for key in ('profile_qualified','source_qualified','originals_authenticated','actual_directory_complete','complete_journal_chain_validated','resource_or_profile_semantics_validated','owner_context_provenance_established'):self.assertIs(second[key],False)
            early,eb=convert(by['early_initialization']);row=m.check_archive(early,eb,check=lambda:None).to_dict()
            self.assertEqual(row['captured_graph_status'],'incomplete_captured_graph');self.assertEqual(row['source_terminal_disposition'],'source_negative')
            self.assertIn('execution/journal.jsonl',row['missing_nodes'])
            observations.append(dict(id='immutable_return_and_early_unknowns',passed=True))

        def test_relative_and_DAG_guard_controls(self):
            for name in ('journal.jsonl','../receipt.json','RECEIPT.JSON','D:/outside','execution\\child\\attempt.json'):
                c=replace(base,run_files=base.run_files+((name,b''),));row=m.check_archive(c,binding,check=lambda:None).to_dict()
                self.assertEqual(row['captured_graph_status'],'inconsistent_captured_graph')
            for identity in ('terminal_self_edge','receipt_future_edge','cross_root_pin','static_dynamic_collision','exception_after_terminal'):
                c,b=convert(by[identity]);row=m.check_archive(c,b,check=lambda:None).to_dict()
                self.assertNotEqual(row['source_terminal_disposition'],'source_positive_observations_pending')
            observations.append(dict(id='ten_locator_DAG_role_and_late_controls',passed=True))

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    record=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='HOLD_CONCRETE_SOURCE_AND_NUMERIC_BOUNDARIES' if result.failures or result.errors else 'passed',source=original,checker=pin(Path(__file__)),
                fixture=pin(HERE/'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json'),contract=pin(HERE/'CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json'),methods=result.testsRun,
                failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],probes=probes,controls=observations,
                source_unchanged=pin(SOURCE)==original,scope='New synthetic byte captures only. Baseline32 and independent branch controls; no actual old archive replay, live file or resource/profile authority.',
                profile_qualified=False,originals_authenticated=False,actual_directory_complete=False,source_qualified=False,SDK_native_payload_operations=0,old_archive_replays=0)
    with PROOF.open('x',encoding='utf-8') as out:json.dump(record,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),status=record['status'],methods=result.testsRun,failures=len(result.failures),errors=len(result.errors))))


if __name__=='__main__':main()
