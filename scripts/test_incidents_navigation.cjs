const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
for (const file of ['index.html', 'incidents.html']) {
  const nav = read(file).match(/<nav class="section-nav"[\s\S]*?<\/nav>/)[0];
  assert(nav.indexOf('AI risk taxonomy') < nav.indexOf('AI risk space'));
  assert(nav.indexOf('AI risk space') < nav.indexOf('AI risk incidents'));
  assert(nav.includes('href="incidents.html"'));
  assert(!nav.includes('>Risk cards<'));
}
const incidents = read('incidents.html');
for (const text of ['In preparation.', 'not yet available', 'Near misses', 'not a separate incident database', 'https://incidentdatabase.ai/', 'https://oecd.ai/en/catalogue/tools/ai-incident-database']) {
  assert(incidents.includes(text));
}
assert(incidents.includes('aria-current="page"'));
assert(read('assets/semantic-space.js').includes("event.key === 'End' || (event.key !== 'Home'"));
console.log('Incident navigation checks passed: ordered views, preparation notice and verified source links.');
