"""Static source fidelity / form boundary checks, not a browser rendering test."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
page=ROOT/'docs/expert-review-genetics-20261026/Expert-source-review.html'
cards=json.loads((ROOT/'data/cache/r07-source-revalidation-20261026-v2/source-cards.json').read_bytes())
class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.quotes=[];self.quote=None;self.ids=[];self.checked=[];self.external=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if 'checked' in attrs or 'selected' in attrs:self.checked.append((tag,attrs))
        for key in ('src','href','action'):
            if key in attrs and not attrs[key].startswith('#'):self.external.append((tag,key,attrs[key]))
        if tag=='blockquote':self.quote=''
        if tag=='script':self.scripts.append(attrs)
    def handle_endtag(self,tag):
        if tag=='blockquote':self.quotes.append(self.quote);self.quote=None
    def handle_data(self,data):
        if self.quote is not None:self.quote+=data
parser=Parser();text=page.read_text(encoding='utf-8');parser.feed(text)
expected=[p['text'] for card in cards['cards'] for p in card['reported_passages']]
assert parser.quotes==expected
assert not parser.checked and not parser.external and len(parser.ids)==len(set(parser.ids))
assert len(parser.scripts)==1 and not parser.scripts[0]
script=(HERE/'embedded-script.js').read_text(encoding='utf-8')
assert all(value not in script for value in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'sendBeacon', 'localStorage', 'eval('))
meta=json.loads((HERE/'form-metadata.json').read_bytes())
assert len(meta['items'])==10 and all({'cannot_assess','outside_expertise'} <= {o['value'] for o in item['options']} for item in meta['items'])
report=dict(status='passed',verbatim_passages=len(expected),source_records=len(cards['cards']),items=10,
            checked_or_selected_defaults=0,external_html_dependencies=0,duplicate_element_ids=0,
            source_cards_sha256=hashlib.sha256((ROOT/'data/cache/r07-source-revalidation-20261026-v2/source-cards.json').read_bytes()).hexdigest(),
            html_sha256=hashlib.sha256(page.read_bytes()).hexdigest(),visual_browser_qa='not_performed',scientific_review='not_performed')
(HERE/'html-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
