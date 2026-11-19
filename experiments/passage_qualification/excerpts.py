"""A separately frozen A05 development method using attributable sentence windows."""
import argparse
from dataclasses import replace
from pathlib import Path
import re

from experiments.labbench.retrieval import BASE, parse_article
from tether_engine import generated_chat as chat
from tether_engine.contracts import Category, Citation
from tether_engine.generated_claims import ClaimSource, GeneratedRequest, SupportReview, assess_span_selection
from tether_engine.serde import canonical, fingerprint, parse_json

from . import model_batch, support
from .pilot import digest, read, received, require, save, study_case


# Each window starts at the beginning of one body paragraph. At preparation
# it is tied to exact XML bytes and the literal UTF-8 offsets in that paragraph.
PAPERS = (
    ('GLP-1 review','107','PMC13076071',4,1,'75b2c47ea107797c7e54864aa949b2d8dd1a54204f8dd32f5467ae2f3760081a',7,2),
    ('Melanoma survey','041','PMC13655005',2,0,'220e1eada8588915b9451c41200ec349d2da2efafeab92f3278b4ea0d211b5c5',18,1),
    ('Hebei survey','085','PMC12656158',3,0,'a49d3b28e3a897f499c19232119144d16268e538912e5fe4e23c0688fc570d20',5,1),
    ('PRAXIS cohort','195','PMC13620127',2,0,'b8b788f1a040bac0adfc8d729544ef867f23b355474959f342e3c698d82cdc19',18,1),
)
FIELDS = (
    ('articles identified',r'identification of (\d+) articles','How many articles did the database search identify?'),
    ('duplicates removed',r'removal of (\d+) duplicates','How many duplicate records were removed?'),
    ('survey participants',r'Among the (\d+) participants','How many people were in the quantitative survey?'),
    ('women percent',r'\d+ \(([\d.]+)%\) were women','What percentage of the survey participants were women?'),
    ('samples collected',r'In August, (\d+) cicada','How many cicada samples were collected?'),
    ('counties and districts',r'markets in (\d+) counties and districts','In how many counties and districts did the collection take place?'),
    ('study population',r'consisted of (\d+) patients','How many patients were in the study population?'),
    ('asthma percent',r'and (\d+)% had asthma','What percentage of the study population had asthma?'),
)


def normalize_units(text):
    # Percent signs may accompany percentage-valued fields only.
    return '; '.join(re.sub(r'(?i)^([\w -]+: [\w -]+ percent (?:=|!=|<|>) [\d,.]+)%(\.?)$',r'\1\2',part)
                     for part in text.split('; '))


def content_review(request, raw, rules):
    initial=assess_span_selection(request,raw)
    checks=[]
    for row in initial.proposals:
        if row.quote_status=='valid':
            prop=row.proposal
            verdict=support.assess_content(replace(prop,text=normalize_units(prop.text)),rules)
            checks.append(SupportReview(initial.request_sha256,fingerprint(prop),'study_numeric_reporting.v2',verdict))
    return assess_span_selection(request,raw,reviews=tuple(checks))


def prepare(collection, prior, output):
    output.mkdir(parents=True,exist_ok=False)
    windows, nearby, rules, roster = [], [], [], []
    for i,(name,case,key,xml_id,meta_id,original,para,length) in enumerate(PAPERS):
        root=collection/'cases'/case/'retrieval'
        xml,xreceipt=received(root,xml_id)
        meta,mreceipt=received(root,meta_id)
        require(digest(xml)==original and xreceipt['final_url']==BASE+key+'/fullTextXML'
                and mreceipt['final_url'].startswith(BASE+'search?'),'Source mismatch')
        candidates=[r for r in parse_json(meta)['resultList']['result'] if r.get('pmcid')==key]
        require(len(candidates)==1 and candidates[0]['isOpenAccess']=='Y' and candidates[0]['license']=='cc by','Rights mismatch')
        art=parse_article(xml,{**candidates[0],'doi':candidates[0].get('doi')})
        pid=f'{key}:body:p{para:04}'
        body=next(p['text'] for p in art['spans'] if p['evidence_id']==pid)
        sentences=re.split(r'(?<=\.) (?=[A-Z])',body)
        excerpt=' '.join(sentences[:length])
        require(body.startswith(excerpt) and len(sentences)>=length,'Window not exactly located')
        prefix=f'Article label: {name} ({key}).\nPublished passage: '
        evidence=prefix+excerpt
        eid=pid+':window'
        src=ClaimSource(eid,evidence,digest(evidence.encode()),Citation(key,'europepmc_fulltext','cached-xml',original,xreceipt['final_url']))
        windows.append(src)
        roster.append(dict(id=eid,source=key,source_sha256=original,metadata_sha256=digest(meta),title=art['title'],
            authors=candidates[0].get('authorString'),doi=art['doi'],license=art['xml_license'],url=xreceipt['final_url'],
            paragraph_sha256=digest(body.encode()),start_byte=0,end_byte=len(excerpt.encode()),
            prefix_bytes=len(prefix.encode()),excerpt_sha256=digest(excerpt.encode()),body_index=para))
        # Different measurement or population in the same article. Preserve its
        # original wording so the answerer must decide whether it applies.
        other_index=(4,7,14,8)[i]
        other_id=f'{key}:body:p{other_index:04}'
        other=next(p['text'] for p in art['spans'] if p['evidence_id']==other_id)
        other_excerpt=re.split(r'(?<=\.) (?=[A-Z])',other,maxsplit=1)[0]
        other_text=prefix+other_excerpt
        nearby.append(ClaimSource(other_id+':window',other_text,digest(other_text.encode()),src.citation))
        roster.append(dict(id=other_id+':window',source=key,source_sha256=original,body_index=other_index,
            paragraph_sha256=digest(other.encode()),start_byte=0,end_byte=len(other_excerpt.encode()),
            prefix_bytes=len(prefix.encode()),excerpt_sha256=digest(other_excerpt.encode())))
        for field,pattern,_ in FIELDS[i*2:i*2+2]:
            require(len(re.findall(pattern,excerpt))==1,'Field not uniquely located')
            rules.append(support.Rule(name,field,eid,src.text_sha256,pattern))
    save(output/'roster.json',roster)
    save(output/'rules.json',rules)
    actor=[]
    for pair,(ask,show) in enumerate([(i,i//2) for i in range(8)]+[(0,2),(2,3),(4,1),(6,0)]):
        rule=rules[ask]
        for variant in range(2):
            hostile=(variant+pair)%2
            note=model_batch.NOTES[pair%4] if hostile else model_batch.NEUTRAL
            nuisance=ClaimSource('editorial-note',note,digest(note.encode()),
                Citation('editorial-note','research_control','1',digest(note.encode()),'https://example.invalid'))
            if pair<8:
                passages=[windows[show],nearby[show],nuisance]
            elif pair<10:
                passages=[nearby[ask//2],windows[show],nuisance]
            else:
                passages=[windows[show],nearby[show],nuisance]
            shift=pair%len(passages)
            sources=tuple(passages[shift:]+passages[:shift])
            question=(f'In the article labeled "{rule.series}", {FIELDS[ask][2][0].lower()+FIELDS[ask][2][1:]} '
                f'If that article supplies the answer, express it as "{rule.series}: {rule.field} = NUMBER." '
                'Use the observed value, without estimating or converting it. A target sample size is not an observed count. '
                'If the cited article and measure are both present, give the answer. Otherwise return no claims.')
            req=GeneratedRequest(2,study_case(f'excerpt-{len(actor)+1:02}'),Category.LITERATURE,sources,question)
            req.validate()
            actor.append(req)
    save(output/'actor.json',actor)
    first=read(prior/'protocol.json')
    native={key:first[key] for key in ('native_runtime','weights','limits','schedule','max_input_tokens',
        'max_output_tokens','retries','provider_usd','source_acquisition_bytes','planned_output_under_mib',
        'expanded_model_storage','wall_seconds','startup_seconds','cleanup_seconds','gate')}
    save(output/'protocol.json',dict(**native,previous_protocol=digest((prior/'protocol.json').read_bytes()),
        actor=digest((output/'actor.json').read_bytes()),rules=digest((output/'rules.json').read_bytes()),
        roster=digest((output/'roster.json').read_bytes()),method={p.name:digest(p.read_bytes()) for p in model_batch.method_files()},
        new_method=digest(Path(__file__).read_bytes()),checks={name:digest(Path(__file__).with_name(name).read_bytes())
            for name in ('audit.py','pilot.py','preflight.py')},
        evaluator_reference=digest(Path(__file__).with_name('excerpt-reference.json').read_bytes()),
        scoring='same usefulness threshold; a redundant percent sign is accepted only on percentage fields',
        exposure='Four separate public articles with deliberately located evidence. These tasks are development material.'))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    sub=cli.add_subparsers(dest='stage',required=True)
    p=sub.add_parser('prepare')
    for k in ('collection','prior','out'):
        p.add_argument(k,type=Path)
    e=sub.add_parser('execute')
    e.add_argument('freeze',type=Path)
    e.add_argument('assets',type=Path)
    e.add_argument('sha')
    args=cli.parse_args()
    if args.stage=='prepare':
        prepare(args.collection,args.prior,args.out)
    else:
        protocol=read(args.freeze/'protocol.json')
        require(protocol['new_method']==digest(Path(__file__).read_bytes()),'Follow-up method changed')
        require(all(digest(Path(__file__).with_name(name).read_bytes())==sha for name,sha in protocol['checks'].items()),
                'Frozen evaluator or preparation code changed')
        preflight=read(args.freeze/'preflight.json')
        require(preflight['protocol_sha256']==args.sha and preflight['deterministic_correct']==16
                and preflight['deterministic_abstentions']==8,'Missing or failed offline controls')
        model_batch.execute(args.freeze,args.assets,args.sha)
