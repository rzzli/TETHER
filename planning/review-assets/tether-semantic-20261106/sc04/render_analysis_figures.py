"""Plot sealed SC04 metrics without rerunning models, scoring, or statistics.

This presentation layer checks acceptance/analysis receipts and direct plot-data
joins. It relies on the accepted qualified analysis for scientific arithmetic and
source/native reconstruction. DOI identity coverage is not evidence entailment.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata as metadata
import json
import math
import os
from pathlib import Path
import stat
import sys
import time

ARMS=('L/O','E/O','L/R','E/R','supplied')
LABELS=('Lexical queries\nLexical passages','Expanded queries\nLexical passages','Lexical queries\nModel ranked','Expanded queries\nModel ranked','Supplied sources\nDiagnostic')
CONTRASTS=('expansion_at_lexical','ranking_at_lexical','combined_vs_lexical','interaction','marginal_expansion','marginal_ranking')
CONTRAST_LABELS=('Expansion with lexical ordering','Ranking with lexical retrieval','Expansion + ranking vs lexical','Expansion × ranking interaction','Marginal expansion','Marginal ranking')
LIMIT=128*1024**2


def need(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(value):return hashlib.sha256(value).hexdigest()


def raw(path):
    path=Path(path);before=path.lstat()
    need(stat.S_ISREG(before.st_mode) and not path.is_symlink() and not getattr(before,'st_file_attributes',0)&0x400,'Nonregular or linked input')
    need(before.st_size<=LIMIT,'Input byte bound')
    with path.open('rb') as f:data=f.read(LIMIT+1)
    after=path.lstat()
    need(len(data)==before.st_size<=LIMIT and (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns),'Input changed during read')
    return data


def load(path):
    def pairs(items):
        result={}
        for k,v in items:need(k not in result,'Duplicate JSON field');result[k]=v
        return result
    def bad(_):raise ValueError('Nonfinite JSON value')
    return json.loads(raw(path),object_pairs_hook=pairs,parse_constant=bad)


def proof(path):
    p=Path(path).absolute();data=raw(p);return dict(path=str(p),bytes=len(data),sha256=sha(data))


def inventory(root):
    result={};total=0;deadline=time.monotonic()+120
    for path in root.rglob('*'):
        need(time.monotonic()<deadline,'Inventory time bound');s=path.lstat()
        need(not path.is_symlink() and not getattr(s,'st_file_attributes',0)&0x400,'Linked inventory entry')
        if path.is_dir():continue
        relative=path.relative_to(root).as_posix()
        if relative=='RECEIPT.json':continue
        total+=s.st_size;need(len(result)<10000 and total<=2*1024**3,'Inventory count/byte bound')
        result[relative]=proof(path)
    return result


def receipt(root,anchor):
    root=Path(root).absolute();s=root.lstat()
    need(root.is_dir() and not root.is_symlink() and not getattr(s,'st_file_attributes',0)&0x400,'Linked receipt root')
    path=root/'RECEIPT.json';need(sha(raw(path))==anchor,'External receipt anchor mismatch')
    value=load(path);need(value['status']=='complete' and value['files']==inventory(root),'Incomplete or changed sealed inventory')
    return value


def anchored_load(path,anchor):
    need(sha(raw(path))==anchor,'External input anchor mismatch');return load(path)


def rate(value,label):
    need(type(value) in (int,float) and math.isfinite(value) and 0<=value<=1,label);return float(value)


def count(value,label):
    need(type(value) is int and value>=0,label);return value


def extract(results,acceptance,fictional):
    purpose='fictional_qualification' if fictional else 'production'
    need(acceptance['status']=='PASS' and acceptance['purpose']==purpose,'Acceptance purpose/status')
    n=2 if fictional else 199;pairs=2 if fictional else 205;groups=1 if fictional else 186
    need(results['scheduled_count']==acceptance['questions']==n and acceptance['arms']==5 and acceptance['answer_records']==n*5,'Complete five-arm schedule')
    need(acceptance['source_pairs']==pairs and acceptance['publication_groups']==groups,'Pinned source/group denominators')
    need(set(results['arms'])==set(results['source_metrics'])==set(ARMS),'Complete arm/source family')
    arms=[];sources=[]
    for arm in ARMS:
        value=results['arms'][arm];c=value['counts'];need(value['scheduled_count']==n,'Arm schedule count')
        correct=count(c['raw_correct'],'Correct count');answered=count(c['raw_answered'],'Substantive count')
        need(correct<=answered<=n,'Correct/substantive counts exceed denominator')
        accuracy=rate(value['raw_metrics']['accuracy'],'Raw accuracy');coverage=rate(value['raw_metrics']['coverage'],'Coverage')
        need(math.isclose(accuracy,correct/n) and math.isclose(coverage,answered/n),'Direct arm rate/count join')
        precision=value['statistical_raw_precision'];defined=value['raw_precision_defined']
        if answered:
            need(defined is True and precision is not None,'Nonzero substantive denominator must define precision')
            precision=rate(precision,'Precision');need(math.isclose(precision,value['raw_metrics']['precision']) and math.isclose(precision,correct/answered),'Precision count/source disagreement')
        else:need(defined is False and precision is None,'Zero substantive denominator requires undefined precision')
        arms.append(dict(arm=arm,scheduled=n,raw_correct=correct,substantive_answers=answered,raw_accuracy=accuracy,substantive_coverage=coverage,substantive_precision=precision))
        layers=[]
        for layer in ('retained','pool','selected'):
            s=results['source_metrics'][arm][layer];den=count(s['annotated_source_count'],'Source denominator');num=count(s['matched_annotated_source_count'],'Source numerator')
            need(den==pairs and num<=den and s['scheduled_count']==n,'Complete source-pair denominator')
            value=rate(s['annotated_source_recall'],'Source-pair coverage');need(math.isclose(value,num/den),'Source count/rate join')
            layers.append(dict(layer=layer,matched=num,annotated_pairs=den,coverage=value))
        need(layers[2]['matched']<=layers[1]['matched']<=layers[0]['matched'],'Selected/pool/retained source nesting')
        sources.append(dict(arm=arm,layers=layers))
    lo,eo,lr,er=[r['raw_accuracy'] for r in arms[:4]]
    expected_contrasts=dict(expansion_at_lexical=eo-lo,ranking_at_lexical=lr-lo,combined_vs_lexical=er-lo,
        interaction=(er-lr)-(eo-lo),marginal_expansion=((eo-lo)+(er-lr))/2,marginal_ranking=((lr-lo)+(er-eo))/2)
    panels=[]
    for key in ('publication_components','question_sensitivity'):
        panel=results['paired']['metrics']['raw_accuracy'][key]
        expected_groups=groups if key=='publication_components' else n
        need(panel['case_count']==n and panel['group_count']==expected_groups and sum(panel['group_sizes'])==n,'Paired denominator')
        need(panel['requested_replicates']==10000 and panel['seed']==20261106,'Frozen bootstrap settings')
        estimable=expected_groups>=2
        need(panel['uncertainty_estimable'] is estimable and panel['completed_replicates']==(10000 if estimable else 0),'CI estimability/replicate count')
        need(set(panel['contrasts'])==set(CONTRASTS),'All six contrasts')
        rows=[]
        for name in CONTRASTS:
            value=panel['contrasts'][name];estimate=value['estimate'];interval=value['ci95']
            need(type(estimate) in (int,float) and math.isfinite(estimate) and -2<=estimate<=2,'Finite contrast estimate')
            need(math.isclose(estimate,expected_contrasts[name],rel_tol=1e-12,abs_tol=1e-12),'Contrast point/arm-rate join')
            if estimable:
                need(isinstance(interval,list) and len(interval)==2 and all(type(v) in (int,float) and math.isfinite(v) and -2<=v<=2 for v in interval) and interval[0]<=interval[1],'Finite ordered CI')
            else:need(interval is None,'One-group CI must remain undefined')
            rows.append(dict(contrast=name,estimate=estimate,ci95=interval))
        panels.append(dict(kind=key,case_count=n,group_count=expected_groups,uncertainty_estimable=estimable,
                           completed_replicates=panel['completed_replicates'],contrasts=rows))
    return dict(kind='sc04_figure_data_v1',purpose=purpose,fictional=fictional,scheduled_questions=n,annotated_source_pairs=pairs,
        publication_groups=groups,arms=arms,contrasts=panels,sources=sources,
        labels=dict(arms=dict(zip(ARMS,LABELS)),contrasts=dict(zip(CONTRASTS,CONTRAST_LABELS))),
        scope=['Presentation of accepted retained numbers only; no score changes, fitting, resampling, or model calls.',
               'Raw accuracy includes every scheduled question; coverage excludes unsure and operational failures.',
               'Precision is conditional on substantive answers and undefined with zero substantive answers.',
               'DOI source-pair identity matches do not establish passage support or scientific entailment.',
               'Supplied sources are a diagnostic arm, not ordinary retrieval.'])


def inputs(analysis,analysis_sha,accepted,accepted_sha,fictional):
    receipt(accepted,accepted_sha);a=load(accepted/'ROOT-ACCEPTANCE.json')
    need(a['analysis_receipt']==proof(analysis/'RECEIPT.json') and a['analysis_receipt']['sha256']==analysis_sha,'Acceptance/analysis receipt join')
    receipt(analysis,analysis_sha)
    r=load(analysis/'worker/RESULTS.json');data=extract(r,a,fictional)
    return data,dict(analysis_receipt=proof(analysis/'RECEIPT.json'),acceptance_receipt=proof(accepted/'RECEIPT.json'),
                    accepted_report=proof(accepted/'ROOT-ACCEPTANCE.json'),results=proof(analysis/'worker/RESULTS.json'),
                    acceptance_code=a['acceptance_code'],controls=a['controls'],
                    trust='Original/native reconstruction and metric arithmetic are delegated to the retained qualified analysis and accepted root report.')


def environment(path,anchor):
    value=anchored_load(path,anchor);need(value['status']=='PASS','Qualified plotting environment required')
    installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in metadata.distributions()}
    need(installed==value['installed'],'Plotting dependency versions changed')
    need(proof(sys.executable)==value['executable'] and proof(sys._base_executable)==value['base_executable'],'Plotting interpreter changed')
    return value


def render(data,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter,PercentFormatter
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'svg.fonttype':'none','svg.hashsalt':'tether-sc04-figures-v1','figure.facecolor':'white','savefig.facecolor':'white'})
    labels=[data['labels']['arms'][a] for a in ARMS];colours=['#286B92']*4+['#9364A6']
    banner='FICTIONAL QUALIFICATION — NOT BENCHMARK RESULTS' if data['fictional'] else 'TETHER · SC04 public-development evaluation'
    files=[]
    def finish(fig,name,title,footer):
        fig.suptitle(title,fontsize=17,fontweight='bold',x=.06,ha='left',y=.94)
        fig.text(.06,.985,banner,fontsize=11,color='#9A3412' if data['fictional'] else '#334155',weight='bold',ha='left',va='top')
        fig.text(.06,.025,footer,fontsize=9,color='#475569',va='bottom',ha='left')
        for ext in ('svg','png'):
            path=output/(name+'.'+ext);fig.savefig(path,dpi=180,metadata={'Creator':'TETHER SC04 accepted-metric renderer'} if ext=='svg' else {'Software':'TETHER SC04 accepted-metric renderer'})
            files.append(proof(path))
        plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,6.4));fig.subplots_adjust(left=.065,right=.98,top=.79,bottom=.28,wspace=.35)
    keys=('raw_accuracy','substantive_coverage','substantive_precision');titles=('Full-schedule accuracy','Substantive answer coverage','Precision among substantive answers')
    for ax,key,title in zip(axes,keys,titles):
        values=[r[key] for r in data['arms']]
        ax.bar(range(5),[0 if v is None else v for v in values],color=colours,width=.68)
        for i,(v,row) in enumerate(zip(values,data['arms'])):
            text='Undefined\n(no substantive answers)' if v is None else f'{v:.1%}'
            ax.text(i,.03 if v is None else v+.035,text,ha='center',va='bottom',fontsize=9)
        ax.set_xticks(range(5),labels,rotation=35,ha='right',fontsize=8);ax.set_ylim(0,1.15);ax.set_yticks([0,.25,.5,.75,1]);ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_title(title,fontsize=11,pad=14);ax.set_axisbelow(True);ax.grid(axis='y',color='#E2E8F0')
    finish(fig,'01-answer-performance','Answer performance across the full schedule',
           f"{data['scheduled_questions']} scheduled questions per arm. Purple = supplied-source diagnostic.\nRaw accuracy and coverage retain failures in their denominators; precision is conditional, not calibrated clinical confidence.")
    fig,axes=plt.subplots(1,2,figsize=(14,7));fig.subplots_adjust(left=.27,right=.96,top=.78,bottom=.20,wspace=.30)
    all_points=[abs(x) for p in data['contrasts'] for r in p['contrasts'] for x in [r['estimate'],*(r['ci95'] or [])]]
    bound=max(.05,max(all_points)*1.25)
    for ax,panel in zip(axes,data['contrasts']):
        for i,row in enumerate(panel['contrasts']):
            ci=row['ci95'];estimate=row['estimate']
            if ci is not None:
                ax.hlines(i,ci[0],ci[1],color='#286B92',linewidth=2);ax.plot([ci[0],ci[1]],[i,i],'|',color='#286B92',markersize=8)
            ax.plot(estimate,i,'o',color='#286B92',markersize=6)
        ax.set_yticks(range(6),CONTRAST_LABELS if ax is axes[0] else ['']*6,fontsize=9);ax.invert_yaxis();ax.set_xlim(-bound,bound);ax.axvline(0,color='#94A3B8',linestyle='--',linewidth=1)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value,_:f'{value*100:g}'));ax.set_xlabel('Difference in raw accuracy (percentage points)',fontsize=9);ax.grid(axis='x',color='#E2E8F0')
        main='Publication-group bootstrap' if panel['kind']=='publication_components' else 'Question-level sensitivity'
        subtitle=f"{panel['group_count']} groups · 10,000 retained replicates" if panel['uncertainty_estimable'] else '1 group · points only; 95% intervals undefined'
        ax.set_title(main+'\n'+subtitle,fontsize=11,pad=14)
    finish(fig,'02-raw-accuracy-contrasts','Six prespecified contrasts and retained 95% intervals',
           'Positive simple/marginal contrasts favor the named intervention; interaction is a difference of differences.\nValues and intervals are read from sealed analysis; this renderer performs no resampling. Question sensitivity does not replace publication grouping.')
    fig,axes=plt.subplots(1,3,figsize=(15,6.4));fig.subplots_adjust(left=.065,right=.98,top=.79,bottom=.28,wspace=.3)
    for j,(ax,title) in enumerate(zip(axes,('Retained source articles','Candidate passage pool','Selected answer context'))):
        rows=[a['layers'][j] for a in data['sources']];values=[r['coverage'] for r in rows]
        ax.bar(range(5),values,color=colours,width=.68)
        for i,(v,r) in enumerate(zip(values,rows)):ax.text(i,v+.035,f"{r['matched']}/{r['annotated_pairs']}",ha='center',fontsize=10)
        ax.set_xticks(range(5),labels,rotation=35,ha='right',fontsize=8);ax.set_ylim(0,1.15);ax.set_yticks([0,.25,.5,.75,1]);ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_title(title,fontsize=11,pad=14);ax.set_axisbelow(True);ax.grid(axis='y',color='#E2E8F0')
    finish(fig,'03-annotated-doi-coverage','Annotated DOI pair coverage through retrieval',
           f"Denominator = {data['annotated_source_pairs']} annotated question–DOI pairs at every layer. Purple = supplied-source diagnostic.\nBibliographic identity match only: zero can reflect missing DOI metadata; matching a DOI does not establish scientific support or entailment.")
    return files


def write(path,value):
    with path.open('xb') as f:f.write(canonical(value)+b'\n')


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--analysis-sha256',required=True)
    p.add_argument('--acceptance',type=Path,required=True);p.add_argument('--acceptance-sha256',required=True)
    p.add_argument('--environment',type=Path,required=True);p.add_argument('--environment-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fictional',action='store_true');a=p.parse_args(argv)
    output=a.output.absolute();output.mkdir(parents=True,exist_ok=False);previous=None;sequence=0
    def event(stage,**values):
        nonlocal previous,sequence
        record=dict(sequence=sequence,previous_sha256=previous,stage=stage,at_utc=datetime.now(timezone.utc).isoformat(),**values)
        previous=sha(canonical(record));record['sha256']=previous;sequence+=1
        with (output/'journal.jsonl').open('ab') as f:f.write(canonical(record)+b'\n');f.flush();os.fsync(f.fileno())
    event('reserved',fictional=a.fictional)
    try:
        env=environment(a.environment,a.environment_sha256);event('environment_verified')
        data,sources=inputs(a.analysis.absolute(),a.analysis_sha256,a.acceptance.absolute(),a.acceptance_sha256,a.fictional);event('accepted_inputs_verified')
        frame=dict(kind='sc04_figure_frame_v1',helper=proof(__file__),environment=proof(a.environment),argv=sys.argv,sources=sources,
            purpose=data['purpose'],dependency_versions=env['installed'],no_models=True,no_network=True,no_statistical_reestimation=True)
        write(output/'FRAME.json',frame);write(output/'PLOT-DATA.json',data);event('plot_data_sealed')
        files=render(data,output);event('rendered',figures=3,files=len(files))
        write(output/'COMPLETE.json',dict(status='complete',purpose=data['purpose'],figures=files,source_proofs=sources,scientific_validation='not_established',visual_inspection='pending'))
        event('complete');write(output/'RECEIPT.json',dict(status='complete',files=inventory(output)))
        print(json.dumps(dict(status='complete',receipt=proof(output/'RECEIPT.json'))));return 0
    except BaseException as error:
        event('failed',error_type=type(error).__name__);write(output/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,message=str(error),automatic_retry=False));raise


if __name__=='__main__':raise SystemExit(main())
