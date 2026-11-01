"""Invented scientific claims/ratings test the contract, never biological truth."""
import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from asof.serde import ContractError, canonical, fingerprint, parse_json, write_json
from tools.science.run_comparison import pin
from tools.science.t6_claim_audit import pointer
from tools.science.t6_contextual_audit import (assess_review, json_nodes, proposition_key,
    surface_from_binding, validate_inventory, compile_surface, audit_v2, build_surface)


class ContextualContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.question = dict(target_id='TEST', indication_id='DISEASE', target_namespace_version='fixture-v1',
            indication_namespace_version='fixture-v1', intended_action='inhibit', modality='antibody', tissue=None)
        self.metric = dict(score=0.8, textMiningSentences=[
            dict(text='Receptor R inhibits signaling; a second clause says "beta β".\nContext follows.'),
            dict(text='Receptor R inhibits signaling; a second clause says "beta β".\nContext follows.'),
            dict(text='MR X to Y: estimate -0.02; interval [-0.03,-0.01]; P 0.01; replication estimate 0.3.')])
        self.doc = self.root / 'dossier.md'
        body = b'# Fixture\r\nUncited interpretation.\r\n'
        units = []
        for identity in ('r1', 'r2'):
            start = len(body)
            body += ('### ' + identity + '\r\n> Source reports a link.\r\n').encode()
            body += b'Provider metrics (descriptive): `' + canonical(self.metric) + b'`.\r\n'
            units.append(dict(observation_id=identity, section_span=dict(start=start, end=len(body)),
                source_audit=dict(projected_original_row=dict(self.metric, id=identity, targetId='TEST',
                    diseaseId='DISEASE', datasourceId='fixture', datatypeId='literature'))))
        self.doc.write_bytes(body)
        self.binding = dict(dossier=pin(self.doc), question=self.question, source_units=units)
        self.surface = surface_from_binding(self.binding)
        self.nodes = {n['node_id']: n for n in self.surface['nodes']}
        self.node = next(n for n in self.surface['nodes'] if n.get('pointer') == '/textMiningSentences/0/text'
                         and n['source_unit_id'] == 'r1')
        self.inventory = self.make_inventory([self.make_claim('c1', self.node)])
        self.references = []
        self.review = self.make_review()

    def fragment(self, node, text=None, last=False):
        raw = self.doc.read_bytes()[node['raw_span']['start']:node['raw_span']['end']]
        value = raw.decode('utf-8') if node['value_type'] == 'literal' else parse_json(raw)
        decoded = value if isinstance(value, str) else raw.decode('utf-8')
        text = text or decoded
        start = decoded.encode().rindex(text.encode()) if last else decoded.encode().index(text.encode())
        return dict(node_id=node['node_id'], span=dict(start=start, end=start + len(text.encode())), text=text)

    def make_claim(self, identity, node):
        return dict(claim_id=identity, stratum='scientific', stance='source_attributed', unit_kind='proposition',
            context=dict(scope='record', id=node['source_unit_id']),
            proposition=dict(subject='Receptor R', predicate='inhibits', object='signaling', negation=False,
                modal='asserted', population=None, tissue=None, intervention=None, comparator=None,
                outcome=None, timing=None, orientation=None),
            focus=self.fragment(node, 'Receptor R inhibits signaling'), context_fragments=[],
            entity_resolution='resolved', entity_reason='Invented fixture subject explicitly named.', numeric_bundle=None,
            dependence=dict(status='unknown',group_ids=[],reason='Source overlap unqualified; not independent.'))

    def make_inventory(self, claims):
        value = dict(schema_version=2, role='evaluation_only', status='draft', annotator_id='fixture-atomizer',
            surface_sha256=fingerprint(self.surface), question=copy.deepcopy(self.question), claims=claims,
            line_dispositions=[], value_dispositions=[])
        for line in self.surface['lines']:
            value['line_dispositions'].append(dict(line_id=line['line_id'], kind='uncertain',
                reason='Full semantic extraction still pending.', claim_ids=[]))
        for node in self.surface['nodes']:
            if node['value_type'] == 'literal':continue
            linked = [c['claim_id'] for c in claims if c['focus']['node_id'] == node['node_id']]
            kind = ('container_context' if node['value_type'] in {'object','array'} else
                    'scientific' if linked else 'uncertain' if node.get('pointer','').endswith('/text') else 'source_data')
            value['value_dispositions'].append(dict(node_id=node['node_id'], kind=kind,
                reason='Invented fixture value disposition; no atomic completeness claim.', claim_ids=linked))
        return value

    def make_review(self):
        return dict(schema_version=2, role='evaluation_only', reviewer_id='fixture-reviewer',
            mode='development_source_review', inventory_sha256=fingerprint(self.inventory),
            surface_sha256=fingerprint(self.surface), references_sha256=fingerprint(self.references),
            claims=[dict(claim_id=c['claim_id'], source_fidelity='supported', scientific_validity='unassessable',
                         applicability='uncertain', attribution='correct', uncertainty='high',
                         reason='Faithfully quoted invented premise; biological truth not inferred.', reference_ids=[])
                    for c in self.inventory['claims']])

    def assess(self, rebind=False):
        if rebind:
            self.review['inventory_sha256'] = fingerprint(self.inventory)
            self.review['references_sha256'] = fingerprint(self.references)
        return assess_review(self.inventory, self.surface, self.review, self.references, approved_roots=[self.root])

    def reference(self):
        parent=dict(role='evaluation_only',facet=dict(statement='Invented referee judgment; not biological evidence.'))
        self.parent=self.root/'adjudication.json';write_json(self.parent,parent)
        value = dict(schema_version=1, role='evaluation_only', reference_id='ref1',
            binding_sha256=self.surface['binding_sha256'],
            question_sha256=fingerprint(self.question), proposition_key=proposition_key(self.inventory['claims'][0], self.question),
            qualification='scope_adjudicated', attestor_id='fixture-adjudicator',
            basis_proof=pin(self.parent),basis_pointer='/facet',basis_value_sha256=fingerprint(parent['facet']),
            basis='Invented scoped judgment for a contract test.', limitations='Not real science or a primary paper.')
        self.ref = self.root / 'reference.json';write_json(self.ref, value)
        self.references = [pin(self.ref)]
        return value

    def test_json_strings_preserve_raw_escapes_and_separate_decoded_offsets(self):
        f=self.inventory['claims'][0]['focus'];self.assertIn('inhibits', f['text'])
        raw=self.doc.read_bytes()[self.node['raw_span']['start']:self.node['raw_span']['end']]
        self.assertIn(b'\\n',raw);self.assertIn(b'\\"',raw)
        validate_inventory(self.inventory,self.surface)
        beta=self.fragment(self.node,'β')
        self.inventory['claims'][0]['focus']=beta
        validate_inventory(self.inventory,self.surface)

    def test_surface_covers_every_byte_and_both_json_occurrences(self):
        self.assertEqual(self.surface['structural_coverage_bytes'],self.doc.stat().st_size)
        lines=self.surface['lines'];self.assertEqual(lines[0]['span']['start'],0)
        self.assertTrue(all(a['span']['end']==b['span']['start'] for a,b in zip(lines,lines[1:])))
        self.assertEqual(len([n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/0/text']),2)
        self.assertEqual(self.surface['scientific_atomization'],'not_performed')

    def test_json_pointer_tokens_match_original_values(self):
        payload=canonical({'a/b':{'~': ['β',0.5,False,None]}})
        data=parse_json(payload)
        for node in json_nodes(payload):
            raw=payload[node['raw_span']['start']:node['raw_span']['end']]
            self.assertEqual(fingerprint(parse_json(raw)),fingerprint(pointer(data,node['pointer'])))

    def test_duplicate_keys_nonfinite_trailing_bom_and_depth_fail(self):
        for payload in (b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"\\ud800":1}',b'{}x',
                        b'\xef\xbb\xbf{}', b'['*130+b'0'+b']'*130):
            with self.subTest(payload=payload[:30]),self.assertRaises(ContractError):json_nodes(payload)

    def test_same_words_with_different_record_subjects_are_distinct_groups(self):
        other=next(n for n in self.surface['nodes'] if n.get('pointer')==self.node['pointer'] and n['source_unit_id']=='r2')
        self.inventory=self.make_inventory([self.make_claim('c1',self.node),self.make_claim('c2',other)])
        self.review=self.make_review();self.assertEqual(self.assess()['canonical_group_count'],2)

    def test_repeated_occurrences_of_one_contextual_proposition_count_once(self):
        other=next(n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/1/text' and n['source_unit_id']=='r1')
        self.inventory=self.make_inventory([self.make_claim('c1',self.node),self.make_claim('c2',other)])
        self.review=self.make_review();result=self.assess()
        self.assertEqual(result['occurrence_count'],2);self.assertEqual(result['canonical_group_count'],1)

    def test_contradictory_duplicate_labels_require_adjudication(self):
        other=next(n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/1/text' and n['source_unit_id']=='r1')
        self.inventory=self.make_inventory([self.make_claim('c1',self.node),self.make_claim('c2',other)])
        self.review=self.make_review();self.review['claims'][1]['source_fidelity']='unsupported'
        with self.assertRaisesRegex(ContractError,'conflicting judgments'):self.assess()

    def test_faithful_questionable_source_can_have_scientific_contradiction(self):
        self.reference();self.review['claims'][0].update(scientific_validity='contradicted',reference_ids=['ref1'])
        result=self.assess(rebind=True)
        self.assertEqual(result['strata'][0]['axes']['source_fidelity']['supported'],1)
        self.assertEqual(result['strata'][0]['axes']['scientific_validity']['contradicted'],1)
        self.assertIsNone(result['scientific_error_rate'])

    def test_quoted_premise_cannot_become_dossier_endorsement(self):
        self.inventory['claims'][0]['stance']='dossier_endorsed'
        with self.assertRaisesRegex(ContractError,'endorsement'):validate_inventory(self.inventory,self.surface)

    def test_unresolved_antecedent_cannot_pass_definite_validity_or_applicability(self):
        self.inventory['claims'][0]['entity_resolution']='uncertain'
        self.review['claims'][0]['applicability']='applicable'
        with self.assertRaisesRegex(ContractError,'Unresolved entity'):self.assess(rebind=True)

    def test_no_scientific_rating_from_source_hash_or_unqualified_reference(self):
        self.review['claims'][0]['scientific_validity']='supported'
        with self.assertRaisesRegex(ContractError,'scoped adjudication'):self.assess()
        ref=self.reference();ref['qualification']='unreviewed';write_json(self.ref,ref);self.references=[pin(self.ref)]
        self.review['claims'][0]['reference_ids']=['ref1']
        with self.assertRaisesRegex(ContractError,'scoped adjudication'):self.assess(rebind=True)

    def test_opposite_actions_modalities_tissues_and_namespace_versions_cannot_reuse(self):
        for key,value in [('intended_action','activate'),('modality','ADC'),('tissue','brain'),('target_namespace_version','v2')]:
            modified=copy.deepcopy(self.inventory);modified['question'][key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):validate_inventory(modified,self.surface)

    def test_source_record_context_must_match_actual_occurrence(self):
        self.inventory['claims'][0]['context']['id']='r2'
        with self.assertRaisesRegex(ContractError,'Record context'):validate_inventory(self.inventory,self.surface)

    def test_clinical_and_cartesian_inference_candidates_stay_unassessable(self):
        self.inventory['claims'][0]['stratum']='clinical_unassessable'
        self.reference();self.review['claims'][0].update(scientific_validity='supported',reference_ids=['ref1'])
        with self.assertRaisesRegex(ContractError,'quarantined'):self.assess(rebind=True)

    def test_estimate_ci_p_are_one_oriented_bundle(self):
        claim=self.inventory['claims'][0];claim['unit_kind']='estimate_bundle'
        numeric=next(n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/2/text' and n['source_unit_id']=='r1')
        claim['context_fragments']=[self.fragment(numeric)]
        self.inventory=self.make_inventory([claim])
        for d in self.inventory['value_dispositions']:
            if d['node_id']==numeric['node_id']:d.update(kind='scientific',claim_ids=['c1'])
        claim['proposition']['orientation']=dict(exposure='X',outcome='Y')
        claim['numeric_bundle']=dict(estimate=self.fragment(numeric,'-0.02'),interval=self.fragment(numeric,'[-0.03,-0.01]'),
                                     p_value=self.fragment(numeric,'0.01',last=True),scale=None,
                                     reason='All numbers invented and grouped for a fixture.')
        self.review=self.make_review();self.assertEqual(self.assess()['canonical_group_count'],1)
        claim['unit_kind']='p_value'
        with self.assertRaisesRegex(ContractError,'Standalone numerical'):validate_inventory(self.inventory,self.surface)

    def test_reverse_mr_orientation_cannot_reuse_reference(self):
        claim=self.inventory['claims'][0];claim['proposition']['orientation']=dict(exposure='X',outcome='Y')
        self.reference();claim['proposition']['orientation']=dict(exposure='Y',outcome='X')
        self.review=self.make_review();self.review['claims'][0].update(scientific_validity='supported',reference_ids=['ref1'])
        with self.assertRaisesRegex(ContractError,'orientation'):self.assess()

    def test_missing_ci_is_null_not_imputed_and_bundle_requires_orientation(self):
        c=self.inventory['claims'][0];c['unit_kind']='estimate_bundle';c['numeric_bundle']=dict(
            estimate=None,interval=None,p_value=None,scale=None,reason='Unreported fixture uncertainty.')
        numeric=next(n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/2/text' and n['source_unit_id']=='r1')
        c['numeric_bundle']['estimate']=self.fragment(numeric,'0.3')
        c['context_fragments']=[self.fragment(numeric)]
        with self.assertRaisesRegex(ContractError,'orientation'):validate_inventory(self.inventory,self.surface)
        c['proposition']['orientation']=dict(exposure='X',outcome='Y')
        validate_inventory(self.inventory,self.surface)

    def test_missing_reordered_duplicate_and_foreign_coverage_fail(self):
        original=copy.deepcopy(self.inventory)
        for transform in (lambda x:x['line_dispositions'].pop(),
                          lambda x:x['line_dispositions'].reverse(),
                          lambda x:x['value_dispositions'].pop(),
                          lambda x:x['value_dispositions'].append(x['value_dispositions'][0])):
            value=copy.deepcopy(original);transform(value)
            with self.assertRaises(ContractError):validate_inventory(value,self.surface)

    def test_mined_text_cannot_disappear_as_generic_metadata(self):
        d=next(d for d in self.inventory['value_dispositions'] if d['node_id']==self.node['node_id'])
        d.update(kind='source_data',claim_ids=[])
        with self.assertRaisesRegex(ContractError,'Mined scientific text'):validate_inventory(self.inventory,self.surface)

    def test_uncertain_extraction_is_not_reviewed_complete(self):
        self.inventory['status']='reviewed'
        with self.assertRaisesRegex(ContractError,'Unresolved extraction'):validate_inventory(self.inventory,self.surface)

    def test_context_is_separate_not_spliced_into_fake_verbatim_text(self):
        claim=self.inventory['claims'][0];claim['context_fragments']=[self.fragment(self.node,'beta β')]
        validate_inventory(self.inventory,self.surface)
        claim['statement']='Receptor R inhibits beta β'
        with self.assertRaisesRegex(ContractError,'not literal statements'):validate_inventory(self.inventory,self.surface)

    def test_bad_fragment_bounds_foreign_node_and_utf8_cut_fail(self):
        original=copy.deepcopy(self.inventory)
        for change in (dict(node_id='foreign'),dict(span=dict(start=True,end=3)),dict(text='invented')):
            value=copy.deepcopy(original);value['claims'][0]['focus'].update(change)
            with self.assertRaises(ContractError):validate_inventory(value,self.surface)
        fragment=self.fragment(self.node,'β');fragment['span']['start']+=1
        self.inventory['claims'][0]['focus']=fragment
        with self.assertRaisesRegex(ContractError,'UTF-8'):validate_inventory(self.inventory,self.surface)

    def test_scientific_and_annotation_strata_cannot_dilute_each_other(self):
        other=next(n for n in self.surface['nodes'] if n.get('pointer')=='/score' and n['source_unit_id']=='r1')
        c=self.make_claim('c2',self.node);c['focus']=self.fragment(other);c['stratum']='annotation'
        c['proposition'].update(predicate='has score',object='0.8')
        self.inventory=self.make_inventory([self.make_claim('c1',self.node),c]);self.review=self.make_review()
        result=self.assess();self.assertEqual(len(result['strata']),2);self.assertIsNone(result['scientific_error_rate'])

    def test_no_claims_or_all_unknown_never_produce_zero_error_victory(self):
        self.inventory=self.make_inventory([]);self.review=self.make_review();result=self.assess()
        self.assertEqual(result['canonical_group_count'],0);self.assertIsNone(result['scientific_error_rate'])
        self.assertEqual(result['atomic_completeness'],'unqualified_draft')

    def test_changed_reference_and_foreign_approved_root_fail(self):
        self.reference();self.review=self.make_review();self.ref.write_bytes(b'{}')
        with self.assertRaises(ContractError):self.assess()
        with self.assertRaises(ContractError):
            assess_review(self.inventory,self.surface,self.review,self.references,approved_roots=[self.root/'other'])

    def test_exact_references_and_full_review_coverage_required(self):
        self.review['claims']=[]
        with self.assertRaisesRegex(ContractError,'every proposed'):self.assess()

    def test_dossier_mutation_and_provider_json_substitution_fail(self):
        self.doc.write_bytes(self.doc.read_bytes()+b'x')
        with self.assertRaises(ContractError):validate_inventory(self.inventory,self.surface)
        self.binding['dossier']=pin(self.doc)
        self.binding['source_units'][0]['source_audit']['projected_original_row']['score']=0.1
        with self.assertRaisesRegex(ContractError,'original projection'):surface_from_binding(self.binding)

    def test_evaluator_roles_bool_versions_and_unknown_fields_fail(self):
        for change in (dict(schema_version=True),dict(role='agent_evidence')):
            value=dict(self.inventory,**change)
            with self.assertRaises(ContractError):validate_inventory(value,self.surface)

    def test_inputs_are_not_mutated_and_source_replay_guarantee_is_explicit(self):
        original=copy.deepcopy((self.inventory,self.review,self.surface,self.references))
        result=self.assess();self.assertEqual(original,(self.inventory,self.review,self.surface,self.references))
        self.assertEqual(result['source_binding'],'not_replayed_by_this_entrypoint')
        self.assertIsNone(result['clinical_probability'])

    def test_unknown_dependence_is_explicit_and_overlap_not_independent_n(self):
        self.inventory['claims'][0]['dependence'].update(status='known_overlap',group_ids=['cohort-A'])
        self.review=self.make_review();result=self.assess()
        self.assertEqual(result['declared_dependence_groups'],{'cohort-A':['c1']})
        self.assertNotIn('independent_n',result)
        self.inventory['claims'][0]['dependence']['status']='unknown'
        with self.assertRaisesRegex(ContractError,'Unknown dependence'):validate_inventory(self.inventory,self.surface)

    def test_duplicate_uncertainty_uses_maximum_not_first_occurrence(self):
        other=next(n for n in self.surface['nodes'] if n.get('pointer')=='/textMiningSentences/1/text' and n['source_unit_id']=='r1')
        self.inventory=self.make_inventory([self.make_claim('c1',self.node),self.make_claim('c2',other)])
        self.review=self.make_review();self.review['claims'][0]['uncertainty']='low'
        self.assertEqual(self.assess()['strata'][0]['axes']['uncertainty'],{'high':1})

    def test_semantic_negation_and_analysis_context_cannot_reuse_reference(self):
        for field,value in [('negation',True),('timing','replication analysis')]:
            inventory=copy.deepcopy(self.inventory);self.reference()
            inventory['claims'][0]['proposition'][field]=value
            self.inventory=inventory;self.review=self.make_review()
            self.review['claims'][0].update(scientific_validity='supported',reference_ids=['ref1'])
            with self.subTest(field=field),self.assertRaisesRegex(ContractError,'proposition/orientation/context'):
                self.assess()

    def test_reference_parent_cannot_change_or_be_unscoped(self):
        self.reference();self.review=self.make_review();self.parent.write_bytes(b'{}')
        with self.assertRaises(ContractError):self.assess()

    def test_every_embedded_value_requires_its_own_disposition(self):
        self.inventory['value_dispositions']=[]
        with self.assertRaisesRegex(ContractError,'Every provider JSON value'):
            validate_inventory(self.inventory,self.surface)

    def test_scalar_cannot_hide_as_container_and_false_coverage_link_fails(self):
        value=next(d for d in self.inventory['value_dispositions'] if d['node_id']==self.node['node_id'])
        value['kind']='container_context'
        with self.assertRaisesRegex(ContractError,'Scalar facts'):validate_inventory(self.inventory,self.surface)

    def test_extra_nonrecord_coverage_entries_are_not_silently_filtered(self):
        for key in ('line_dispositions','value_dispositions'):
            value=copy.deepcopy(self.inventory);value[key].append(17)
            with self.subTest(key=key),self.assertRaises(ContractError):validate_inventory(value,self.surface)

    def test_same_hypothesis_reference_is_not_reused_for_a_different_run_context(self):
        self.reference();ref=parse_json(self.ref.read_bytes());ref['binding_sha256']='different-origin-or-program'
        write_json(self.ref,ref);self.references=[pin(self.ref)];self.review=self.make_review()
        with self.assertRaises(ContractError):self.assess()

    def test_reference_cannot_change_between_a_hash_check_and_parse(self):
        from tools.science.run_comparison import check_pin
        reference=self.reference();reference['qualification']='unreviewed'
        write_json(self.ref,reference);self.references=[pin(self.ref)];self.review=self.make_review()
        self.review['claims'][0].update(scientific_validity='supported',reference_ids=['ref1'])
        def prior_check_then_mutate(proof):
            result=check_pin(proof)
            if Path(proof['path'])==self.ref:
                changed=dict(reference,qualification='scope_adjudicated');write_json(self.ref,changed)
            return result
        with patch('tools.science.run_comparison.check_pin',side_effect=prior_check_then_mutate):
            with self.assertRaises(ContractError):self.assess()


@unittest.skipUnless(importlib.util.find_spec('pyarrow'),'install the ingest extra for source-audit tests')
class ContextualOriginalIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.test_science_t6_dossier_binding import DossierSourceBindingTests
        self.fixture=DossierSourceBindingTests(methodName='runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.fixture.rows[0]['textMiningSentences']=[dict(text='Invented β text with "quotes".\nNo biological claim.')]
        self.fixture.evidence(self.fixture.rows)
        self.fixture.prepare();self.fixture.bind()

    def test_surface_and_audit_replay_actual_format_originals(self):
        f=self.fixture;surface=compile_surface(f.binding_proof,approved_roots=[f.root])
        holder=type('FixtureHolder',(),{'surface':surface,'question':surface['question']})()
        inventory=ContextualContractTests.make_inventory(holder,[])
        review=dict(schema_version=2,role='evaluation_only',reviewer_id='fixture-reviewer',mode='development_source_review',
            inventory_sha256=fingerprint(inventory),surface_sha256=fingerprint(surface),references_sha256=fingerprint([]),claims=[])
        result=audit_v2(f.binding_proof,inventory,review,[],approved_roots=[f.root])
        self.assertEqual(result['source_binding'],'current_originals_replayed')
        self.assertEqual(result['atomic_completeness'],'unqualified_draft')
        self.assertIsNone(result['scientific_error_rate'])
        self.assertTrue(any(n.get('pointer')=='/textMiningSentences/0/text' for n in surface['nodes']))

    def test_changed_original_is_not_replaced_by_surface_snapshot(self):
        f=self.fixture;compile_surface(f.binding_proof,approved_roots=[f.root])
        with (f.raw/'evidence.parquet').open('ab') as stream:stream.write(b'drift')
        with self.assertRaises(ContractError):compile_surface(f.binding_proof,approved_roots=[f.root])

    def test_build_retains_draft_scope_and_refuses_existing_output(self):
        from asof.journal import read_chain
        f=self.fixture;out=f.root/'contextual'
        result=build_surface(f.binding_proof,out,approved_roots=[f.root])
        self.assertEqual(result['scientific_atomization'],'not_performed')
        self.assertEqual(parse_json((out/'draft-inventory.json').read_bytes())['claims'],[])
        self.assertEqual(read_chain(out/'journal.jsonl')[-1]['event'],'build_completed')
        original=(out/'report.json').read_bytes()
        with self.assertRaises(FileExistsError):build_surface(f.binding_proof,out,approved_roots=[f.root])
        self.assertEqual(original,(out/'report.json').read_bytes())

    def test_interrupt_and_write_failure_leave_terminal_journal(self):
        from asof.journal import read_chain
        f=self.fixture
        for error in (KeyboardInterrupt(),OSError('invented disk fault')):
            output=f.root/type(error).__name__
            target='compile_surface' if isinstance(error,KeyboardInterrupt) else None
            if target:
                context=patch('tools.science.t6_contextual_audit.compile_surface',side_effect=error)
            else:
                context=patch('asof.serde.write_json',side_effect=error)
            with context,self.assertRaises(type(error)):
                build_surface(f.binding_proof,output,approved_roots=[f.root])
            self.assertEqual(read_chain(output/'journal.jsonl')[-1]['event'],
                             'build_interrupted' if isinstance(error,KeyboardInterrupt) else 'build_failed')

    def test_concurrent_reservation_does_not_repeat_source_compile(self):
        f=self.fixture;surface=compile_surface(f.binding_proof,approved_roots=[f.root]);out=f.root/'concurrent'
        def attempt():
            try:return build_surface(f.binding_proof,out,approved_roots=[f.root])['status']
            except FileExistsError:return 'already_reserved'
        with patch('tools.science.t6_contextual_audit.compile_surface',return_value=surface) as compile_mock:
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(compile_mock.call_count,1)
        self.assertIn('already_reserved',results)

    def test_oversized_output_fails_without_truncating_values(self):
        from asof.journal import read_chain
        f=self.fixture;surface=compile_surface(f.binding_proof,approved_roots=[f.root]);out=f.root/'oversize'
        with patch('tools.science.t6_contextual_audit.compile_surface',return_value=surface), \
             patch('tools.science.t6_contextual_audit.MAX_SOURCE_BYTES',32):
            with self.assertRaisesRegex(ContractError,'no records dropped'):
                build_surface(f.binding_proof,out,approved_roots=[f.root])
        self.assertEqual(read_chain(out/'journal.jsonl')[-1]['event'],'build_failed')


if __name__=='__main__':unittest.main()
