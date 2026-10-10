const assert = require('node:assert/strict');
const {replacements, preferEvidencePDF} = require('../assets/evidence-pdf-links.js');
const cards = require('../data/heart_l4_risk_cards.json');
let changed = 0;
assert.deepEqual(replacements, require('../data/evidence_pdf_url_map.json'));
for (const card of cards) {
  const mapped = preferEvidencePDF(card);
  if (Object.values(replacements).includes(card.Evidence_URL)) changed++;
  assert.deepEqual({...mapped, Evidence_URL:card.Evidence_URL}, card);
  if (!replacements[card.Evidence_URL]) assert.equal(mapped.Evidence_URL, card.Evidence_URL);
  assert(!Object.keys(replacements).includes(card.Evidence_URL));
}
assert.equal(Object.keys(replacements).length, 8);
assert.equal(changed, 231);
console.log(`${changed} verified PDF URLs in the canonical dataset; website mapping is idempotent.`);
