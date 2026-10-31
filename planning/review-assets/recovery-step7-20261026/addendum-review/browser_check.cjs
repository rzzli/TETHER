const { chromium } = require('C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../../..');
const out = path.join(root, 'data/cache/r07-genetics-form-browser-20261026');
fs.mkdirSync(out, {recursive:true});
const source = path.join(root, 'docs/expert-review-genetics-20261026/Expert-source-review.html');
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
        assert.equal(await page.locator('.passage').count(),13);
        assert.equal(await page.locator('input:checked').count(),0);
        assert.equal(await page.locator('#review fieldset').count(),10);
        const initial=await page.evaluate(()=>buildExport());
        assert.equal(initial.role,'evaluation_only');
        assert.equal(initial.review_status,'partial_source_review_unadjudicated');
        assert(initial.responses.every(r=>r.selection===null));
        assert(!Object.hasOwn(initial,'score'));
        const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));
        await page.screenshot({path:path.join(out,name+'-top.png')});
        assert(dimensions.scroll<=viewport.width && dimensions.body<=viewport.width,'Horizontal overflow '+JSON.stringify(dimensions));
        await page.locator('#reviewer-id').fill('QA fixture only — not a human submission');
        await page.locator('#review input[value="cannot_assess"]').first().check();
        await page.locator('#elapsed').fill('3.5');
        const selected=await page.evaluate(()=>buildExport());
        assert.equal(selected.responses.filter(r=>r.selection==='cannot_assess').length,1);
        assert.equal(selected.elapsed_minutes_self_reported,3.5);
        const downloadPromise=page.waitForEvent('download');
        await page.locator('#save').click();
        const download=await downloadPromise;
        const filename=path.join(out,name+'-export-fixture.json');
        await download.saveAs(filename);
        const exported=JSON.parse(fs.readFileSync(filename,'utf8'));
        assert.equal(exported.reviewer.reviewer_id,'QA fixture only — not a human submission');
        assert.equal(exported.role,'evaluation_only');
        assert.equal(exported.responses.filter(r=>r.selection!==null).length,1);
        await page.screenshot({path:path.join(out,name+'-save.png')});
        report.views.push({name,viewport,dimensions,source_cards:13,items:10,blank_default:true,unknown_preserved:true,download_roundtrip:true});
      } finally {await context.close();}
    }
    assert.deepEqual(report.external_requests,[]);
    assert.deepEqual(report.page_errors,[]);
    report.status='passed';
  } catch(error) {report.status='failed';report.error=String(error);process.exitCode=1;}
  finally {await browser.close();fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));}
})();
