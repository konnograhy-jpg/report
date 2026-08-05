const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const page = fs.readFileSync(path.join(__dirname, '..', 'boss', 'tenders', 'tenders_2026_8_4_20260804_1625.html'), 'utf8');

test('test tender page explains that another designer currently holds the tender', () => {
  assert.match(page, /resData\.error === 'tender_already_assigned'/);
  assert.match(page, /resData\.assignedDesigner/);
  assert.match(page, /目前由/);
  assert.match(page, /請先討論/);
});

test('test tender page derives a stable tender ID rather than a time-based fallback', () => {
  assert.match(page, /new URL\(targetUrl\)\.searchParams\.get\('pk'\)/);
  assert.doesNotMatch(page, /TENDER-" \+ Math\.floor\(Date\.now\(\) \/ 1000\)/);
});

test('test tender page shows the stable tender ID used for each acceptance or assignment conflict', () => {
  assert.match(page, /穩定標案識別：\$\{tenderId\}/);
});
