"""Static verbatim and separation checks; not browser rendering or science review."""
import base64
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PAGE=ROOT/'docs/expert-review-genetics-followup-20261026/Candidate-followup.html'
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.kind=None;self.text='';self.sources=[];self.answers=[];self.original=[];self.defaults=[];self.external=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('class') in ('source-text','candidate-text','original-json'):
            self.kind=attrs['class'];self.text=''
        if 'checked' in attrs or 'selected' in attrs:self.defaults.append(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        for key in ('href','src','action'):
            if key in attrs and not attrs[key].startswith('#'):self.external.append(attrs[key])
    def handle_data(self,data):
        if self.kind:self.text+=data
    def handle_endtag(self,tag):
        if self.kind and tag in ('blockquote','pre'):
            {'source-text':self.sources,'candidate-text':self.answers,'original-json':self.original}[self.kind].append(self.text)
            self.kind=None
parser=Parser();text=PAGE.read_text(encoding='utf-8');parser.feed(text)
key=json.loads((HERE/'mask-key-INTERNAL.json').read_bytes());original=[];claims=[]
for candidate in key['candidates']:
    raw=Path(candidate['wrapper_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==candidate['wrapper_sha256']
    content=json.loads(base64.b64decode(json.loads(raw)['body_base64']))['content']
    original.append(content);claims.extend(c['text'] for c in json.loads(content)['claims'])
assert parser.original==original and parser.answers==claims
cards=json.loads((ROOT/'data/cache/r07-source-revalidation-20261026-v2/source-cards.json').read_bytes())
assert parser.sources==[p['text'] for c in cards['cards'] for p in c['reported_passages']]
assert not parser.defaults and not parser.external and len(parser.ids)==len(set(parser.ids))
assert all(word not in text for word in ('Qwen','ContractError','source-review.md','exposed-il6r-genetics-current','exposed-il6r-genetics-simplified'))
assert 'WITHHOLD' in text and 'not a security barrier' in text
assert {p.name for p in PAGE.parent.iterdir()}=={'Candidate-followup.html','README.md'}
result=dict(status='passed',candidate_texts_verbatim=len(claims),original_json_blocks_verbatim=2,
            source_passages_verbatim=13,defaults=0,external_html_dependencies=0,internal_key_outside_share=True,
            html_sha256=hashlib.sha256(PAGE.read_bytes()).hexdigest(),scientific_validation='not_established',visual_browser_qa='not_performed')
(HERE/'fidelity-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
