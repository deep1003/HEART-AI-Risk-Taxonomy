const assert = require('node:assert/strict');
const {replacements, preferEvidencePDF} = require('../assets/evidence-pdf-links.js');
const cards = require('../data/heart_l4_risk_cards.json');
let changed = 0;
for (const card of cards) {
  const mapped = preferEvidencePDF(card);
  if (mapped.Evidence_URL !== card.Evidence_URL) changed++;
  assert.deepEqual({...mapped, Evidence_URL:card.Evidence_URL}, card);
  if (!replacements[card.Evidence_URL]) assert.equal(mapped.Evidence_URL, card.Evidence_URL);
}
assert.equal(Object.keys(replacements).length, 8);
assert(changed > 180);
console.log(`${changed} card access links updated; definitions, quotes, DOI and official source links preserved.`);
