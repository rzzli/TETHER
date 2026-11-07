"""Regression-first offline quotation boundaries; never use local model assets."""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode, fingerprint
from tether_engine.journal import RunJournal
from tether_engine.study import tokenization as tok
from tether_engine.study.stable_read import checked_path, deadline_check, hash_file, stable_files
from tether_engine.study.tokenization import parse_token_trace, prepare_tokenizer_spec

TEMP_ROOT = Path(__file__).resolve().parents[1] / 'data/cache'


class TokenBoundaryTests(unittest.TestCase):
    def test_trace_requires_exact_complete_nonnegative_ids_and_count(self):
        self.assertEqual(parse_token_trace(b'[1, 20, 3]\nTotal number of tokens: 3\n'), 3)
        for raw in (b'[1]\nTotal number of tokens: 2\n', b'[-1]\nTotal number of tokens: 1\n',
                    b'[true]\nTotal number of tokens: 1\n', b'[1]\n[2]\nTotal number of tokens: 1\n',
                    b'[1', b'[1]\nTotal number of tokens: 1\nextra'):
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                parse_token_trace(raw)

    def test_deadline_and_paths_fail_before_access(self):
        with self.assertRaises(TimeoutError):
            deadline_check(time.monotonic() - 1)
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as tmp:
            for value in ('../escape', 'file:stream', 'a/../b', 'NUL', '/absolute'):
                with self.subTest(value=value), self.assertRaises(ContractError):
                    checked_path(Path(tmp), value)
            with self.assertRaises(ContractError):
                checked_path(Path('.'), 'pyproject.toml')

    def test_arbitrary_executable_authority_denied(self):
        with self.assertRaises(ContractError):
            prepare_tokenizer_spec({'executable': 'arbitrary.exe'}, {}, deadline=time.monotonic()+10)

    def test_stable_read_denies_write_and_releases(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as tmp:
            path = Path(tmp) / 'fixture.txt'
            path.write_bytes(b'invented')
            if os.name != 'nt':
                with self.assertRaises(ContractError):
                    with stable_files([path], deadline=time.monotonic()+10):
                        self.fail('Unsupported platform must fail closed')
                return
            with stable_files([path], deadline=time.monotonic()+10):
                self.assertEqual(hash_file(path, time.monotonic()+10)['bytes'], 8)
                with self.assertRaises(OSError):
                    path.write_bytes(b'changed')
            path.write_bytes(b'after release')


class FakeChild:
    pid = 12345

    def __init__(self, argv, **kwargs):
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(b'[1, 20, 3]\nTotal number of tokens: 3\n')
        self.stderr = io.BytesIO(b'')
        self.killed = False

    def poll(self):
        return 0

    def kill(self):
        self.killed = True

    def wait(self, timeout):
        return 0


class TokenizationArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=TEMP_ROOT)
        cls.root = Path(cls.tmp.name)
        cls.model = cls.root/'model'
        (cls.model/'runtime').mkdir(parents=True)
        names = [f'qwen-0000{i}-of-00003.gguf' for i in (1,2,3)] + ['runtime/llama-tokenize.exe']
        names += [f'runtime/fake-{i:02d}.dll' for i in range(30)]
        assets = []
        for name in names:
            path = cls.model/name
            raw = ('invented fixture '+name).encode()
            path.write_bytes(raw)
            assets.append(dict(relative_path=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
        cls.resource = dict(schema_version=1, kind='approved_local_tokenizer_assets',
            inventory_sha256=hashlib.sha256(b'invented inventory').hexdigest(),
            acquisition_sha256=hashlib.sha256(b'invented acquisition').hexdigest(),
            version='invented_test_assets_never_executed', assets=assets)
        (cls.root/'inventory.json').write_bytes(b'invented inventory')
        (cls.root/'acquisition.json').write_bytes(b'invented acquisition')
        cls.authority = {name:dict(root_id='proofs',relative_path=name+'.json') for name in ('inventory','acquisition')}
        cls.roots = dict(model=cls.model, proofs=cls.root)
        cls.resource_patch = patch.object(tok, '_resource', return_value=cls.resource)
        cls.resource_patch.start()
        cls.spec = prepare_tokenizer_spec(cls.authority, cls.roots, deadline=time.monotonic()+60)
        cls.prompt = 'Unicode α\n<|im_start|>\x00 trailing\n'
        real_run = tok._run_child

        def fake_run(*args):
            return real_run(*args, process_factory=FakeChild)
        cls.bundle = cls.root/'bundle'
        with patch.object(tok, '_run_child', side_effect=fake_run):
            cls.result = tok.tokenize_prompt(cls.prompt, cls.spec, time.monotonic()+60, cls.bundle,
                                             payload_sha256='a'*64)

    @classmethod
    def tearDownClass(cls):
        cls.resource_patch.stop()
        cls.tmp.cleanup()

    def verify(self, path=None, anchor=None):
        with patch.object(tok.subprocess, 'Popen', side_effect=AssertionError('replay must not spawn')):
            return tok.verify_tokenization(path or self.bundle, anchor or self.result['receipt_sha256'],
                hashlib.sha256(self.prompt.encode()).hexdigest(), fingerprint(self.spec), expected_payload_sha256='a'*64)

    def test_complete_quote_exact_unicode_stdin_and_readonly_replay(self):
        quote = self.verify()
        self.assertEqual((quote['token_count'], quote['input_reservation']), (3,35))
        self.assertEqual(quote['generation_calls'], 0)
        self.assertEqual((self.bundle/'prompt.bin').read_bytes(), self.prompt.encode())
        with self.assertRaises(TypeError):
            self.spec['assets'][0]['sha256'] = '0'*64
        with self.assertRaises(TypeError):
            quote['child']['exit_code'] = 9

    def test_external_anchor_prompt_spec_and_payload_required(self):
        for anchor, prompt, spec, payload in (('0'*64,hashlib.sha256(self.prompt.encode()).hexdigest(),fingerprint(self.spec),'a'*64),
              (self.result['receipt_sha256'],'0'*64,fingerprint(self.spec),'a'*64),
              (self.result['receipt_sha256'],hashlib.sha256(self.prompt.encode()).hexdigest(),'0'*64,'a'*64),
              (self.result['receipt_sha256'],hashlib.sha256(self.prompt.encode()).hexdigest(),fingerprint(self.spec),'b'*64)):
            with self.subTest(anchor=anchor,payload=payload), self.assertRaises(ContractError):
                tok.verify_tokenization(self.bundle, anchor, prompt, spec, expected_payload_sha256=payload)

    def test_asset_mutation_extra_dll_and_spec_flags_fail_before_child(self):
        extra = self.model/'runtime/extra.dll'
        extra.write_bytes(b'not approved')
        try:
            with patch.object(tok, '_run_child', side_effect=AssertionError('must not dispatch')):
                with self.assertRaises(ContractError):
                    tok.tokenize_prompt('a',self.spec,time.monotonic()+60,self.root/'extra-rejected')
        finally:
            extra.unlink()
        shard = self.model/self.spec['assets'][0]['relative_path']
        original = shard.read_bytes()
        shard.write_bytes(b'changed')
        try:
            with patch.object(tok, '_run_child', side_effect=AssertionError('must not dispatch')):
                with self.assertRaises(ContractError):
                    tok.tokenize_prompt('a',self.spec,time.monotonic()+60,self.root/'changed-rejected')
        finally:
            shard.write_bytes(original)
        bad = encode(self.spec)
        bad['argv'].append('--arbitrary')
        with self.assertRaises(ContractError):
            tok.tokenize_prompt('a',bad,time.monotonic()+60,self.root/'bad-spec')

    def test_trace_and_accounting_tampering_rejected_even_if_resealed(self):
        for key,value in [('token_count',4),('generation_calls',1),('child',{'pid':999})]:
            target = self.root/('resealed-'+key)
            shutil.copytree(self.bundle,target)
            quote = json.loads((target/'quote.json').read_bytes())
            quote[key] = value
            (target/'quote.json').write_bytes(canonical(quote))
            receipt = json.loads((target/'receipt.json').read_bytes())
            receipt['quote_sha256'] = fingerprint(quote)
            receipt['files']['quote.json'] = encode(hash_file(target/'quote.json',time.monotonic()+10))
            raw = canonical(receipt)
            (target/'receipt.json').write_bytes(raw)
            with self.subTest(key=key), self.assertRaises(ContractError):
                self.verify(target,hashlib.sha256(raw).hexdigest())

    def test_no_output_reuse_and_expired_deadline_does_not_spawn(self):
        with self.assertRaises(FileExistsError):
            tok.tokenize_prompt('a',self.spec,time.monotonic()+60,self.bundle)
        with patch.object(tok,'_run_child',side_effect=AssertionError('must not dispatch')):
            with self.assertRaises(TimeoutError):
                tok.tokenize_prompt('a',self.spec,time.monotonic()-1,self.root/'expired')
        self.assertFalse((self.root/'expired').exists())

    def test_interruption_retains_failure_without_retry(self):
        target = self.root/'interrupted'
        with patch.object(tok,'_run_child',side_effect=KeyboardInterrupt) as child:
            with self.assertRaises(KeyboardInterrupt):
                tok.tokenize_prompt('a',self.spec,time.monotonic()+60,target)
        self.assertEqual(child.call_count,1)
        self.assertEqual(json.loads((target/'failure.json').read_bytes())['status'],'interrupted')
        self.assertFalse((target/'receipt.json').exists())


class ChildBoundaryTests(unittest.TestCase):
    def invoke(self,factory,deadline=None):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as tmp:
            output=Path(tmp)/'output'
            journal=RunJournal(output,kind='build')
            try:
                return tok._run_child(['invented.exe'],b'exact\n',deadline or time.monotonic()+2,
                                       output,journal,process_factory=factory)
            finally:
                journal.close()

    def test_stdout_overflow_stops_and_cleans_owned_child(self):
        children=[]
        def factory(*args,**kwargs):
            child=FakeChild(*args,**kwargs)
            child.stdout=io.BytesIO(b'x'*(tok.MAX_STREAM_BYTES+1))
            child.poll=lambda: None
            children.append(child)
            return child
        with self.assertRaises(ContractError):
            self.invoke(factory)
        self.assertTrue(children[0].killed)

    def test_timeout_stops_only_owned_child(self):
        children=[]
        def factory(*args,**kwargs):
            child=FakeChild(*args,**kwargs)
            child.poll=lambda: None
            children.append(child)
            return child
        with self.assertRaises(TimeoutError):
            self.invoke(factory,time.monotonic()+.03)
        self.assertEqual(len(children),1)
        self.assertTrue(children[0].killed)

    def test_cleanup_still_kills_if_poll_itself_raises(self):
        children=[]
        def factory(*args,**kwargs):
            child=FakeChild(*args,**kwargs)
            def broken_poll():
                raise OSError('invented poll error')
            child.poll=broken_poll
            children.append(child)
            return child
        with self.assertRaises(OSError):
            self.invoke(factory)
        self.assertTrue(children[0].killed)

    def test_pipe_fault_after_poll_before_completed_branch_is_rejected(self):
        class DelayedThread:
            def __init__(self,target,args,**kwargs):
                self.target,self.args,self.done=target,args,False
            def start(self):
                pass
            def is_alive(self):
                if not self.done:
                    self.done=True
                    self.target(*self.args)
                return False
            def join(self,timeout):
                pass
        class FaultOnFirstClose(io.BytesIO):
            first=True
            def close(self):
                if self.first:
                    self.first=False
                    raise OSError('invented late stdin close fault')
                super().close()
        def factory(*args,**kwargs):
            child=FakeChild(*args,**kwargs)
            child.stdin=FaultOnFirstClose()
            return child
        with patch.object(tok.threading,'Thread',DelayedThread), self.assertRaises(OSError):
            self.invoke(factory)

    def test_expiry_during_spawn_never_feeds_stdin(self):
        children=[]
        class CountingInput(io.BytesIO):
            written=0
            def write(self,value):
                self.written+=len(value)
                return super().write(value)
        def factory(*args,**kwargs):
            child=FakeChild(*args,**kwargs)
            child.stdin=CountingInput()
            children.append(child)
            time.sleep(.04)
            return child
        with self.assertRaises(TimeoutError):
            self.invoke(factory,time.monotonic()+.02)
        self.assertEqual(children[0].stdin.written,0)

    def test_environment_drops_secret_and_model_overrides(self):
        with patch.dict(os.environ,{'LLAMA_MODEL':'bad','HF_TOKEN':'secret','UNRELATED_SECRET':'secret','PATH':'bad'}):
            env=tok._environment()
        self.assertNotIn('HF_TOKEN',env)
        self.assertNotIn('LLAMA_MODEL',env)
        self.assertNotIn('UNRELATED_SECRET',env)
        self.assertNotEqual(env.get('PATH'),'bad')


if __name__ == '__main__':
    unittest.main()
