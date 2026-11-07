"""Assemble evaluator-only source references after two reviews and adjudication.

No majority rule is used. The adjudicator supplies the disposition and rationale;
the assembler checks its exact source coverage and binds the accepted artifacts.
"""
from datetime import datetime, timezone
from pathlib import Path

from tether_engine.contracts import Case
from tether_engine.serde import ContractError, decode, read_json, safe_child, sha256_file, write_json
from tools.science.qualification import validate_reference
from tools.science.reference_panel import read_bound_json, validate_q1


def index_reviews(review):
    return {(c['case_id'],o['observation_id']):o for c in review['cases'] for o in c['observations']}


def assemble(source_root, review_paths, adjudication_path, output, *, source_report_sha256):
    source_root, output = Path(source_root), Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        loaded = [read_bound_json(p) for p in review_paths]
        panels = [p for p,h in loaded]
        frozen_inputs = {Path(p):h for p,(_,h) in zip(review_paths,loaded)}
        adjudication, adjudication_hash = read_bound_json(adjudication_path)
        frozen_inputs[Path(adjudication_path)] = adjudication_hash
        reports = [validate_q1(p,source_root,source_report_sha256) for p in panels]
        if len(panels) != 2 or len({p['reviewer_id'] for p in panels}) != 2:
            raise ContractError('Reference assembly needs two different blinded reviewers')
        if len({p['model_provenance']['execution_id'] for p in panels}) != 2:
            raise ContractError('Reference review contexts are not separated')
        if (adjudication.get('source_report_sha256') != source_report_sha256 or
                adjudication.get('external_independence') is not False or
                not adjudication.get('model_provenance')):
            raise ContractError('Adjudication source scope or provenance is incomplete')
        execution = adjudication['model_provenance'].get('execution_id')
        if not execution or execution in {p['model_provenance']['execution_id'] for p in panels}:
            raise ContractError('Adjudication requires a distinct third execution context')
        expected_pins = {h for p,h in loaded}
        if set(adjudication.get('review_sha256s',[])) != expected_pins:
            raise ContractError('Adjudication does not bind both sealed Q1 reviews')
        indexed = [index_reviews(p) for p in panels]
        decided = index_reviews(adjudication)
        if (len(decided) != sum(len(c['observations']) for c in adjudication['cases']) or
                set(decided) != set(indexed[0]) or set(decided) != set(indexed[1])):
            raise ContractError('Adjudication must cover every original row exactly once')
        source_report,_ = read_bound_json(source_root/'reference-report.json',source_report_sha256)
        frozen_inputs[source_root/'reference-report.json'] = source_report_sha256
        references = []
        for entry in source_report['cases']:
            folder = safe_child(source_root,entry['case_id'])
            context,_ = read_bound_json(folder/'reference-context.json',entry['reference_context_sha256'])
            frozen_inputs[folder/'reference-context.json'] = entry['reference_context_sha256']
            frozen_inputs[folder/'source-packet.json'] = context['source_packet_sha256']
            frozen_inputs[folder/'raw-row-audit.json'] = context['raw_row_audit_sha256']
            case = decode(Case,context['case'])
            packet,_ = read_bound_json(folder/'source-packet.json',context['source_packet_sha256'])
            observations = packet['observations']
            raw_audit,_ = read_bound_json(folder/'raw-row-audit.json',context['raw_row_audit_sha256'])
            audit = {r['observation_id']:r for r in raw_audit}
            for observation in observations:
                key = (case.case_id,observation['observation_id'])
                decision = decided[key]
                if not decision.get('rationale') or decision.get('source_row_sha256') != audit[key[1]]['source_row_sha256']:
                    raise ContractError('Adjudication lacks a source-bound rationale')
                raw = audit[key[1]]
                reference = {'schema_version':1,'role':'evaluation_only',
                    'reference_id':case.case_id+':'+key[1], 'case_id':case.case_id,
                    'hypothesis_sha256':case.hypothesis.key,'source_row_sha256':raw['source_row_sha256'],
                    'statement':observation['statement'],'answer':decision['answer'],
                    'context':{'observed':observation['context'],'source_metrics':observation['source_metrics'],
                               'missingness':observation['missingness'],
                               'adjudicated_limits':decision.get('context_qualifiers')},
                    'source_evidence':[{'artifact_sha256':raw['source']['sha256'],
                        'locator':raw['physical_locator'],'url':raw['source']['source_url'],
                        'retrieved_at':observation['availability']['retrieved_at']}],
                    'reviews':[{'reviewer_id':p['reviewer_id'],'reviewer_kind':'ai_agent',
                        'blinded_to_arm_outputs':p['blind_to_arm_outputs'],'model_provenance':p['model_provenance'],
                        'answer':i[key]['answer'],'rationale':i[key]['rationale'],'rubric':i[key]['rubric']}
                        for p,i in zip(panels,indexed)],
                    'adjudication':{'rationale':decision['rationale'],'model_provenance':adjudication['model_provenance'],
                                    'input_sha256s':sorted(expected_pins),'independence_evidence':None},
                    'reference_level':'ai_source_adjudicated','validation_claim':'source_grounded_ai_reference',
                    'version_applicability':{'status':'exact','snapshot_id':source_report['build_report_sha256']},
                    'interpretation':'Resource annotation fidelity; no therapeutic benefit or independent scientific truth inferred'}
                validate_reference(reference)
                references.append(reference)
        for path,expected in frozen_inputs.items():
            if sha256_file(path) != expected:
                raise ContractError('Reference input changed during assembly: '+str(path))
        write_json(output/'references.json',{'schema_version':1,'role':'evaluation_only','references':references})
        report = {'schema_version':1,'role':'evaluation_only','status':'source_reference_assembled',
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'references':len(references),'cases':len(source_report['cases']),
            'review_validations':reports,'pins':[{'path':str(p),'sha256':h} for p,h in frozen_inputs.items()],
            'references_sha256':sha256_file(output/'references.json'),
            'clinical_labels':False,'independent_scientific_truth':False,'probabilities':'withheld'}
        write_json(output/'report.json',report)
        return report
    except BaseException as error:
        write_json(output/'failure.json',{'status':'failed','error_type':type(error).__name__,'error':str(error)})
        raise
