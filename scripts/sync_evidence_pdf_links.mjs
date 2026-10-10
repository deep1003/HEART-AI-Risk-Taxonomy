import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

const require = createRequire(import.meta.url);
const {replacements, preferEvidencePDF} = require('../assets/evidence-pdf-links.js');
const root = path.resolve(import.meta.dirname, '..');
const data = path.join(root, 'data');
const output = path.join(data, 'HEART_L4_Risk_Cards.xlsx');
const backup = path.join(root, 'evidence_work', 'pdf_sync_before');
await fs.mkdir(backup, {recursive:true});
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const sheet = workbook.worksheets.getItem('Risk Cards');
const rows = sheet.getUsedRange().values;
const column = rows[0].indexOf('Evidence_URL');
assert(column >= 0);
const previewRange = 'U1:W4';
async function preview(name) {
  const image = await workbook.render({sheetName:'Risk Cards', range:previewRange, scale:1, format:'png'});
  await fs.writeFile(path.join(backup, name), new Uint8Array(await image.arrayBuffer()));
}
if (process.argv.includes('--inspect')) {
  console.log((await workbook.inspect({kind:'sheet',include:'id,name',maxChars:1500})).ndjson);
  console.log((await workbook.inspect({kind:'table',range:'Risk Cards!U1:W4',include:'values,formulas',tableMaxRows:4,tableMaxCols:3,maxChars:2500})).ndjson);
  await preview('before.png');
  process.exit(0);
}
const names = ['heart_l4_risk_cards.json','heart_l4_risk_cards.csv','HEART_L4_Risk_Cards.xlsx','manifest.json',
  'semantic_space.json','l3_semantic_colours.json','l4_semantic_colours.json','keyword_semantics.json'];
for (const name of names) {
  try { await fs.copyFile(path.join(data,name),path.join(backup,name),fs.constants.COPYFILE_EXCL); }
  catch (error) { if (error.code !== 'EEXIST') throw error; }
}
const originalRaw = await fs.readFile(path.join(data,names[0]),'utf8');
const original = JSON.parse(originalRaw);
const cards = original.map(preferEvidencePDF);
assert.equal(cards.length,622);
const byId = new Map(cards.map(card=>[card.L4_ID,card]));
let changed = 0;
for (let index=1;index<rows.length;index++) {
  const row = rows[index];
  const target = byId.get(row[0]);
  assert(target,`Unknown workbook card ${row[0]}`);
  assert.equal(row[column],original[index-1].Evidence_URL);
  if (row[column] !== target.Evidence_URL) {
    sheet.getCell(index,column).values = [[target.Evidence_URL]];
    changed++;
  }
}
const pdfCount = cards.filter(card=>Object.values(replacements).includes(card.Evidence_URL)).length;
assert.equal(pdfCount,231);
// Preserve the existing workbook's BOM-prefixed identifier header on import.
sheet.getRange('A1').values = [['\ufeffL4_ID']];
await workbook.recalculate();
console.log((await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1500})).ndjson);
await preview('after.png');
await (await SpreadsheetFile.exportXlsx(workbook)).save(output);
// Keep existing serialization, BOM and line endings; replace only verified URLs.
for (const name of names.slice(0,2)) {
  let text = await fs.readFile(path.join(data,name),'utf8');
  for (const [before,after] of Object.entries(replacements)) text = text.replaceAll(before,after);
  if (name.endsWith('.json')) assert.deepEqual(JSON.parse(text),cards);
  await fs.writeFile(path.join(data,name),text);
}
const hash = buffer=>crypto.createHash('sha256').update(buffer).digest('hex');
const oldHash = hash(originalRaw);
const newHash = hash(await fs.readFile(path.join(data,names[0])));
// Only access metadata changed: refresh provenance without recomputing positions,
// embeddings, colours or filter memberships from unchanged names/definitions.
for (const name of names.slice(4)) {
  const raw = await fs.readFile(path.join(data,name),'utf8');
  assert.equal(JSON.parse(raw).source_sha256,oldHash);
  await fs.writeFile(path.join(data,name),raw.replace(oldHash,newHash));
}
const l4Path = path.join(data,'l4_semantic_colours.json');
const l4Raw = await fs.readFile(l4Path,'utf8');
await fs.writeFile(l4Path,l4Raw.replace(JSON.parse(l4Raw).l3_palette_sha256,
  hash(await fs.readFile(path.join(data,'l3_semantic_colours.json')))));
const manifestPath = path.join(data,'manifest.json');
const manifest = JSON.parse(await fs.readFile(manifestPath,'utf8'));
for (const [key,name] of [['csv',names[1]],['json',names[0]],['xlsx',names[2]]]) {
  manifest.files[key] = {path:name,sha256:hash(await fs.readFile(path.join(data,name)))};
}
manifest.evidence_pdf_sync = {verified_papers:8,updated_card_urls:pdfCount,access_links_synced_at_utc:new Date().toISOString(),review:'evidence_pdf_access_review.md'};
await fs.writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');
console.log(`Synchronized ${changed} URLs across JSON, CSV and Excel; originals backed up in ${backup}`);
