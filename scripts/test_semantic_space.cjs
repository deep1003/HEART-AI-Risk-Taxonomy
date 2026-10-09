const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.join(__dirname, '..');
const {activeIds, escape, nodeRadius} = require(path.join(root, 'assets/semantic-space.js'));
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
assert(data.clusters.length > 1);
assert.equal(data.method.embedding_dimensions, 384);
assert.equal(data.method.edge_count, data.edges.length);
assert(data.points.every(point => Number.isInteger(point.degree) && point.degree >= 0));
assert(data.clusters.every(cluster => /^#[a-f0-9]{6}$/i.test(cluster.color)));
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
  for(const cluster of data.clusters){
    const selected=activeIds(data,{scenario:scenario.id,cluster:cluster.id});
    assert.equal(selected.size,scenario.ids.filter(id=>cluster.ids.includes(id)).length);
  }
}
assert(activeIds(data, {scenario:'delivery-robots'}).has('G_SYS_PERF_015'));
assert(activeIds(data, {scenario:'factory-humanoids'}).has('P_SYS_CONTROL_037'));
assert(activeIds(data, {scenario:'home-humanoids'}).has('P_SYS_CONTROL_046'));
assert(!activeIds(data, {scenario:'home-humanoids'}).has('G_INT_PRIV_031'));
assert(activeIds(data, {scenario:'network-agents', keyword:'security'}).has('A_SYS_AUTH_001'));
assert.equal(activeIds(data, {scenario:'missing'}).size, 0);
assert.deepEqual(data.keywords.map(item => item.name), ['Misuse', 'Mis/disinformation', 'Hate and unfairness', 'Self-harm', 'Cybersecurity', 'Democracy', 'Education', 'Labour', 'Human rights', 'Out of control', 'Prompt injection']);
assert(data.keywords.every(item => item.ids.length > 0));
assert(data.edges.every(([a,b,weight]) => a !== b && sourceIds.has(a) && sourceIds.has(b) && weight >= .45 && weight <= 1));
const degrees = new Map([...sourceIds].map(id=>[id,0]));
const strengths = new Map([...sourceIds].map(id=>[id,0]));
for(const [a,b,w] of data.edges){degrees.set(a,degrees.get(a)+1);degrees.set(b,degrees.get(b)+1);strengths.set(a,strengths.get(a)+w);strengths.set(b,strengths.get(b)+w);}
assert(data.points.every(point=>degrees.get(point.id)===point.degree));
assert(data.points.every(point=>Math.abs(strengths.get(point.id)-point.strength)<1e-5));
assert.equal(nodeRadius(5,5,40),3);
assert.equal(nodeRadius(40,5,40),15);
assert(nodeRadius(20,5,40)>nodeRadius(10,5,40));
assert(Number.isFinite(nodeRadius(5,5,5)));
assert(Math.abs(data.points.reduce((sum,p)=>sum+p.strength,0)-2*data.edges.reduce((sum,e)=>sum+e[2],0))<1e-4);
assert(!escape('<script>').includes('<script>'));
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
assert(html.includes('aria-controls="semantic-space" aria-selected="true"'));
assert(html.includes('aria-labelledby="risk-cards-tab" hidden'));
assert(!html.includes('src="assets/kt-logo.svg"'));
const original=fs.readFileSync(path.join(root,'assets/kt-logo.svg'),'utf8');
const reverse=fs.readFileSync(path.join(root,'assets/kt-logo-light.svg'),'utf8');
assert.equal(reverse.trim(),original.replace('fill="black"','fill="white"').trim());
console.log(`Semantic-network smoke tests passed: 622 IDs, 47 L3, ${data.clusters.length} communities, ${data.edges.length} weighted links, degree counts, scenario/keyword intersections and unchanged source hash.`);
