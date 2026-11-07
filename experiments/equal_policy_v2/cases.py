"""Post-result corrected fictional corpus, without modifying the frozen v1.

Only pure construction helpers are reused. No validator, producer, experiment
result or model is imported to derive an expected decision. Every case is marked
authored/exposed; none is a private held-out evaluation.
"""
import copy
import hashlib
from pathlib import Path

try:
    from equal_policy import cases as _v1
except ModuleNotFoundError as error:
    if error.name != 'equal_policy':
        raise
    from experiments.equal_policy import cases as _v1

canonical = _v1.canonical
file_bytes = _v1.file_bytes
fingerprint = _v1.fingerprint
POLICY_IDS = _v1.POLICY_IDS
HYPOTHESIS_FIELDS = _v1.HYPOTHESIS_FIELDS
BUDGET = copy.deepcopy(_v1.BUDGET)
source_documents = _v1.source_documents
runtime_witness_specs = _v1.runtime_witness_specs
CORPUS_ID = 'tether-equal-policy-fictional-v2'
STRATUM = 'exposed_authored_construction'
LATER_OBSERVATION_ID = 'obs-later-perturbation'


def case_specs():
    rows = _v1.case_specs()
    by_id = {row['control_id']: row for row in rows}
    by_id['EP023']['preparation']['recipe']['v2_source_correction'] = 'seal_unrelated_source'
    for identifier in ('EP072', 'EP097'):
        row = by_id[identifier]
        row['preparation']['recipe']['v2_extra_evidence'] = 'eligible_later_perturbation'
        row['oracle']['observables'].update(
            admitted_observation_ids=['obs-1', LATER_OBSERVATION_ID], dispatches=1)
    # A corrupt chain cannot supply trustworthy partial-recovery observations.
    by_id['EP077']['oracle']['observables'] = {}
    # A new clean neighbor is independently declared from the valid base input,
    # never copied from the invalid replay output or its observed disposition.
    parent = copy.deepcopy(by_id['EP001'])
    parent.update(control_id='EP109', operation='verify_run',
        title='Unaltered recorded selection binds its request and verifies')
    parent['preparation']['recipe'] = dict(sealed_producer='valid_recorded', sealed_mutation='none')
    parent['oracle'] = dict(decision='accept', obligation_ids=['EP-EXEC-02', 'EP-VERIFY-02'],
        rationale=parent['title'], observables=dict(feature_values={'genetic_support': 0.75},
            prediction_status='scored', probability_is_null=False, selected_observation_ids=['obs-1'], dispatches=1))
    rows.append(parent)
    for row in rows:
        prior = row['construction_stratum'] if row['control_id'] != 'EP109' else None
        row['revision_provenance'] = dict(original_construction_stratum=prior,
            original_corpus_id='tether-equal-policy-fictional-v1' if prior else None,
            post_result_correction=row['control_id'] in ('EP023', 'EP072', 'EP075', 'EP077', 'EP097'),
            new_clean_neighbor=row['control_id']=='EP109',
            exposure='Authored with policy/code and original comparison results available; not held out')
        row['construction_stratum'] = STRATUM
    return rows


def prepare_documents(spec):
    documents = _v1.prepare_documents(spec)
    recipe = spec['preparation']['recipe']
    if recipe.get('v2_source_correction'):
        if recipe['v2_source_correction'] != 'seal_unrelated_source':
            raise ValueError('Unknown v2 source correction')
        extra = next(node for node in documents['snapshot']['sources'] if node['source_id']=='unrelated-source')
        extra['sha256'] = hashlib.sha256(file_bytes(documents['source'])).hexdigest()
        extra['receipt_sha256'] = hashlib.sha256(file_bytes(documents['receipt'])).hexdigest()
    if recipe.get('v2_extra_evidence'):
        if recipe['v2_extra_evidence'] != 'eligible_later_perturbation':
            raise ValueError('Unknown v2 evidence construction')
        later = copy.deepcopy(documents['evidence']['observations'][0])
        later.update(observation_id=LATER_OBSERVATION_ID, category='perturbation',
            statement='Fictional perturbation evidence creates eligible later work; software control only.',
            features={'perturbation_support': 0.75})
        documents['evidence']['observations'].append(later)
        _v1.seal_sources(documents)
    return documents


def write_source_bundle(root, spec, *, trusted_runtime=None):
    # The unchanged v1 writer provides exclusive creation and explicit file-fault
    # handling. Narrow corrections apply only inside its newly created bundle.
    descriptor, pending = _v1.write_source_bundle(root, spec, trusted_runtime=trusted_runtime)
    recipe = spec['preparation']['recipe']
    if recipe.get('v2_source_correction') or recipe.get('v2_extra_evidence'):
        documents = prepare_documents(spec)
        for name in ('snapshot', 'evidence'):
            (Path(root)/'input'/(name+'.json')).write_bytes(file_bytes(documents[name]))
    return descriptor, pending


def oracle_manifest():
    return dict(schema_version=1, corpus_id=CORPUS_ID, status='construction_not_frozen',
        independence='Normative authored expectations; all cases exposed to policy/code and original results. No held-out claim.',
        cases=[dict(control_id=row['control_id'], operation=row['operation'], variant=row['variant'],
                    construction_stratum=row['construction_stratum'], **copy.deepcopy(row['oracle'])) for row in case_specs()])


def case_manifest():
    return dict(schema_version=1, corpus_id=CORPUS_ID, status='construction_not_frozen', cases=case_specs())
