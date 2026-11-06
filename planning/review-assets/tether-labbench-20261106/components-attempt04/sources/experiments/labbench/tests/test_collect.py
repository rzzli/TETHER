from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from uuid import UUID

from asof.serde import ContractError,canonical,parse_json,fingerprint
from experiments.labbench import collect as c
from experiments.labbench import retrieval as r


def query_fixture(root,count=3):
    rows=[{"id":str(UUID(int=index+1)),"question":f"Which fictional chlorophyll protein {index} uses sunlight?",
           "choices":["(A) Fictional green","(B) Insufficient information to answer the question","(C) Fictional blue"]} for index in range(count)]
    path=root/"query-only.json";raw=canonical(rows)+b"\n";path.write_bytes(raw)
    return path,c._sha(raw),rows


def fictional_fetch(url,**kwargs):
    if '/search?' in url:
        body=canonical({"resultList":{"result":[{"pmcid":"PMC321","title":"Fictional study","doi":"10.000/fake",
              "isOpenAccess":"Y","license":"cc by","firstPublicationDate":"2020-01-01"}]}})
    else:
        body=b'<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmc">321</article-id><permissions><license><ext-link xlink:href="https://creativecommons.org/licenses/by/4.0/">CCBY</ext-link></license></permissions></article-meta></front><body><p>Fictional chlorophyll protein uses sunlight.</p></body></article>'
    return {"status":200,"body":body,"final_url":url,"headers":{}}


class CollectionTests(unittest.TestCase):
    def test_full_fictional_collection_uses_only_task_projection_and_seals_cutoff(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,queries=query_fixture(base)
            with patch.object(r,'fetch_http',side_effect=fictional_fetch) as fetch:
                manifest=c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
            self.assertEqual(fetch.call_count,9)
            self.assertEqual(manifest['schedule'],tuple(q['id'] for q in queries))
            self.assertEqual(manifest['totals']['counts']['completed'],3)
            self.assertEqual(manifest['totals']['cases_with_sources'],3)
            self.assertTrue((base/'out/COMPLETE.json').exists())
            verified=c.verify_collection(base/'out',c._sha((base/'out/manifest.json').read_bytes()))
            self.assertEqual(verified,manifest)
            for case in manifest['cases']:
                source=parse_json((base/'out'/case['task_sources']['path']).read_bytes())
                self.assertEqual(set(source[0]),{'source_id','sha256','text'})
                self.assertLessEqual(case['sealed_at_utc'],manifest['cutoff'])
            with self.assertRaises(TypeError):manifest['cases'][0]['status']='changed'

    def test_no_source_is_completed_missingness_not_biological_absence(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,_=query_fixture(base,1)
            def empty(url,**kwargs):return {'status':200,'body':b'{"resultList":{"result":[]}}','final_url':url,'headers':{}}
            with patch.object(r,'fetch_http',side_effect=empty):manifest=c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
            self.assertEqual(manifest['status'],'completed')
            self.assertEqual(manifest['totals']['completed_without_sources'],1)
            self.assertFalse(manifest['cases'][0]['coverage']['absence_of_evidence_claim'])
            self.assertEqual(c.verify_collection(base/'out',c._sha((base/'out/manifest.json').read_bytes())),manifest)

    def test_fatal_case_preserves_all_remaining_ids_and_disallows_default_consumption(self):
        for error,state in ((RuntimeError('fictional'),'failed'),(KeyboardInterrupt(),'interrupted')):
            with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
                base=Path(temp);path,sha,queries=query_fixture(base)
                with patch.object(r,'retrieve',side_effect=error) as retrieve:
                    manifest=c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
                self.assertEqual(retrieve.call_count,1)
                self.assertEqual([x['status'] for x in manifest['cases']],[state,'unexecuted','unexecuted'])
                self.assertEqual(manifest['status'],'partial')
                self.assertFalse((base/'out/COMPLETE.json').exists())
                self.assertTrue((base/'out/PARTIAL.json').exists())
                proof=c._sha((base/'out/manifest.json').read_bytes())
                with self.assertRaises(ContractError):c.verify_collection(base/'out',proof)
                self.assertEqual(c.verify_collection(base/'out',proof,allow_partial=True),manifest)
                self.assertEqual(manifest['totals']['unknown_transfer_upper_bytes'],r.DEFAULT_POLICY['total_bytes'])

    def test_deadline_after_one_case_prevents_later_dispatch_and_records_every_id(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,_=query_fixture(base)
            real_retrieve=r.retrieve;clock=[time.monotonic()]
            def overrun(*args,**kwargs):
                result=real_retrieve(*args,**kwargs);clock[0]+=100;return result
            with patch.object(c,'_now',side_effect=lambda:clock[0]),patch.object(r,'fetch_http',side_effect=fictional_fetch),patch.object(r,'retrieve',side_effect=overrun) as retrieve:
                manifest=c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
            self.assertEqual(retrieve.call_count,1)
            self.assertEqual([x['status'] for x in manifest['cases']],['failed','unexecuted','unexecuted'])
            self.assertEqual(manifest['cases'][0]['reason'],'stage_deadline_during_case')
            self.assertIsNotNone(manifest['cases'][0]['retrieval'])
            self.assertIsNone(manifest['cases'][0]['task_sources'])
            self.assertEqual(c.verify_collection(base/'out',c._sha((base/'out/manifest.json').read_bytes()),allow_partial=True),manifest)

    def test_remaining_budget_is_recomputed_after_durable_reservation(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,_=query_fixture(base,1)
            clock=[time.monotonic()];real_append=c.RunJournal.append
            def delayed(journal,event,**details):
                result=real_append(journal,event,**details)
                if event=='collection_case_reserved':clock[0]+=6
                return result
            real_retrieve=r.retrieve
            def checked(*args,**kwargs):
                self.assertEqual(kwargs['policy']['question_seconds'],4)
                self.assertEqual(kwargs['policy']['request_seconds'],4)
                return real_retrieve(*args,**kwargs)
            with patch.object(c,'_now',side_effect=lambda:clock[0]),patch.object(c.RunJournal,'append',new=delayed),patch.object(r,'retrieve',side_effect=checked),patch.object(r,'fetch_http',side_effect=fictional_fetch):
                result=c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=10)
            self.assertEqual(result['status'],'completed')

    def test_mutated_source_or_query_and_extra_evaluator_fields_fail(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,rows=query_fixture(base,1)
            with patch.object(r,'fetch_http',side_effect=fictional_fetch):c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
            proof=c._sha((base/'out/manifest.json').read_bytes())
            (base/'out/queries.json').write_bytes(b'[]')
            with self.assertRaises(ContractError):c.verify_collection(base/'out',proof)
            rows[0]['ideal']='hidden';payload=canonical(rows);path.write_bytes(payload)
            with patch.object(r,'retrieve') as retrieve:
                with self.assertRaises(ContractError):c.collect(path,c._sha(payload),base/'invalid',r.DEFAULT_POLICY,stage_seconds=20)
            retrieve.assert_not_called()
            self.assertTrue((base/'invalid/FAILED.json').exists())

    def test_concurrent_same_output_cannot_duplicate_dispatch(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,_=query_fixture(base,1)
            entered=threading.Event();release=threading.Event();real_retrieve=r.retrieve;results=[]
            def blocked(*args,**kwargs):entered.set();release.wait(3);return real_retrieve(*args,**kwargs)
            def owner():results.append(c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20))
            with patch.object(r,'retrieve',side_effect=blocked) as retrieve,patch.object(r,'fetch_http',side_effect=fictional_fetch):
                thread=threading.Thread(target=owner);thread.start();self.assertTrue(entered.wait(3))
                with self.assertRaises(FileExistsError):c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
                release.set();thread.join(5)
            self.assertFalse(thread.is_alive());self.assertEqual(retrieve.call_count,1);self.assertEqual(results[0]['status'],'completed')

    def test_write_failure_retains_inspectable_unresolved_schedule(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp);path,sha,rows=query_fixture(base)
            real_publish=c.publish_bytes
            def fail_case(path,payload):
                if path.name=='case.json':raise OSError('fictional storage failure')
                return real_publish(path,payload)
            with patch.object(r,'fetch_http',side_effect=fictional_fetch),patch.object(c,'publish_bytes',side_effect=fail_case):
                with self.assertRaises(OSError):c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
            inspected=c.inspect_collection(base/'out')
            self.assertEqual(inspected['status'],'incomplete')
            self.assertEqual([x['status'] for x in inspected['cases']],['interrupted','unexecuted','unexecuted'])
            self.assertFalse((base/'out/SEALED.json').exists())

    def test_isolated_cli_without_network_completes_under_owned_job(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp).resolve();path,sha,rows=query_fixture(base,1)
            rows[0]['question']='What is it?';raw=canonical(rows)+b'\n';path.write_bytes(raw);sha=c._sha(raw)
            policy=base/'policy.json';policy_raw=canonical(r.DEFAULT_POLICY);policy.write_bytes(policy_raw)
            command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(base/'empty-cache'),str(Path(c.__file__).resolve()),
                '--queries',str(path),'--query-sha256',sha,'--output',str(base/'out'),'--policy',str(policy),
                '--policy-sha256',c._sha(policy_raw),'--stage-seconds','10']
            result=subprocess.run(command,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=parse_json((base/'out/manifest.json').read_bytes())
            self.assertEqual(manifest['totals']['completed_without_sources'],1)
            self.assertEqual(c.verify_collection(base/'out',c._sha((base/'out/manifest.json').read_bytes()))['status'],'completed')

    def test_cli_watchdog_stops_stalled_local_work_and_inspection_keeps_schedule(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp).resolve();path,sha,rows=query_fixture(base,2)
            policy=base/'policy.json';policy_raw=canonical(r.DEFAULT_POLICY);policy.write_bytes(policy_raw)
            helper=base/'stall.py'
            helper.write_text('import sys,time\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(Path.cwd()))+')\n'
                'from experiments.labbench import collect\n'
                'def stall(*args,**kwargs):time.sleep(30)\n'
                'collect.retrieval.retrieve=stall\n'
                'raise SystemExit(collect.main())\n',encoding='utf-8')
            command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(base/'empty-cache'),str(helper),
                '--queries',str(path),'--query-sha256',sha,'--output',str(base/'out'),'--policy',str(policy),
                '--policy-sha256',c._sha(policy_raw),'--stage-seconds','1']
            started=time.monotonic();result=subprocess.run(command,capture_output=True,text=True,timeout=8)
            self.assertEqual(result.returncode,124,result.stderr)
            self.assertLess(time.monotonic()-started,6)
            self.assertTrue((base/'out/WATCHDOG.json').exists())
            self.assertFalse((base/'out/COMPLETE.json').exists())
            inspected=c.inspect_collection(base/'out')
            self.assertEqual([case['status'] for case in inspected['cases']],['interrupted','unexecuted'])

    def test_watchdog_marker_write_failure_still_terminates_owned_process(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            base=Path(temp).resolve();blocked=base/'not-a-directory';blocked.write_bytes(b'preserved')
            helper=base/'watchdog.py'
            helper.write_text('import sys,time\nsys.path.insert(0,'+repr(str(Path.cwd()))+')\n'
                'from experiments.labbench.runtime import DeadlineWatchdog,contain_process_tree,empty_import_cache\n'
                'empty_import_cache()\nhandle=contain_process_tree()\n'
                'with DeadlineWatchdog(time.monotonic()+0.2,sys.argv[1]):time.sleep(30)\n',encoding='utf-8')
            command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(base/'empty-cache'),str(helper),str(blocked/'marker.json')]
            result=subprocess.run(command,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,124,result.stderr)
            self.assertEqual(blocked.read_bytes(),b'preserved')

    def test_resealed_journal_config_reservation_and_terminal_contradictions_rejected(self):
        for target,mutate in (
            ('collection_configured',lambda details:details['configuration'].update(bytes=0)),
            ('collection_case_reserved',lambda details:details.update(maximum_body_bytes=0)),
            ('collection_sealed',lambda details:details.update(status='partial'))):
            with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
                base=Path(temp);path,sha,_=query_fixture(base,1)
                with patch.object(r,'fetch_http',side_effect=fictional_fetch):c.collect(path,sha,base/'out',r.DEFAULT_POLICY,stage_seconds=20)
                root=base/'out';manifest_sha=c._sha((root/'manifest.json').read_bytes())
                events=[parse_json(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
                previous=None
                for event in events:
                    if event['event']==target:mutate(event['details'])
                    event.pop('sha256');event['previous_sha256']=previous
                    event['sha256']=fingerprint(event);previous=event['sha256']
                raw=b''.join(canonical(event)+b'\n' for event in events)
                (root/'journal.jsonl').write_bytes(raw)
                for flag in ('SEALED.json','COMPLETE.json'):
                    seal=parse_json((root/flag).read_bytes());seal['journal_sha256']=c._sha(raw)
                    (root/flag).write_bytes(canonical(seal)+b'\n')
                with self.subTest(event=target),self.assertRaises(ContractError):c.verify_collection(root,manifest_sha)


if __name__=='__main__':unittest.main()
