from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import io
from contextlib import redirect_stdout
import tempfile
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import run as r


class AnalysisRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def args(self,**changes):
        values=dict(primary_root=str(self.root/'missing-primary'),primary_root_sha256='0'*64,
            supplied_root=str(self.root/'missing-supplied'),supplied_root_sha256='1'*64,
            output=str(self.root/'attempt'),analysis_inputs=None,analysis_inputs_sha256=None,fictional=True,seconds=60)
        values.update(changes);return Namespace(**values)

    def test_output_reserved_before_missing_production_inputs(self):
        args=self.args(fictional=False)
        with self.assertRaisesRegex(ValueError,'Production requires'):r.execute(args)
        root=Path(args.output)
        self.assertTrue((root/'FAILURE.json').is_file())
        self.assertEqual([e['event'] for e in r.journal(root/'journal.jsonl')],['analysis_reserved','analysis_failed'])

    def test_existing_output_never_reused(self):
        log=r.Journal(self.root/'attempt');log.close();before=(log.root/'journal.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):r.execute(self.args())
        self.assertEqual((log.root/'journal.jsonl').read_bytes(),before)

    def test_concurrent_reservation_has_exactly_one_winner(self):
        def reserve(_):
            try:log=r.Journal(self.root/'attempt');log.close();return True
            except FileExistsError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(reserve,range(2)))
        self.assertEqual(sorted(result),[False,True])
        self.assertEqual(len(r.journal(self.root/'attempt/journal.jsonl')),1)

    def test_network_and_subprocess_dispatch_forbidden_in_worker(self):
        for event in ('socket.connect','socket.getaddrinfo','socket.bind','subprocess.Popen','os.system'):
            with self.assertRaises(PermissionError):r.no_dispatch(event,())
        r.no_dispatch('import',())

    def test_worker_cannot_modify_input_or_external_original(self):
        root=self.root/'worker';root.mkdir();guard=r.worker_write_guard(root)
        guard('open',(str(root/'out.json'),'wb',os.O_WRONLY|os.O_CREAT))
        guard('open',(str(self.root/'original.json'),'rb',os.O_RDONLY))
        with self.assertRaises(PermissionError):guard('open',(str(self.root/'original.json'),'wb',os.O_WRONLY))
        with self.assertRaises(PermissionError):guard('os.remove',(str(self.root/'original.json'),-1))

    def test_frame_write_failure_retains_failure_record(self):
        original=r.publish
        def write(path,value):
            if Path(path).name=='FRAME.json':raise OSError('Invented disk failure')
            return original(path,value)
        with patch.object(r,'publish',side_effect=write),self.assertRaises(OSError):r.execute(self.args())
        self.assertEqual(r.decode((self.root/'attempt/FAILURE.json').read_bytes())['stage'],'analysis_frame')

    def test_interrupted_supervisor_retains_partial_streams_without_retry(self):
        from tether._process import EngineInterrupted,EngineResult
        interrupted=EngineInterrupted(EngineResult(None,b'partial',b'diagnostic',dict(invented=True)))
        with patch('tether._process.supervise_command',side_effect=interrupted) as supervise,self.assertRaises(EngineInterrupted):r.execute(self.args())
        self.assertEqual(supervise.call_count,1)
        self.assertEqual((self.root/'attempt/stdout.log').read_bytes(),b'partial')
        self.assertEqual((self.root/'attempt/stderr.log').read_bytes(),b'diagnostic')
        self.assertTrue((self.root/'attempt/FAILURE.json').exists())
        self.assertFalse((self.root/'attempt/RECEIPT.json').exists())

    def test_deadline_supervisor_diagnostics_use_actual_retained_attribute(self):
        from tether._process import EngineDeadlineExceeded,EngineResult
        error=EngineDeadlineExceeded('Invented deadline')
        error.tether_engine_result=EngineResult(None,b'partial',b'',dict(process_reaped=True))
        with patch('tether._process.supervise_command',side_effect=error) as supervise,self.assertRaises(EngineDeadlineExceeded):r.execute(self.args())
        self.assertEqual(supervise.call_count,1)
        self.assertTrue(r.decode((self.root/'attempt/SUPERVISION.json').read_bytes())['process_reaped'])
        self.assertEqual((self.root/'attempt/stdout.log').read_bytes(),b'partial')
        self.assertTrue((self.root/'attempt/FAILURE.json').exists())

    def test_bad_fictional_anchor_cannot_relax_production_gate(self):
        with self.assertRaisesRegex(ValueError,'fictional fixtures'):r.fictional_inputs(dict(root_sha256='0'*64),dict(root_sha256='1'*64))

    def test_fictional_mode_rejects_production_keys_before_dispatch(self):
        args=self.args(analysis_inputs='original-keys.json',analysis_inputs_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'no production evaluator'):r.execute(args)
        self.assertFalse((Path(args.output)/'COMMAND.json').exists())

    def test_inspection_retains_verified_prefix_of_interrupted_journal(self):
        log=r.Journal(self.root/'attempt');log.close()
        with (log.root/'journal.jsonl').open('ab') as stream:stream.write(b'{"partial":')
        output=io.StringIO()
        with redirect_stdout(output):r.inspect(log.root)
        result=r.decode(output.getvalue());self.assertEqual(result['verified_events'],1)
        self.assertEqual(result['trailing_uncommitted_bytes'],11)
        self.assertFalse(result['completion_verified']);self.assertFalse(result['automatic_retry'])


if __name__=='__main__':unittest.main()
