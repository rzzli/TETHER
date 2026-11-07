"""Invented recovery partitions and clock contracts; no scientific inputs."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from uuid import UUID
from unittest.mock import patch
from tether_engine.serde import encode
from . import contracts as c


def payload(root,production=False):
    ids=[str(UUID(int=i+1)) for i in range(199 if production else 2)];failed=184 if production else 0
    original=root/'original';original.mkdir(exist_ok=True)
    frame=dict(purpose='production' if production else 'fictional_qualification',schedule=ids,phase_seconds=dict(repair=7200,removal=7200))
    path=original/'FRAME.json'
    if not path.exists():c.write(path,frame)
    rows=[dict(ordinal=i,id=key,execution_id=f'00000000-0000-0000-0000-000000000001-repair-{i:04d}',
        status='codec_failure' if production and i==2 else 'completed' if i<failed else 'failed' if i==failed else 'unexecuted') for i,key in enumerate(ids)]
    return dict(frame=frame,frame_proof=c.capture(path)[0],original_root=str(original),schedule=ids,repair_rows=rows,failed_ordinal=failed,
        untouched_repair_ordinals=list(range(failed+1,len(ids))),untouched_removal_ordinals=list(range(len(ids))),
        completed_phases=dict(critic={},refinement_collect={},pair_prepare={}),pair_prepare={},failed_call={'prediction':None},
        elapsed=dict(repair_process_total_seconds=780.484,repair_worker_wall_seconds=780.015,repair_stage_seal_elapsed_seconds=686.531,
            outer_process_total_seconds=4181.828),budgets=dict(outer_seconds=43200,repair_stage_seconds=7100))


class RecoveryContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()

    def test_production_partition_and_conservative_nested_clocks(self):
        p=payload(self.root,True);parts=c.partition(p);budgets=c.budgets(p,parts)
        self.assertEqual(parts['repair_dispatch'],tuple(range(185,199)));self.assertEqual(len(parts['removal_dispatch']),199)
        self.assertEqual(budgets['max_new_generation_calls'],213);self.assertEqual(budgets['max_new_source_http_requests'],0)
        self.assertEqual(budgets['phase_remaining_seconds']['repair'],6419);self.assertEqual(budgets['outer_remaining_seconds'],39018)
        self.assertEqual(budgets['repair_stage_remaining_seconds'],6413)

    def test_completed_failed_and_untouched_cannot_be_reclassified(self):
        for key,value in [('failed_ordinal',183),('untouched_repair_ordinals',list(range(184,199))),('untouched_removal_ordinals',[1])]:
            p=payload(self.root,True);p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):c.partition(p)
        p=payload(self.root,True);p['repair_rows'][184]['status']='completed'
        with self.assertRaises(ValueError):c.partition(p)

    def test_invalid_duration_and_budget_reset_rejected(self):
        for value in (True,-1,float('inf'),float('nan'),8000):
            p=payload(self.root);p['elapsed']['repair_process_total_seconds']=value
            with self.subTest(value=value),self.assertRaises(ValueError):c.budgets(p,c.partition(p))
        p=payload(self.root);p['elapsed']['repair_stage_seal_elapsed_seconds']=1000
        with self.assertRaises(ValueError):c.budgets(p,c.partition(p))

    def test_fictional_original_budgets_remain_original(self):
        p=payload(self.root);p['frame']['phase_seconds']=dict(repair=600,removal=600);p['budgets']['repair_stage_seconds']=120
        p['elapsed']=dict(repair_process_total_seconds=10,repair_worker_wall_seconds=9,repair_stage_seal_elapsed_seconds=8,outer_process_total_seconds=30)
        result=c.budgets(p,c.partition(p));self.assertEqual(result['phase_remaining_seconds']['repair'],590);self.assertEqual(result['repair_stage_remaining_seconds'],112)

    def test_strict_captured_proof_and_nested_immutability(self):
        item=c.write(self.root/'test.json',{'nested':{'values':[1]}});data=c.read(item)
        with self.assertRaises(TypeError):data['nested']['values'][0]=2
        (self.root/'test.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):c.read(item)

    def test_capture_bounds_allocation_by_observed_size(self):
        target=self.root/'small';target.write_bytes(b'abc');actual=Path.open;requests=[]
        class Stream:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):self.stream.__enter__();return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,count):requests.append(count);return self.stream.read(count)
        with patch.object(Path,'open',lambda path,*a,**kw:Stream(actual(path,*a,**kw))):
            self.assertEqual(c.capture(target)[1],b'abc')
        self.assertEqual(requests,[4])

    def test_oversized_capture_is_rejected_before_open(self):
        target=self.root/'large';target.write_bytes(b'abcd')
        with patch.object(Path,'open',side_effect=AssertionError('must not allocate/open')):
            with self.assertRaisesRegex(ValueError,'oversized'):c.capture(target,maximum=3)

    def test_capture_rejects_growth_during_read(self):
        target=self.root/'growth';target.write_bytes(b'abc');actual=Path.open
        class Stream:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):self.stream.__enter__();return self
            def __exit__(self,*args):return self.stream.__exit__(*args)
            def fileno(self):return self.stream.fileno()
            def read(self,count):
                raw=self.stream.read(count)
                with actual(target,'ab') as changed:changed.write(b'd')
                return raw
        with patch.object(Path,'open',lambda path,*a,**kw:Stream(actual(path,*a,**kw))):
            with self.assertRaisesRegex(ValueError,'changed'):c.capture(target)

    def test_capture_rejects_open_handle_identity_substitution(self):
        target=self.root/'identity';target.write_bytes(b'abc')
        import os
        from types import SimpleNamespace
        actual=os.fstat
        def changed(fd):
            value=actual(fd)
            return SimpleNamespace(st_dev=value.st_dev,st_ino=value.st_ino+1,st_size=value.st_size,st_mtime_ns=value.st_mtime_ns,st_ctime_ns=value.st_ctime_ns)
        with patch.object(os,'fstat',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'identity'):c.capture(target)

    def test_duplicate_keys_and_nonfinite_metadata_rejected(self):
        for i,raw in enumerate((b'{"status":1,"status":2}',b'{"value":NaN}')):
            path=self.root/f'{i}.json';path.write_bytes(raw)
            with self.assertRaises(ValueError):c.read(c.capture(path)[0])

    def test_parent_identity_does_not_depend_on_inspection_or_output(self):
        p=payload(self.root);first=c.identity(p['original_root'],p['frame_proof'])
        copied=encode(p['frame_proof']);self.assertEqual(first,c.identity(p['original_root'],copied))
        copied['sha256']='0'*64;self.assertNotEqual(first,c.identity(p['original_root'],copied))

    def test_full_schedule_and_canonical_paths(self):
        with self.assertRaises(ValueError):c.schedule(['not-a-uuid'],'fictional_qualification')
        with self.assertRaises(ValueError):c.path('relative')


if __name__=='__main__':unittest.main()
