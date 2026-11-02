"""Independent fictional probes of the new TETHER layer; no provider input."""
from pathlib import Path
import importlib,os,sys,tempfile,unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/tether/src'))
from tether import _presentation as layer
from asof.serde import ContractError,MAX_NORMALIZED_JSON_BYTES,read_json

class FrontDoorIndependentTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='tether-independent-',dir=ROOT/'data/cache')
  self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def test_oversize_metadata_rejected_before_open(self):
  p=self.root/'large.json'
  with p.open('wb') as f:f.truncate(MAX_NORMALIZED_JSON_BYTES+1)
  original=Path.open
  def guarded(path,*args,**kwargs):
   mode=args[0] if args else kwargs.get('mode','r')
   if path==p and mode=='rb':raise AssertionError('oversized_metadata_open_attempted')
   return original(path,*args,**kwargs)
  with patch.object(Path,'open',new=guarded),self.assertRaises(ContractError):layer._json(p)
 def test_core_metadata_control_rejects_before_open(self):
  p=self.root/'large.json'
  with p.open('wb') as f:f.truncate(MAX_NORMALIZED_JSON_BYTES+1)
  with patch.object(Path,'open',side_effect=AssertionError('must_not_open')),self.assertRaises(ContractError):read_json(p)
 def test_oversize_outer_journal_inspection_is_bounded(self):
  outer=self.root/'outer';(outer/'attempt').mkdir(parents=True);p=outer/'attempt/journal.jsonl'
  with p.open('wb') as f:f.truncate(MAX_NORMALIZED_JSON_BYTES+1)
  original=Path.open
  def guarded(path,*args,**kwargs):
   mode=args[0] if args else kwargs.get('mode','r')
   if path==p and mode=='rb':raise AssertionError('oversized_journal_open_attempted')
   return original(path,*args,**kwargs)
  with patch.object(Path,'open',new=guarded):result=layer.inspect_outer(outer)
  self.assertEqual(result['journal_inspection_error'],'ContractError')
 def test_read_detects_file_changed_during_read(self):
  p=self.root/'changing.json';p.write_bytes(b'{}');original=Path.open
  state={'changed':False}
  class Reader:
   def __init__(self,f):self.f=f
   def __getattr__(self,n):return getattr(self.f,n)
   def __enter__(self):return self
   def __exit__(self,*args):return self.f.__exit__(*args)
   def read(self,*args):
    data=self.f.read(*args)
    if not state['changed']:
     state['changed']=True;p.write_bytes(b'[]\n')
    return data
  def changing(path,*args,**kwargs):
   f=original(path,*args,**kwargs)
   mode=args[0] if args else kwargs.get('mode','r')
   return Reader(f) if path==p and mode=='rb' else f
  with patch.object(Path,'open',new=changing),self.assertRaises(ContractError):layer._read(p)
  self.assertTrue(state['changed'])
 def test_noninterrupt_communicate_failure_reaps_owned_child(self):
  p=Mock();p.poll.return_value=None;p.returncode=-1
  p.communicate.side_effect=[OSError('fictional pipe read failed'),(b'',b'')]
  with patch.object(layer.subprocess,'Popen',return_value=p) as spawn,self.assertRaises(OSError):layer.invoke_engine(['demo','--output','invented'])
  spawn.assert_called_once();p.terminate.assert_called_once();self.assertGreaterEqual(p.communicate.call_count,2)
 def test_interrupt_timeout_kills_and_reaps_once(self):
  p=Mock();p.poll.return_value=None;p.returncode=-1
  p.communicate.side_effect=[KeyboardInterrupt(),layer.subprocess.TimeoutExpired('fictional',5),(b'out',b'err')]
  with patch.object(layer.subprocess,'Popen',return_value=p) as spawn,self.assertRaises(layer.EngineInterrupted):layer.invoke_engine(['demo','--output','invented'])
  spawn.assert_called_once();p.terminate.assert_called_once();p.kill.assert_called_once();self.assertEqual(p.communicate.call_count,3)
 def test_duplicate_keys_and_nonfinite_metadata_rejected(self):
  p=self.root/'bad.json'
  for payload in [b'{"x":0,"x":1}',b'{"x":NaN}']:
   p.write_bytes(payload)
   with self.subTest(payload=payload),self.assertRaises(ContractError):layer._json(p)
 def test_unsafe_logical_paths_rejected(self):
  for value in ['', '../x', 'a/../x', '/root', 'a//b', 'a\\b', 'C:/x']:
   with self.subTest(value=value),self.assertRaises(ContractError):layer._relative(value)
 def test_wrong_runtime_distribution_rejects_code_proof(self):
  def version(name):return '0.3.10' if name=='asof-target-agents' else '0.4.0'
  with patch.object(layer.metadata,'version',side_effect=version),self.assertRaises(ContractError):layer.code_proof()
 def test_private_reference_token_and_class_are_same_identity(self):
  public=importlib.import_module('tether.study.source_fact_sources');legacy=importlib.import_module('asof.study.source_fact_sources')
  self.assertIs(public,legacy);self.assertIs(public._TOKEN,legacy._TOKEN);self.assertIs(public.VerifiedReference,legacy.VerifiedReference)
 def test_all_approved_normal_imports_preserve_legacy_metadata(self):
  from tether._aliases import _LEGACY_MODULES
  for suffix in sorted(_LEGACY_MODULES):
   legacy=importlib.import_module('asof.'+suffix);before=(legacy.__name__,legacy.__package__,legacy.__spec__,legacy.__loader__,legacy.__file__)
   public=importlib.import_module('tether.'+suffix)
   with self.subTest(suffix=suffix):
    self.assertIs(public,legacy);self.assertEqual((legacy.__name__,legacy.__package__,legacy.__spec__,legacy.__loader__,legacy.__file__),before)
 def test_metadata_schema_bool_cannot_alias_one(self):
  common=dict(schema_version=True,method=layer.METHOD,brand='TETHER',status='completed',role='evaluation_only',agent_visible=False,scientific_validation='not_established')
  with self.assertRaises(ContractError):layer._envelope(common,set(common))

if __name__=='__main__':unittest.main(verbosity=2)
