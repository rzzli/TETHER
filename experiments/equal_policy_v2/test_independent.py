"""Unscored version-routing tests; --native explicitly enables installed fixtures.

Ordinary discovery runs only standard-library fake-payload tests. Native fixture
production requires this file's explicit --native driver under an isolated
current installed interpreter with -I. It never executes the 109-case comparison corpus.
"""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.history import read_checkpoint

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'experiments'))
from equal_policy import independent as old
from equal_policy import independent_runtime as old_runtime
from equal_policy_v2 import independent as current
from equal_policy_v2 import independent_runtime as runtime


class VersionedIndependentTests(unittest.TestCase):
    def setUp(self):
        cache=PROJECT/'data/cache/equal-policy-v2-independent-unit'; cache.mkdir(parents=True,exist_ok=True)
        temporary=tempfile.TemporaryDirectory(dir=cache); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def payload(self,pair=('0.6.0','0.4.0')):
        paths={}
        for name,version in zip(('tether','tether_engine'),pair):
            directory=self.root/name; directory.mkdir(exist_ok=True)
            (directory/'__init__.py').write_text('__version__ = '+repr(version)+'\n',encoding='utf-8')
            (directory/'logic.py').write_text('VALUE = 1\n',encoding='utf-8')
            paths[name+'_file']=str((directory/'__init__.py').resolve())
        return dict(schema_version=1,versions=dict(zip(('tether','tether_engine'),pair)),runtime_paths=paths)

    def distribution(self,name,version,suffix=''):
        path=self.root/(name.replace('-','_')+'-'+version+suffix+'.dist-info'); path.mkdir()
        (path/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n',encoding='utf-8')

    def test_exact_version_pairs_only(self):
        for pair in (('0.6.0','0.4.0'),):
            self.assertTrue(runtime.approved_versions(dict(zip(('tether','tether_engine'),pair))))
        for value in (None,[],{},dict(tether='0.5.2',tether_engine='0.4.0'),dict(tether='0.6.0',tether_engine='0.3.13'),
                      dict(tether='0.6.00',tether_engine='0.4.0'),dict(tether='0.5.2',tether_engine='0.3.13',extra=True),
                      dict(tether=0.52,tether_engine='0.3.13')):
            self.assertFalse(runtime.approved_versions(value),value)

    def test_supported_literal_payloads_and_matching_distribution_versions(self):
        for pair in (('0.6.0','0.4.0'),):
            with self.subTest(pair=pair):
                trusted=self.payload(pair)
                proof=runtime.launcher_proof(trusted)
                self.assertEqual((proof['facade_version'],proof['core_version']),pair)
                self.assertEqual(proof['installed_distributions'],{'tether-target-engine':None,'tether-target-agents':None})
        self.distribution('tether-target-agents','0.6.0'); self.distribution('tether-target-engine','0.4.0')
        proof=runtime.launcher_proof(trusted)
        self.assertEqual(proof['installed_distributions'],{'tether-target-engine':'0.4.0','tether-target-agents':'0.6.0'})

    def test_trusted_pair_must_equal_actual_pair_each_call(self):
        trusted=self.payload()
        runtime.launcher_proof(trusted)
        trusted['versions']=dict(tether='0.5.2',tether_engine='0.3.13')
        with self.assertRaisesRegex(old.PolicyError,'Trusted runtime version differs'):
            runtime.launcher_proof(trusted)
        trusted=self.payload(('0.5.2','0.4.0'))
        with self.assertRaisesRegex(old.PolicyError,'Unsupported installed package version'):
            runtime.launcher_proof(trusted)

    def test_distribution_mismatch_and_duplicate_metadata_reject(self):
        trusted=self.payload()
        self.distribution('tether-target-agents','0.5.2')
        with self.assertRaisesRegex(old.PolicyError,'distribution version differs'):
            runtime.launcher_proof(trusted)
        self.distribution('tether-target-agents','0.6.0')
        with self.assertRaisesRegex(old.PolicyError,'Duplicate installed distribution'):
            runtime.launcher_proof(trusted)

    def test_per_call_actual_payload_hashes_and_inventory_are_not_cached(self):
        trusted=self.payload(); trusted['launcher_proof']={'code':'intentionally stale manifest'}
        before=runtime.launcher_proof(trusted)
        (self.root/'tether/logic.py').write_text('VALUE = 2\n',encoding='utf-8')
        after=runtime.launcher_proof(trusted)
        self.assertNotEqual(before['code']['logic.py']['sha256'],after['code']['logic.py']['sha256'])
        (self.root/'tether/added.py').write_text('EXTRA = True\n',encoding='utf-8')
        self.assertIn('added.py',runtime.launcher_proof(trusted)['code'])
        core_before=old_runtime.core_code(trusted)
        (self.root/'tether_engine/logic.py').write_text('VALUE = 3\n',encoding='utf-8')
        self.assertNotEqual(core_before,old_runtime.core_code(trusted))

    def test_unstable_capture_and_nonliteral_actual_version_reject(self):
        trusted=self.payload()
        with patch.object(runtime,'capture',side_effect=[{'one':1},{'two':2}]):
            with self.assertRaisesRegex(old.PolicyError,'changed during capture'):
                runtime.launcher_proof(trusted)
        (self.root/'tether/__init__.py').write_text("__version__ = '.'.join(['0','5','1'])\n",encoding='utf-8')
        with self.assertRaisesRegex(old.PolicyError,'literal'):
            runtime.launcher_proof(trusted)

    def test_current_source_closure_and_archived_helper_bytes_have_separate_identities(self):
        names=('independent','independent_local','independent_policy','independent_render','independent_runtime','independent_schema')
        # Original byte identities are checked against the immutable Git checkpoint.
        # Renamed current code has no inherited runtime qualification.
        archived_hashes={'experiments/equal_policy/independent.py': '38db99353bab07e5ed8eb6dc75b6f1f6d38615fc75287bc65c0c9b7a9f5f8e36', 'experiments/equal_policy/independent_local.py': 'd37e976e0c253f91c5001b0f9878c6897320d457713a7ea420f88a376b719965', 'experiments/equal_policy/independent_policy.py': '0f52cd17ffbe06efeed9e6df99ff21d3c1eca5d39ec77190d856d4b6253cdcb6', 'experiments/equal_policy/independent_render.py': '3213a4fbc58e6a73881cd16df3aee432cb2f55e4e113e8775c45cea5d1740135', 'experiments/equal_policy/independent_runtime.py': '7aeec8ff4b3154709cbdc8158669470f507f97ccf37d923f543558e4f77a63d1', 'experiments/equal_policy/independent_schema.py': '66f2c80a0be3c381cfd4ad6e5e7a5a27c55e8597601ea4af1c472b67b317b545'}
        for prefix,members in (('equal_policy',names),('equal_policy_v2',('independent','independent_runtime'))):
            for name in members:
                module=importlib.import_module(prefix+'.'+name); path=Path(module.__file__)
                for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                    if isinstance(node,ast.Import): imports=[x.name for x in node.names]
                    elif isinstance(node,ast.ImportFrom): imports=[node.module or '']
                    else: continue
                    self.assertFalse(any(x.split('.')[0] in ('tether_engine','tether') for x in imports),(path,imports))
                if prefix=='equal_policy':
                    relative=path.relative_to(PROJECT).as_posix()
                    self.assertEqual(hashlib.sha256(read_checkpoint(relative)).hexdigest(), archived_hashes[relative])
        code='import sys,json; sys.path.insert(0,'+repr(str(PROJECT/'experiments'))+'); import equal_policy_v2.independent; print(json.dumps([n for n in sys.modules if n.split(".")[0] in ("tether_engine","tether")]))'
        result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,timeout=20,check=True)
        self.assertEqual(json.loads(result.stdout),[])


def native_suite():
    """Native classes are created only by the explicit isolated driver."""
    from equal_policy import cases, materialize, policy_cases, reference

    class InstalledOuterParity(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            identity=reference.runtime_identity()
            if not sys.flags.isolated:
                raise RuntimeError('Native parity requires an isolated current installed interpreter with -I')
            if identity['tether_version']!='0.6.0' or identity['tether_engine_version']!='0.4.0':
                raise RuntimeError('This parity control requires the current supported pair')
            if not all('site-packages' in identity[k] for k in ('tether_engine_file','tether_file')):
                raise RuntimeError('Product imports must come from the qualified installation')
            cls.fixture_root=tempfile.TemporaryDirectory()
            cls.addClassCleanup(cls.fixture_root.cleanup)
            fixture=Path(cls.fixture_root.name)
            (fixture/'QUALIFICATION.json').write_text(json.dumps({
                'scope':'invented unit envelope; current installed bytes, no inherited qualification',
                'runtime':identity}),encoding='utf-8')
            cls.trusted=reference.trusted_runtime(fixture)

        def setUp(self):
            cache=PROJECT/'data/cache/equal-policy-v2-independent-native'; cache.mkdir(parents=True,exist_ok=True)
            temporary=tempfile.TemporaryDirectory(dir=cache); self.addCleanup(temporary.cleanup)
            self.root=Path(temporary.name); self.counter=0

        def fixture(self,policy=False):
            self.counter+=1; root=self.root/('UNIT-'+str(self.counter))
            spec=dict(control_id='UNIT-OUTER-'+str(self.counter),operation='prepare_run',
                variant='artifact_policy_v2' if policy else 'core_v2_catalog1',
                preparation=dict(base='policy_t6' if policy else 'core_t1',changes=[],after_seal=[],
                    recipe=dict(policy_recipe='none',omit_scorer=True) if policy else {}))
            descriptor,_=cases.write_source_bundle(root,spec,trusted_runtime='trusted-runtime.json')
            materialize.save(root/'trusted-runtime.json',self.trusted)
            if policy: descriptor,_=policy_cases.prepare_policy_sources(root,spec,descriptor)
            descriptor=reference.materialize_outer(root,descriptor)
            return root,descriptor

        def test_valid_schema1_and_schema2_outer_decisions_and_observables_match(self):
            for policy in (False,True):
                with self.subTest(policy=policy):
                    root,descriptor=self.fixture(policy)
                    left=old.validate_bundle(root,descriptor); right=current.validate_bundle(root,descriptor)
                    self.assertEqual(left['decision'],'accept',left)
                    self.assertEqual(right,left)
                    self.assertTrue(right['observables']['code_matches_current'])

        def test_resealed_outer_faults_match_old_decisions_and_observables(self):
            for policy,mutation in ((False,'process_supervision_reseal'),(False,'outer_code_proof_reseal'),
                                    (False,'dossier_reseal'),(True,'copied_control_reseal'),(True,'projection_reseal')):
                with self.subTest(policy=policy,mutation=mutation):
                    root,descriptor=self.fixture(policy)
                    self.assertEqual(current.validate_bundle(root,descriptor)['decision'],'accept')
                    materialize.mutate_outer(root,descriptor,mutation)
                    left=old.validate_bundle(root,descriptor); right=current.validate_bundle(root,descriptor)
                    self.assertEqual(left['decision'],'reject',left)
                    self.assertEqual(right,left)

    return unittest.defaultTestLoader.loadTestsFromTestCase(InstalledOuterParity)


if __name__=='__main__':
    if '--native' in sys.argv:
        sys.argv.remove('--native')
        outcome=unittest.TextTestRunner(verbosity=2).run(native_suite())
        raise SystemExit(not outcome.wasSuccessful())
    unittest.main(verbosity=2)
