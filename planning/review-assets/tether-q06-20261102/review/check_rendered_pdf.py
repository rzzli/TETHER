"""Independent read-only Q06 staged source/PDF retention and contact sheets."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from pypdf import PdfReader
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
STAGE = ROOT / 'data/cache/tether-q06/working-v2'
PDF = STAGE / 'paper/tether-source-reporting-preprint.pdf'
BUILD = STAGE / 'paper/TETHER-PDF-BUILD.json'
PREVIEWS = STAGE / 'tmp/pdfs/q06-pages/b6a93fadbd309ba0'
checks = []
def digest(raw): return hashlib.sha256(raw).hexdigest()
def check(name, ok, detail=None): checks.append(dict(name=name, passed=bool(ok), detail=detail))
pdf_bytes = PDF.read_bytes()
build = json.loads(BUILD.read_text())
stage_record = json.loads((ROOT / 'planning/review-assets/tether-q06-20261102/STAGE-PREPARATION-working-v2.json').read_text())
check('pdf_exact_expected_hash', digest(pdf_bytes) == 'b6a93fadbd309ba03fe2497d0e59fcd5bf4344d7ed7cd3693840ee87485b5f23')
reader = PdfReader(PDF)
check('23_pages', len(reader.pages) == 23)
check('author_blank', not reader.metadata.get('/Author'))
pages = [page.extract_text() for page in reader.pages]
for i, text in enumerate(pages, 1):
    (HERE / f'pdf-page-{i:02d}.txt').write_text(text, encoding='utf-8')
    check(f'page_{i}_nonempty', len(text) > 100)
    check(f'page_{i}_no_replacement_or_placeholder', '\ufffd' not in text and 'ZZINLINEPLACEHOLDER' not in text)
    check(f'page_{i}_header_footer', re.match(rf'^TETHER - Working research draft\s+{i}\s+', text) is not None)

# pypdf text extraction only; no renderer/parser imports. Exact ordered search
# of each source line, heading, caption and table cell after documented visible
# Markdown/typography removal; PDF headers/footers are excluded from the search.
def norm(text):
    text = text.translate(str.maketrans({'\u2010':'-', '\u2011':'-', '\u2012':'-', '\u2013':'-', '\u2014':' - ', '\u2212':'-', '\u2018':"'", '\u2019':"'", '\u201c':'"', '\u201d':'"', '\u00a0':' '}))
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))
def visible(text):
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    return text
clean_pages = [re.sub(rf'^TETHER - Working research draft\s+{i}\s+', '', t) for i, t in enumerate(pages, 1)]
# Merged vector figures occur last in PDF operator order, even when they are
# visually above a body paragraph. Remove only the exact, independently
# extracted figure suffixes on the three inspected figure pages. Otherwise a
# paragraph continuing across a page break is interrupted in raw extraction.
normalized_pages = [norm(t) for t in clean_pages]
for page_number, filename in [(6, 'figure1-flow.pdf'), (8, 'figure2-availability.pdf'), (9, 'figure3-controls.pdf')]:
    figure = PdfReader(STAGE / 'paper/results/figures' / filename)
    figure_text = norm(figure.pages[0].extract_text())
    suffix_matches = normalized_pages[page_number - 1].endswith(figure_text)
    check('exact_vector_text_suffix:' + filename, suffix_matches)
    if suffix_matches:
        normalized_pages[page_number - 1] = normalized_pages[page_number - 1][:-len(figure_text)]
alltext = ''.join(normalized_pages)
cursor = 0
unit_count = 0
retention_failures = []
source_records = []
for name in ['manuscript.md', 'supplement.md']:
    orig = ROOT / 'paper/revisions/20261102' / name
    staged = STAGE / 'paper' / name
    raw = orig.read_bytes()
    actual = staged.read_bytes()
    transformed = raw.replace(b'](../../results/', b'](results/')
    if name == 'supplement.md':
        transformed = transformed.replace(b'](../../release/tether-v2/CURRENT-SOFTWARE.md)', b'](../documentation/CURRENT-SOFTWARE.md)').replace(b'](../../release/tether-v2/SOFTWARE-QUALIFICATION.json)', b'](../documentation/SOFTWARE-QUALIFICATION.json)')
    check(name + '_only_declared_link_transforms', transformed == actual)
    source_records.append(dict(source=str(orig.relative_to(ROOT)), source_sha256=digest(raw), staged_sha256=digest(actual)))
    for lineno, line in enumerate(actual.decode('utf-8').splitlines(), 1):
        if not line.strip(): continue
        if line.startswith('|'):
            parts = [x.strip() for x in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?', x) for x in parts): continue
        else:
            parts = [re.sub(r'^#{1,6}\s+', '', line)]
        for part in parts:
            unit_count += 1
            key = norm(visible(part))
            at = alltext.find(key, cursor)
            if at < 0:
                retention_failures.append(dict(source=name, line=lineno, text=part[:180]))
            else:
                cursor = at + len(key)
check('every_visible_source_unit_in_order', not retention_failures, dict(units=unit_count, failures=retention_failures))
uris = []
for page in reader.pages:
    for ref in page.get('/Annots', []):
        action = ref.get_object().get('/A', {})
        if action.get('/URI'): uris.append(str(action['/URI']))
check('software_json_annotation_preserved', '../documentation/SOFTWARE-QUALIFICATION.json' in uris)
check('software_guide_annotation_preserved', '../documentation/CURRENT-SOFTWARE.md' in uris)
check('formatter_exact_narrow_revision', digest((ROOT / 'tools/presentation/build_tether_manuscript_v2.py').read_bytes()) == 'c695400bf7a411f661d0b3bd8f1771eee3d550bd793e178ad6bd29318916b719')

images = sorted(PREVIEWS.glob('page-*.png'))
check('all23_previews', len(images) == 23)
preview_records = [dict(file=p.name, sha256=digest(p.read_bytes())) for p in images]
sheets = []
for start in range(0, len(images), 4):
    sheet = Image.new('RGB', (1740, 2260), '#d3d9de')
    draw = ImageDraw.Draw(sheet)
    for offset, path in enumerate(images[start:start+4]):
        page = Image.open(path).convert('RGB')
        page.thumbnail((850, 1100))
        x, y = (offset % 2) * 870 + 10, (offset // 2) * 1130 + 25
        sheet.paste(page, (x, y))
        draw.text((x, y-20), f'PAGE {start+offset+1}', fill='black')
    dest = HERE / f'pdf-contact-{start+1:02d}-{min(start+4,len(images)):02d}.png'
    sheet.save(dest)
    sheets.append(dict(path=str(dest), sha256=digest(dest.read_bytes())))
check('pdf_stable_during_check', PDF.read_bytes() == pdf_bytes)
result = dict(schema_version=1, checked_at_utc=datetime.now(timezone.utc).isoformat(), status='PASS_NAMED_PDF_CHECKS' if all(c['passed'] for c in checks) else 'FINDINGS', checks=checks, pdf=dict(path=str(PDF),sha256=digest(pdf_bytes),bytes=len(pdf_bytes)), sources=source_records, build_manifest_sha256=digest(BUILD.read_bytes()), stage_record_sha256=digest((ROOT/'planning/review-assets/tether-q06-20261102/STAGE-PREPARATION-working-v2.json').read_bytes()), checker_sha256=digest(Path(__file__).read_bytes()), previews=preview_records, contact_sheets=sheets, scope='Independent staged-source transformations, ordered visible source retention, links and page metadata; visual review separately required. No backend/source study rerun.')
out = HERE / ('PDF-CHECK-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
with out.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2)
print(json.dumps(dict(record=str(out),status=result['status'],checks=len(checks),failures=[c for c in checks if not c['passed']],contact_sheets=sheets),indent=2))
