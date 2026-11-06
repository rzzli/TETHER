"""Independent raw-XML passage and DOI checks for SC04 analysis.

The caller must first verify the enclosing source receipt/package anchor. These
checks never turn a reference-paper match into semantic support or relevance.
"""
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit
import xml.etree.ElementTree as ET

from .native_records import need,read,digest,safe_path


def doi(value):
    if not isinstance(value,str) or not value.strip():return None
    value=value.strip()
    if value.lower().startswith('doi:'):value=value[4:].strip()
    if value.startswith(('https://','http://')):
        parsed=urlsplit(value)
        if parsed.netloc.lower() not in ('doi.org','dx.doi.org','www.doi.org') or parsed.query or parsed.fragment:return None
        value=unquote(parsed.path.lstrip('/'))
    if re.fullmatch(r'10\.[0-9]{4,9}/[^\s"\\]+',value) is None:return None
    return value.lower()


def local_path(root,name):
    root=safe_path(root);relative=Path(name)
    need(not relative.is_absolute() and not relative.drive and '..' not in relative.parts,'Unsafe original source path')
    path=safe_path(root/relative);need(path.is_relative_to(root),'Linked/escaped original source')
    return path


def read_article(root,source):
    original=source['original'];raw=read(local_path(root,original['path']),2*1024**2)
    need(len(raw)==original['bytes'] and digest(raw)==original['sha256'],'Original article byte binding')
    need(b'<!ENTITY' not in raw.upper(),'Entity declarations are excluded')
    tree=ET.fromstring(raw)
    pmcs=[''.join(n.itertext()).strip().removeprefix('PMC') for n in tree.findall('./front/article-meta/article-id')
          if n.get('pub-id-type') in ('pmc','pmcid')]
    need(source['source_id'].removeprefix('PMC') in pmcs,'Article-front PMC identity')
    xml_raw=[''.join(n.itertext()).strip() for n in tree.findall('./front/article-meta/article-id') if n.get('pub-id-type')=='doi']
    xml_normalized={doi(value) for value in xml_raw};unknown_xml=None in xml_normalized;xml_normalized.discard(None)
    metadata=doi(source.get('doi'));reason=None;resolved=None;basis=None
    if unknown_xml:reason='invalid_article_front_doi'
    elif len(xml_normalized)>1:reason='conflicting_article_front_dois'
    elif metadata and xml_normalized and metadata not in xml_normalized:reason='metadata_xml_doi_conflict'
    elif metadata:resolved=metadata;basis='metadata_and_xml' if xml_normalized else 'metadata_only'
    elif xml_normalized:resolved=next(iter(xml_normalized));basis='xml_only'
    else:reason='doi_unavailable'
    paragraphs={}
    for section,xpath in (('abstract','.//abstract//p'),('body','.//body//p')):
        elements=tree.findall(xpath);need(len(elements)<=10000,'Original paragraph count bound')
        for i,element in enumerate(elements):
            text=' '.join(' '.join(element.itertext()).split())
            if text:paragraphs[f'{source["source_id"]}:{section}:p{i:04d}']=text
    need(len({s['evidence_id'] for s in source['spans']})==len(source['spans']),'Duplicate manifest paragraph identity')
    need({s['evidence_id']:s['text'] for s in source['spans']}==paragraphs,'Manifest paragraphs differ from original XML')
    for span in source['spans']:need(digest(span['text'].encode())==span['text_sha256'],'Original paragraph hash')
    return dict(source_id=source['source_id'],paragraphs=paragraphs,original_sha256=original['sha256'],
        metadata_doi_raw=source.get('doi'),xml_dois_raw=xml_raw,reconciled_doi=resolved,doi_basis=basis,doi_unknown_reason=reason,
        scope='Exact captured article/text identity; no assertion of relevance or answer entailment.')


def selected_passages(items,bindings,articles):
    by_id={b['source_id']:b for b in bindings}
    need(len(by_id)==len(bindings),'Ambiguous passage binding')
    seen=set();selected_dois=set();rows=[]
    for item in items:
        key=item['source_id'];need(key not in seen and key in by_id,'Missing/duplicate selected raw passage');seen.add(key)
        binding=by_id[key];need(binding['document_id'] in articles,'Missing original article')
        article=articles[binding['document_id']]
        need(binding['original_sha256']==article['original_sha256'],'Selected original article binding')
        span=article['paragraphs'][binding['span_id']];start,end=binding['character_start'],binding['character_end']
        need(type(start) is int and type(end) is int and 0<=start<end<=len(span),'Original character offsets')
        need(binding['parent_text_sha256']==digest(span.encode()) and span[start:end]==item['text'] and
             item['sha256']==digest(item['text'].encode()),'Selected passage differs from original characters')
        if article['reconciled_doi']:selected_dois.add(article['reconciled_doi'])
        rows.append(dict(source_id=key,document_id=binding['document_id'],doi=article['reconciled_doi'],bytes=len(item['text'].encode())))
    return dict(passages=rows,selected_dois=sorted(selected_dois),selected_bytes=sum(r['bytes'] for r in rows),
                semantic_support_verified=False)
