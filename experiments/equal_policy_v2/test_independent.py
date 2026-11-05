"""Unscored version-routing tests; --native explicitly enables installed fixtures.

Ordinary discovery runs only standard-library fake-payload tests. Native fixture
production requires this file's explicit --native driver under the pinned old
installed interpreter with -I. It never executes the 109-case comparison corpus.
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

PROJECT = Path(__file__).resolve().parents[2]
QUALIFIED = PROJECT/'data/cache/tether-051-installed-qualification-attempt02'
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

    def payload(self,pair=('0.5.1','0.3.12')):
        paths={}
        for name,version in zip(('tether','asof'),pair):
            directory=self.root/name; directory.mkdir(exist_ok=True)
            (directory/'__init__.py').write_text('__version__ = '+repr(version)+'\n',encoding='utf-8')
            (directory/'logic.py').write_text('VALUE = 1\n',encoding='utf-8')
            paths[name+'_file']=str((directory/'__init__.py').resolve())
        return dict(schema_version=1,versions=dict(zip(('tether','asof'),pair)),runtime_paths=paths)

    def distribution(self,name,version,suffix=''):
        path=self.root/(name.replace('-','_')+'-'+version+suffix+'.dist-info'); path.mkdir()
        (path/'METADATA').write_text('Metadata-Version: 2.1\nName: '+name+'\nVersion: '+version+'\n',encoding='utf-8')

    def test_exact_version_pairs_only(self):
        for pair in (('0.5.1','0.3.12'),('0.5.2','0.3.13')):
            self.assertTrue(runtime.approved_versions(dict(zip(('tether','asof'),pair))))
        for value in (None,[],{},dict(tether='0.5.2',asof='0.3.12'),dict(tether='0.5.1',asof='0.3.13'),
                      dict(tether='0.5.10',asof='0.3.12'),dict(tether='0.5.2',asof='0.3.13',extra=True),
                      dict(tether=0.52,asof='0.3.13')):
            self.assertFalse(runtime.approved_versions(value),value)

    def test_supported_literal_payloads_and_matching_distribution_versions(self):
        for pair in (('0.5.1','0.3.12'),('0.5.2','0.3.13')):
            with self.subTest(pair=pair):
                trusted=self.payload(pair)
                proof=runtime.launcher_proof(trusted)
                self.assertEqual((proof['facade_version'],proof['core_version']),pair)
                self.assertEqual(proof['installed_distributions'],{'asof-target-agents':None,'tether-target-agents':None})
        self.distribution('tether-target-agents','0.5.2'); self.distribution('asof-target-agents','0.3.13')
        proof=runtime.launcher_proof(trusted)
        self.assertEqual(proof['installed_distributions'],{'asof-target-agents':'0.3.13','tether-target-agents':'0.5.2'})

    def test_trusted_pair_must_equal_actual_pair_each_call(self):
        trusted=self.payload()
        runtime.launcher_proof(trusted)
        trusted['versions']=dict(tether='0.5.2',asof='0.3.13')
        with self.assertRaisesRegex(old.PolicyError,'Trusted runtime version differs'):
            runtime.launcher_proof(trusted)
        trusted=self.payload(('0.5.2','0.3.12'))
        with self.assertRaisesRegex(old.PolicyError,'Unsupported installed package version'):
            runtime.launcher_proof(trusted)

    def test_distribution_mismatch_and_duplicate_metadata_reject(self):
        trusted=self.payload()
        self.distribution('tether-target-agents','0.5.2')
        with self.assertRaisesRegex(old.PolicyError,'distribution version differs'):
            runtime.launcher_proof(trusted)
        self.distribution('tether-target-agents','0.5.1')
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
        (self.root/'asof/logic.py').write_text('VALUE = 3\n',encoding='utf-8')
        self.assertNotEqual(core_before,old_runtime.core_code(trusted))

    def test_unstable_capture_and_nonliteral_actual_version_reject(self):
        trusted=self.payload()
        with patch.object(runtime,'capture',side_effect=[{'one':1},{'two':2}]):
            with self.assertRaisesRegex(old.PolicyError,'changed during capture'):
                runtime.launcher_proof(trusted)
        (self.root/'tether/__init__.py').write_text("__version__ = '.'.join(['0','5','1'])\n",encoding='utf-8')
        with self.assertRaisesRegex(old.PolicyError,'literal'):
            runtime.launcher_proof(trusted)

    def test_source_closure_has_no_product_imports_and_original_helpers_match_freeze(self):
        names=('independent','independent_local','independent_policy','independent_render','independent_runtime','independent_schema')
        frozen=json.loads((PROJECT/'data/benchmark/tether-equal-policy-20261102-attempt03/FROZEN.json').read_bytes())
        for prefix,members in (('equal_policy',names),('equal_policy_v2',('independent','independent_runtime'))):
            for name in members:
                module=importlib.import_module(prefix+'.'+name); path=Path(module.__file__)
                for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                    if isinstance(node,ast.Import): imports=[x.name for x in node.names]
                    elif isinstance(node,ast.ImportFrom): imports=[node.module or '']
                    else: continue
                    self.assertFalse(any(x.split('.')[0] in ('asof','tether') for x in imports),(path,imports))
                if prefix=='equal_policy':
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),frozen['sources'][path.relative_to(PROJECT).as_posix()]['sha256'])
        code='import sys,json; sys.path.insert(0,'+repr(str(PROJECT/'experiments'))+'); import equal_policy_v2.independent; print(json.dumps([n for n in sys.modules if n.split(".")[0] in ("asof","tether")]))'
        result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,timeout=20,check=True)
        self.assertEqual(json.loads(result.stdout),[])


def native_suite():
    """Native classes are created only by the explicit isolated driver."""
    from equal_policy import cases, materialize, policy_cases, reference

    class InstalledOuterParity(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            identity=reference.runtime_identity()
            if not sys.flags.isolated or Path(sys.executable).resolve()!=(QUALIFIED/'environment/Scripts/python.exe').resolve():
                raise RuntimeError('Native parity requires the original qualified installed interpreter with -I')
            if identity['tether_version']!='0.5.1' or identity['asof_version']!='0.3.12':
                raise RuntimeError('This parity control compares the original supported pair')
            if not all('site-packages' in identity[k] for k in ('asof_file','tether_file')):
                raise RuntimeError('Product imports must come from the qualified installation')
            cls.trusted=reference.trusted_runtime(QUALIFIED)

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
