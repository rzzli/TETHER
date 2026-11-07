"""Unscored v2 corpus construction/admission tests; no scored corpus execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'experiments'))
from equal_policy import cases as original
from equal_policy_v2 import cases


class CorrectedCorpusTests(unittest.TestCase):
    def specs(self):
        return {row['control_id']: row for row in cases.case_specs()}

    def temporary(self):
        cache = PROJECT / 'data/cache/equal-policy-v2-corpus-unit'
        cache.mkdir(parents=True, exist_ok=True)
        context = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(context.cleanup)
        return Path(context.name)

    def test_inventory_is_explicitly_posthoc_exposed(self):
        rows = cases.case_specs()
        self.assertEqual(len(rows), 109)
        self.assertEqual([r['control_id'] for r in rows], [f'EP{i:03d}' for i in range(1,110)])
        self.assertTrue(all(r['construction_stratum']=='exposed_authored_construction' for r in rows))
        self.assertEqual(cases.oracle_manifest()['corpus_id'],'tether-equal-policy-fictional-v2')

    def test_original_declarations_unchanged_and_results_not_imported(self):
        before = original.canonical(original.case_specs())
        docs = cases.case_specs(); docs[0]['oracle']['observables'].clear()
        self.assertEqual(original.canonical(original.case_specs()), before)
        self.assertTrue(cases.case_specs()[0]['oracle']['observables'])
        tree = ast.parse(Path(cases.__file__).read_text(encoding='utf-8'))
        forbidden = {'tether_engine','tether','reference','independent','reconstruct','run_comparison'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom): names=[node.module or '']+[a.name for a in node.names]
            else: continue
            self.assertFalse(any(name.split('.')[-1] in forbidden for name in names),names)

    def test_corrupt_recovery_reject_has_no_successful_recovery_observables(self):
        spec = self.specs()['EP077']
        self.assertEqual(spec['oracle']['decision'],'reject')
        self.assertEqual(spec['oracle']['observables'],{})
        self.assertEqual(spec['preparation']['recipe']['sealed_mutation'],'journal_chain')

    def test_lineage_escape_source_is_correctly_sealed(self):
        docs=cases.prepare_documents(self.specs()['EP023'])
        extra=next(n for n in docs['snapshot']['sources'] if n['source_id']=='unrelated-source')
        self.assertEqual(extra['sha256'],hashlib.sha256(cases.file_bytes(docs['source'])).hexdigest())
        self.assertEqual(extra['receipt_sha256'],hashlib.sha256(cases.file_bytes(docs['receipt'])).hexdigest())
        self.assertEqual(docs['evidence']['observations'][0]['input_refs'],['unrelated-source'])
        self.assertEqual(docs['snapshot']['artifacts'][0]['input_refs'],['mapping-1'])

    def test_lineage_escape_is_the_only_blocker_in_corrected_unit_fixture(self):
        from equal_policy import independent, reference
        root=self.temporary()/'lineage'
        spec=self.specs()['EP023']; descriptor,_=cases.write_source_bundle(root,spec)
        for validator in (reference.validate_bundle,independent.validate_bundle):
            result=validator(root,descriptor)
            self.assertEqual(result['decision'],'reject',result)
            self.assertIn('lineage escapes',result.get('reason',result.get('error','')))
        documents=cases.prepare_documents(spec)
        documents['evidence']['observations'][0]['input_refs']=['mapping-1']
        documents['snapshot']['artifacts'][0]['sha256']=hashlib.sha256(cases.file_bytes(documents['evidence'])).hexdigest()
        for name in ('snapshot','evidence'):
            (root/'input'/(name+'.json')).write_bytes(cases.file_bytes(documents[name]))
        for validator in (reference.validate_bundle,independent.validate_bundle):
            result=validator(root,descriptor)
            self.assertEqual(result['decision'],'accept',result)

    def test_overquote_has_later_admitted_eligible_records_in_both_implementations(self):
        from equal_policy import independent, reference
        from tether_engine.chrono import load_snapshot
        from tether_engine.contracts import Case, Category
        from tether_engine.serde import decode
        identity=reference.runtime_identity()
        self.assertTrue(sys.flags.isolated)
        self.assertTrue(all('site-packages' in identity[k] for k in ('tether_engine_file','tether_file')))
        root=self.temporary()
        for cid in ('EP072','EP097'):
            with self.subTest(control=cid):
                folder=root/cid
                spec=copy.deepcopy(self.specs()[cid]); spec['operation']='prepare_run'
                descriptor,pending=cases.write_source_bundle(folder,spec)
                case_doc=json.loads((folder/'input/case.json').read_bytes())
                snapshot_doc=json.loads((folder/'input/snapshot.json').read_bytes())
                catalog=json.loads((folder/'input/catalog.json').read_bytes())
                store=load_snapshot(folder/'input/snapshot.json',decode(Case,case_doc),folder/'input/catalog.json')
                native=store.query(decode(Case,case_doc),Category.PERTURBATION)
                self.assertEqual([r.observation.observation_id for r in native],['obs-later-perturbation'])
                other=independent.admit(independent.decode('Case',case_doc),independent.decode('Snapshot',snapshot_doc),folder/'input',catalog)
                later=[k for k,r in other['records'].items() if independent.permitted(case_doc,r,'perturbation')]
                self.assertEqual(later,['obs-later-perturbation'])
                self.assertEqual(other['exclusions'],[])
                with patch('tether_engine.agents.ExtractiveBackend.quote',side_effect=AssertionError('No quote')) as quote, \
                     patch('tether_engine.agents.ExtractiveBackend.select',side_effect=AssertionError('No dispatch')) as select, \
                     patch('tether_engine.local_model.LocalSelectionBackend.quote',side_effect=AssertionError('No local quote')), \
                     patch('tether_engine.local_model.LocalSelectionBackend.select',side_effect=AssertionError('No local dispatch')):
                    for validator in (reference.validate_bundle,independent.validate_bundle):
                        result=validator(folder,descriptor)
                        self.assertEqual(result['decision'],'accept',result)
                        self.assertEqual(result['observables']['eligible_observation_ids'],['obs-1','obs-later-perturbation'])
                    quote.assert_not_called(); select.assert_not_called()

    def test_clean_recorded_parent_has_independent_normative_observables(self):
        spec=self.specs()['EP109']
        self.assertEqual(spec['preparation']['recipe']['sealed_producer'],'valid_recorded')
        self.assertEqual(spec['preparation']['recipe']['sealed_mutation'],'none')
        self.assertEqual(spec['oracle']['decision'],'accept')
        self.assertEqual(spec['oracle']['observables']['feature_values'],{'genetic_support':0.75})
        self.assertEqual(spec['oracle']['observables']['selected_observation_ids'],['obs-1'])
        self.assertEqual(spec['oracle']['observables']['prediction_status'],'scored')
        self.assertFalse(spec['oracle']['observables']['probability_is_null'])
        self.assertEqual(self.specs()['EP075']['oracle']['decision'],'reject')

    def test_written_corrected_inputs_equal_in_memory_and_descriptor_hides_oracle(self):
        root=self.temporary()
        for cid in ('EP023','EP072','EP097','EP109'):
            with self.subTest(control=cid):
                spec=self.specs()[cid]; expected=cases.prepare_documents(spec)
                descriptor,pending=cases.write_source_bundle(root/cid,spec)
                self.assertNotIn('oracle',cases.canonical(descriptor).decode())
                for name,value in expected.items():
                    self.assertEqual((root/cid/'input'/(name+'.json')).read_bytes(),cases.file_bytes(value))
                with self.assertRaises(FileExistsError): cases.write_source_bundle(root/cid,spec)


if __name__=='__main__': unittest.main(verbosity=2)
