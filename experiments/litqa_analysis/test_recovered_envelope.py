"""Fictional supervised envelopes; invented native responses, no live models."""
from contextlib import contextmanager
from pathlib import Path
import os
import socket
import unittest
from unittest.mock import patch

from tether_engine.serde import encode
from experiments.litqa_recovery import test_run as controls
from experiments.litqa_analysis import recovered_envelope as e
from experiments.litqa_analysis import test_recovered_run as fixtures


class RecoveredEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.block = patch.object(socket,'create_connection',side_effect=AssertionError('No live transport'))
        self.block.start(); self.addCleanup(self.block.stop)
        self.f = controls.ControllerTests('runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        # Replace the controller unit fixture's abbreviated pin map with the
        # actual complete current source closure before freezing any execution.
        pins = {name:e.envelopes.proof(e.REPO/name)['sha256'] for name in e._code_names()}
        controls.r.source_pins.return_value = pins
        qualification_path = Path(self.f.certificate['qualification']['path'])
        qualification = e.load(qualification_path); qualification['code_pins'] = pins
        qualification_path.write_bytes(e.canonical(qualification)+b'\n')
        self.f.certificate['qualification'] = e.envelopes.proof(qualification_path)
        self.f.certificate['current_code_pins'] = pins
        cert_path = Path(self.f.certificate_proof['path']); cert_path.write_bytes(e.canonical(self.f.certificate)+b'\n')
        self.f.certificate_proof = e.envelopes.proof(cert_path)
        self.f.frame.update(code_pins=pins,transition_certificate=self.f.certificate_proof)
        frame_path = Path(self.f.frame_proof['path']); frame_path.write_bytes(e.canonical(self.f.frame)+b'\n')
        self.f.frame_proof = e.envelopes.proof(frame_path)
        self.f.owner = self.owner
        self.original_child = self.f.child
        self.f.child = self.child

    @contextmanager
    def owner(self,spec,bindings,*,output,journal,parent_deadline):
        owner = self.f.n.f.owner; self.f.server_calls += 1
        record = dict(started=True,pid=12345,server_stopped=False,exit_code=None,secondary_failures=[],
            peak_native_memory_bytes=None,peak_native_memory_reason='Invented fixture',elapsed_seconds=.01)
        owner.terminal_record = record
        (output/'server-command.json').write_bytes(e.canonical(encode(spec)))
        for name in ('server.stdout.log','server.stderr.log'): (output/name).write_bytes(b'')
        journal.append('server_started',pid=12345); journal.append('server_ready',pid=12345)
        try: yield owner
        finally:
            record.update(server_stopped=True,exit_code=0)
            journal.append('server_terminal',**record)

    def child(self,command,*,limits):
        result = self.original_child(command,limits=limits)
        options = dict(zip(command[7::2],command[8::2])); root = Path(options['--output'])
        worker = command[6]=='worker'
        path = root/'CONFIG.json' if worker else root.parent/'worker/CONFIG.json'
        rows = [dict(path=str(path),mode='r',flags=0,allowed=True,basis='output' if worker else 'explicit_data_or_runtime')]
        if worker and root.parent.name=='collect':
            rows.append(dict(path=str(self.f.authority/'collection-execution/CLAIM.json'),mode='x',
                flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL,allowed=True,basis='exclusive_collection_claim'))
        (root/'io-audit.jsonl').write_bytes(b''.join(e.canonical(r)+b'\n' for r in rows))
        return result

    def execute(self): return self.f.execute()

    def check(self):
        return e.reconstruct(self.f.output,e.envelopes.proof(self.f.output/'ROOT-RECEIPT.json')['sha256'])

    def seal(self,phase=None):
        root = self.f.output; complete = e.load(root/'COMPLETE.json')
        if phase:
            phase_root = root/phase; package = e.load(phase_root/'PACKAGE-RECEIPT.json')
            package['files'] = e.envelopes.inventory(phase_root,omit=('PACKAGE-RECEIPT.json',))
            (phase_root/'PACKAGE-RECEIPT.json').write_bytes(e.canonical(package))
            complete['phases'][phase]['receipt'] = e.envelopes.proof(phase_root/'PACKAGE-RECEIPT.json')
        (root/'COMPLETE.json').write_bytes(e.canonical(complete))
        events = e.journal(root/'journal.jsonl')
        for event in events:
            if event['event']=='phase_accepted': event['details']['descriptor'] = complete['phases'][event['details']['phase']]
        events[-1]['details']['complete'] = e.envelopes.proof(root/'COMPLETE.json')
        fixtures.RecoveredRunTests.rechain(root/'journal.jsonl',events)
        receipt = e.load(root/'ROOT-RECEIPT.json'); receipt['files'] = e.envelopes.inventory(root,omit=('ROOT-RECEIPT.json',))
        (root/'ROOT-RECEIPT.json').write_bytes(e.canonical(receipt))

    def test_complete_envelope_and_answers_reconstruct_without_maintained_replay(self):
        self.execute()
        with patch.object(controls.r,'replay',side_effect=AssertionError('No maintained attestation')), \
             patch.object(controls.r,'verify_frame',side_effect=AssertionError('No maintained frame verification')):
            result = self.check()
        self.assertTrue(result['supervised_root_verified'])
        self.assertTrue(result['native_calls_checked'])
        self.assertEqual(len(result['records']['supplied']),3)
        self.assertEqual(result['resources']['answer']['model']['generation_calls'],3)
        self.assertFalse(result['scientific_correctness_scored'])
        self.assertFalse(result['producer_equivalence_independently_adjudicated'])

    def test_resealed_negative_controller_time_is_rejected(self):
        self.execute(); path = self.f.output/'COMPLETE.json'; value=e.load(path)
        value['wall_seconds']=-1; path.write_bytes(e.canonical(value)); self.seal()
        with self.assertRaisesRegex(ValueError,'Controller elapsed'): self.check()

    def test_resealed_root_failure_marker_is_rejected(self):
        self.execute(); (self.f.output/'FAILURE.json').write_text('{}'); self.seal()
        with self.assertRaisesRegex(ValueError,'root artifact membership'): self.check()

    def test_resealed_review_failure_event_is_rejected(self):
        self.execute(); path=self.f.output/'answer/review/journal.jsonl'; events=e.journal(path)
        events.append(dict(sequence=len(events),previous_sha256=None,event='execution_failed',details={},sha256=''))
        fixtures.RecoveredRunTests.rechain(path,events); self.seal('answer')
        with self.assertRaisesRegex(ValueError,'review event binding'): self.check()

    def test_resealed_worker_path_escape_is_rejected_by_independent_audit(self):
        self.execute(); path=self.f.output/'answer/worker/io-audit.jsonl'
        value=dict(path=str(self.f.output/'answer/worker/../../../private.json'),mode='w',flags=os.O_WRONLY,
                   allowed=True,basis='output')
        path.write_bytes(e.canonical(value)+b'\n'); self.seal('answer')
        with self.assertRaisesRegex(ValueError,'allowlist classification'): self.check()

    def test_resealed_supervisor_cleanup_failure_is_rejected(self):
        self.execute(); path=self.f.output/'answer/execution-SUPERVISION.json'; value=e.load(path)
        value['supervision']['process_reaped']=False; path.write_bytes(e.canonical(value)); self.seal('answer')
        with self.assertRaisesRegex(ValueError,'process supervision'): self.check()

    def test_resealed_model_identity_substitution_is_rejected(self):
        self.execute(); path=self.f.output/'answer/worker/MODEL.json'; value=e.load(path)
        value['alias']='substituted'; path.write_bytes(e.canonical(value)); self.seal('answer')
        with self.assertRaisesRegex(ValueError,'model launch'): self.check()

    def test_resealed_undeclared_phase_artifact_is_rejected(self):
        self.execute(); (self.f.output/'answer/extra.json').write_text('{}'); self.seal('answer')
        with self.assertRaisesRegex(ValueError,'phase artifact membership'): self.check()

    def test_upper_envelope_changed_during_lower_reconstruction_is_rejected(self):
        self.execute(); original=e.recovered_run.native_records.reconstruct; changed=False
        def mutate(*args,**kwargs):
            nonlocal changed
            if not changed:
                changed=True
                path=self.f.output/'COMPLETE.json'
                value=e.load(path); value['wall_seconds']+=1
                path.write_bytes(e.canonical(value))
            return original(*args,**kwargs)
        with patch.object(e.recovered_run.native_records,'reconstruct',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed|mismatch'): self.check()
        self.assertTrue(changed)


if __name__=='__main__': unittest.main()
