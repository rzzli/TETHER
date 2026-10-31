"""Exactly three root-selected observation/representability test corrections."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent


def once(t,a,b):
    assert t.count(a)==1,(a,t.count(a))
    return t.replace(a,b)


def live_then_finish(indent='            '):
    return '\n'.join(indent+x for x in [
        "held_ref=D.invoke(w.owner.file_ref,w.blobs[3]['path']);held_state=D.invoke(w.owner.file_state,held_ref)",
        "D.invoke(w.owner.reserve_output,fixture['common']['output_key']);D.invoke(w.owner.capture_early)",
        "token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)",
        "loaded=D.invoke(w.owner.load_source,'cohort_entry');D.invoke(w.owner.check)",
        "self.assertEqual(D.invoke(loaded.run),('cohort-entry-v1','cohort-leaf-v1'));D.invoke(w.owner.check)",
        "D.invoke(C.continue_once,continuation,C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))"])


def main():
    choice=H/'ROLE-AWARE-REPRESENTABILITY-AND-OBSERVATION-CORRECTION-v4.json'
    assert hashlib.sha256(choice.read_bytes()).hexdigest()=='73d80d6fa424b5135d8519f7952b86797ea69465407781fe5ba80507b02a28e9'
    raw=(H/'role_aware_producer_extension_tests_v1.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='a87ff334f2a4b6e03314a85d5960be1d3f6a6b709ba3095a100d14c5084d018f'
    t=raw.decode()
    t=once(t,"            guard();w=virtual_world(virtual_blobs(bulk_size=0,empty_metadata=True),S.PROFILE_N4)\n            try:",
        "            guard();w=virtual_world(virtual_blobs(bulk_size=0,empty_metadata=True),S.PROFILE_N4,run=False)\n            "+live_then_finish().lstrip()+"\n            try:")
    t=once(t,"                state=w.owner.file_state(w.owner.file_ref(w.blobs[3]['path']))\n                self.assertIsNone(state.assembly);self.assertIsNone(state.blob)",
        "                self.assertIs(held_ref._state,held_state);self.assertIs(w.owner.file_ref(w.blobs[3]['path']),held_ref)\n                state=held_state\n                self.assertIsNone(state.assembly);self.assertIsNone(state.blob)\n                with self.assertRaises(S.SharedOwnerError) as misuse:D.invoke(w.owner.file_state,held_ref)\n                self.assertEqual(misuse.exception.code,'FINALIZED_MISUSE')")
    t=once(t,"                raw=legacy(w);self.assertFalse(raw['pure_seam_complete'])",
        "                issued=D.invoke(w.owner.snapshot);self.assertIs(type(issued),S.ProducerSnapshot);self.assertIs(issued.owner,w.owner)\n                raw=D.invoke(issued.to_dict);self.assertFalse(raw['pure_seam_complete'])\n                self.assertEqual(raw['schema_version'],2);self.assertEqual(raw['errors']['primary']['phase'],'freeze')\n                self.assertIs(w.owner.exception_for_token(raw['errors']['primary']['identity']),error)\n                with self.assertRaises(L.FormatError) as refused:D.projected_snapshot(w,issued)\n                self.assertEqual(refused.exception.code,'LEGACY_NOT_REPRESENTABLE')\n                self.assertIs(w.owner.primary,error);self.assertTrue(D.same(raw,D.invoke(issued.to_dict)))")
    t=once(t,"            w=virtual_world(blobs,S.PROFILE_ORIGINAL7_1M,artifacts=True)\n            try:",
        "            w=virtual_world(blobs,S.PROFILE_ORIGINAL7_1M,artifacts=True,run=False)\n            "+live_then_finish().lstrip()+"\n            try:")
    t=once(t,"                bulk=w.owner.file_state(w.owner.file_ref(blobs[3]['path']))\n                self.assertIsNone(bulk.assembly);self.assertIsNone(bulk.blob);self.assertEqual(bulk.capture_state,'NOT_REQUESTED')",
        "                self.assertIs(held_ref._state,held_state);self.assertIs(w.owner.file_ref(blobs[3]['path']),held_ref)\n                bulk=held_state\n                self.assertIsNone(bulk.assembly);self.assertIsNone(bulk.blob);self.assertEqual(bulk.capture_state,'NOT_REQUESTED')\n                with self.assertRaises(S.SharedOwnerError) as misuse:D.invoke(w.owner.file_state,held_ref)\n                self.assertEqual(misuse.exception.code,'FINALIZED_MISUSE')")
    with (H/'role_aware_producer_extension_tests_v2.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    print('Prepared three-method-only extension testsV2; no subject import/test')


if __name__=='__main__':main()
