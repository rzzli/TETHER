"""Public API uses real supervision with fictional policy-bound inputs."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tether.api import PolicyInputs, BundleArtifact, run_offline, verify_run, export_run, verify_bundle
from tether import _presentation, _catalog_policy
from tether_engine.serde import ContractError, fingerprint

if __package__:
    from .catalog_fixtures import make_fixture, write
else:
    from catalog_fixtures import make_fixture, write


class PublicApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="public-api-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exports = tempfile.TemporaryDirectory(prefix="public-api-exports-")
        self.addCleanup(self.exports.cleanup)
        self.export_root = Path(self.exports.name)
        self.f = make_fixture(self.root)
        p = self.f["paths"]
        self.f['case'].update(task='T6', program=None, endpoint=None)
        artifact = self.f['snapshot']['artifacts'][0]
        packet = self.f['normalized']/artifact['path']
        document = json.loads(packet.read_bytes())
        document['observations'] = [row for row in document['observations'] if row['category'] != 'clinical']
        write(packet, document)
        artifact['sha256'] = hashlib.sha256(packet.read_bytes()).hexdigest()
        old = self.f['policy']['artifacts'][-1]
        new = _catalog_policy.artifact_record(**{k:v for k,v in old.items() if k not in ('artifact_id','sha256','bytes')},
                                              sha256=artifact['sha256'],bytes=packet.stat().st_size)
        self.f['policy']['artifacts'][-1] = new
        self.f['policy']['uses'][0]['grants'][-1]['artifact_id'] = new['artifact_id']
        self.f['policy']['uses'][0]['snapshot_fingerprint'] = fingerprint(self.f['snapshot'])
        self.f['policy']['uses'][0]['case_fingerprint'] = fingerprint(self.f['case'])
        write(p['snapshot'], self.f['snapshot'])
        write(p['case'], self.f['case'])
        write(p['policy'], self.f['policy'])
        self.inputs = PolicyInputs(p["case"], p["snapshot"], p["source_catalog"], p["policy"], p["roots"],
                                   "fictional-use", "f" * 64)

    def test_run_verify_export_relocate_and_corruption(self):
        run = run_offline(self.inputs, self.root / "run", source_roots=(self.root,))
        self.assertTrue(run.dossier.is_file())
        report = verify_run(run, source_roots=(self.root,))
        self.assertEqual(report['artifact_policy']['status'], 'artifact_policy_consistency_verified')
        bundle = export_run(run, self.export_root / "bundle", source_roots=(self.root,))
        with self.assertRaises(ContractError):
            export_run(replace(run, engine_receipt_sha256="0"*64), self.root/"wrong", source_roots=(self.root,))
        self.assertFalse((self.root/"wrong").exists())
        moved = self.export_root / "relocated Ω"
        bundle.directory.rename(moved)
        # Delete only this test's newly created input folders; originals do not exist outside it.
        shutil.rmtree(self.f['normalized'])
        shutil.rmtree(self.f['raw_root'])
        self.assertEqual(verify_bundle(BundleArtifact(moved, bundle.manifest_sha256))['source_tier'], 'included')
        with self.assertRaises(ContractError):
            verify_bundle(BundleArtifact(moved, "0"*64))

    def test_missing_roots_and_bad_grant_never_dispatch(self):
        for reason in ('roots', 'grant'):
            with self.subTest(reason=reason), patch.object(_presentation, 'invoke_engine') as call:
                if reason == 'grant':
                    self.f['policy']['uses'][0].update(status='blocked', blockers=['fictional denial'])
                    write(self.f['paths']['policy'],self.f['policy'])
                output = self.root / reason
                with self.assertRaises(ContractError):
                    run_offline(self.inputs, output, source_roots=() if reason == 'roots' else (self.root,))
                call.assert_not_called()
                self.assertTrue((output/'tether-failure.json').is_file())

    def test_collision_never_dispatches_or_overwrites(self):
        output = self.root/'occupied'
        output.mkdir()
        (output/'sentinel').write_bytes(b'keep')
        with patch.object(_presentation,'invoke_engine') as call, self.assertRaises(FileExistsError):
            run_offline(self.inputs,output,source_roots=(self.root,))
        call.assert_not_called()
        self.assertEqual((output/'sentinel').read_bytes(),b'keep')

    def test_invalid_parameters_fail_before_output_creation(self):
        for kwargs, kind in ((dict(source_roots=[self.root]),TypeError),
                             (dict(source_roots=(self.root,),process_timeout_seconds=-1),ContractError)):
            with self.subTest(kwargs=kwargs), self.assertRaises(kind):
                run_offline(self.inputs,self.root/'invalid',**kwargs)
            self.assertFalse((self.root/'invalid').exists())
        with self.assertRaises(TypeError):
            run_offline(self.inputs, 'not-a-Path', source_roots=(self.root,))

    def test_unknown_use_and_false_frame_fail_before_dispatch(self):
        for change in (dict(use_id='unknown'),dict(frame_sha256='0'*64)):
            with self.subTest(change=change), patch.object(_presentation,'invoke_engine') as call:
                with self.assertRaises(ContractError):
                    run_offline(replace(self.inputs,**change),self.root/next(iter(change)),source_roots=(self.root,))
                call.assert_not_called()
