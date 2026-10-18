"""Archive NLM XML records for cited primary papers when HTML has access gates."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from asof.serde import ContractError, read_json, sha256_file, write_json


def archive(panel_paths, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    urls = {s['url'] for p in panel_paths for c in read_json(p)['cases'] for s in c['primary_sources']}
    pmids = sorted({re.fullmatch(r'https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?', u).group(1)
                    for u in urls if re.fullmatch(r'https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?', u)})
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urlencode(
        {'db':'pubmed','id':','.join(pmids),'retmode':'xml'})
    write_json(output/'request.json', {'url':url,'requested_pmids':pmids,
        'retrieved_at_utc':datetime.now(timezone.utc).isoformat(), 'retry_count':0})
    try:
        with urlopen(url, timeout=30) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
            if response.status != 200 or len(raw) > 16 * 1024 * 1024:
                raise ContractError('Unusable NLM response')
        with (output/'pubmed.xml').open('xb') as stream:
            stream.write(raw)
        tree = ET.fromstring(raw)
        rows = []
        for node in tree.findall('./PubmedArticle'):
            pmid = node.findtext('./MedlineCitation/PMID')
            article = node.find('./MedlineCitation/Article')
            rows.append({'pmid':pmid, 'title':''.join(article.find('ArticleTitle').itertext()),
                'abstract':'\n'.join(''.join(t.itertext()) for t in article.findall('./Abstract/AbstractText')),
                'locator':f"PubmedArticle/MedlineCitation[PMID='{pmid}']",
                'source_url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/',
                'artifact_sha256':sha256_file(output/'pubmed.xml'),
                'access_depth':'abstract' if article.findall('./Abstract/AbstractText') else 'metadata'})
        if len({r['pmid'] for r in rows}) != len(rows) or {r['pmid'] for r in rows} != set(pmids):
            raise ContractError('NLM response does not exactly cover requested primary records')
        result = {'schema_version':1,'role':'evaluation_only','status':'archived',
                  'records':rows,'artifact_sha256':sha256_file(output/'pubmed.xml'),
                  'assertion_correctness':'not_inferred_from_bibliographic_matching'}
        write_json(output/'report.json', result)
        return result
    except BaseException as error:
        write_json(output/'failure.json', {'error_type':type(error).__name__,'error':str(error)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--panels', nargs='+', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = archive(args.panels,args.output)
    print({'status':report['status'],'primary_records':len(report['records'])})
