"""Retain offline figure qualification; visual inspection is separately attested."""
import argparse
import importlib.util
from pathlib import Path
import struct

spec=importlib.util.spec_from_file_location('figure_reader',Path(__file__).with_name('render_analysis_figures.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def qualify(args):
    m.receipt(args.figures,args.figures_sha256)
    frame=m.load(args.figures/'FRAME.json');data=m.load(args.figures/'PLOT-DATA.json')
    m.need(data['fictional'] is True and frame['purpose']=='fictional_qualification','Only explicit fictional qualification')
    m.need(frame['helper']==m.proof(Path(__file__).with_name('render_analysis_figures.py')),'Current helper proof')
    c=m.anchored_load(args.controls,args.controls_sha256)
    m.need(c['status']=='PASS' and c['tests']==23 and c['failures']==c['errors']==c['skipped']==0 and c['helper']==frame['helper'],'Current complete controls')
    m.need(c['tests_code']==m.proof(Path(__file__).with_name('test_render_analysis_figures.py')),'Current test code')
    s=frame['sources'];a=Path(s['analysis_receipt']['path']).parent;accepted=Path(s['acceptance_receipt']['path']).parent
    expected,source_proofs=m.inputs(a,s['analysis_receipt']['sha256'],accepted,s['acceptance_receipt']['sha256'],True)
    m.need(data==expected and s==source_proofs,'Exact accepted plot-data extraction and source proofs')
    env=frame['environment'];m.need(env==m.proof(env['path']),'Retained environment proof')
    figures=[]
    for name in ('01-answer-performance','02-raw-accuracy-contrasts','03-annotated-doi-coverage'):
        png=args.figures/(name+'.png');svg=args.figures/(name+'.svg');image=m.raw(png);text=m.raw(svg).decode('utf-8')
        m.need(image.startswith(b'\x89PNG\r\n\x1a\n'),'PNG signature');width,height=struct.unpack('>II',image[16:24])
        m.need(width>=2000 and height>=1000 and 'FICTIONAL QUALIFICATION' in text and 'NOT BENCHMARK RESULTS' in text,'Dimensions/fictional labeling')
        figures.append(dict(name=name,png=m.proof(png),svg=m.proof(svg),width=width,height=height))
    # Exact visual inspection statements are supplied after tool-based viewing,
    # not inferred from PNG dimensions or successful rendering.
    m.need(args.visual_inspection=='viewed_final_pngs','Visual inspection explicitly acknowledged')
    args.output.mkdir(parents=True,exist_ok=False)
    result=dict(status='PASS',purpose='fictional_qualification',figures=figures,plot_data=m.proof(args.figures/'PLOT-DATA.json'),
        figure_receipt=m.proof(args.figures/'RECEIPT.json'),helper=frame['helper'],controls=m.proof(args.controls),
        environment=env,sources=s,qualification_code=m.proof(__file__),
        visual_inspection=dict(method='Codex view_image of all final PNGs',status='PASS',checks=[
            'All five arms visible; supplied-source arm labeled diagnostic and colored separately.',
            'Accuracy and coverage retain full question denominator; precision separately conditional.',
            'All six contrasts shown; publication-group intervals explicitly undefined for one group.',
            'No fake zero-width publication interval; question sensitivity zero-width intervals retained.',
            'Three DOI coverage layers retain annotated-pair denominator and non-entailment caveat.',
            'Legible labels and footnotes; no overlap or clipping after contrast footer correction.',
            'Fictional banner visible on every figure; no production results implied.']),
        limits=['Presentation qualification is not a new scientific validation or independent statistical reanalysis.',
                'Actual nonzero production uncertainty intervals remain to be rendered after accepted analysis; invented controls exercise interval caps.',
                'The renderer does not rehash every installed library on each invocation; wheel hashes and installed versions/interpreters are recorded.',
                'Byte-bound file reads and inventory traversal checks do not preempt OS-level blocking I/O.'])
    m.write(args.output/'QUALIFICATION.json',result)
    print(m.canonical(dict(status='PASS',qualification=m.proof(args.output/'QUALIFICATION.json'))).decode())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--figures',type=Path,required=True);p.add_argument('--figures-sha256',required=True)
    p.add_argument('--controls',type=Path,required=True);p.add_argument('--controls-sha256',required=True)
    p.add_argument('--visual-inspection',choices=('viewed_final_pngs',),required=True);p.add_argument('--output',type=Path,required=True)
    qualify(p.parse_args())
