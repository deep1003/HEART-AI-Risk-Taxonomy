const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.join(__dirname, '..');
const {activeIds, escape} = require(path.join(root, 'assets/semantic-space.js'));
const raw = fs.readFileSync(path.join(root, 'data/heart_l4_risk_cards.json'));
const cards = JSON.parse(raw);
const data = JSON.parse(fs.readFileSync(path.join(root, 'data/semantic_space.json')));
const sourceIds = new Set(cards.map(card => card.L4_ID));
assert.equal(data.source_sha256, crypto.createHash('sha256').update(raw).digest('hex'));
assert.equal(sourceIds.size, 622);
assert.equal(new Set(cards.map(card => card.L3_ID)).size, 47);
assert.equal(data.points.length, 622);
assert.equal(new Set(data.points.map(point => point.id)).size, 622);
assert(data.points.every(point => sourceIds.has(point.id) && Number.isFinite(point.x) && Number.isFinite(point.y)));
assert.equal(activeIds(data, {}).size, 622);
assert.equal(data.scenarios.length, 4);
assert.equal(data.clusters.length, 12);
assert.equal(data.clusters.flatMap(cluster => cluster.ids).length, 622);
assert.equal(new Set(data.clusters.flatMap(cluster => cluster.ids)).size, 622);
for (const scenario of data.scenarios) {
  const active = activeIds(data, {scenario:scenario.id});
  assert.equal(active.size, scenario.ids.length);
  assert(active.size > 0 && active.size < 622);
  for (const keyword of data.keywords) {
    const selected = activeIds(data, {scenario:scenario.id, keyword:keyword.id});
    assert([...selected].every(id => active.has(id) && keyword.ids.includes(id)));
    assert.equal(selected.size, scenario.ids.filter(id => keyword.ids.includes(id)).length);
  }
}
assert(activeIds(data, {scenario:'delivery-robots'}).has('G_SYS_PERF_015'));
assert(activeIds(data, {scenario:'factory-humanoids'}).has('P_SYS_CONTROL_037'));
assert(activeIds(data, {scenario:'home-humanoids'}).has('P_SYS_CONTROL_046'));
assert(!activeIds(data, {scenario:'home-humanoids'}).has('G_INT_PRIV_031'));
assert(activeIds(data, {scenario:'network-agents', keyword:'security'}).has('A_SYS_AUTH_001'));
assert.equal(activeIds(data, {scenario:'missing'}).size, 0);
assert.equal(activeIds(data, {scenario:'network-agents', keyword:'navigation'}).size, 0);
assert(data.edges.every(([a,b]) => a !== b && sourceIds.has(a) && sourceIds.has(b)));
assert(!escape('<script>').includes('<script>'));
console.log('Semantic-space smoke tests passed: 622 IDs, 47 L3, 4 overlapping scenarios, 12 topics, all keyword intersections, source hash and finite fixed coordinates.');
