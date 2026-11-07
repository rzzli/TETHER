"""Explicitly invented HTTP bodies for controller qualification only."""
from tether_engine.serde import canonical


def queries():
    return [dict(id=f'00000000-0000-0000-0000-{i:012d}',
                 question=question,choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])
            for i,question in [(901,'In the invented Lumarin experiment, what happened to cobalt uptake after treatment?'),
                               (902,'In the invented Vesprine experiment, what happened to amber uptake after treatment?')]]


def fetch(url,**limits):
    if '/search?' in url:
        body=canonical(dict(resultList=dict(result=[dict(pmcid='PMC7000001',title='Explicitly invented SC04 control',
            doi=None,isOpenAccess='Y',license='cc by',firstPublicationDate='2020-01-01')])))
    else:
        body=b'''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta>
<article-id pub-id-type="pmcid">PMC7000001</article-id><permissions><license>
<license-p>This is an explicitly invented control, not a publication. Creative Commons Attribution License.</license-p>
<ext-link xlink:href="https://creativecommons.org/licenses/by/4.0/"/></license></permissions>
</article-meta></front><body><p>In the invented Lumarin experiment, treatment increased cobalt uptake relative to vehicle.</p>
<p>In the invented Vesprine experiment, treatment reduced amber uptake relative to vehicle.</p></body></article>'''
    return dict(status=200,body=body,final_url=url,headers={'Content-Type':'application/json' if '/search?' in url else 'application/xml',
                                                          'X-TETHER-Fixture':'invented-no-http-dispatch'})
