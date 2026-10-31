"""Validate unanswered shareable files and prepare a local browser smoke fixture."""
import hashlib
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

ROOT = Path(__file__).resolve().parents[3]
AREA = ROOT / 'docs/expert-review-20261026'
CACHE = ROOT / 'data/cache/opus-response-expert-qa-20261026'
CACHE.mkdir(exist_ok=True)
source = (AREA / 'Expert-review.html').read_text(encoding='utf-8')
expected = [f'{prefix}{i:02d}' for prefix in ('S', 'R') for i in range(1, 10)]


class InspectHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.radio = {}
        self.ids = []
        self.prefilled = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'input' and attrs.get('type') == 'radio':
            self.radio.setdefault(attrs['name'], []).append(attrs['value'])
            self.prefilled += 'checked' in attrs


parsed = InspectHTML()
parsed.feed(source)
assert list(parsed.radio) == expected
assert all(options == list('ABCDE') for options in parsed.radio.values())
assert len(parsed.ids) == len(set(parsed.ids))
assert parsed.prefilled == 0
assert not any(term in source for term in ('D:\\', 'E:\\', '/benchmark/', 'review-a/', 'Qwen', '4650', 'failed-candidate'))
assert not re.search(r'<(?:script|link|img)[^>]+(?:src|href)=["\']https?://', source)
script = re.search(r'<script>(.*?)</script>', source, re.S).group(1)
(CACHE / 'review.js').write_text(script, encoding='utf-8')
subprocess.run(['node', '--check', str(CACHE / 'review.js')], check=True)

pdf = PdfReader(AREA / 'Expert-review.pdf')
fields = pdf.get_fields()
assert len(pdf.pages) == 9
assert len(fields) == 63
assert set(expected) == {key for key, value in fields.items() if value.get('/FT') == '/Btn'}
assert all(fields[key].get('/V') in (None, '/Off') for key in expected)
widgets = 0
for page in pdf.pages:
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    for annotation in page.get('/Annots', []):
        widget = annotation.get_object()
        if widget.get('/Subtype') != '/Widget':
            continue
        widgets += 1
        x1, y1, x2, y2 = map(float, widget['/Rect'])
        assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
        assert widget.get('/AP', {}).get('/N') is not None
        if widget.get('/Parent'):
            assert widget in [kid.get_object() for kid in widget['/Parent'].get_object()['/Kids']]
text = '\n'.join(page.extract_text() for page in pdf.pages)
assert all(key in text for key in expected)
assert '\ufffd' not in text and '\u25a0' not in text
writer = PdfWriter()
writer.clone_document_from_reader(pdf)
writer.update_page_form_field_values(None, {'S01': NameObject('/E'), 'R01': NameObject('/E'),
                                         'reviewer_id': 'QA fixture only'}, auto_regenerate=False)
with (CACHE / 'filled-smoke.pdf').open('wb') as stream:
    writer.write(stream)
filled = PdfReader(CACHE / 'filled-smoke.pdf')
assert filled.get_fields()['S01']['/V'] == '/E'
assert filled.get_fields()['R01']['/V'] == '/E'
for key in ('S01', 'R01'):
    assert sum(kid.get_object().get('/AS') == '/E' for kid in filled.get_fields()[key]['/Kids']) == 1

browser_check = r'''
<script>
(async()=>{const result={checks:[]};try{
const check=(name,value)=>{if(!value)throw Error(name);result.checks.push(name);};
check('candidate hidden initially',byId('candidate-stage').hidden);
byId('reveal').click();check('unanswered Part 1 blocks reveal',byId('candidate-stage').hidden);
for(const q of PACKET.source_questions)document.querySelector('input[name="'+q.id+'"][value="E"]').checked=true;
byId('reviewer').value='QA fixture only';byId('reveal').click();
check('candidate revealed after source answers',!byId('candidate-stage').hidden);
check('source first pass preserves all nine',Object.keys(collect().source_only_first_pass.answers).length===9);
check('source answers locked',document.querySelector('input[name="S01"]').disabled);
document.querySelector('input[name="R01"][value="E"]').checked=true;save();
const saved=JSON.parse(localStorage.getItem(KEY));check('draft persisted',saved.answers.R01.choice==='E');
let captured;URL.createObjectURL=blob=>{captured=blob;return 'blob:qa-only';};URL.revokeObjectURL=()=>{};HTMLAnchorElement.prototype.click=()=>{};
byId('export').click();const output=JSON.parse(await captured.text());
check('export is correct packet',output.packet_id===PACKET.packet_id);
check('export retains unknown responses',output.answers.S01.choice==='E'&&output.answers.R01.choice==='E');
check('no automatic grading',!('score' in output));
window.confirm=()=>true;const previous=localStorage.getItem(KEY);
await byId('import-file').onchange({target:{files:[new File(['{"schema_version":1,"packet_id":"wrong"}'],'wrong.json')]}});
check('wrong packet import leaves draft intact',localStorage.getItem(KEY)===previous);
result.status='passed';
}catch(error){result.status='failed';result.error=error.message;}
const pre=document.createElement('pre');pre.id='qa-result';pre.textContent=JSON.stringify(result);document.body.appendChild(pre);
})();
</script>
'''
# This is an intentionally marked local QA copy, never a reviewer deliverable.
(CACHE / 'browser-smoke.html').write_text(source.replace('</body>', browser_check + '</body>'), encoding='utf-8')
report = dict(status='passed', questions=18, options=90, pdf_pages=len(pdf.pages),
              pdf_fields=len(fields), widgets=widgets, blank_answers=True,
              field_bounds_checked=True, appearances_checked=True, fill_roundtrip='passed',
              javascript_syntax='passed', private_path_and_verdict_leak_check='passed',
              browser_functional_check='pending_separate_headless_run',
              files={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (AREA/'Expert-review.html', AREA/'Expert-review.pdf')})
(CACHE / 'validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
