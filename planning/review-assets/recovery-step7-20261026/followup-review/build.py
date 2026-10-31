"""Separate coordinator-held follow-up; original answers, no repair or AI ratings."""
import base64
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
DEST=ROOT/'docs/expert-review-genetics-followup-20261026'
RUN=ROOT/'runs/r07-native-diagnostic-20261026T165505Z'
SOURCE=ROOT/'data/cache/r07-source-revalidation-20261026-v2/source-cards.json'
cards=json.loads(SOURCE.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def esc(value):return html.escape(str(value))
def literal(value):return json.dumps(value,ensure_ascii=False,indent=2)
assert sha((RUN/'terminal-seal.json').read_bytes())=='863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41'

# This deterministic assignment is a mask, not randomization. Keep its key internal.
assignments=[('A','exposed-il6r-genetics-simplified'),('B','exposed-il6r-genetics-current')]
candidates=[];key=[]
for label,cell in assignments:
    raw=(RUN/'cells'/cell/'raw-response.bin').read_bytes()
    native=json.loads(base64.b64decode(json.loads(raw)['body_base64']))
    text=native['content'];document=json.loads(text)
    request=json.loads((RUN/'cells'/cell/'request.json').read_bytes())
    assert sha(canonical(request))==cards['request_sha256']
    assert request['source_request']['evidence'][0]['scientific_record']==cards['cards'][0]['scientific_record']
    candidates.append(dict(label=label,document=document,original_text=text,content_sha256=sha(text.encode())))
    key.append(dict(candidate=label,cell_id=cell,wrapper_path=str(RUN/'cells'/cell/'raw-response.bin'),
                    wrapper_sha256=sha(raw),original_content_sha256=sha(text.encode())))

dimensions=[
 ('fidelity','How faithfully does this answer represent the supplied source material?'),
 ('attribution','How clearly does it distinguish the present study from cited prior findings?'),
 ('orientation','How clearly does it preserve the exposure → outcome direction and relevant biological context?'),
 ('quantitative','How adequately does it handle reported estimates, uncertainty, discovery/replication and unknown scales or units?'),
 ('applicability','How appropriately does it address relevance and limits for the proposed antibody intervention?'),
 ('traceability','How easy is it to trace the answer’s claims to the supplied excerpts using the references as provided?'),
 ('usefulness','How useful is the answer for a careful, source-bounded response to the reporting question?')]
options=[('adequate','Adequate for this reporting task'),('minor','Minor qualification or clarification needed'),
         ('major','Major qualification, omission or correction needed'),('not_useful','Not useful for this dimension'),
         ('cannot_assess','Cannot assess from the supplied material'),('outside_expertise','Outside my expertise')]
def radio(name,choices):
    return ''.join(f'<label class="choice"><input type="radio" name="{name}" value="{value}"><span>{esc(label)}</span></label>' for value,label in choices)

answer_blocks=[]
for candidate in candidates:
    label=candidate['label'];doc=candidate['document'];claims=[]
    for index,claim in enumerate(doc.get('claims',[])):
        details=''.join(f'<div class="field"><strong>{esc(name)}</strong><pre>{esc(literal(value))}</pre></div>' for name,value in claim.items() if name not in {'text','limitations'})
        limits=claim.get('limitations')
        if isinstance(limits,list):
            limits_html='<ul>'+''.join(f'<li>{esc(value)}</li>' for value in limits)+'</ul>' if limits else '<p class="literal">[]</p>'
        else:limits_html='<p>No limitations field is present in the original answer.</p>'
        claims.append(f'<article><h3>Statement {index+1}</h3><blockquote class="candidate-text">{esc(claim.get("text",""))}</blockquote><h4>Limitations as provided</h4>{limits_html}<details><summary>Other statement fields and exact citation values</summary>{details}</details></article>')
    top_fields=''.join(f'<div class="field"><strong>{esc(name)}</strong><pre>{esc(literal(value))}</pre></div>' for name,value in doc.items() if name!='claims')
    ratings=[]
    for identifier,question in dimensions:
        name=f'{label}-{identifier}'
        ratings.append(f'''<fieldset><legend>{esc(question)}</legend>{radio(name,options)}<div class="grid"><label>Confidence (optional)<select id="{name}-confidence"><option value="">Choose if useful</option><option>Low</option><option>Moderate</option><option>High</option><option>Cannot assess</option></select></label><label>Passage IDs / answer wording (optional)<input id="{name}-evidence" placeholder="For example: P03; quote the relevant wording"></label></div><label>Rationale or qualifications (optional)<textarea id="{name}-rationale" rows="2"></textarea></label></fieldset>''')
    answer_blocks.append(f'''<section id="candidate-{label}"><h2>Candidate {label}</h2><p class="small">The answer text and field values below are displayed as supplied. No missing fields or references have been completed. Headings are navigation aids, not ratings.</p>{''.join(claims)}<details><summary>Answer-level fields as supplied</summary>{top_fields}</details><details><summary>Original answer JSON, verbatim</summary><pre class="original-json">{esc(candidate['original_text'])}</pre></details></section><section><h2>Your assessment of Candidate {label}</h2>{''.join(ratings)}</section>''')

passages=''.join(f'<article id="P{i+1:02}"><h3>P{i+1:02} · {esc(p["section"])}</h3><blockquote class="source-text">{esc(p["text"])}</blockquote><p class="small pointer">E0 /source_metrics/textMiningSentences/{i}/text</p></article>' for i,p in enumerate(cards['cards'][0]['reported_passages']))
meta=dict(schema_version=1,form_id='genetics-candidate-followup-20261026-v1',role='evaluation_only',
          request_sha256=cards['request_sha256'],source_cards_sha256=sha(SOURCE.read_bytes()),
          candidate_content_sha256={c['label']:c['content_sha256'] for c in candidates},
          question=cards['question'],case_id=cards['case']['case_id'])
script='''const META=__META__, DIMENSIONS=__DIMENSIONS__, CHOICES=__CHOICES__;
function value(id){return document.getElementById(id).value.trim();}
function selected(name){const element=document.querySelector('input[name="'+name+'"]:checked');return element?element.value:null;}
function buildExport(){
 const minutesText=value('elapsed'),minutes=minutesText===''?null:Number(minutesText);
 if(minutes!==null&&(!Number.isFinite(minutes)||minutes<0))throw new Error('Elapsed minutes must be blank or nonnegative.');
 const reviews=['A','B'].map(candidate=>({candidate,dimensions:DIMENSIONS.map(([id,question])=>{const name=candidate+'-'+id,choice=selected(name);return {dimension:id,question,selection:choice,selection_label:choice?CHOICES.find(row=>row[0]===choice)[1]:null,confidence:value(name+'-confidence')||null,evidence:value(name+'-evidence')||null,rationale:value(name+'-rationale')||null};})}));
 const completed=reviews.every(review=>review.dimensions.every(item=>item.selection!==null));
 return {...META,exported_at_utc:new Date().toISOString(),reviewer_type:'human_self_reported',
 status:completed?'candidate_followup_submitted_unadjudicated':'partial_candidate_followup_unadjudicated',scientific_validation:'not_established_by_form',
 reviewer_id:value('reviewer-id')||null,source_ref_id:value('source-ref-id')||null,
 source_reference_submitted:selected('reference-submitted'),prior_candidate_exposure:selected('prior-exposure'),
 expertise:value('expertise')||null,conflicts_of_interest:value('coi')||null,
 elapsed_minutes_self_reported:minutes,candidates:reviews,
 paired_preference:selected('preference'),paired_preference_rationale:value('preference-rationale')||null,
 overall_comments:value('comments')||null};
}
document.getElementById('save').addEventListener('click',()=>{try{const output=buildExport();const blob=new Blob([JSON.stringify(output,null,2)+'\\n'],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='genetics-followup-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('save-status').textContent='Responses downloaded. Return through your agreed channel; this page sends nothing.';}catch(error){document.getElementById('save-status').textContent=error.message;}});
'''.replace('__META__',json.dumps(meta,ensure_ascii=False).replace('</','<\\/')).replace('__DIMENSIONS__',json.dumps(dimensions)).replace('__CHOICES__',json.dumps(options))
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none';script-src 'unsafe-inline';style-src 'unsafe-inline';connect-src 'none';base-uri 'none';form-action 'none'"><title>Coordinator-held genetics follow-up</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6f8;color:#193044;font:16px/1.55 system-ui,Segoe UI,sans-serif}header,main,footer{max-width:1180px;margin:auto;padding:22px}h1{font-size:2rem}h2{font-size:1.4rem}h3{font-size:1.1rem}h4{font-size:1rem;margin-bottom:6px}.gate{padding:18px;background:#fff2d5;border-left:5px solid #a96d15}.layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:22px}.layout>div{min-width:0}section,fieldset,article{background:white;border:1px solid #c8d3df;border-radius:7px;margin:0 0 16px;padding:16px;min-width:0}article{border-left:4px solid #7197aa}legend{font-weight:650;padding:0 5px}.choice{display:flex;gap:10px;align-items:flex-start;padding:6px 0}input[type=radio]{margin-top:6px;flex-shrink:0}label{display:block}input:not([type=radio]),textarea,select{width:100%;font:inherit;padding:9px;border:1px solid #9aabb9;border-radius:4px;margin:5px 0 10px}textarea{resize:vertical}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}blockquote{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}pre{font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%}.small{font-size:.9rem;color:#4c6172}.pointer,code{overflow-wrap:anywhere}summary{cursor:pointer;font-weight:650;padding:8px 0}.field{padding:8px;border-bottom:1px solid #dce3e9}button{font:inherit;font-weight:650;padding:12px 20px;background:#175575;color:white;border:0;border-radius:5px;cursor:pointer}:focus-visible{outline:3px solid #a36b0f;outline-offset:3px}a{color:#175575}@media(max-width:850px){.layout,.grid{grid-template-columns:1fr}header,main,footer{padding:14px}}@media print{body{background:white}.layout{display:block}button{display:none}}
</style></head><body><header><h1>Genetics reporting follow-up</h1><div class="gate"><strong>COORDINATOR: WITHHOLD THIS FILE until the reviewer’s independent source-only reference has been submitted and retained.</strong><p>Reviewers: if that step is not complete, stop before reading the candidates and contact your coordinator. Do not revise your original reference after viewing these answers; record later qualifications separately.</p><p class="small">This is a procedural gate, not a security barrier. All candidate content is already inside this static file. The coordinator protects independence by keeping source-only and candidate files separate and releasing them in sequence.</p></div><p>Assess two anonymous answers using only the supplied source material. The labels do not imply quality or order of merit. No score or preferred answer is supplied.</p><nav><a href="#source">Sources</a> · <a href="#candidate-A">Candidate A</a> · <a href="#candidate-B">Candidate B</a> · <a href="#compare">Compare</a></nav></header><main>
<section><h2>Reference and reviewer details</h2><div class="grid"><label>Reviewer ID (optional)<input id="reviewer-id"></label><label>Submitted source-reference ID (optional)<input id="source-ref-id"></label></div><fieldset><legend>Has your independent source-only reference been submitted?</legend>__REFERENCE_GATE__</fieldset><fieldset><legend>Before this follow-up, had you seen either candidate answer?</legend>__EXPOSURE__</fieldset><label>Relevant expertise (optional)<input id="expertise"></label><label>Conflicts of interest or exposure details (optional)<textarea id="coi" rows="2"></textarea></label></section>
<section><h2>The reporting question</h2><p>__QUESTION__</p><p><strong>Case:</strong> IL6R inhibition by antibody for rheumatoid arthritis; tissue unspecified. This is a development hypothesis, not a conclusion.</p><p class="small">Judge source fidelity and reporting usefulness. This exercise does not recompute MR, establish causality, or determine clinical efficacy.</p></section>
<div class="layout"><div id="source"><section><h2>Supplied source material</h2><p>One offered Open Targets 25.09 / Europe PMC record; PMID 34539640, PMC8447937; supplied publication date 2021-09-03. The full article was not retrieved for this form.</p><p>__STATEMENT__</p><p class="small">All 13 passages are preserved, including repetitions. Repeated extracts are not independent studies. Null record fields indicate missing supplied context, not proof of absent biology.</p></section>__PASSAGES__<section><details><summary>Complete source-only record and provenance</summary><pre>__SOURCE_JSON__</pre></details></section></div><div>__CANDIDATES__</div></div>
<section id="compare"><h2>Paired judgment</h2><fieldset><legend>Which answer is more useful for this source-bounded reporting task?</legend>__PREFERENCE__</fieldset><label>Reason, key evidence or qualifications (optional)<textarea id="preference-rationale" rows="3"></textarea></label><label>Other comments (optional)<textarea id="comments" rows="3"></textarea></label><label>Elapsed review time, minutes (optional, self-reported)<input type="number" id="elapsed" min="0" step="0.1"></label></section>
<section><h2>Save your assessment</h2><p>No choice is preselected. Unanswered items remain blank. This offline page does not send, automatically save or retain your responses; download before closing.</p><button type="button" id="save">Save follow-up responses (JSON)</button><p id="save-status" role="status" aria-live="polite"></p><p class="small">Exports are evaluation_only and unadjudicated. Forms are preparation materials—not completed human responses or scientific validation.</p></section></main><footer class="small">Form __FORM_ID__ · Source request <code>__REQUEST_HASH__</code></footer><script>__SCRIPT__</script></body></html>'''
replace={'__REFERENCE_GATE__':radio('reference-submitted',[('yes','Yes — submitted before candidate exposure'),('no','No — stop here and contact the coordinator'),('uncertain','Uncertain — contact the coordinator')]),
 '__EXPOSURE__':radio('prior-exposure',[('not_seen','No'),('possibly_seen','Possibly / unsure'),('seen','Yes — disclose context if useful')]),
 '__PREFERENCE__':radio('preference',[('A','Candidate A'),('B','Candidate B'),('tie','Equally useful'),('neither','Neither is useful enough for this task'),('uncertain','Cannot determine from the supplied material'),('outside_expertise','Outside my expertise')]),
 '__QUESTION__':esc(cards['question']['text']),'__STATEMENT__':esc(cards['cards'][0]['statement']),
 '__PASSAGES__':passages,'__SOURCE_JSON__':esc(literal(cards)),'__CANDIDATES__':''.join(answer_blocks),
 '__FORM_ID__':meta['form_id'],'__REQUEST_HASH__':meta['request_sha256'],'__SCRIPT__':script}
for marker,value in replace.items():page=page.replace(marker,value)
(DEST/'Candidate-followup.html').write_text(page,encoding='utf-8')
(HERE/'embedded-script.js').write_text(script,encoding='utf-8')
(HERE/'mask-key-INTERNAL.json').write_text(json.dumps(dict(role='evaluation_only_internal_mask_key',assignment='deterministic_not_randomized',candidates=key),indent=2)+'\n',encoding='utf-8')
(HERE/'provenance.json').write_text(json.dumps(dict(schema_version=1,role='evaluation_only_preparation',
 source_cards_sha256=sha(SOURCE.read_bytes()),request_sha256=cards['request_sha256'],run_seal_sha256=sha((RUN/'terminal-seal.json').read_bytes()),
 mask_key_sha256=sha((HERE/'mask-key-INTERNAL.json').read_bytes()),candidate_count=2,source_passages=13,dimensions_per_candidate=7,
 candidate_content_sha256=meta['candidate_content_sha256'],html_sha256=sha((DEST/'Candidate-followup.html').read_bytes()),
 original_answers_repaired=False,source_only_packet_modified=False,model_calls=0,external_retrievals=0,
 human_responses_collected=False,scientific_validation='not_established',visual_browser_qa='not_performed'),indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidates':2,'passages':13,'dimensions_per_candidate':7,'html_sha256':sha((DEST/'Candidate-followup.html').read_bytes())}))
