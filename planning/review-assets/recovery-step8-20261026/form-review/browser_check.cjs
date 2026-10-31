const { chromium } = require('C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../../..');
const out = path.join(root, 'data/cache/r08-source-form-browser-20261026');
fs.mkdirSync(out, {recursive:true});
const source = path.join(root, 'docs/expert-review-source-feasibility-20261026/Expert-source-review.html');
const expected = JSON.parse(fs.readFileSync(path.join(__dirname,'expected-text.json'),'utf8'));
const report = {status:'running', source_only:true, fixture_is_human_submission:false, views:[], external_requests:[], page_errors:[]};
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
        assert.equal(await page.locator('blockquote').count(),8);
        assert.deepEqual(await page.locator('blockquote').allTextContents(),expected);
        assert.equal(await page.locator('input:checked').count(),0);
        assert.equal(await page.locator('#review fieldset').count(),14);
        const initial=await page.evaluate(()=>buildExport());
        assert.equal(initial.role,'evaluation_only');
        assert.equal(initial.status,'unadjudicated');
        assert.equal(initial.review_type,'source_only');
        assert(Object.values(initial.answers).every(value=>value===null));
        assert(!Object.hasOwn(initial.answers,'viewport'));
        const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
        await page.screenshot({path:path.join(out,name+'-top.png')});
        assert(dimensions.scroll<=viewport.width && dimensions.body<=viewport.width,'Horizontal overflow '+JSON.stringify(dimensions));
        await page.locator('input[name="reviewer_id"]').fill('QA fixture only — not a human submission');
        const unknown=page.locator('input[name="BTK_direct_reporting"][value="Cannot assess from the supplied material"]');
        if(await unknown.count()) await unknown.check();
        else {const labels=await page.locator('input[name="BTK_direct_reporting"]').evaluateAll(inputs=>inputs.map(i=>({value:i.value,label:i.parentElement.textContent})));throw Error('Missing cannot_assess option '+JSON.stringify(labels));}
        await page.locator('input[name="elapsed_minutes"]').fill('4.5');
        const selected=await page.evaluate(()=>buildExport());
        assert.equal(selected.answers.BTK_direct_reporting,'Cannot assess from the supplied material');
        assert.equal(selected.answers.elapsed_minutes,'4.5');
        const downloadPromise=page.waitForEvent('download');
        await page.locator('#download').click();
        const download=await downloadPromise;
        const filename=path.join(out,name+'-export-fixture.json');
        await download.saveAs(filename);
        const exported=JSON.parse(fs.readFileSync(filename,'utf8'));
        assert.equal(exported.answers.reviewer_id,'QA fixture only — not a human submission');
        assert.equal(exported.role,'evaluation_only');
        assert.equal(exported.answers.BTK_direct_reporting,'Cannot assess from the supplied material');
        assert.equal(exported.answers.CTLA4_direct_reporting,null);
        await page.screenshot({path:path.join(out,name+'-save.png')});
        await page.locator('#context-0').scrollIntoViewIfNeeded();
        await page.screenshot({path:path.join(out,name+'-sources.png')});
        await page.locator('details').first().evaluate(element=>{element.open=true;});
        await page.locator('details').first().scrollIntoViewIfNeeded();
        const expanded=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
        assert(expanded.scroll<=viewport.width && expanded.body<=viewport.width,'Expanded source locator overflows '+JSON.stringify(expanded));
        await page.screenshot({path:path.join(out,name+'-locator.png')});
        report.views.push({name,viewport,dimensions,source_occurrences:8,unique_source_texts:7,question_groups:14,blank_defaults:true,source_text_escaped_exactly:true,unknown_preserved:true,download_roundtrip:true});
      } finally {await context.close();}
    }
    assert.deepEqual(report.external_requests,[]);
    assert.deepEqual(report.page_errors,[]);
    report.status='passed';
  } catch(error) {report.status='failed';report.error=String(error);process.exitCode=1;}
  finally {await browser.close();fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
})();
