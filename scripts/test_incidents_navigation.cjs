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
const html = read('index.html');
assert(/id="semantic-space-tab"[^>]*aria-selected="true"/.test(html));
assert(/id="risk-cards-tab"[^>]*aria-selected="false"/.test(html));
assert(/id="explore"[^>]* hidden/.test(html));
assert(read('assets/semantic-space.js').includes("else if (!location.hash || ['#semantic-space','#ai-risk-space'].includes(location.hash)) switchTab(true)"));
assert(read('assets/semantic-space.js').includes("if (['#explore','#taxonomy-panel'].includes(location.hash)) switchTab(false)"));
const about = read('about.html');
const disclosure = about.match(/<details id="mapping-details"[^>]*>([\s\S]*?)<\/details>/);
assert(disclosure);
assert(!/<details id="mapping-details"[^>]*\bopen\b/.test(about));
assert(disclosure[1].includes('Technical process and AI for Everyone (Korea) example'));
assert(disclosure[1].includes('295 candidate cards'));
assert(disclosure[1].includes('L2-normalised'));
assert(about.indexOf('Keywords select candidate cards') < about.indexOf('<details id="mapping-details"'));
for (const text of ['Keywords &amp; applications mapping', 'L2-normalised', 'concept-specific threshold', 'explicit exclusions applied last', '295 candidate cards (259 General, 36 Agentic)']) assert(about.includes(text));
const network = JSON.parse(read('data/semantic_space.json'));
const cards = JSON.parse(read('data/heart_l4_risk_cards.json'));
const selected = new Set(network.scenarios.find(item => item.id === 'ai-for-everyone').ids);
assert.equal(selected.size, 295);
assert.equal(cards.filter(card => selected.has(card.L4_ID) && card.L1_ID === 'L1_G').length, 259);
assert.equal(cards.filter(card => selected.has(card.L4_ID) && card.L1_ID === 'L1_A').length, 36);
console.log('Incident navigation checks passed: ordered views, preparation notice and verified source links.');
