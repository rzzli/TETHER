// Optional browser acceptance check. Requires Playwright through NODE_PATH or local installation.
// Uses a fresh headless profile; never reads or changes the reviewer's browser draft.
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const assert = require('node:assert/strict');

(async () => {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw Error('Usage: node check_review_workbook.cjs Review.html fresh-qa-directory');
  await fs.mkdir(output, { recursive: false });
  const browser = await chromium.launch({ channel: process.env.REVIEW_BROWSER_CHANNEL || 'msedge', headless: true });
  const checks = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requests.push(r.url()));
    page.on('dialog', d => d.accept());
    await page.goto(pathToFileURL(path.resolve(input)).href);
    assert.equal(await page.locator('.case-section').count(), 10);
    assert.equal(await page.locator('article.card').count(), 20);
    assert.equal(await page.locator('#progress').getAttribute('value'), '0');
    assert.equal(await page.locator('select').evaluateAll(els => els.every(e => e.value === '')), true);
    await page.screenshot({ path: path.join(output, 'desktop.png') });
    checks.push('Ten cases / twenty claims, no preselected judgments');

    await page.locator('#reviewer').fill('QA reviewer');
    await page.locator('#f0c0source_support').selectOption('Cannot assess');
    await page.locator('#f0c0rationale').fill('QA only: source interpretation requires expert review.');
    await page.reload();
    assert.equal(await page.locator('#reviewer').inputValue(), 'QA reviewer');
    assert.equal(await page.locator('#f0c0source_support').inputValue(), 'Cannot assess');
    assert.match(await page.locator('#progressText').textContent(), /^0 of 20/);
    checks.push('Autosave and reload; partial responses never count as completed');

    await page.evaluate(() => {
      document.querySelectorAll('select').forEach(el => {
        el.value = 'Cannot assess'; el.dispatchEvent(new Event('input', { bubbles: true }));
      });
      document.querySelectorAll('textarea[id$="rationale"]').forEach(el => {
        el.value = 'QA only: not a scientific judgment.'; el.dispatchEvent(new Event('input', { bubbles: true }));
      });
    });
    await page.locator('#summaryNav').click();
    assert.match(await page.locator('#summaryStatus').textContent(), /All required fields are complete/);
    const downloadEvent = page.waitForEvent('download');
    await page.locator('#exportBtn').click();
    const download = await downloadEvent;
    const draftPath = path.join(output, 'synthetic-browser-test-answers.json');
    await download.saveAs(draftPath);
    const draft = JSON.parse(await fs.readFile(draftPath, 'utf8'));
    assert.equal(draft.completed_claims, 20);
    assert.equal(draft.review_status, 'single_reviewer_complete');
    assert.equal(draft.scientific_adjudication, 'pending');
    assert.equal(draft.forms.length, 10);
    assert(draft.forms.every(f => f.role === 'evaluation_only' && f.scientific_adjudication === 'pending'));
    checks.push('Export preserves all source-linked answers and pending scientific adjudication');

    await page.locator('#resetBtn').click();
    assert.equal(await page.locator('#reviewer').inputValue(), '');
    await page.locator('#importFile').setInputFiles(draftPath);
    await page.waitForFunction(() => document.getElementById('progress').value === 20);
    assert.equal(await page.locator('#reviewer').inputValue(), 'QA reviewer');
    const wrong = { ...draft, package_id: 'different-workbook' };
    await page.locator('#importFile').setInputFiles({ name: 'wrong.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(wrong)) });
    await page.waitForFunction(() => document.getElementById('toast').textContent.startsWith('Import failed:'));
    assert.match(await page.locator('#progressText').textContent(), /^20 of 20/);
    checks.push('Reset/import round trip; foreign draft rejected without changing answers');

    await page.locator('#summaryNav').click();
    const reportEvent = page.waitForEvent('download');
    await page.locator('#reportBtn').click();
    await (await reportEvent).saveAs(path.join(output, 'synthetic-browser-test-summary.md'));
    assert.match(await fs.readFile(path.join(output, 'synthetic-browser-test-summary.md'), 'utf8'), /Scientific adjudication pending/);
    checks.push('Readable summary download');

    await page.setViewportSize({ width: 390, height: 844 });
    for (let i = 0; i < 10; i++) {
      await page.locator('#nav' + i).click();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    await page.locator('#nav0').click(); await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(output, 'mobile.png') });
    checks.push('All ten cases fit a 390px mobile viewport');
    await page.setViewportSize({ width: 1000, height: 1100 });
    await page.evaluate(() => dispatchEvent(new Event('beforeprint')));
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.case-section').evaluateAll(els => els.every(e => getComputedStyle(e).display !== 'none')), true);
    assert.equal(await page.locator('.answer-print').count() > 140, true);
    await page.screenshot({ path: path.join(output, 'print-layout.png') });
    await page.emulateMedia({ media: 'screen' });
    await page.evaluate(() => dispatchEvent(new Event('afterprint')));
    assert.equal(await page.locator('.answer-print').count(), 0);
    checks.push('Print shows all cases and current answers, then restores normal form');
    assert.deepEqual(errors, []);
    assert.equal(requests.some(url => /^https?:/.test(url)), false);
    checks.push('No browser errors or automatic network requests');

    const isolated = await browser.newContext();
    await isolated.addInitScript(() => { Storage.prototype.setItem = () => { throw Error('blocked'); }; });
    const offline = await isolated.newPage();
    await offline.goto(pathToFileURL(path.resolve(input)).href);
    await offline.locator('#reviewer').fill('Storage unavailable QA');
    assert.match(await offline.locator('#saveStatus').textContent(), /storage unavailable/);
    await offline.locator('#summaryNav').click();
    const event = offline.waitForEvent('download'); await offline.locator('#exportBtn').click();
    const saved = await event;
    const text = await fs.readFile(await saved.path(), 'utf8');
    const partial = JSON.parse(text);
    assert.equal(partial.reviewer, 'Storage unavailable QA');
    assert.equal(partial.forms.every(f => f.reviewed_at === null), true);
    await isolated.close();
    checks.push('Storage-denied fallback still exports; unanswered cases have no review timestamp');
    await fs.writeFile(path.join(output, 'report.json'), JSON.stringify({ status: 'passed', checks, scientific_review: 'not_run', browser: 'Headless Edge; fresh isolated profiles' }, null, 2));
    console.log(JSON.stringify({ status: 'passed', checks: checks.length }));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
