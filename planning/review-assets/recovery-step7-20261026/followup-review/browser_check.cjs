const { chromium } = require('C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../../..');
const out = path.join(root, 'data/cache/r07-followup-form-browser-20261026');
fs.mkdirSync(out, {recursive:true});
const source = path.join(root, 'docs/expert-review-genetics-followup-20261026/Candidate-followup.html');
const report = {status:'running', coordinator_held:true, fixture_is_human_submission:false, views:[], external_requests:[], page_errors:[]};
(async()=>{
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--disable-background-networking']});
  try {
    for (const [name, viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
      const context = await browser.newContext({viewport,acceptDownloads:true});
      try {
        await context.route(/^https?:/,route=>{report.external_requests.push(route.request().url());return route.abort();});
        const page=await context.newPage();
        page.on('pageerror',e=>report.page_errors.push(String(e)));
        await page.goto(pathToFileURL(source).href,{waitUntil:'load'});
        assert.equal(await page.locator('blockquote.source-text').count(),13);
        assert.equal(await page.locator('.original-json').count(),2);
        assert.equal(await page.locator('input:checked').count(),0);
        const initial=await page.evaluate(()=>buildExport());
        assert.equal(initial.role,'evaluation_only');
        assert.equal(initial.status,'partial_candidate_followup_unadjudicated');
        assert(initial.candidates.every(c=>c.dimensions.length===7 && c.dimensions.every(r=>r.selection===null)));
        assert.equal(initial.paired_preference,null);
        assert.equal(initial.source_ref_id,null);
        assert.equal(initial.source_reference_submitted,null);
        assert(!Object.hasOwn(initial,'score'));
        const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
        await page.screenshot({path:path.join(out,name+'-top.png')});
        assert(dimensions.scroll<=viewport.width && dimensions.body<=viewport.width,'Horizontal overflow '+JSON.stringify(dimensions));
        await page.locator('#reviewer-id').fill('QA fixture only — not a human submission');
        await page.locator('#source-ref-id').fill('QA-NOT-AN-ACTUAL-REFERENCE');
        await page.locator('input[name="reference-submitted"][value="yes"]').check();
        await page.locator('input[name="A-fidelity"][value="cannot_assess"]').check();
        await page.locator('input[name="B-fidelity"][value="outside_expertise"]').check();
        await page.locator('input[name="preference"][value="neither"]').check();
        await page.locator('#elapsed').fill('4.5');
        const selected=await page.evaluate(()=>buildExport());
        assert.equal(selected.candidates[0].dimensions[0].selection,'cannot_assess');
        assert.equal(selected.candidates[1].dimensions[0].selection,'outside_expertise');
        assert.equal(selected.elapsed_minutes_self_reported,4.5);
        assert.equal(selected.paired_preference,'neither');
        assert.equal(selected.status,'partial_candidate_followup_unadjudicated');
        const downloadPromise=page.waitForEvent('download');
        await page.locator('#save').click();
        const download=await downloadPromise;
        const filename=path.join(out,name+'-export-fixture.json');
        await download.saveAs(filename);
        const exported=JSON.parse(fs.readFileSync(filename,'utf8'));
        assert.equal(exported.reviewer_id,'QA fixture only — not a human submission');
        assert.equal(exported.role,'evaluation_only');
        assert.equal(exported.candidates.flatMap(c=>c.dimensions).filter(r=>r.selection!==null).length,2);
        assert.equal(exported.source_ref_id,'QA-NOT-AN-ACTUAL-REFERENCE');
        await page.screenshot({path:path.join(out,name+'-save.png')});
        await page.locator('#candidate-A').scrollIntoViewIfNeeded();
        await page.screenshot({path:path.join(out,name+'-candidate.png')});
        report.views.push({name,viewport,dimensions,source_cards:13,candidates:2,dimensions_per_candidate:7,blank_default:true,unknown_and_expertise_preserved:true,download_roundtrip:true});
      } finally {await context.close();}
    }
    assert.deepEqual(report.external_requests,[]);
    assert.deepEqual(report.page_errors,[]);
    report.status='passed';
  } catch(error) {report.status='failed';report.error=String(error);process.exitCode=1;}
  finally {await browser.close();fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
})();
