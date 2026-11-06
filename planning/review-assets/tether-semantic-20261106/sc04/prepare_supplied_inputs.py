"""Trusted diagnostic-only DOI projection. Never imported by primary workers.

The parent is reference-bearing. Output contains paper identities but no answer
key, options, key passage or canary. It is forbidden in ordinary retrieval.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import urlsplit,unquote

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from asof.journal import RunJournal
from asof.atomic import publish_bytes
from asof.serde import canonical,parse_json,freeze
from experiments.labbench.data_views import verify_views,verify_originals,ORIGINAL
from experiments.litqa_comparison import pipeline,preparation,codecs

ORIGINAL_PREPARATION=ROOT/'data/benchmark/labbench/preparation-20261106-attempt02'
PRIMARY_PREPARATION=ROOT/'data/benchmark/litqa_comparison/preparation-20261106-attempt02/MANIFEST.json'
PRIMARY_SHA='29a18fb45f4f8fe76b52eb833ddf351b4fa9a47c82a2fa9d9a971ff38f814dc4'


def doi(value):
    codecs.need(isinstance(value,str),'Source hint must be a string')
    parts=urlsplit(value)
    # Only extract identities here. Never fetch the original URL: the diagnostic
    # resolver later constructs a fixed-origin HTTPS Europe PMC request.
    codecs.need(parts.scheme in ('http','https') and parts.netloc in ('doi.org','dx.doi.org') and
                not parts.query and not parts.fragment,'Expected DOI resolver URL')
    identity=unquote(parts.path.lstrip('/')).lower()
    codecs.need(len(identity)<=256 and re.fullmatch(r'10\.[0-9]{4,9}/[a-z0-9._;()/<>:-]+',identity) is not None,'Unsafe or unknown DOI syntax')
    return identity


def project(original,questions):
    codecs.need(len(original)==len(questions),'Diagnostic complete cohort')
    hints=[];ordered=[];seen=set()
    for row,question in zip(original,questions):
        codecs.need(row['id']==question['id'] and row['question']==question['question'],'Diagnostic question identity')
        codecs.question_view(question)
        codecs.need(isinstance(row['sources'],list) and 0<len(row['sources'])<=2,'Declared source count per question')
        identities=[doi(value) for value in row['sources']]
        codecs.need(len(set(identities))==len(identities),'Duplicate annotated DOI within question')
        hints.append(dict(id=question['id'],question=question['question'],dois=identities))
        for identity in identities:
            if identity not in seen:ordered.append(identity);seen.add(identity)
    return freeze(dict(hints=hints,doi_schedule=ordered))


class ProjectionTests(unittest.TestCase):
    def test_only_diagnostic_fields_escape_mixed_original(self):
        q=dict(id='00000000-0000-0000-0000-000000000001',question='An invented question?')
        row=dict(q,sources=['https://doi.org/10.1234/Example'],ideal='secret-answer',distractors=['secret-choice'],
                 **{'key-passage':'secret-passage','canary':'secret-canary'})
        result=project([row],[q]);self.assertEqual(set(result['hints'][0]),{'id','question','dois'})
        self.assertNotIn(b'secret',canonical(result));self.assertEqual(result['doi_schedule'],('10.1234/example',))

    def test_wrong_identity_or_duplicate_doi_fails(self):
        q=dict(id='00000000-0000-0000-0000-000000000001',question='An invented question?')
        row=dict(q,sources=['https://doi.org/10.1234/a']*2)
        with self.assertRaises(ValueError):project([row],[q])
        row['sources']=['https://doi.org/10.1234/a'];row['question']='Other question?'
        with self.assertRaises(ValueError):project([row],[q])

    def test_doi_syntax_and_origin_fail_closed(self):
        for value in ('https://evil.org/10.1234/a','https://doi.org/10.1234/a?q=x',
                      'https://doi.org/10.1234/a%22%20OR%20anything','ftp://doi.org/10.1234/a'):
            with self.assertRaises(ValueError):doi(value)

    def test_original_legacy_resolver_url_normalizes_without_fetching(self):
        self.assertEqual(doi('http://dx.doi.org/10.1016/j.cell.2023.05.041'),'10.1016/j.cell.2023.05.041')

    def test_legacy_sici_suffix_is_preserved_not_truncated(self):
        identity='10.1002/(sici)1097-0177(200006)218:2<235::aid-dvdy2>3.0.co;2-g'
        self.assertEqual(doi('https://doi.org/'+identity),identity)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.self_test:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProjectionTests))
        if not result.wasSuccessful():raise SystemExit(1)
        return
    codecs.need(args.output is not None,'Fresh output required')
    journal=RunJournal(args.output,kind='build')
    try:
        old=verify_views(ORIGINAL_PREPARATION,preparation.SOURCE_MANIFEST_SHA)
        _,proofs,original=verify_originals(old['original_root'],old['acquisition_receipt_sha256'])
        primary_proof=pipeline.proof(PRIMARY_PREPARATION)
        codecs.need(primary_proof['sha256']==PRIMARY_SHA,'Primary question projection anchor')
        primary=pipeline.read(primary_proof);questions=preparation.load_product(primary,'source_queries')
        projected=project([parse_json(line) for line in original.splitlines()],questions)
        sizes=Counter(len(row['dois']) for row in projected['hints'])
        codecs.need(len(projected['hints'])==199 and len(projected['doi_schedule'])==190 and sizes=={1:193,2:6},'Declared 199/190/205 cohort')
        outputs={}
        for name in ('hints','doi_schedule'):
            p=journal.output/(name+'.json');publish_bytes(p,canonical(projected[name])+b'\n');outputs[name]=pipeline.proof(p)
        manifest=dict(kind='sc04_supplied_source_selection_inputs_v1',role='diagnostic_selection_only',
            ordinary_retrieval_permitted=False,answerer_may_read=False,correct_answers_included=False,key_passages_included=False,
            questions=199,unique_dois=190,question_doi_pairs=205,source_counts=dict(sizes),products=outputs,
            schedule=[q['id'] for q in questions],original_preparation_sha256=preparation.SOURCE_MANIFEST_SHA,
            primary_preparation=primary_proof,original=dict(path=str(Path(old['original_root'])/ORIGINAL),
                sha256=proofs[ORIGINAL]['sha256'],bytes=proofs[ORIGINAL]['bytes'],role='mixed_reference_only'),
            projector=pipeline.proof(Path(__file__)),selection_uses_reference_paper_identity=True,
            explanation='Privileged paper identities for a separately labelled diagnostic; never ordinary retrieval performance.')
        publish_bytes(journal.output/'MANIFEST.json',canonical(manifest)+b'\n')
        manifest_proof=pipeline.proof(journal.output/'MANIFEST.json')
        journal.append('diagnostic_projection_completed',manifest_sha256=manifest_proof['sha256'])
        publish_bytes(journal.output/'ANCHOR.json',canonical(manifest_proof)+b'\n')
        print(canonical(manifest_proof).decode())
    except BaseException as error:journal.fail(error,'diagnostic_projection');raise
    finally:journal.close()


if __name__=='__main__':main()
