// DOM-free export checks; no browser, rendering, network, or reviewer answers.
const fs=require('fs'), vm=require('vm'), path=require('path');
const values=new Map(), selections=new Map();
const element=id=>{if(!values.has(id))values.set(id,{value:'',textContent:'',addEventListener(){}});return values.get(id);};
const document={getElementById:element,querySelector(selector){const name=/name="([^"]+)"/.exec(selector)[1];return selections.has(name)?{value:selections.get(name)}:null;},querySelectorAll(){return [];}};
const context={document,Date,Number,JSON,Error};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'embedded-script.js'),'utf8'),context);
const empty=context.buildExport();
if(empty.role!=='evaluation_only'||empty.responses.length!==10||!empty.responses.every(r=>r.selection===null&&r.confidence===null&&r.rationale===null))throw Error('Default responses are not blank');
if(empty.review_status!=='partial_source_review_unadjudicated'||empty.reviewer.prior_candidate_exposure!==null)throw Error('Defaults overstate review or independence');
selections.set('orientation','outside_expertise');
const partial=context.buildExport();
if(partial.responses[0].selection!=='outside_expertise'||partial.responses[0].selection_label!=='Outside my expertise')throw Error('Selection not retained');
element('elapsed').value='-1';let rejected=false;try{context.buildExport();}catch{rejected=true;}if(!rejected)throw Error('Negative time accepted');
element('elapsed').value='2.5';if(context.buildExport().elapsed_minutes_self_reported!==2.5)throw Error('Time not retained');
const report={status:'passed',mode:'DOM-free JavaScript checks, not browser visual QA',items:10,blank_defaults:true,role:'evaluation_only',unadjudicated_status:true,selection_roundtrip:true,negative_elapsed_rejected:true,network_calls:0};
fs.writeFileSync(path.join(__dirname,'export-check.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
