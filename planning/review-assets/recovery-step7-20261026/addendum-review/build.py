"""Build one source-only offline form from the approved cards/request, never outputs."""
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
DEST=ROOT/'docs/expert-review-genetics-20261026'
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'data/cache/r07-source-revalidation-20261026-v2/source-cards.json'
REQUEST=SOURCE.parent/'prepared-request.json'
cards=json.loads(SOURCE.read_bytes()); request=json.loads(REQUEST.read_bytes())
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
assert digest(canonical(request))==cards['request_sha256']
assert request['question']==cards['question'] and request['source_request']['case']==cards['case']
assert len(cards['cards'])==len(request['source_request']['evidence'])
for card,row in zip(cards['cards'],request['source_request']['evidence']):
    assert card['scientific_record']==row['scientific_record']
    assert card['reported_passages']==row['scientific_record']['source_metrics']['textMiningSentences']

questions=[
('orientation','How clearly can you identify the reported exposure → outcome orientation?',[
 'sIL6R / IL6-signaling exposure → arthritis outcome(s)',
 'Arthritis exposure → sIL6R / IL6-signaling outcome(s)',
 'Both orientations are explicitly assessed in the supplied material',
 'The excerpts do not establish a single interpretable orientation',
 'Other or mixed interpretation — explain if useful']),
('attribution','Can the current-study findings be separated from cited prior findings?',[
 'Yes, the supplied attribution supports separating them',
 'Partly; some statements can be assigned but others remain unclear',
 'No; I would need further source context to assign them reliably',
 'I identify only one attribution category in these excerpts',
 'Other or mixed interpretation — explain if useful']),
('design','How adequately is the study-design description supported by the supplied material?',[
 'Enough to describe the reported design, but not to evaluate its assumptions fully',
 'Enough to describe and evaluate the relevant design assumptions',
 'Only limited design labels are available; fuller context is needed',
 'The design descriptions appear internally inconsistent',
 'Other assessment — explain if useful']),
('instruments','What level of instrument/proxy reporting can you support from these excerpts?',[
 'Variant/proxy details can be reported, with qualification about missing selection or validation detail',
 'A complete instrument set and its validation can be reconstructed from the supplied material',
 'Only a general reference to genetic instruments/proxies can be supported',
 'Instrument/proxy information is absent or not interpretable here',
 'Other or mixed assessment — explain if useful']),
('estimates','How usable are the reported RA estimates and uncertainty for a source-bounded summary?',[
 'At least one RA numerical estimate and uncertainty can be attributed to a reported analysis',
 'Numerical estimates are shown, but attribution or interpretation needs clarification',
 'Only a qualitative RA finding can be safely described',
 'The supplied material does not support an RA estimate summary',
 'Other or mixed assessment — explain if useful']),
('scale','How well are the effect scale and exposure units established by the supplied material?',[
 'Both the effect scale and exposure units can be specified',
 'Only part of the scale/unit information can be specified',
 'I would leave scale/unit details unspecified without additional source context',
 'The scale/unit information appears inconsistent',
 'Other assessment — explain if useful']),
('replication','How should discovery and replication be represented together?',[
 'The supplied quantitative information allows a direct comparison of both analyses',
 'A replication statement can be reported, but quantitative or contextual comparison is limited',
 'Only the initial finding can be described from the supplied material',
 'The passages do not allow reliable separation of initial and replication findings',
 'Other or mixed interpretation — explain if useful']),
('context','How complete is the context for interpreting the reported genetic findings?',[
 'Enough relevant context is supplied for a bounded summary with explicit caveats',
 'Some context is supplied, but key population, sex-stratum, ancestry or study details remain unresolved',
 'Context is too limited to summarize the findings responsibly',
 'The supplied context appears inconsistent across passages or fields',
 'Other assessment — explain if useful']),
('transfer','What can this source packet support about the case hypothesis: IL6R inhibition by antibody, tissue unspecified?',[
 'A direct estimate for that specific intervention/modality/context',
 'An indirect relevance assessment, with explicit limits on transfer from genetic evidence',
 'Only a report of source findings; intervention applicability cannot be assessed here',
 'I see a context or direction mismatch that should be explained',
 'Other or mixed assessment — explain if useful']),
('sufficiency','What is your overall judgment of this packet for the stated reporting question?',[
 'Sufficient for a bounded source summary with clearly stated limits',
 'Useful, but additional passages are needed before a coherent summary',
 'Suitable only to identify a source for further review',
 'The reporting question needs narrowing or clarification',
 'Other judgment — explain if useful'])]
common=['Cannot assess from the supplied material','Outside my expertise']
items=[dict(id=key,question=question,options=[dict(value=f'option_{i+1}',label=label) for i,label in enumerate(options)]+
           [dict(value='cannot_assess',label=common[0]),dict(value='outside_expertise',label=common[1])]) for key,question,options in questions]
metadata=dict(schema_version=1,form_id='genetics-source-review-20261026-v1',role='evaluation_only',
    source_cards_sha256=digest(SOURCE.read_bytes()),request_file_sha256=digest(REQUEST.read_bytes()),
    request_sha256=cards['request_sha256'],question_key=request['question_key'],hypothesis_key=request['hypothesis_key'],
    case_id=cards['case']['case_id'],question=cards['question'],
    source_ids=[dict(alias=c['source_alias'],observation_id=c['observation_id'],admitted_sha256=c['admitted_sha256']) for c in cards['cards']])
escape=html.escape
passages=[]
for card in cards['cards']:
    for i,passage in enumerate(card['reported_passages']):
        passages.append(f'<article class="passage" id="P{i+1:02}"><h3>P{i+1:02} · {escape(passage["section"])}</h3><blockquote>{escape(passage["text"])}</blockquote><p class="pointer">E0 /source_metrics/textMiningSentences/{i}/text</p></article>')
sections=[]
for index,item in enumerate(items):
    options=''.join(f'<label class="choice"><input type="radio" name="{item["id"]}" value="{o["value"]}"><span>{escape(o["label"])}</span></label>' for o in item['options'])
    sections.append(f'''<fieldset><legend>{index+1}. {escape(item['question'])}</legend>{options}
    <div class="details-grid"><label>Confidence (optional)<select id="{item['id']}-confidence"><option value="">Choose if useful</option><option>Low</option><option>Moderate</option><option>High</option><option>Cannot assess</option></select></label>
    <label>Passage IDs (optional)<input id="{item['id']}-passages" placeholder="For example: P06, P09"></label></div>
    <label>Rationale, qualifications or alternative interpretation (optional)<textarea id="{item['id']}-rationale" rows="3"></textarea></label></fieldset>''')
script='''const META=__META__;
const ITEMS=__ITEMS__;
function field(id){return document.getElementById(id).value.trim();}
function selected(name){const input=document.querySelector('input[name="'+name+'"]:checked');return input?input.value:null;}
function buildExport(){
 const responses=ITEMS.map(item=>{const value=selected(item.id);return {item_id:item.id,question:item.question,
 selection:value,selection_label:value?item.options.find(o=>o.value===value).label:null,
 confidence:field(item.id+'-confidence')||null,passage_ids_free_text:field(item.id+'-passages')||null,
 rationale:field(item.id+'-rationale')||null};});
 const rawMinutes=field('elapsed');const minutes=rawMinutes===''?null:Number(rawMinutes);
 if(minutes!==null&&(!Number.isFinite(minutes)||minutes<0)){throw new Error('Elapsed minutes must be blank or a nonnegative number.');}
 return {...META,exported_at_utc:new Date().toISOString(),reviewer_type:'human_self_reported',
 review_status:responses.every(r=>r.selection!==null)?'source_review_submitted_unadjudicated':'partial_source_review_unadjudicated',
 scientific_validation:'not_established_by_form',reference_type:'source_only_unadjudicated',
 reviewer:{reviewer_id:field('reviewer-id')||null,expertise:field('expertise')||null,
 conflicts_of_interest:field('coi')||null,prior_candidate_exposure:selected('exposure'),
 reference_workflow:selected('independence'),outside_material_used:field('outside-material')||null},
 elapsed_minutes_self_reported:minutes,responses,additional_source_needs:field('source-needs')||null,
 overall_comments:field('overall-comments')||null};
}
function updateProgress(){const count=ITEMS.filter(item=>selected(item.id)!==null).length;document.getElementById('progress').textContent=count+' of '+ITEMS.length+' items answered. Unanswered items remain blank in export.';}
document.getElementById('save').addEventListener('click',()=>{try{const output=buildExport();const blob=new Blob([JSON.stringify(output,null,2)+'\\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='genetics-source-review-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('save-status').textContent='Download created. Keep this file and return it to the coordinator using your agreed channel.';}catch(error){document.getElementById('save-status').textContent=error.message;}});
document.querySelectorAll('input[type="radio"]').forEach(input=>input.addEventListener('change',updateProgress));
updateProgress();
'''.replace('__META__',json.dumps(metadata,ensure_ascii=False).replace('</','<\\/')).replace('__ITEMS__',json.dumps(items,ensure_ascii=False).replace('</','<\\/'))
context=json.dumps(cards['cards'][0]['scientific_context'],indent=2,ensure_ascii=False)
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; base-uri 'none'; form-action 'none'">
<title>Source-only genetics review · IL6R</title><style>
:root{font-family:system-ui,Segoe UI,sans-serif;color:#182d40;background:#f3f6f8;line-height:1.55}body{margin:0}header,main,footer{max-width:1320px;margin:auto;padding:24px}header{padding-bottom:8px}h1{font-size:2rem;margin:10px 0}h2{font-size:1.35rem}h3{font-size:1rem;margin:0 0 8px}.badge{display:inline-block;background:#dcebe7;padding:4px 10px;border-radius:5px;font-weight:650}.notice{background:#fff4d8;border-left:4px solid #aa7215;padding:14px 18px}.layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:24px}section,fieldset,.passage{background:white;border:1px solid #cbd5df;border-radius:8px;padding:18px;margin:0 0 16px}fieldset{min-width:0}legend{font-size:1.05rem;font-weight:700;padding:0 6px}blockquote{margin:0;white-space:pre-wrap}.pointer{font:12px ui-monospace,monospace;color:#52677a;overflow-wrap:anywhere}.choice{display:flex;align-items:flex-start;gap:10px;margin:8px 0;padding:7px;border-radius:5px}.choice:hover{background:#f0f5f8}input[type=radio]{margin-top:6px;flex-shrink:0}label{display:block}textarea,input:not([type=radio]),select{box-sizing:border-box;width:100%;padding:10px;border:1px solid #9dabb8;border-radius:4px;font:inherit;margin:5px 0 12px}textarea{resize:vertical}.details-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}pre{font:12px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer;font-weight:600}button{font:inherit;font-weight:650;border:0;border-radius:5px;background:#174f6b;color:white;padding:12px 22px;cursor:pointer}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #b47c18;outline-offset:3px}.small{font-size:.9rem;color:#44596a}.save{border-top:2px solid #174f6b}a{color:#174f6b}@media(max-width:850px){.layout,.details-grid{grid-template-columns:1fr}header,main,footer{padding:16px}}@media print{body{background:white}.layout{display:block}button,.save{display:none}section,fieldset,.passage{break-inside:avoid}details{display:block}}
</style></head><body><header><span class="badge">Independent source-only reference</span><h1>Genetics reporting review · IL6R</h1>
<p>Read the supplied excerpts, then record your own assessment. This is a reporting review—not an examination, an MR computation, or independent validation of causality.</p>
<p class="notice">Complete this source-only reference before viewing any candidate response. No candidate output, AI verdict, answer key or preselected answer is included. This AI-prepared form has not itself received scientific review.</p>
<p><a href="#sources">Read the source</a> · <a href="#review">Complete 10 items</a> · <a href="#save-section">Save locally</a></p></header><main>
<section><h2>Your review and independence</h2><div class="details-grid"><label>Reviewer ID (optional; use an assigned ID rather than personal contact details)<input id="reviewer-id"></label><label>Relevant expertise (optional)<input id="expertise" placeholder="For example: statistical genetics / MR methods"></label></div>
<label>Conflicts of interest (optional; describe any relevant relationship, or write none)<textarea id="coi" rows="2"></textarea></label>
<fieldset><legend>Have you previously seen a candidate answer to this genetics task?</legend><label class="choice"><input type="radio" name="exposure" value="not_seen"><span>No</span></label><label class="choice"><input type="radio" name="exposure" value="possibly_seen"><span>Possibly / unsure</span></label><label class="choice"><input type="radio" name="exposure" value="seen"><span>Yes — disclose context below if useful</span></label></fieldset>
<fieldset><legend>How was this reference prepared?</legend><label class="choice"><input type="radio" name="independence" value="independent_before_candidates"><span>Independently, before candidate exposure and discussion with other reviewers</span></label><label class="choice"><input type="radio" name="independence" value="not_independent"><span>With prior candidate exposure or discussion</span></label><label class="choice"><input type="radio" name="independence" value="uncertain"><span>Uncertain / other arrangement</span></label></fieldset>
<label>Any outside material, assistance or previous familiarity used? (optional; first-pass instructions ask you to use only this packet)<textarea id="outside-material" rows="2"></textarea></label></section>
<div class="layout"><div id="sources"><section><h2>The reporting question</h2><p>__QUESTION__</p><p><strong>Case hypothesis:</strong> IL6R inhibition by antibody for rheumatoid arthritis; tissue unspecified. This hypothesis is a question, not an established conclusion. Case origin: __ORIGIN__.</p><p><strong>Source scope:</strong> one offered Open Targets 25.09 / Europe PMC record. Literature identifiers: PMID 34539640; PMC8447937. Supplied publication date: 2021-09-03. Only the excerpts below and the retained record are available in this packet; the full article was not fetched.</p><p class="small">Quoted wording, uncertainty, author attributions and repeated passages are retained unchanged. Repeated extracts from one record are not separate studies. Source statements are not independently adjudicated facts.</p></section>
<section><h2>Record annotation</h2><p>__STATEMENT__</p><p class="small">The provider evidence score is descriptive. It is not an intervention effect size or a clinical probability.</p></section>
__PASSAGES__
<section><h2>Supplied structured context</h2><pre>__CONTEXT__</pre><p class="small">Null or empty values describe gaps in this supplied record. They do not establish that the original study lacks those details or that biological effects are absent.</p><details><summary>Complete source-only record and provenance</summary><pre>__FULL_SOURCE__</pre></details></section></div>
<div id="review"><section><h2>Your assessment</h2><p>Select the closest description for each item. Use the rationale field for qualifications or a different interpretation. “Cannot assess” and “Outside my expertise” are valid responses. No score is calculated.</p><p id="progress" aria-live="polite"></p></section>__ITEMS_HTML__</div></div>
<section><h2>Anything needed next?</h2><label>Additional source text or information needed (optional)<textarea id="source-needs" rows="3"></textarea></label><label>Overall comments or qualifications (optional)<textarea id="overall-comments" rows="3"></textarea></label><label>Elapsed review time in minutes (optional, self-reported)<input type="number" id="elapsed" min="0" step="0.1"></label></section>
<section class="save" id="save-section"><h2>Save your responses</h2><p>This page works offline. It makes no network requests and does not automatically save, transmit or store your answers. Save a JSON file before closing; unanswered items remain blank.</p><button id="save" type="button">Save responses (JSON)</button><p id="save-status" role="status" aria-live="polite"></p><p class="small">The export is labeled evaluation_only and unadjudicated. Keep it separate from agent-visible evidence. Return it using the channel agreed with your coordinator; this page sends nothing.</p></section>
</main><footer class="small">Form __FORM_ID__ · Source request fingerprint <code>__FINGERPRINT__</code><p>Technical source binding is separate from scientific validation. No biological conclusion or reviewer independence is established merely by opening or exporting this form.</p></footer><script>__SCRIPT__</script></body></html>'''
replacements={'__QUESTION__':escape(cards['question']['text']),'__ORIGIN__':escape(cards['case']['origin']),
 '__STATEMENT__':escape(cards['cards'][0]['statement']),'__PASSAGES__':'\n'.join(passages),'__CONTEXT__':escape(context),
 '__FULL_SOURCE__':escape(json.dumps(cards,ensure_ascii=False,indent=2)),'__ITEMS_HTML__':'\n'.join(sections),
 '__FORM_ID__':metadata['form_id'],'__FINGERPRINT__':metadata['request_sha256'],'__SCRIPT__':script}
for marker,value in replacements.items():page=page.replace(marker,value)
assert '__SCRIPT__' not in page
(DEST/'Expert-source-review.html').write_text(page,encoding='utf-8')
(HERE/'form-metadata.json').write_text(json.dumps(dict(metadata=metadata,items=items),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(HERE/'embedded-script.js').write_text(script,encoding='utf-8')
(HERE/'provenance.json').write_text(json.dumps(dict(schema_version=1,role='evaluation_only_preparation',
 inputs=[dict(path=str(p),sha256=digest(p.read_bytes()),bytes=p.stat().st_size) for p in (SOURCE,REQUEST)],
 source_cards_match_bound_request=True,source_count=len(cards['cards']),verbatim_passage_count=len(passages),item_count=len(items),
 output=dict(path=str(DEST/'Expert-source-review.html'),sha256=digest(page.encode()),bytes=len(page.encode())),
 candidate_outputs_read=0,answer_keys_read=0,external_sources_used=0,model_calls=0,
 scientific_review='not_performed',visual_browser_qa='not_performed'),indent=2)+'\n',encoding='utf-8')
print(json.dumps({'sources':len(cards['cards']),'passages':len(passages),'items':len(items),'html_bytes':len(page.encode())}))
