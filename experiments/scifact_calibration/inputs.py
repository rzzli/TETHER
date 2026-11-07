"""Independent, purpose-bound reconstruction of preserved SciFact preparations.

Only this preparation-audit reader sees the mixed-role original archive. Its
return value contains corpus/query views, never reference answers. Archived
projectors are compared as syntax trees and are never imported or executed.
"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import io
import math
import os
from pathlib import Path
import re
import tarfile
import unicodedata

from tether_engine.serde import ContractError, canonical, encode, freeze, parse_json

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 64 * 1024**2
MEMBERS = tuple('data/'+name+'.jsonl' for name in ('corpus','claims_train','claims_dev','claims_test'))


def need(ok, message):
    if not ok: raise ContractError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def same(left,right):
    return canonical(left)==canonical(right)


def local_path(value):
    need(isinstance(value, (str, Path)), 'Local path required')
    text = str(value)
    path = Path(text)
    need(path.is_absolute() and not text.startswith(('\\\\','//')) and
         not any(p in ('.','..') for p in text.replace('\\','/').split('/')) and
         all(p not in ('.','..') and not p.endswith((' ','.')) for p in path.parts[1:]), 'Canonical local path required')
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            need(not item.is_symlink() and not getattr(info,'st_file_attributes',0) & 0x400, 'Linked input/output ancestor')
    return path


def original_locator(value, repository_root):
    """Resolve preserved acquisition paths against their pinned original root."""
    need(isinstance(value,str) and bool(value),'Original locator required')
    pieces=value.replace('\\','/').split('/')
    need(not value.startswith(('\\\\','//')) and
         all(p not in ('.','..') and not p.endswith((' ','.')) for p in pieces),
         'Aliased original locator')
    path=Path(value)
    if path.is_absolute(): return local_path(value)
    need(not path.drive and not path.root and all(pieces),'Rooted or empty relative locator')
    return local_path(repository_root/path)


def capture(proof, maximum=MAX_BYTES):
    """Validate and return one captured buffer; consumers never re-open it."""
    need(isinstance(proof, Mapping) and set(proof)=={'path','bytes','sha256'}, 'Exact file proof required')
    need(type(proof['bytes']) is int and 0 <= proof['bytes'] <= maximum and
         isinstance(proof['sha256'],str) and re.fullmatch('[0-9a-f]{64}',proof['sha256']), 'Invalid file proof')
    path=local_path(proof['path'])
    need(path.is_file(), 'Missing regular input')
    with path.open('rb') as stream: raw=stream.read(proof['bytes']+1)
    need(len(raw)==proof['bytes'] and digest(raw)==proof['sha256'], 'Bound input bytes changed')
    return raw


def anchored(path, expected, maximum=MAX_BYTES):
    path=local_path(path)
    proof=dict(path=str(path),bytes=path.stat().st_size,sha256=expected)
    return capture(proof,maximum),proof


def _jsonl(raw, member):
    rows=[]
    for index,line in enumerate(raw.splitlines(keepends=True),1):
        need(index<=20000 and len(line)<=1024**2 and line.strip(), 'Invalid or oversized JSONL')
        row=parse_json(line); need(isinstance(row,dict), 'JSONL object required')
        rows.append((row,dict(member=member,line_1based=index,raw_line_sha256=digest(line))))
    need(rows,'Empty task member')
    return rows


def _integer(value): return type(value) is int and value>=0


def _pairs(claims):
    result=[]
    for row in sorted(claims,key=lambda x:x['id']):
        for did in sorted(set(row['cited_doc_ids'])|set(map(int,row['evidence']))):
            rationales=row['evidence'].get(str(did),[])
            sets=[list(r['sentences']) for r in rationales]
            result.append(dict(claim_id=row['id'],doc_id=did,label=rationales[0]['label'] if rationales else 'NEI',
                rationale_sentences=sorted({s for r in sets for s in r}),rationale_sets=sets,
                negative_basis=None if rationales else 'annotated_cited_document_without_evidence'))
    return result


def _split(train,dev):
    """Reconstruct connected components independently of the original union-find."""
    claims={r['id']:r for r in train+dev}; origins={r['id']:'train' for r in train}
    origins.update({r['id']:'dev' for r in dev})
    bydoc,bytext=defaultdict(list),defaultdict(list)
    for cid,row in sorted(claims.items()):
        for did in sorted(set(row['cited_doc_ids'])|set(map(int,row['evidence']))): bydoc[did].append(cid)
        normalized=' '.join(unicodedata.normalize('NFKC',row['claim']).casefold().split())
        bytext[digest(normalized.encode())].append(cid)
    adjacency={cid:set() for cid in claims}
    for ids in [*bydoc.values(),*bytext.values()]:
        for cid in ids[1:]: adjacency[ids[0]].add(cid); adjacency[cid].add(ids[0])
    unseen=set(claims); groups=[]
    while unseen:
        stack=[min(unseen)]; component=set()
        while stack:
            cid=stack.pop()
            if cid in component: continue
            component.add(cid); stack.extend(adjacency[cid]-component)
        unseen-=component; ids=sorted(component)
        group=dict(group_id=digest(canonical(ids)),claim_ids=ids,
            train_ids=[k for k in ids if origins[k]=='train'],dev_ids=[k for k in ids if origins[k]=='dev'])
        if group['dev_ids']: group['partition']='dev_connected'
        groups.append(group)
    eligible=sorted((g for g in groups if not g['dev_ids']),
        key=lambda g:(digest(('20261105:'+g['group_id']).encode()),g['group_id']))
    for i,g in enumerate(eligible): g['partition']='fit' if i<int(len(eligible)*.70) else 'tune' if i<int(len(eligible)*.85) else 'calibration'
    partitions={key:[] for key in ('fit','tune','calibration','dev','quarantined_train')}; group_by_claim={}
    for group in sorted(groups,key=lambda g:g['group_id']):
        for cid in group['claim_ids']:
            group_by_claim[str(cid)]=group['group_id']; part=group['partition']
            if part=='dev_connected': part='dev' if origins[cid]=='dev' else 'quarantined_train'
            partitions[part].append(cid)
    for values in partitions.values(): values.sort()
    labels={p:dict(sorted(Counter(r['label'] for r in _pairs([claims[c] for c in ids])).items())) for p,ids in partitions.items()}
    issues=[dict(partition=p,missing_pair_labels=sorted({'SUPPORT','CONTRADICT','NEI'}-set(labels[p])))
            for p in ('fit','tune','calibration') if set(labels[p])!={'SUPPORT','CONTRADICT','NEI'}]
    return dict(schema_version=1,seed=20261105,algorithm='source_or_nfkc_casefold_whitespace_exact_claim_components_v1',
        assignment='sorted_seeded_group_hash_floor_70_85_percent_group_boundaries',partitions=partitions,
        group_by_claim=group_by_claim,groups=sorted(groups,key=lambda g:g['group_id']),
        source_edges={str(k):v for k,v in sorted(bydoc.items()) if len(v)>1},
        exact_text_edges={k:v for k,v in sorted(bytext.items()) if len(v)>1},counts={p:len(v) for p,v in partitions.items()},
        eligible_group_count=len(eligible),group_count=len(groups),pair_label_counts=labels,feasibility_issues=issues)


def _reconstruct(raw):
    payloads={}; members={}; inventory=[]; seen=set(); total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for index,item in enumerate(archive):
            name=item.name; parts=name.split('/')
            need(index<100 and name and not name.startswith('/') and '\\' not in name and ':' not in name and
                 all(p not in ('','.','..') for p in parts) and name not in seen,'Invalid archive member')
            seen.add(name); total+=item.size
            need((item.isfile() or item.isdir()) and 0<=item.size<=16*1024**2 and total<=MAX_BYTES,'Invalid archive size/type')
            cross=bool(re.fullmatch(r'data/cross_validation/fold_[1-5]/claims_(?:train|dev)_[1-5]\.jsonl',name))
            directory=name in {'data','data/cross_validation',*(f'data/cross_validation/fold_{i}' for i in range(1,6))}
            apple=parts[-1].startswith('._') and (name=='._data' or name.startswith('data/cross_validation/'))
            need(name in MEMBERS or cross or (item.isdir() and directory) or (item.isfile() and apple),'Unknown archive member')
            need(not (name in MEMBERS or cross) or item.isfile(),'Task member must be regular')
            disposition='native_task_input' if name in MEMBERS else 'unused_cross_validation' if cross else 'directory' if item.isdir() else 'apple_metadata'
            inventory.append(dict(name=name,bytes=item.size,kind='file' if item.isfile() else 'directory',disposition=disposition))
            if name in MEMBERS:
                with archive.extractfile(item) as stream: body=stream.read(item.size+1)
                need(len(body)==item.size,'Truncated source member'); payloads[name]=body
                members[name]=dict(sha256=digest(body),bytes=len(body))
    need(set(payloads)==set(MEMBERS),'Missing task members')
    corpus={}; corpus_bindings={}; excluded=Counter()
    for row,binding in _jsonl(payloads[MEMBERS[0]],MEMBERS[0]):
        need({'doc_id','title','abstract'}<=set(row),'Missing corpus fields'); did=row['doc_id']
        need(_integer(did) and did not in corpus and isinstance(row['title'],str) and isinstance(row['abstract'],list)
             and row['abstract'] and all(isinstance(s,str) for s in row['abstract']),'Invalid corpus record')
        need('structured' not in row or type(row['structured']) is bool,'Invalid structured flag')
        view={k:row[k] for k in ('doc_id','title','abstract')}; corpus[did]=view
        binding.update(projected_sha256=digest(canonical(view)),field_sha256={k:digest(canonical(v)) for k,v in view.items()})
        corpus_bindings[str(did)]=binding; excluded.update(set(row)-set(view))
    claims={}; bindings={}; exclusions={}; ids=set(); diagnostics=[]
    for partition in ('train','dev','test'):
        member='data/claims_'+partition+'.jsonl'; values=[]; locators={}; extras=Counter()
        for row,binding in _jsonl(payloads[member],member):
            need({'id','claim'}<=set(row),'Missing claim fields'); cid=row['id']
            need(_integer(cid) and cid not in ids and isinstance(row['claim'],str) and row['claim'].strip(),'Invalid claim identity/text')
            ids.add(cid); need(partition=='test' or {'evidence','cited_doc_ids'}<=set(row),'Missing supervised fields')
            evidence=row.get('evidence',{}); cited=row.get('cited_doc_ids',[])
            need(isinstance(evidence,dict) and isinstance(cited,list) and all(_integer(d) and d in corpus for d in cited),'Invalid annotation containers')
            if len(cited)!=len(set(cited)):
                diagnostics.append(dict(kind='duplicate_cited_document_preserved',split=partition,claim_id=cid,
                    original_count=len(cited),unique_count=len(set(cited)),
                    handling='References preserve original array; source-component edges and pair identities are sets.'))
            for key,rationales in evidence.items():
                need(key.isdigit() and str(int(key))==key and int(key) in corpus and isinstance(rationales,list) and rationales,'Invalid evidence document')
                labels=set(); used=set()
                for rationale in rationales:
                    need(isinstance(rationale,dict) and set(rationale)=={'label','sentences'} and rationale['label'] in ('SUPPORT','CONTRADICT'),'Invalid rationale')
                    sentences=rationale['sentences']
                    need(isinstance(sentences,list) and sentences and all(_integer(s) and s<len(corpus[int(key)]['abstract']) for s in sentences)
                         and len(set(sentences))==len(sentences) and not used.intersection(sentences),'Invalid rationale span')
                    used.update(sentences); labels.add(rationale['label'])
                need(len(labels)==1,'Conflicting source labels')
            view=dict(id=cid,claim=row['claim'],evidence=evidence,cited_doc_ids=cited); values.append(view)
            query=dict(id=cid,claim=row['claim'])
            binding.update(query_sha256=digest(canonical(query)),reference_sha256=digest(canonical(view)),
                field_sha256={k:digest(canonical(v)) for k,v in view.items()})
            locators[str(cid)]=binding; extras.update(set(row)-set(view))
        claims[partition]=values; bindings[partition]=locators; exclusions[partition]=dict(extras)
    split=_split(claims['train'],claims['dev']); combined={r['id']:r for p in ('train','dev') for r in claims[p]}
    products={}
    def add(key,path,value,fmt,kind,purposes,fields,parents):
        body=b''.join(canonical(r)+b'\n' for r in value) if fmt=='jsonl' else canonical(value)+b'\n'
        products[key]=(body,dict(path=path,sha256=digest(body),bytes=len(body),format=fmt,kind=kind,
            purposes=sorted(set(purposes)|{'preparation_audit'}),fields=fields,rows=len(value) if fmt=='jsonl' else None,logical_parents=parents))
    add('corpus','views/corpus.jsonl',[corpus[k] for k in sorted(corpus)],'jsonl','public_corpus',
        ['fit','tune','calibrate','predict','evaluate'],['doc_id','title','abstract'],['member:data/corpus.jsonl:doc_id,title,abstract'])
    for part,purpose in (('fit','fit'),('tune','tune'),('calibration','calibrate'),('dev','predict')):
        rows=[combined[k] for k in split['partitions'][part]]; member='dev' if part=='dev' else 'train'
        add('queries_'+part,'views/queries_'+part+'.jsonl',[dict(id=r['id'],claim=r['claim']) for r in rows],
            'jsonl','query_only',[purpose],['id','claim'],['member:data/claims_'+member+'.jsonl:id,claim','split:membership'])
        add('references_'+part,'restricted/references_'+part+'.jsonl',rows,'jsonl','fit_supervision' if part=='fit' else 'evaluation_reference',
            ['evaluate' if part=='dev' else purpose],['id','claim','evidence','cited_doc_ids'],
            ['member:data/claims_'+member+'.jsonl:id,claim,evidence,cited_doc_ids','split:membership'])
    add('fit_pairs','restricted/fit_pairs.jsonl',_pairs([combined[k] for k in split['partitions']['fit']]),'jsonl','fit_supervision',
        ['fit'],['claim_id','doc_id','label','rationale_sentences','rationale_sets','negative_basis'],['references_fit'])
    add('split','restricted/split.json',split,'json','preparation_split',[],[],
        ['member:data/claims_train.jsonl:source_and_text_links','member:data/claims_dev.jsonl:source_and_text_links'])
    add('source_bindings','restricted/source_bindings.json',dict(corpus=corpus_bindings,claims=bindings),'json','preparation_locator_proof',[],[],['archive:physical_members'])
    checks=dict(members=members,inventory=inventory,schema_exclusions=dict(corpus=dict(excluded),claims=exclusions),
        diagnostics=diagnostics,counts=dict(corpus=len(corpus),**{p:len(v) for p,v in claims.items()}),
        split_counts=split['counts'],pair_label_counts=split['pair_label_counts'],feasibility_issues=split['feasibility_issues'])
    return products,split,checks


@dataclass(frozen=True)
class VerifiedPreparation:
    frame_proof: Mapping
    manifest: Mapping
    calibration_ids: tuple
    corpus: tuple
    queries: tuple
    source_proofs: tuple


def verify_preparation_transition(frame_path, expected_sha256, *, purpose='calibrate'):
    """Audit all original projections; authorize only retained calibration views."""
    need(purpose=='calibrate','Only the explicit calibrate consumer purpose is authorized')
    raw,frame_proof=anchored(frame_path,expected_sha256,1024**2); frame=parse_json(raw)
    fields={'schema_version','kind','purpose','original_repository_root','manifest','archive','acquisition','archive_receipt',
            'journal','build_report','projectors','expected_counts','expected_partitions','expected_calibration_ids'}
    need(set(frame)==fields and type(frame['schema_version']) is int and frame['schema_version']==1 and frame['kind']=='sc05_preparation_transition_v1'
         and frame['purpose']==purpose,'Unsupported preparation transition')
    manifest_raw=capture(frame['manifest']); manifest=parse_json(manifest_raw)
    need(type(manifest['schema_version']) is int and manifest['schema_version']==1 and manifest['kind']=='scifact_preparation' and manifest['authority_version']=='purpose_field_projection_v1','Unsupported original authority')
    original_root=local_path(frame['original_repository_root']); projectors=frame['projectors']
    names=['experiments/scifact/data_views.py','experiments/scifact/split.py']
    need(isinstance(projectors,list) and [x['logical_path'] for x in projectors]==names,'Exact historical projector closure required')
    expected_pins={}; source_proofs=[frame_proof]
    old_prefix=bytes((97,115,111,102)).decode()
    for item in projectors:
        need(set(item)=={'logical_path','historical','current'},'Invalid projector descriptor')
        need(local_path(item['current']['path'])==ROOT/item['logical_path'],'Wrong maintained projector locator')
        old=capture(item['historical']); new=capture(item['current'])
        old_tree=ast.parse(old.decode('utf-8-sig')); new_tree=ast.parse(new.decode('utf-8-sig'))
        for node in ast.walk(old_tree):
            if isinstance(node,ast.ImportFrom) and node.module and (node.module==old_prefix or node.module.startswith(old_prefix+'.')):
                node.module='tether_engine'+node.module[len(old_prefix):]
        need(ast.dump(old_tree,include_attributes=False)==ast.dump(new_tree,include_attributes=False),'Projector transition changes executable semantics')
        expected_pins[str(original_root/item['logical_path'])]=item['historical']['sha256']
        source_proofs.extend([item['historical'],item['current']])
    need(manifest['source_pins']==expected_pins,'Original projector proof mismatch')
    captures={key:capture(frame[key]) for key in ('archive','acquisition','archive_receipt','journal','build_report')}
    acquisition=parse_json(captures['acquisition']); receipt=parse_json(captures['archive_receipt'])
    entries=[r for r in acquisition['originals'] if Path(r['file']).name=='scifact-data.tar.gz']
    need(len(entries)==1,'Exactly one acquisition archive required'); entry=entries[0]
    archive_path=original_locator(entry['file'],original_root)
    receipt_path=original_locator(entry['receipt_file'],original_root)
    need(archive_path==local_path(frame['archive']['path']) and entry['sha256']==frame['archive']['sha256'] and entry['bytes']==frame['archive']['bytes']
         and receipt_path==local_path(frame['archive_receipt']['path']) and entry['receipt_sha256']==frame['archive_receipt']['sha256'],'Acquisition proof mismatch')
    need(receipt.get('status')=='downloaded_not_parsed' and original_locator(receipt['path'],original_root)==archive_path and receipt['sha256']==entry['sha256']
         and receipt['bytes']==entry['bytes'] and receipt['url']==entry['source_url'],'Transport receipt mismatch')
    expected_archive=dict(frame['archive'],receipt_path=frame['archive_receipt']['path'],receipt_sha256=frame['archive_receipt']['sha256'],
        url=receipt['url'],downloaded_at=receipt['finished_at_utc'],physical_role='mixed_role_preparation_container',allowed_purposes=['prepare','preparation_audit'])
    need(manifest['archive']==expected_archive and manifest['acquisition']=={k:frame['acquisition'][k] for k in ('path','sha256')},'Original archive authority mismatch')
    products,split,checks=_reconstruct(captures['archive'])
    need(set(manifest['products'])==set(products),'Original product membership mismatch')
    base=local_path(frame['manifest']['path']).parent
    need(Path(frame['manifest']['path']).name=='manifest.json' and Path(frame['journal']['path'])==base/'journal.jsonl'
         and Path(frame['build_report']['path'])==base/'build-report.json','Original control locators differ')
    allowed={'manifest.json','journal.jsonl','build-report.json'}
    for key,(body,metadata) in products.items():
        need(same(manifest['products'][key],metadata),'Reconstructed product metadata or purpose differs')
        proof=dict(path=str(base/metadata['path']),bytes=metadata['bytes'],sha256=metadata['sha256'])
        need(capture(proof)==body,'Reconstructed product differs'); source_proofs.append(proof); allowed.add(metadata['path'])
    actual=set();actual_dirs=set()
    for folder,dirs,files in os.walk(base):
        for name in dirs+files: local_path(Path(folder)/name)
        actual_dirs.update((Path(folder)/name).relative_to(base).as_posix() for name in dirs)
        actual.update((Path(folder)/name).relative_to(base).as_posix() for name in files)
    need(actual==allowed,'Original preparation has missing or extra files')
    expected_dirs={str(p).replace('\\','/') for name in allowed for p in Path(name).parents if str(p)!='.'}
    need(actual_dirs==expected_dirs,'Original preparation has missing or extra directories')
    for key,value in checks.items(): need(same(manifest[key],value),'Reconstructed preparation accounting differs: '+key)
    need(same(frame['expected_counts'],checks['counts']) and same(frame['expected_partitions'],checks['split_counts']) and
         same(frame['expected_calibration_ids'],split['partitions']['calibration']),'External preparation schedule/count mismatch')
    previous=None; events=[]
    for line in captures['journal'].splitlines():
        event=parse_json(line); sha=event.pop('sha256')
        need(event['sequence']==len(events) and event['previous_sha256']==previous and digest(canonical(event))==sha,'Original journal chain differs')
        previous=sha; events.append(event)
    need(events and events[0]['event']=='build_reserved' and events[-1]['event']=='build_completed'
         and not any(x['event'] in ('build_failed','build_interrupted') for x in events),'Original preparation did not complete')
    terminal=events[-1]['details']; elapsed=terminal.get('elapsed_seconds')
    need(terminal.get('manifest_sha256')==frame['manifest']['sha256'] and same(terminal.get('counts'),checks['counts'])
         and type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=0,'Original terminal binding differs')
    report=dict(schema_version=1,status='prepared',manifest_sha256=frame['manifest']['sha256'],elapsed_seconds=elapsed,
        **{k:checks[k] for k in ('counts','split_counts','pair_label_counts','feasibility_issues','diagnostics')},candidate_generation=False,native_scoring=False)
    need(same(parse_json(captures['build_report']),report),'Original report differs')
    source_proofs.extend(frame[k] for k in ('manifest','archive','acquisition','archive_receipt','journal','build_report'))
    views=lambda key:tuple(freeze(parse_json(line)) for line in products[key][0].splitlines())
    return VerifiedPreparation(freeze(frame_proof),freeze(manifest),tuple(frame['expected_calibration_ids']),views('corpus'),
                               views('queries_calibration'),tuple(freeze(p) for p in source_proofs))
