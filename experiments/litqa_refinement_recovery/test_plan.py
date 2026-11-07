"""Permanent authority controls with an explicitly invented parent capability."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from tether_engine.serde import encode,freeze
from . import contracts as c,plan,original
from .test_contracts import payload


class RecoveryPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall);patch.object(c,'ROOT',self.root).start()
        self.payload=payload(self.root);self.descriptor=dict(inspection={},source_archive={},baseline_acceptance={})
        self.registry=c.authority_registry(original_root=self.payload['original_root'],purpose='fictional_qualification');self.registry.mkdir(parents=True)
        self.reconstruct=patch.object(original,'reconstruct',side_effect=lambda *a,**kw:SimpleNamespace(payload=freeze(self.payload))).start()
        self.revalidation_patch=patch.object(original,'revalidate',return_value=True)
        self.revalidate=self.revalidation_patch.start()
        patch.object(plan,'_sources',return_value=freeze([{'test_only_source_closure':1}])).start()

    def test_plan_and_reservation_are_pure_and_independent_of_output(self):
        value=plan.prepare(self.descriptor);self.assertFalse(value['automatic_retry']);self.assertEqual(value['partition']['repair_dispatch'],(1,))
        result=plan.reserve(value,self.registry,self.root/'planning')
        reread,_=plan.verify(result['plan'],result['authority']);self.assertEqual(reread,value)
        self.assertFalse(c.read(result['complete'])['model_or_http_execution_performed'])

    def test_second_output_cannot_claim_same_parent(self):
        value=plan.prepare(self.descriptor);first=plan.reserve(value,self.registry,self.root/'first');raw=Path(first['authority']['path']).read_bytes()
        with self.assertRaises(FileExistsError):plan.reserve(value,self.registry,self.root/'second')
        self.assertEqual(Path(first['authority']['path']).read_bytes(),raw)
        self.assertTrue(c.read(c.capture(self.root/'second/FAILURE.json')[0])['authority_may_be_reserved'])

    def test_alternate_registry_rejected(self):
        alternate=self.root/'alternate';alternate.mkdir();value=plan.prepare(self.descriptor)
        with self.assertRaisesRegex(ValueError,'stable'):plan.reserve(value,alternate,self.root/'planning')
        self.assertFalse((self.root/'planning').exists())

    def test_mutated_plan_fails_before_authority(self):
        value=encode(plan.prepare(self.descriptor));value['partition']['repair_dispatch']=[0,1]
        with self.assertRaises(ValueError):plan.reserve(value,self.registry,self.root/'planning')
        self.assertEqual(list(self.registry.iterdir()),[])

    def test_changed_original_after_claim_keeps_permanent_reservation(self):
        value=plan.prepare(self.descriptor)
        def changed(verified):
            if (self.registry/value['parent_identity']/'AUTHORITY.json').exists():raise ValueError('invented parent change')
            return True
        with patch.object(original,'revalidate',side_effect=changed),self.assertRaisesRegex(ValueError,'parent change'):
            plan.reserve(value,self.registry,self.root/'planning')
        self.assertTrue((self.registry/value['parent_identity']/'AUTHORITY.json').is_file())
        self.assertTrue((self.root/'planning/FAILURE.json').is_file())

    def test_reservation_reuses_one_exact_issued_parent(self):
        value=plan.prepare(self.descriptor);self.reconstruct.reset_mock();self.revalidate.reset_mock()
        plan.reserve(value,self.registry,self.root/'planning')
        self.assertEqual(self.reconstruct.call_count,1)
        handles=[call.args[0] for call in self.revalidate.call_args_list]
        self.assertGreaterEqual(len(handles),2);self.assertTrue(all(item is handles[0] for item in handles))

    def test_verify_can_return_issued_parent_without_second_reconstruction(self):
        reserved=plan.reserve(plan.prepare(self.descriptor),self.registry,self.root/'planning');self.reconstruct.reset_mock()
        value,authority,verified=plan.verify(reserved['plan'],reserved['authority'],return_parent=True)
        self.assertEqual(self.reconstruct.call_count,1);self.assertEqual(verified.payload['schedule'],value['schedule'])

    def test_changed_reader_closure_after_claim_is_rejected(self):
        value=plan.prepare(self.descriptor)
        def sources():return ({'version':2 if (self.registry/value['parent_identity']/'AUTHORITY.json').exists() else 1},)
        with patch.object(plan,'_sources',side_effect=sources,create=True),self.assertRaisesRegex(ValueError,'source closure'):
            plan.reserve(value,self.registry,self.root/'planning')
        self.assertTrue((self.registry/value['parent_identity']/'AUTHORITY.json').is_file())

    def test_reuse_does_not_accept_forged_or_copied_capability(self):
        # Unmock the real registry boundary: knowing its token/fields is not
        # authority to create a new operation-scoped parent capability.
        self.revalidation_patch.stop()
        forged=original.VerifiedParent(freeze(self.payload),original.fingerprint(self.payload),original._TOKEN)
        with self.assertRaisesRegex(ValueError,'Issued'):plan._revalidate(forged,plan._sources())

    def test_resealed_authority_cannot_enlarge_dispatch(self):
        result=plan.reserve(plan.prepare(self.descriptor),self.registry,self.root/'planning')
        value=encode(c.read(result['authority']));value['allowed_dispatch']['repair']=[0,1]
        target=Path(result['authority']['path']);target.write_bytes(canonical(value))
        with self.assertRaises(ValueError):plan.verify(result['plan'],c.capture(target)[0])


from tether_engine.serde import canonical
if __name__=='__main__':unittest.main()
