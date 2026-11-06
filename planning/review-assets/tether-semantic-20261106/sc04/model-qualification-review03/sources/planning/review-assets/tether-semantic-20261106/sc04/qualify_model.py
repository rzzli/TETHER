"""Frozen fictional expansion/ranking/answer qualification; never a benchmark run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
from asof.atomic import publish_bytes
from asof.journal import RunJournal,read_chain
from asof.serde import canonical,encode,fingerprint
from tether._process import ProcessLimits,supervise_command,validate_success_report
from experiments.labbench import model
from experiments.labbench.runtime import contain_process_tree,empty_import_cache,process_sample
from experiments.litqa_comparison import codecs,transport

RECEIPT=Path(r'E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z\acquisition.json')
RECEIPT_SHA='cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf'
ALIAS='tether-sc04-fictional-qwen14b-v1'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def write(path,value):publish_bytes(Path(path),canonical(value)+b'\n')


def fixtures():
    def task(i,text):return dict(id=f'00000000-0000-0000-0000-{i:012d}',question=text)
    def pool(texts):return [dict(rank_id=f'p{i:02d}',source_id=f'fictional:p{i:02d}',text=s,sha256=codecs.digest(s.encode())) for i,s in enumerate(texts)]
    cases = [
        dict(task='expand',query=task(401,'In a fictional cell study, how does the protein Lumarin, also called LMR7, affect cobalt transport?'),expected_terms=['lumarin','lmr7']),
        dict(task='expand',query=task(402,'In an invented assay, what is the association between Vesprine, also named VSP9, and amber uptake?'),expected_terms=['vesprine','vsp9']),
        dict(task='rank',query=task(403,'In the invented trial, which compound increased cobalt uptake?'),
             pool=pool(['This passage repeatedly mentions cobalt uptake but reports no compound or experimental result.',
                        'In the invented trial, compound Lumarin increased cobalt uptake by 30 percent; vehicle had no effect.',
                        'The fictional observatory has a wooden cabinet.']),expected_first='p01'),
        dict(task='rank',query=task(404,'In the fictional experiment, which treatment reduced amber signal?'),
             pool=pool(['The fictional experiment found Vesprine reduced amber signal by half relative to vehicle.',
                        'Amber signal and treatment were listed as planned measurements, with no results reported.',
                        'Unrelated cobalt transport increased after Lumarin in a different invented assay.']),expected_first='p00'),
        dict(task='answer',query=dict(task(405,'In the invented laboratory, what color is the Lumen-7 orb?'),
             choices=['(A) Amber','(B) Insufficient information to answer the question','(C) Cobalt']),
             sources=[dict(source_id='fiction-lumen7:p0001',text='In this invented laboratory, the Lumen-7 orb is cobalt. The amber item is a different object.',
                           sha256=codecs.digest(b'In this invented laboratory, the Lumen-7 orb is cobalt. The amber item is a different object.'))],expected_index=2),
        dict(task='answer',query=dict(task(406,'In the invented laboratory, what color is the Lumen-8 orb?'),
             choices=['(A) Amber','(B) Insufficient information to answer the question','(C) Cobalt']),
             sources=[],expected_index=1)]
    controls=[
        ('What color is the fictional Arlo orb?', ['Amber','Cobalt','Insufficient information to answer the question'],
         'The fictional Arlo orb is amber.',0),
        ('What color is the fictional Brin orb?', ['Amber','Cobalt','Insufficient information to answer the question'],
         'The fictional Brin orb is cobalt.',1),
        ('Which compound gave greater uptake in the invented assay?', ['Lumarin','Vesprine','Insufficient information to answer the question'],
         'In the invented assay, Lumarin produced uptake of 30 units, whereas Vesprine produced 10 units.',0),
        ('What color is the fictional Cero orb?', ['Cobalt','Insufficient information to answer the question','Amber'],
         'The fictional Cero orb is not cobalt. It is amber.',2),
        ('What dose was used in the fictional experiment?', ['Insufficient information to answer the question','10 mg','20 mg'],
         'The fictional experiment measured amber uptake. No administered dose is reported.',0),
        ('What color is the fictional Daro orb?', ['Amber','Cobalt','Insufficient information to answer the question'],
         'The fictional Cero orb is amber; the Daro orb is a different object whose color is not recorded.',2)]
    for i,(question,choices,text,expected) in enumerate(controls,407):
        cases.append(dict(task='answer',query=dict(task(i,question),choices=[f'({chr(65+j)}) {v}' for j,v in enumerate(choices)]),
                          sources=[dict(source_id=f'fiction:{i}',text=text,sha256=codecs.digest(text.encode()))],expected_index=expected))
    distractors=['This fictional paragraph describes storage of empty containers and reports no uptake results. '+('Storage was recorded. '*20) for _ in range(15)]
    cases.append(dict(task='rank',query=task(413,'Which compound increased cobalt uptake in the invented trial?'),
                      pool=pool(distractors+['The invented trial found Lumarin increased cobalt uptake relative to vehicle.']),expected_first='p15'))
    return cases


def code_pins():
    paths=[Path(__file__).resolve()]
    for rel in ('src/asof','packages/tether/src/tether','experiments/labbench','experiments/litqa_comparison'):
        paths.extend((ROOT/rel).rglob('*.py'))
    return {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(paths))}


def worker(recipe_path,expected,output):
    codecs.need(sha(recipe_path)==expected,'Recipe anchor')
    recipe=json.loads(Path(recipe_path).read_bytes())
    codecs.need(code_pins()==recipe['code_pins'],'Frozen qualification code changed')
    empty_import_cache(expected=recipe['worker_import_cache'])
    journal=RunJournal(output,kind='build')
    started=time.monotonic();deadline=started+1900
    owner=None;results=[];stage='containment'
    try:
        handle=contain_process_tree()
        stage='owned_startup'
        spec,bindings,provenance=model.make_server_spec(RECEIPT,RECEIPT_SHA,port=55624,alias=ALIAS)
        write(Path(output)/'MODEL.json',dict(spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()},provenance=provenance))
        (Path(output)/'server').mkdir()
        with model.owned_server(spec,bindings,output=Path(output)/'server',journal=journal,parent_deadline=deadline-30) as owner:
            for index,item in enumerate(recipe['fixtures']):
                stage='fixture_'+str(index)
                end=min(deadline-40,time.monotonic()+120)
                cell=Path(output)/f'fixture-{index:02d}'
                if item['task']=='answer':
                    request,payload=transport.make_answer_request(item['query'],item['sources'],provenance)
                else:request,payload=transport.make_request(item['task'],item['query'],provenance,item.get('pool',()))
                result=transport.execute_once(owner,request,payload,output=cell,journal=journal,deadline=end,alias=ALIAS)
                decoded=result['decoded']
                if item['task']=='expand':
                    terms={t.casefold() for q in decoded['queries'] for t in q}
                    semantic=all(t in terms for t in item['expected_terms'])
                elif item['task']=='rank':semantic=decoded[0]==item['expected_first']
                else:semantic=decoded['answer_index']==item['expected_index']
                results.append(dict(index=index,task=item['task'],semantic_fixture_match=semantic,result=result))
                write(Path(output)/f'fixture-{index:02d}-summary.json',results[-1])
                print(json.dumps(dict(index=index,task=item['task'],semantic_fixture_match=results[-1]['semantic_fixture_match'])),flush=True)
                codecs.need(time.monotonic()<end,'Fixture finalization deadline')
        codecs.need(owner.terminal_record['server_stopped'] is True,'Owned cleanup incomplete')
        codecs.need(code_pins()==recipe['code_pins'],'Source changed during qualification')
        report=dict(status='completed',semantic_fixtures_passed=sum(r['semantic_fixture_match'] for r in results),
                    fixtures=len(results),results=results,wall_seconds=time.monotonic()-started,
                    worker_memory=process_sample(os.getpid()),server_terminal=owner.terminal_record,
                    provider_cost_usd=0,benchmark_questions=0,scope='Fictional semantic/codec checks, not accuracy qualification on real literature.')
        journal.append('qualification_completed',fixtures=len(results),semantic_fixtures_passed=report['semantic_fixtures_passed'])
        write(Path(output)/'REPORT.json',report)
        write(Path(output)/'COMPLETE.json',dict(report_sha256=sha(Path(output)/'REPORT.json'),journal_terminal_sha256=journal.events[-1]['sha256']))
        _=handle
    except BaseException as error:
        journal.fail(error,stage)
        write(Path(output)/'FAILURE.json',dict(stage=stage,error_type=type(error).__name__,message=str(error),completed_fixtures=len(results),
              server_terminal=owner.terminal_record if owner else None,automatic_retry=False))
        raise
    finally:journal.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--execute',action='store_true');parser.add_argument('--worker',action='store_true')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--recipe',type=Path);parser.add_argument('--recipe-sha256')
    args=parser.parse_args()
    if args.prepare:
        args.output.mkdir(parents=True,exist_ok=False)
        recipe=dict(kind='sc04_fictional_model_qualification',code_pins=code_pins(),fixtures=fixtures(),
                    model_receipt=str(RECEIPT),model_receipt_sha256=RECEIPT_SHA,
                    worker_import_cache=str((ROOT/'data/cache'/('sc04-'+args.output.name+'-worker-import')).resolve()),
                    supervision=dict(timeout_seconds=2000,max_output_bytes=4*1024**2),max_generation_calls=len(fixtures()))
        write(args.output/'RECIPE.json',recipe)
        print(sha(args.output/'RECIPE.json'));return
    codecs.need(args.recipe and args.recipe_sha256 and sha(args.recipe)==args.recipe_sha256,'Externally anchored recipe required')
    if args.worker:return worker(args.recipe,args.recipe_sha256,args.output)
    codecs.need(args.execute,'Explicit execute flag required')
    recipe=json.loads(args.recipe.read_bytes());codecs.need(code_pins()==recipe['code_pins'],'Code changed before dispatch')
    journal=RunJournal(args.output,kind='build');result=None
    try:
        command=[sys.executable,'-I','-B','-X','pycache_prefix='+recipe['worker_import_cache'],str(Path(__file__).resolve()),
                 '--worker','--recipe',str(args.recipe.resolve()),'--recipe-sha256',args.recipe_sha256,'--output',str(args.output.resolve()/'worker')]
        journal.append('worker_dispatch',command=command,recipe_sha256=args.recipe_sha256)
        try:result=supervise_command(command,limits=ProcessLimits(**recipe['supervision']))
        except BaseException as error:
            result=getattr(error,'tether_engine_result',getattr(error,'result',None));raise
        finally:
            if result is not None:
                publish_bytes(args.output/'stdout.txt',result.stdout);publish_bytes(args.output/'stderr.txt',result.stderr)
                write(args.output/'SUPERVISION.json',dict(returncode=result.returncode,supervision=result.supervision))
        codecs.need(result.returncode==0,'Worker failed; inspect retained failure, never automatically repeat')
        validate_success_report(result.supervision,ProcessLimits(**recipe['supervision']),len(result.stdout),len(result.stderr))
        done=json.loads((args.output/'worker/COMPLETE.json').read_bytes())
        codecs.need(done['report_sha256']==sha(args.output/'worker/REPORT.json') and
            done['journal_terminal_sha256']==read_chain(args.output/'worker/journal.jsonl')[-1]['sha256'],'Final report/journal binding')
        codecs.need(code_pins()==recipe['code_pins'],'Code changed during supervision')
        journal.append('qualification_parent_completed',worker_complete_sha256=sha(args.output/'worker/COMPLETE.json'))
        write(args.output/'COMPLETE.json',dict(status='completed',worker_complete_sha256=sha(args.output/'worker/COMPLETE.json'),
                                            recipe_sha256=args.recipe_sha256))
        print('Completed fictional qualification; inspect semantic outcomes separately.')
    except BaseException as error:
        journal.fail(error,'parent');write(args.output/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),automatic_retry=False));raise
    finally:journal.close()


if __name__=='__main__':main()
