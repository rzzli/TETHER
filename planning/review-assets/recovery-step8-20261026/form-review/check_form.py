import hashlib,json
from html.parser import HTMLParser
from pathlib import Path
root=Path('docs/expert-review-source-feasibility-20261026'); audit=Path(__file__).parent
class FormParser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.inside=False;self.parts=[];self.texts=[];self.groups=set();self.external=[];self.defaults=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='blockquote':self.inside=True;self.parts=[]
        if tag=='input' and a.get('type')=='radio':
            self.groups.add(a['name'])
            if 'checked' in a:self.defaults.append(a)
        if tag in ('script','iframe','img','link') and ('src' in a or 'href' in a):self.external.append(a)
    def handle_data(self,data):
        if self.inside:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='blockquote':self.texts.append(''.join(self.parts));self.inside=False
p=FormParser();p.feed((root/'Expert-source-review.html').read_text(encoding='utf-8'))
expected=json.loads((audit/'expected-text.json').read_bytes())
assert p.texts==expected and len(p.texts)==8
assert len(p.groups)==14 and not p.defaults and not p.external
expected_files={'Expert-source-review.html','README.md','Recruitment.md'}
actual_files=set(f.name for f in root.iterdir())
assert actual_files in (expected_files, expected_files|{'Expert-source-review-share.zip'})
out={'status':'static_checks_passed','exact_passage_equality':True,'passage_occurrences':8,'unique_passage_texts':len(set(p.texts)),'radio_groups':len(p.groups),'preselected_radio_answers':0,'external_dependencies':0,'clean_share_files':3,'browser_render_and_export_qa':'pending_root','html_sha256':hashlib.sha256((root/'Expert-source-review.html').read_bytes()).hexdigest()}
(audit/'static-checks.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
