"""Explicitly invented privileged-paper diagnostic controls."""
from asof.serde import canonical
from experiments.litqa_comparison import qualification_fixtures as primary

DOI='10.1234/invented'


def queries():return primary.queries()


def fetch(url,**limits):
    if '/search?' not in url:return primary.fetch(url,**limits)
    body=canonical(dict(hitCount=1,resultList=dict(result=[dict(pmcid='PMC7000001',doi=DOI,title='Explicitly invented diagnostic control',
        isOpenAccess='Y',license='cc by',firstPublicationDate='2020-01-01')])))
    return dict(status=200,body=body,final_url=url,headers={'Content-Type':'application/json','X-TETHER-Fixture':'invented-no-http-dispatch'})
