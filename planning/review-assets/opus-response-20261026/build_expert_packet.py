"""Build the unanswered development exercise from retained source/candidate bytes.

Uses the Codex bundled document dependencies, not the project's runtime environment.
No model calls, network calls, answer keys or external web assets are included.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/expert-review-20261026'
SOURCE = ROOT / 'runs/question-development-20261026T023832Z/tasks/mechanism-context/scientific-view.json'
CANDIDATE = ROOT / 'data/benchmark/labels/question-development-review-20261026/attempt-v1/candidate-original-content.txt'
PACKET_ID = 'asof-il6r-development-review-20261026-v1'
TITLE = 'Independent Scientific Evidence Review'
SUBTITLE = 'IL6R and rheumatoid arthritis development exercise'


def question(identifier, stem, options, evidence):
    assert len(options) == 5
    return dict(id=identifier, stem=stem, options=options, evidence=evidence)


SOURCE_QUESTIONS = [
    question('S01', 'What type of evidence is supplied in the source cards?', [
        'A report of a randomized antibody trial.',
        'A secondary review summarizing earlier research and proposals.',
        'A prospective genetic association cohort.',
        'A pharmacokinetic experiment.',
        'Cannot assess from the supplied material.',
    ], 'Source citation and description'),
    question('S02', 'Which experimental context is reported in P4 for the RANKL finding?', [
        'Treated RA patients followed for joint damage.',
        'RA fibroblast-like synoviocytes exposed to IL-6 with or without soluble IL-6R.',
        'Healthy volunteers receiving an IL6R antibody.',
        'Human hepatocytes exposed to a small molecule.',
        'Cannot assess from the supplied material.',
    ], 'P4'),
    question('S03', 'Which contrast accompanies the RANKL finding in P4?', [
        'IL-6 plus soluble IL-6R versus IL-6 alone.',
        'Antibody versus placebo in patients.',
        'Gene knockout versus wild type.',
        'No contrast is described.',
        'Cannot assess from the supplied material.',
    ], 'P4'),
    question('S04', 'Which endpoint is reported for that contrast in P4?', [
        'Reduced clinical disease activity.',
        'Improved survival.',
        'RANKL induction.',
        'Antibody concentration.',
        'Cannot assess from the supplied material.',
    ], 'P4'),
    question('S05', 'Which result is described in P5?', [
        'IL6R blockade suppressed a reported B-cell RAG gene-expression response.',
        'IL6R blockade cured RA.',
        'A drug improved an adjudicated clinical endpoint.',
        'Antibody binding affinity was measured.',
        'Cannot assess from the supplied material.',
    ], 'P5'),
    question('S06', 'How should the antibody-development statement in P2 be classified?', [
        'A demonstrated clinical treatment effect.',
        'A conditional mechanism/development proposal attributed to earlier authors.',
        'A direct measurement of antibody efficacy in the supplied experiment.',
        'Proof that every IL6R intervention has the same effect.',
        'Cannot assess from the supplied material.',
    ], 'P2'),
    question('S07', 'How should the repeated identical passages in this extraction be treated?', [
        'As independent experimental replications.',
        'As independent patients.',
        'As repeated text; independence of underlying studies remains unresolved.',
        'As contradictory evidence.',
        'Cannot assess from the supplied material.',
    ], 'Occurrence note below the source cards'),
    question('S08', 'Which statement about sample size, dose and exposure duration is justified?', [
        'All three are specified for the RANKL result.',
        'Only sample size is specified for that result.',
        'Only dose and duration are specified for that result.',
        'These details are not provided in the supplied excerpt set.',
        'Cannot assess from the supplied material.',
    ], 'P1-P7; consider these excerpts, not the entire article'),
    question('S09', 'What conclusion about patient treatment benefit is established by these excerpts?', [
        'Benefit from an IL6R antibody is demonstrated in treated patients.',
        'Benefit from an IL6R antibody is disproven.',
        'They supply biological/proposal context without establishing a patient treatment effect.',
        'The resource annotation supplies a probability of benefit.',
        'Cannot assess from the supplied material.',
    ], 'P1-P7; consider these excerpts, not the entire article'),
]

RATING_QUESTIONS = [
    question('R01', 'How well does Candidate A answer the requested mechanism-context question?', [
        'Fully answers it with useful, appropriately bounded context.',
        'Substantially answers it, with minor omissions.',
        'Provides some supported content but omits important supplied context.',
        'Does not provide a scientifically usable answer.',
        'Cannot assess or outside my expertise.',
    ], 'Question, source cards and both candidate claims'),
    question('R02', 'How do you interpret the repeated limitation about no specific experimental or observational context?', [
        'Clearly justified for the supplied passages as a whole.',
        'Justified for particular missing details, but too broad as written.',
        'Clearly contradicted and unambiguously denies every available context.',
        'Ambiguous; clarification is needed before assigning that interpretation.',
        'Cannot assess or outside my expertise.',
    ], 'P4-P7 and the exact limitation; explain your reading'),
    question('R03', 'How is applicability to the IL6R inhibition/antibody hypothesis best described?', [
        'The supplied evidence demonstrates a specific context mismatch.',
        'Some disease/action alignment exists, but applicability remains uncertain.',
        'Alignment is sufficient to establish patient benefit.',
        'There is insufficient information to judge alignment.',
        'Outside my expertise.',
    ], 'Case hypothesis, source cards and candidate context_mismatch labels'),
    question('R04', 'How should the candidate population field RA patients be understood?', [
        'A demonstrated enrolled and treated study population.',
        'The intended disease population only; the candidate makes that meaning clear.',
        'Ambiguous; intended population and observed subjects should be distinguished.',
        'Proven irrelevant to the supplied evidence.',
        'Cannot assess or outside my expertise.',
    ], 'Candidate structured fields and supplied experimental contexts'),
    question('R05', 'Does A1\'s actual cited passage P1 support its pathway-target claim?', [
        'Fully supports the claim.',
        'Supports part of the claim only.',
        'Does not support it, although another supplied passage may.',
        'Contradicts the claim.',
        'Cannot assess or outside my expertise.',
    ], 'P1 and A1; assess the actual citation separately from other support'),
    question('R06', 'Does A2\'s actual cited passage P2 support its antibody-development claim?', [
        'Fully supports the claim.',
        'Supports part of the claim only.',
        'Does not support it, although another supplied passage may.',
        'Contradicts the claim.',
        'Cannot assess or outside my expertise.',
    ], 'P2 and A2; assess the actual citation separately from other support'),
    question('R07', 'Which single change would most improve the scientific usefulness of this answer?', [
        'Preserve the reported experimental model, contrast and endpoint.',
        'Improve the exact source citation and attribution.',
        'Distinguish proposals from observations more clearly.',
        'Explain applicability, uncertainty or ambiguous fields more clearly.',
        'No change needed, another change, or cannot assess; explain below.',
    ], 'Choose the most important change, not every desirable improvement'),
    question('R08', 'What is the highest scientific problem severity you identify in the candidate?', [
        'Critical: a clear false or unsupported conclusion likely to reverse the scientific assessment.',
        'Major: a consequential error or omission, without that critical conclusion.',
        'Minor: a limited precision or presentation problem.',
        'No scientific problem identified in the material assessed.',
        'Cannot assess or outside my expertise.',
    ], 'Assess scientific content, not native JSON formatting; explain uncertainty'),
    question('R09', 'How much underlying scientific credibility can you assess from the supplied review excerpts?', [
        'Enough to accept every mechanistic statement as independently established.',
        'Some statements raise a specific biological or methodological concern; explain.',
        'Source fidelity can be assessed, but underlying validity needs primary-study review.',
        'I have no specific concern, but cannot independently validate the underlying studies here.',
        'Outside my expertise or cannot assess.',
    ], 'Optional critique may include source wording such as soluble IL-6R; do not silently correct it'),
]

INSTRUCTIONS = (
    'We ask you to judge how accurately a research summary describes supplied biological evidence. '
    'This is a development exercise, not an examination of your professional competence. '
    'Complete the source-only section before reading Candidate A. No account, installation or '
    'internet research is required. Choose one option per question. Uncertainty and outside-expertise '
    'responses are valid. Confidence means confidence in your judgment, including that evidence is insufficient. '
    'Please work independently and record any later external lookup separately. '
    'The initial 30-45 minute estimate is unmeasured; please record your actual time.'
)
CASE = ('Case hypothesis: IL6R inhibition using an antibody for rheumatoid arthritis. '
        'Intended tissue is unspecified. The review task is to identify reported manipulation/exposure, '
        'model/population, comparator, endpoint and timing when supplied, distinguish findings from proposals, '
        'and explain limits of applicability. Missing details do not imply absent biology or patient benefit.')
CITATION = ('Charles J Malemud. Recent advances in neutralizing the IL-6 pathway in arthritis. '
            'Open Access Rheumatology, 2009;1:133-150. DOI 10.2147/OARRR.S6266. '
            'Secondary review, not an original experiment. Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC5074717/.')
SOURCE_NOTE = ('These are the seven unique passages supplied to the candidate, in first-occurrence order. '
               'The extraction contains 12 occurrences: P1 once, P2 once, P3 three times, P4 twice, '
               'P5 three times, P6 once and P7 once. Repeated passages are not independent studies. '
               'The cards are selected excerpts, not the entire article. Sample size, dose, duration '
               'and complete primary-study methods are not provided here. The source wording is preserved, '
               'including statements you may wish to question. Judge fidelity and underlying credibility separately.')
GLOSSARY = ('RA = rheumatoid arthritis; RA-FLS = fibroblast-like synoviocytes associated with RA; '
            'sIL-6R = soluble IL-6 receptor; RANKL = receptor activator of nuclear factor kappa-B ligand; '
            'RAG = recombination activating gene; SF = synovial fluid; gp130 = glycoprotein 130. '
            'These expansions do not establish an experimental result.')


def load_data():
    view = json.loads(SOURCE.read_text(encoding='utf-8'))
    candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))
    cards = []
    seen = set()
    for index, passage in enumerate(view['records'][0]['reported_passages']):
        text = passage['text']
        if text not in seen:
            cards.append(dict(id='P' + str(len(cards) + 1), text=text, first_occurrence=index))
            seen.add(text)
    assert len(cards) == 7 and len(candidate['claims']) == 2
    questions = SOURCE_QUESTIONS + RATING_QUESTIONS
    assert len({q['id'] for q in questions}) == len(questions) == 18
    return dict(packet_id=PACKET_ID, title=TITLE, subtitle=SUBTITLE, cards=cards,
                claims=candidate['claims'], source_questions=SOURCE_QUESTIONS,
                rating_questions=RATING_QUESTIONS)


def build_html(data):
    def esc(value):
        return html.escape(str(value), quote=True)

    def render_questions(questions):
        blocks = []
        for q in questions:
            options = ''.join(
                f'<label class="option"><input type="radio" name="{q["id"]}" value="{chr(65+i)}">'
                f'<span><b>{chr(65+i)}.</b> {esc(option)}</span></label>'
                for i, option in enumerate(q['options']))
            blocks.append(f'''<fieldset data-question="{q['id']}"><legend>{q['id']}. {esc(q['stem'])}</legend>
<p class="hint">Evidence: {esc(q['evidence'])}</p>{options}
<div class="subfields"><label>Confidence in this judgment <select data-confidence="{q['id']}"><option value="">Unanswered</option><option>Low</option><option>Moderate</option><option>High</option></select></label>
<label>Source card or short explanation <textarea data-note="{q['id']}" rows="2" placeholder="Optional; especially helpful for ambiguity or concerns"></textarea></label></div></fieldset>''')
        return '\n'.join(blocks)

    cards = ''.join(f'<article class="source"><h3>{c["id"]}</h3><p>{esc(c["text"])}</p></article>' for c in data['cards'])
    candidates = []
    for index, claim in enumerate(data['claims']):
        citation = 'P1' if index == 0 else 'P2'
        rows = ''.join(f'<dt>{esc(k.replace("_", " "))}</dt><dd>{esc("Unspecified (null)" if v is None else str(v).lower() if isinstance(v, bool) else v)}</dd>'
                       for k, v in claim['proposition'].items())
        candidates.append(f'''<article class="candidate"><h3>A{index+1}</h3><p>{esc(claim['text'])}</p>
<p><b>Actual cited passage:</b> {citation}. <b>Applicability label:</b> {esc(claim['applicability'])}.</p>
<p><b>Limitation:</b> {esc(claim['limitations'][0])}</p><details open><summary>Scientific structured fields</summary><dl>{rows}</dl></details></article>''')
    rendered = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Independent Scientific Evidence Review</title><style>
:root{font-family:system-ui,Segoe UI,sans-serif;color:#17212b;background:#f5f6f7;line-height:1.55}body{margin:0}main{max-width:880px;margin:auto;padding:28px 24px 80px;background:white}h1{font-size:2rem;line-height:1.2;margin:0 0 8px}h2{font-size:1.45rem;margin-top:36px}h3{font-size:1.1rem;margin-bottom:6px}.subtitle,.hint{color:#4c5966}.hint{font-size:.92rem}label{display:block}input[type=text],textarea,select,input[type=number]{font:inherit;box-sizing:border-box;max-width:100%;border:1px solid #8d98a2;border-radius:5px;padding:9px;background:white;color:#17212b}input[type=text],textarea{width:100%}.meta{display:grid;grid-template-columns:1fr 1fr;gap:14px}.meta label{font-size:.95rem}fieldset{border:1px solid #aeb7bf;border-radius:8px;padding:18px;margin:24px 0;break-inside:avoid}legend{font-weight:650;padding:0 6px}.option{display:flex;gap:10px;align-items:flex-start;border-radius:5px;padding:9px 8px;cursor:pointer}.option:hover{background:#edf3f8}.option:has(input:checked){background:#e5eff8}.option input{width:18px;height:18px;margin-top:4px;flex-shrink:0}.subfields{margin-top:14px;display:grid;grid-template-columns:190px 1fr;gap:14px}.subfields label{font-size:.9rem}.subfields textarea,.subfields select{margin-top:6px}.source{border-left:3px solid #8194a6;padding-left:18px;margin:22px 0}.source h3{color:#1c3448}.candidate{padding:4px 0 14px;border-bottom:1px solid #b7c0c7}dl{display:grid;grid-template-columns:minmax(120px,1fr) 3fr;gap:6px 16px;font-size:.92rem}dt{color:#4c5966}dd{margin:0}button,.download{font:inherit;padding:10px 15px;border-radius:5px;border:1px solid #37556d;background:#254c6a;color:white;cursor:pointer;text-decoration:none;display:inline-block;margin:5px 6px 5px 0}button.secondary{background:white;color:#254c6a}button:disabled{opacity:.5;cursor:default}.toolbar{position:sticky;top:0;background:#fff;border-bottom:1px solid #c6ced5;padding:8px 0;z-index:2}.toolbar p{margin:0;font-size:.88rem}#message{min-height:1.4em;font-size:.9rem}a{color:#1e557b}small{color:#4c5966}[hidden]{display:none!important}.footer{border-top:1px solid #c6ced5;padding-top:20px;margin-top:34px}input:focus-visible,button:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #d19d33;outline-offset:2px}@media(max-width:600px){main{padding:20px 16px 70px}.meta,.subfields{grid-template-columns:1fr}h1{font-size:1.65rem}dl{grid-template-columns:1fr}dd{margin-bottom:6px}}@media print{body{background:white}main{max-width:none;padding:0}.toolbar,button,.screen-only{display:none!important}h2{break-after:avoid}#candidate-stage[hidden]{display:none!important}fieldset{border:1px solid #888}textarea{min-height:38px}details{display:block}}
</style></head><body><main><h1>Independent Scientific Evidence Review</h1><p class="subtitle">IL6R and rheumatoid arthritis development exercise</p>
<p>__INSTRUCTIONS__</p><p><b>Privacy:</b> this file makes no network requests and does not upload answers. Draft saving depends on your browser. Export a backup before closing.</p>
<div class="toolbar"><button id="export">Export answers</button><button id="import" class="secondary">Import draft</button><button id="print" class="secondary">Print this stage</button><span id="progress"></span><p id="message" role="status" aria-live="polite"></p><input type="file" id="import-file" accept="application/json,.json" hidden></div>
<h2>Reviewer details</h2><div class="meta">
<label>Reviewer ID or preferred name<input type="text" id="reviewer" autocomplete="off"></label>
<label>Relevant field or role<input type="text" id="expertise"></label>
<label>Relevant experience<input type="text" id="experience" placeholder="Briefly describe; years optional"></label>
<label>Prior exposure to this example or project<select id="exposure"><option value="">Unanswered</option><option>No</option><option>Yes</option><option>Unsure</option></select></label>
<label>Conflicts or related involvement<input type="text" id="conflicts" placeholder="None, or describe"></label>
<label>Credit preference<select id="credit"><option value="">Unanswered</option><option>Pseudonymous</option><option>Attributed with agreement</option><option>Discuss with coordinator</option></select></label>
<label>Actual review time in minutes<input type="number" id="minutes" min="0"></label>
<label>Areas outside your expertise<input type="text" id="outside"></label></div>
<h2>The scientific question</h2><p>__CASE__</p><p>__GLOSSARY__</p>
<h2>Source cards</h2><p>__CITATION__ <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC5074717/" target="_blank" rel="noopener">Optional original article</a>.</p>
<p>__SOURCE_NOTE__</p>__CARDS__
<p class="hint">Source attribution: &copy; 2009 Malemud; publisher and licensee Dove Medical Press Ltd. The article permits noncommercial use with attribution. These selected passages were retained in the project's source packet.</p>
<section id="source-stage"><h2>Part 1 Source only</h2><p>Answer before seeing the candidate summary. Choose one option for each item; use the uncertainty option when needed.</p>__SOURCE_QUESTIONS__
<label>Your source-only summary of the important contexts and limits<textarea id="source-reference" rows="4" placeholder="Optional; what should a useful answer preserve?"></textarea></label>
<p>When you continue, this first-stage record is preserved in your exported answers. This helps keep source reading distinct from candidate assessment. This exposed development exercise is not a locked H5 evaluation.</p>
<button id="reveal">Preserve Part 1 and show Candidate A</button></section>
<section id="candidate-stage" hidden><h2>Part 2 Candidate assessment</h2><p>Candidate A is one anonymous development response. Below are its two prose claims, actual citations, limitations and scientific structured fields. No prior review verdict is supplied. Formatting-contract validity is outside this exercise.</p>
__CANDIDATES__<p class="hint">context_mismatch is the candidate's label. Judge whether the source establishes a mismatch. Unspecified (null) means that field was left unanswered.</p>
__RATING_QUESTIONS__<label>Important correction or uncertainty not captured above<textarea id="final-note" rows="4"></textarea></label>
<label>External information used after the source-only stage, if any<textarea id="lookups" rows="2" placeholder="Source, date and what it changed; leave blank if none"></textarea></label>
<p>Please export your answers and return the file through your agreed channel. There is no automatic submission or score.</p></section>
<div class="footer"><p><a href="Expert-review.pdf">Fillable or printable PDF</a> &middot; <a href="Recruitment.md">Invitation and purpose</a></p><small>Packet __PACKET_ID__. Development only. No clinical prediction or treatment recommendation.</small><p><button id="reset" class="secondary">Start a new review</button></p></div>
<script>
const PACKET=__DATA__,KEY='asof-expert-review:'+PACKET.packet_id,IDS=[...PACKET.source_questions,...PACKET.rating_questions].map(q=>q.id),META=['reviewer','expertise','experience','exposure','conflicts','credit','minutes','outside','source-reference','final-note','lookups'];
let firstPass=null,startedAt=new Date().toISOString();const byId=id=>document.getElementById(id),message=t=>byId('message').textContent=t;
function collect(){const answers={};for(const id of IDS){answers[id]={choice:document.querySelector('input[name="'+id+'"]:checked')?.value||null,confidence:document.querySelector('[data-confidence="'+id+'"]').value||null,note:document.querySelector('[data-note="'+id+'"]').value};}const metadata={};for(const id of META)metadata[id]=byId(id).value;return {schema_version:1,role:'evaluation_only',packet_id:PACKET.packet_id,purpose:'development_orientation_not_locked_H5',started_at:startedAt,exported_at:new Date().toISOString(),candidate_revealed:firstPass!==null,source_only_first_pass:firstPass,metadata,answers};}
function progress(){const v=collect(),n=Object.values(v.answers).filter(a=>a.choice).length;byId('progress').textContent=n+' / '+IDS.length+' answered';}
function save(){try{localStorage.setItem(KEY,JSON.stringify(collect()));}catch(e){message('Draft storage is unavailable. Export answers to keep a copy.');}progress();}
function showCandidate(){byId('candidate-stage').hidden=false;byId('reveal').disabled=true;byId('reveal').textContent='Part 1 preserved';for(const q of PACKET.source_questions){for(const input of document.querySelectorAll('[data-question="'+q.id+'"] input,[data-question="'+q.id+'"] select,[data-question="'+q.id+'"] textarea'))input.disabled=true;}byId('source-reference').readOnly=true;}
function restore(value){if(value.packet_id!==PACKET.packet_id||value.schema_version!==1||!value.metadata||!value.answers)throw Error('This is not an answer file for this packet version.');for(const id of META)byId(id).value=typeof value.metadata[id]==='string'?value.metadata[id]:'';for(const id of IDS){const a=value.answers[id]||{};if(a.choice&&!['A','B','C','D','E'].includes(a.choice))throw Error('Invalid answer choice.');const input=a.choice?document.querySelector('input[name="'+id+'"][value="'+a.choice+'"]'):null;if(input)input.checked=true;document.querySelector('[data-confidence="'+id+'"]').value=['Low','Moderate','High'].includes(a.confidence)?a.confidence:'';document.querySelector('[data-note="'+id+'"]').value=typeof a.note==='string'?a.note:'';}firstPass=value.source_only_first_pass||null;startedAt=typeof value.started_at==='string'?value.started_at:startedAt;if(firstPass)showCandidate();progress();}
document.addEventListener('input',save);document.addEventListener('change',save);
byId('reveal').onclick=()=>{const v=collect();if(PACKET.source_questions.some(q=>!v.answers[q.id].choice)){message('Please answer each Part 1 item, using Cannot assess when appropriate.');return;}firstPass={preserved_at:new Date().toISOString(),answers:Object.fromEntries(PACKET.source_questions.map(q=>[q.id,v.answers[q.id]])),source_reference:byId('source-reference').value};showCandidate();save();message('Part 1 preserved. Candidate A is now available below.');byId('candidate-stage').scrollIntoView({behavior:'smooth'});};
byId('export').onclick=()=>{const value=collect(),blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Expert-review-'+(value.metadata.reviewer||'anonymous').replace(/[^a-z0-9_-]/gi,'_')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Answer file exported. Please save it and return it through your agreed channel.');};
byId('print').onclick=()=>window.print();byId('import').onclick=()=>byId('import-file').click();byId('import-file').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>1000000)throw Error('Answer file is too large.');if(!confirm('Replace the current draft with this saved answer file? Export first if needed.'))return;const imported=JSON.parse(await f.text());if(imported.packet_id!==PACKET.packet_id||imported.schema_version!==1||!imported.metadata||!imported.answers)throw Error('This file is not a draft for this packet.');for(const id of IDS){const a=imported.answers[id]||{};if(a.choice&&!['A','B','C','D','E'].includes(a.choice))throw Error('Invalid answer choice.');}localStorage.setItem(KEY,JSON.stringify(imported));location.reload();}catch(error){message(error.message);}};
byId('reset').onclick=()=>{if(confirm('Clear this browser draft and start a new review? Export a backup first.')){try{localStorage.removeItem(KEY);}catch(e){}location.reload();}};
try{const value=localStorage.getItem(KEY);if(value)restore(JSON.parse(value));}catch(error){message('Saved draft could not be loaded. Import a valid exported answer file or start a new review.');}progress();
</script></main></body></html>'''
    replacements = dict(INSTRUCTIONS=esc(INSTRUCTIONS), CASE=esc(CASE), GLOSSARY=esc(GLOSSARY),
                        CITATION=esc(CITATION), SOURCE_NOTE=esc(SOURCE_NOTE), CARDS=cards,
                        SOURCE_QUESTIONS=render_questions(SOURCE_QUESTIONS),
                        RATING_QUESTIONS=render_questions(RATING_QUESTIONS),
                        CANDIDATES=''.join(candidates), PACKET_ID=PACKET_ID,
                        DATA=json.dumps(dict(packet_id=PACKET_ID, source_questions=SOURCE_QUESTIONS,
                                             rating_questions=RATING_QUESTIONS), ensure_ascii=False).replace('<', '\\u003c'))
    for name, value in replacements.items():
        rendered = rendered.replace('__' + name + '__', value)
    (OUT / 'Expert-review.html').write_text(rendered, encoding='utf-8')


STYLES = getSampleStyleSheet()
pdfmetrics.registerFont(TTFont('ReviewSans', 'C:/Windows/Fonts/arial.ttf'))
STYLES.add(ParagraphStyle(name='ReviewBody', fontName='ReviewSans', fontSize=10, leading=14,
                         spaceAfter=8, textColor=colors.black))
STYLES.add(ParagraphStyle(name='ReviewSmall', parent=STYLES['ReviewBody'], fontSize=8.8, leading=12))
STYLES.add(ParagraphStyle(name='ReviewSource', parent=STYLES['ReviewBody'], fontSize=9.6,
                         leading=13, spaceAfter=6))
STYLES.add(ParagraphStyle(name='ReviewCompact', parent=STYLES['ReviewSmall'], leading=11,
                         spaceAfter=3))
for name in ('Title', 'Heading1', 'Heading2', 'Heading3'):
    STYLES[name].textColor = colors.black
STYLES['Title'].fontSize = 23
STYLES['Title'].leading = 28
STYLES['Title'].alignment = TA_LEFT
STYLES['Heading3'].spaceBefore = 5
STYLES['Heading3'].spaceAfter = 4


def para(text, style='ReviewBody'):
    return Paragraph(html.escape(text).replace('\n', '<br/>'), STYLES[style])


class TextField(Flowable):
    def __init__(self, name, label, height=27):
        Flowable.__init__(self)
        self.name, self.label, self.height = name, label, height + 20
        self.box_height = height

    def wrap(self, width, height):
        self.width = width
        return width, self.height

    def draw(self):
        self.canv.setFont('Helvetica', 9)
        self.canv.drawString(0, self.height - 11, self.label)
        self.canv.acroForm.textfield(name=self.name, tooltip=self.label, x=0, y=1,
                                    width=self.width, height=self.box_height, relative=True,
                                    fontName='Helvetica', fontSize=9, borderWidth=.5,
                                    fillColor=colors.white, borderColor=colors.HexColor('#8b969e'),
                                    textColor=colors.black, fieldFlags='multiline' if self.box_height > 22 else '')


class ChoiceQuestion(Flowable):
    def __init__(self, item):
        Flowable.__init__(self)
        self.item = item

    def wrap(self, width, height):
        self.width = width
        self.stem = para(self.item['id'] + '. ' + self.item['stem'])
        self.stem_height = self.stem.wrap(width, height)[1]
        self.options = []
        for i, text in enumerate(self.item['options']):
            p = para(chr(65+i) + '. ' + text, 'ReviewSmall')
            h = max(15, p.wrap(width-23, height)[1])
            self.options.append((p, h + 5))
        self.height = self.stem_height + sum(h for _, h in self.options) + 67
        return width, self.height

    def draw(self):
        y = self.height - self.stem_height
        self.stem.drawOn(self.canv, 0, y)
        y -= 4
        for i, (p, h) in enumerate(self.options):
            y -= h
            self.canv.acroForm.radio(name=self.item['id'], value=chr(65+i),
                                    tooltip=self.item['id'] + ' choose one option',
                                    x=0, y=y + h - 16, size=11, relative=True,
                                    selected=False, buttonStyle='circle', borderWidth=.7,
                                    borderColor=colors.HexColor('#5f6c76'), fillColor=colors.white)
            p.drawOn(self.canv, 22, y + 3)
        self.canv.setFont('Helvetica', 8)
        self.canv.drawString(0, y - 10, 'Confidence')
        self.canv.acroForm.choice(name=self.item['id'] + '_confidence', tooltip='Confidence in your judgment',
                                 x=55, y=y - 15, width=105, height=17, relative=True,
                                 options=['Unanswered', 'Low', 'Moderate', 'High'], value='Unanswered',
                                 fontName='Helvetica', fontSize=8, fillColor=colors.white,
                                 borderWidth=.5, borderColor=colors.HexColor('#8b969e'))
        self.canv.drawString(175, y - 10, 'Source card or short explanation')
        self.canv.acroForm.textfield(name=self.item['id'] + '_note', tooltip='Source card or short explanation',
                                    x=0, y=y - 48, width=self.width, height=27, relative=True,
                                    fontName='Helvetica', fontSize=8, fieldFlags='multiline',
                                    fillColor=colors.white, borderWidth=.5,
                                    borderColor=colors.HexColor('#8b969e'))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#465561'))
    canvas.drawString(19*mm, 13*mm, 'IL6R development exercise | Unanswered expert form | 26 October 2026')
    canvas.drawRightString(A4[0]-19*mm, 13*mm, str(doc.page))
    canvas.restoreState()


def build_pdf(data):
    story = [para(TITLE, 'Title'), para(SUBTITLE), para(INSTRUCTIONS), para(CASE),
             para('How to use this form', 'Heading2'),
             para('Complete Part 1 before reading Candidate A. Save a copy of your first-stage answers before continuing. '
                  'This PDF contains both stages and cannot enforce that order. The HTML guides the sequence. '
                  'Choose one option per question, then optionally record confidence and a short explanation. '
                  'Return a saved filled PDF or an annotated paper copy through your agreed channel. No automatic submission or score.'),
             TextField('reviewer_id', 'Reviewer ID or preferred name', 19),
             TextField('expertise', 'Relevant field, role and experience', 28),
             TextField('conflicts', 'Conflicts or related involvement; enter None if none', 23),
             TextField('exposure', 'Have you seen this example/project before? No / Yes / Unsure; explain if needed', 23),
             TextField('credit', 'Credit preference: pseudonymous / attributed by agreement / discuss', 19),
             TextField('minutes', 'Actual review minutes and areas outside your expertise', 23), PageBreak(),
             para('Source cards', 'Heading1'), para(CITATION), para(SOURCE_NOTE), para(GLOSSARY, 'ReviewSmall')]
    for card in data['cards']:
        story.append(KeepTogether([para(card['id'], 'Heading3'), para(card['text'], 'ReviewSource')]))
    story += [para('Source attribution: Copyright 2009 Malemud; publisher and licensee Dove Medical Press Ltd. '
                   'The article permits noncommercial use with attribution. Selected source text is reproduced unchanged.', 'ReviewSmall'),
              PageBreak(), para('Part 1 Source only', 'Heading1'),
              para('Answer before reading the candidate. The questions concern only the supplied excerpt set, not the whole article.')]
    for q in SOURCE_QUESTIONS:
        story += [ChoiceQuestion(q), Spacer(1, 10)]
    story += [TextField('source_only_reference', 'Your source-only summary of important contexts and limits', 60),
              para('Stop here and save your Part 1 answers before continuing. Candidate A begins on the next page.'),
              PageBreak(), para('Part 2 Candidate assessment', 'Heading1'),
              para('Candidate A is one anonymous development response. Its prose, citations, limitations and scientific '
                   'structured fields appear below. No prior review verdict is supplied. Native JSON formatting is outside this exercise.')]
    for i, claim in enumerate(data['claims']):
        story += [para('A' + str(i+1), 'Heading2'), para(claim['text']),
                  para('Actual cited passage: ' + ('P1' if i == 0 else 'P2') + '. Applicability label: ' + claim['applicability'] + '.'),
                  para('Limitation: ' + claim['limitations'][0])]
        for key, value in claim['proposition'].items():
            text = 'Unspecified (null)' if value is None else str(value).lower() if isinstance(value, bool) else value
            story.append(para(key.replace('_', ' ') + ': ' + text, 'ReviewCompact'))
    story += [para('context_mismatch is the candidate label; judge whether the evidence establishes a mismatch. '
                   'Unspecified (null) means the field was unanswered.'), PageBreak(),
              para('Your scientific judgments', 'Heading1'),
              para('There is no predetermined answer key for these judgments. Explain ambiguity or concerns where useful. '
                   'Save and return the form through your agreed channel after completing this section.')]
    for q in RATING_QUESTIONS:
        story += [ChoiceQuestion(q), Spacer(1, 10)]
    story += [TextField('final_note', 'Important correction or uncertainty not captured above', 50),
              TextField('external_lookup', 'External information used after Part 1, if any: source, date and effect on your judgment', 35)]
    doc = SimpleDocTemplate(str(OUT / 'Expert-review.pdf'), pagesize=A4,
                            leftMargin=19*mm, rightMargin=19*mm,
                            topMargin=18*mm, bottomMargin=22*mm,
                            title=TITLE, author='AsOf project', subject=SUBTITLE)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = load_data()
    build_html(data)
    build_pdf(data)
    manifest = dict(packet_id=PACKET_ID, purpose='unanswered_development_orientation',
                    source_view_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    candidate_sha256=hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),
                    unique_source_passages=7, original_passage_occurrences=12,
                    source_questions=9, judgment_questions=9,
                    prefilled_answers=0, automatic_score=False, network_requests=False,
                    files={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [OUT/'Expert-review.html', OUT/'Expert-review.pdf', OUT/'Recruitment.md']})
    (Path(__file__).parent / 'expert-packet-provenance.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
