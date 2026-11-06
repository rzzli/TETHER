"""Root closure checks of retained qualified gates, seals and current documents.

This consumes separately implemented audits; it does not replace their full
source verification or repeat inference. Output is fresh and no-clobber.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[4]
STAGE = ROOT / 'planning/review-assets/tether-labbench-20261106'
ANCHORS = {
 'stage/generation-freeze-attempt02/GENERATION-FREEZE.json':'4359d589205caec39085872cc72cd5799323e2285e0993b58405e7e70ccd2fe5',
 'components-attempt04/VALIDATION.json':'8049780903b7c0b5be101ad1703a6d9ab236833b5e701889eff0beea1b1f6b65',
 'operational-audit/COLLECTION-FINAL-01.json':'d43e6fb9f3c55791511bcec48c269a00a2ed4084bbbf4f15b3122785051652ef',
 'operational-audit/GENERATION-FINAL-03.json':'abcd5878cb83f1e7e481239e347952c9ae207ef47cf373d59977af3f69810576',
 'operational-audit/SOURCE-DOI-02.json':'d8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7',
 'operational-audit/SOURCE-DOI-COMPARISON-01.json':'8b1bf151426afe91525b8783249f28cbe421ba8fa09b82206f15a2e550ffa764',
 'stage/RESOURCE-SCOPE-02.json':'8c39c654b6711e4c03c3ab4b1a476f65ede8f7277f46a0d19b3df665122c5218',
 'stage/SCORE-CONTROL-01.json':'1050b77e9f073159ee4a0bbc4a5b62def5137d9fa76a6516d80e958158447302',
}
DATA_ANCHORS = {
 'data/benchmark/labbench/generation-20261106T011303Z-attempt01/SEALED.json':'46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447',
 'data/benchmark/labbench/evaluation-20261106T011303Z-attempt01/SEALED.json':'118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f',
 'data/benchmark/labbench/reconstruction-20261106-attempt01/RECONSTRUCTION.json':'e184cbaefa4ca767d0dcf0c55286b96ea768f624fd512d9585ec4aefe41f4fa0',
 'data/benchmark/labbench/reconstruction-comparison-20261106-attempt01/COMPARISON.json':'0374f21ca3b7b49ba6810adc7cb316f960b2050c6e76630ce611986066e429a6',
}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    proofs=[]
    for base, entries in ((STAGE,ANCHORS),(ROOT,DATA_ANCHORS)):
        for name, expected in entries.items():
            path=base/name
            assert sha(path)==expected, name
            proofs.append(dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=expected,bytes=path.stat().st_size))
    gate=json.loads((STAGE/'components-attempt04/VALIDATION.json').read_bytes())
    assert gate['status']=='PASS' and gate['returncode']==0 and gate['tests']==97 and gate['sources_unchanged'] is True
    for name, expected in gate['source_pins'].items(): assert sha(ROOT/name)==expected, name
    assert gate['source_pins']==gate['source_pins_after']
    eval_root=ROOT/'data/benchmark/labbench/evaluation-20261106T011303Z-attempt01'
    seal=json.loads((eval_root/'SEALED.json').read_bytes())
    for name, proof in seal['outputs'].items():
        assert name==proof['path'] and sha(eval_root/name)==proof['sha256']
        assert (eval_root/name).stat().st_size==proof['bytes']
    assert sha(eval_root/'journal.jsonl')==seal['journal_sha256']
    report=json.loads((eval_root/'REPORT.json').read_bytes())
    blind=json.loads((ROOT/'data/benchmark/labbench/reconstruction-20261106-attempt01/RECONSTRUCTION.json').read_bytes())
    for key in ('scheduled_count','raw_metrics','checked_metrics','counts','rates','raw_precision_defined','checked_precision_defined'):
        assert report[key]==blind[key], key
    assert report['status']=='completed' and report['scheduled_count']==199
    assert report['resources']['new_model_calls']==report['resources']['new_retrieval_calls']==0
    for arm in ('retained_fulltext_alignment','selected_for_prompt_alignment'):
        assert report[arm]['doi_identifier']['hit_doi_count']==10
        assert report[arm]['doi_identifier']['annotated_doi_count']==205
        assert report[arm]['primary']['observed_annotated_source_hit_questions']==10
    docs=['README.md','TODO.md','planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md',
          'planning/review-assets/tether-labbench-20261106/STATUS.md',
          'reports/TETHER benchmark comparison update 2026-11-06.md',
          'memory/MEMORY.md','memory/project-goals.md','memory/research-log-2026-11-06-labbench-results.md']
    local_links=0;doc_proofs=[]
    for name in docs:
        path=ROOT/name;text=path.read_text(encoding='utf-8-sig')
        for match in re.finditer(r'\[[^\]\n]*\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            target=match[1] or match[2]
            if target.startswith(('http:','https:','mailto:','#')):continue
            local=(path.parent/unquote(target.split('#')[0])).resolve()
            assert local.exists(),(name,target)
            local_links+=1
        doc_proofs.append(dict(path=name,sha256=sha(path)))
    todo=(ROOT/'TODO.md').read_text(encoding='utf-8')
    assert '- [x] BG04' in todo and '- [ ] BG05' in todo and '- [ ] BG06' in todo
    result=dict(schema_version=1,status='PASS',stage='BG04',completed_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Declared original199 public LitQA2 measurement; no semantic/clinical qualification',
        retained_external_anchors=proofs,qualified_maintained_tests=97,unchanged_qualified_source_files=len(gate['source_pins']),
        evaluator_products_rehashed=len(seal['outputs']),local_document_links_checked=local_links,documents=doc_proofs,
        native_metrics=report['raw_metrics'],counts=report['counts'],same_candidate_checked_metrics=report['checked_metrics'],
        source_doi_pairs=[10,205],source_hit_questions=[10,199],
        limitations=['Failed fictional semantic control retained','Public exposed task; no contamination-free/private evaluation',
          'Source identity is not entailment','Shared-source producer; filtering cannot create correct answers',
          'Conditional source resolution selected by metadata','Finalization outside worker deadline; total outer stopwatch missing',
          'Fixed-cap read allocation inefficiency remains frozen','Marginal check/GPU/energy costs unmeasured',
          'Separate code checks are not independent human biological validation'],
        next_stage='BG05 policy-equivalent Inspect; BG06 final audit remains',new_model_calls=0,new_network_requests=0,
        acceptance_code_sha256=sha(Path(__file__)))
    with (STAGE/'STAGE-ACCEPTANCE-01.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'status':'PASS','stage':'BG04','local_links':local_links,'unchanged_sources':len(gate['source_pins']),'tests':97}))


if __name__=='__main__':main()
