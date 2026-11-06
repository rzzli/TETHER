"""Freeze evaluator references/grouping before new primary answers exist."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import canonical
from experiments.labbench.data_views import verify_views
from experiments.litqa_comparison import preparation,pipeline,codecs
from experiments.litqa_analysis.metrics import publication_components


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    journal=RunJournal(args.output,kind='build')
    try:
        primary_root=ROOT/'data/benchmark/litqa_comparison/primary-production-20261106-attempt01'
        codecs.need(not (primary_root/'answer').exists(),'Analysis input freeze must precede primary answer generation')
        original=ROOT/'data/benchmark/labbench/preparation-20261106-attempt02'
        old=verify_views(original,preparation.SOURCE_MANIFEST_SHA)
        hint_manifest=pipeline.proof(ROOT/'data/benchmark/litqa_comparison/supplied-source-inputs-20261106-attempt03/MANIFEST.json')
        codecs.need(hint_manifest['sha256']=='6635f6b0501b0b40abeda01b7ca723f5b3309838f6e6e4ba4810689f1378290d','Diagnostic annotation projection')
        projection=pipeline.read(hint_manifest);hints=pipeline.read(projection['products']['hints'])
        queries=pipeline.read(pipeline.proof(original/'queries.json'));ids=[q['id'] for q in queries]
        codecs.need(len(ids)==199 and ids==[h['id'] for h in hints],'Full original question schedule')
        annotations={h['id']:h['dois'] for h in hints};groups=publication_components(ids,annotations)
        # Independent graph traversal checks the union-find grouping before it
        # becomes a fixed analysis input. No outcome labels enter either method.
        owners=defaultdict(set)
        for key,dois in annotations.items():
            for doi in dois:owners[doi].add(key)
        remaining=set(ids);independent=[]
        while remaining:
            todo=[next(iter(remaining))];component=set()
            while todo:
                key=todo.pop()
                if key in component:continue
                component.add(key)
                for doi in annotations[key]:todo.extend(owners[doi]-component)
            remaining-=component;independent.append(frozenset(component))
        codecs.need(set(map(frozenset,groups))==set(independent),'Independent publication component reconstruction')
        grouping=dict(kind='shared_annotated_doi_connected_components',role='evaluation_only',groups=groups,
                      questions=199,components=len(groups),size_distribution=dict(Counter(len(g) for g in groups)))
        publish_bytes(journal.output/'GROUPS.json',canonical(grouping)+b'\n')
        references=pipeline.proof(original/old['products']['references']['path'])
        codecs.need(references['sha256']==old['products']['references']['sha256'],'Native reference bytes')
        manifest=dict(kind='sc04_analysis_inputs_v1',role='evaluation_only',created_at_utc=datetime.now(timezone.utc).isoformat(),
            primary_answers_existed_at_freeze=False,questions=199,question_schedule=ids,reference_keys=references,
            answer_queries=pipeline.proof(original/'queries.json'),annotation_projection=hint_manifest,
            groups=pipeline.proof(journal.output/'GROUPS.json'),bootstrap_replicates=10000,seed=20261106,
            primary_metrics=['raw_accuracy','correct_and_admitted_yield'],
            primary_contrasts=['expansion_at_lexical','ranking_at_lexical','combined_vs_lexical','interaction','marginal_expansion','marginal_ranking'],
            interval='95% linear percentile bootstrap; publication components primary, paired questions sensitivity',
            specification=pipeline.proof(ROOT/'planning/review-assets/tether-semantic-20261106/sc04/ANALYSIS-SPECIFICATION.md'),
            addendum=pipeline.proof(ROOT/'planning/review-assets/tether-semantic-20261106/sc04/ANALYSIS-SPECIFICATION-ADDENDUM.md'),
            grouping_code=pipeline.proof(ROOT/'experiments/litqa_analysis/metrics.py'),freeze_helper=pipeline.proof(Path(__file__)),
            native_scorer=pipeline.proof(ROOT/'experiments/labbench/evaluate.py'),
            exposure='Repeated public development evaluation; no untouched holdout or calibrated risk claim.')
        publish_bytes(journal.output/'MANIFEST.json',canonical(manifest)+b'\n')
        proof=pipeline.proof(journal.output/'MANIFEST.json');journal.append('analysis_inputs_frozen',manifest_sha256=proof['sha256'])
        publish_bytes(journal.output/'ANCHOR.json',canonical(proof)+b'\n')
        print(canonical(dict(manifest=proof,questions=199,publication_components=len(groups),size_distribution=grouping['size_distribution'])).decode())
    except BaseException as error:journal.fail(error,'analysis_input_freeze');raise
    finally:journal.close()


if __name__=='__main__':main()
