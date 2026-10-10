const state = { cards: [], filtered: [], visible: 48, l2: "" };
const el = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const domainColors = {"General AI":"#3867d6","Agentic AI":"#138a72","Physical AI":"#c44a3d"};
const domainOrder = {"General AI":0,"Agentic AI":1,"Physical AI":2};

function hierarchy(card) {
  return `${card.L1_ID} ${card.L1_Name_en} (${card.L1_Name_ko}) › ${card.L2_ID} ${card.L2_Name_en} (${card.L2_Name_ko}) › ${card.L3_ID} ${card.L3_Name_en} (${card.L3_Name_ko})`;
}

function populateFilters() {
  const domains = [...new Set(state.cards.map(card => card.L1_Name_en))].sort();
  const categories = [...new Map(state.cards.map(card => [card.L3_ID, `${card.L3_ID} ${card.L3_Name_en} (${card.L3_Name_ko})`])).entries()].sort((a,b) => a[1].localeCompare(b[1]));
  el('domain-filter').insertAdjacentHTML('beforeend', domains.map(value => `<option>${esc(value)}</option>`).join(''));
  el('l3-filter').insertAdjacentHTML('beforeend', categories.map(([id,label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join(''));
  buildTree();
}

function buildTree() {
  const byL1 = new Map();
  state.cards.forEach(card => {
    if (!byL1.has(card.L1_ID)) byL1.set(card.L1_ID, {nameEn:card.L1_Name_en,nameKo:card.L1_Name_ko,cards:[]});
    byL1.get(card.L1_ID).cards.push(card);
  });
  el('taxonomy-tree').innerHTML = [...byL1.entries()].sort((a,b) => domainOrder[a[1].nameEn] - domainOrder[b[1].nameEn]).map(([l1Id,l1]) => {
    const byL2 = new Map();
    l1.cards.forEach(card => {
      if (!byL2.has(card.L2_ID)) byL2.set(card.L2_ID,{nameEn:card.L2_Name_en,nameKo:card.L2_Name_ko,cards:[]});
      byL2.get(card.L2_ID).cards.push(card);
    });
    const l2Html = [...byL2.entries()].map(([l2Id,l2]) => {
      const l3 = [...new Map(l2.cards.map(card => [card.L3_ID,card])).values()].sort((a,b) => a.L3_Name_en.localeCompare(b.L3_Name_en));
      return `<div class="tree-l2"><button class="tree-l2-head" type="button" data-l2="${esc(l2Id)}"><span>${esc(l2.nameEn)}</span><b>${l2.cards.length}</b></button>${l3.map(card => `<button class="tree-l3" type="button" data-l3="${esc(card.L3_ID)}"><code>${esc(card.L3_ID.replace(`${l1Id.slice(-1)}_`,''))}</code><span>${esc(card.L3_Name_en)}</span><b>${l2.cards.filter(item => item.L3_ID === card.L3_ID).length}</b></button>`).join('')}</div>`;
    }).join('');
    return `<details class="tree-domain" open style="--domain:${domainColors[l1.nameEn]}"><summary data-l1="${esc(l1.nameEn)}"><span>${esc(l1.nameEn)}</span><b>${l1.cards.length}</b></summary>${l2Html}</details>`;
  }).join('');
}

function closeTreeOnMobile() {
  if (window.matchMedia('(max-width: 840px)').matches) {
    el('taxonomy-panel').classList.remove('open');
    el('tree-toggle').setAttribute('aria-expanded','false');
  }
}

function syncTreeSelection() {
  el('show-all').classList.toggle('active', !el('domain-filter').value && !state.l2 && !el('l3-filter').value);
  document.querySelectorAll('[data-l2]').forEach(node => node.classList.toggle('active', node.dataset.l2 === state.l2));
  document.querySelectorAll('[data-l3]').forEach(node => node.classList.toggle('active', node.dataset.l3 === el('l3-filter').value));
}

function applyFilters() {
  const query = el('search').value.trim().toLocaleLowerCase();
  const domain = el('domain-filter').value;
  const l3 = el('l3-filter').value;
  state.filtered = state.cards.filter(card => {
    if (domain && card.L1_Name_en !== domain) return false;
    if (state.l2 && card.L2_ID !== state.l2) return false;
    if (l3 && card.L3_ID !== l3) return false;
    if (!query) return true;
    const text = [card.L4_ID, card.L4_Name_en, card.L4_Name_ko, card.Risk_Definition_en, card.Risk_Definition_ko, card.L3_Name_en, card.L3_Name_ko, card.Evidence_Reference_Title].join(' ').toLocaleLowerCase();
    return text.includes(query);
  });
  state.visible = 48;
  const chosen = state.cards.find(card => card.L3_ID === l3) || state.cards.find(card => card.L2_ID === state.l2) || state.cards.find(card => card.L1_Name_en === domain);
  let heading = 'All risk cards';
  let path = '';
  if (l3 && chosen) { heading = chosen.L3_Name_en; path = `${chosen.L1_Name_en} › ${chosen.L2_Name_en} › ${chosen.L3_Name_en} (${chosen.L3_Name_ko})`; }
  else if (state.l2 && chosen) { heading = chosen.L2_Name_en; path = `${chosen.L1_Name_en} › ${chosen.L2_Name_en} (${chosen.L2_Name_ko})`; }
  else if (domain) { heading = domain; path = `${chosen?.L1_Name_en || domain} (${chosen?.L1_Name_ko || ''})`; }
  el('active-heading').textContent = heading;
  el('active-path').textContent = path;
  el('active-path').hidden = !path;
  syncTreeSelection();
  renderCards();
}

function renderCards() {
  const cards = state.filtered.slice(0, state.visible);
  el('card-grid').innerHTML = cards.map(card => `
    <button class="risk-card" type="button" data-card-id="${esc(card.L4_ID)}" style="--card-accent:${domainColors[card.L1_Name_en]}">
      <span class="card-meta"><span class="badge">${esc(card.L4_ID)}</span><span class="badge domain">${esc(card.L1_Name_en)}</span></span>
      <h3>${esc(card.L4_Name_en)} <span class="ko">(${esc(card.L4_Name_ko)})</span></h3>
      <p class="definition-preview">${esc(card.Risk_Definition_en)}</p>
      <p class="breadcrumb">${esc(card.L3_ID)} ${esc(card.L3_Name_en)}</p>
    </button>`).join('');
  el('result-count').textContent = `${state.filtered.length.toLocaleString()} cards`;
  el('load-more').hidden = state.visible >= state.filtered.length;
  el('card-grid').setAttribute('aria-busy', 'false');
}

function openCard(card) {
  const attributes = [];
  if (card.Facet) attributes.push(`<span class="badge">Facet: ${esc(card.Facet)}</span>`);
  if (card.Act_Type) attributes.push(`<span class="badge">Act-type: ${esc(card.Act_Type)}</span>`);
  const attributeSection = attributes.length ? `<section class="detail-section"><h3>L4 attributes</h3><div class="attributes">${attributes.join('')}</div></section>` : '';
  const referenceMeta = [card.Evidence_Reference_Authors, card.Evidence_Reference_Year, card.Evidence_Reference_Type].filter(Boolean).map(esc).join(' · ');
  el('dialog-content').innerHTML = `
    <div class="card-meta" style="--card-accent:${domainColors[card.L1_Name_en]}"><span class="badge">${esc(card.L4_ID)}</span><span class="badge domain">${esc(card.L1_Name_en)}</span></div>
    <h2 id="dialog-title">${esc(card.L4_Name_en)} (${esc(card.L4_Name_ko)})</h2>
    <div class="hierarchy">${esc(hierarchy(card))}</div>
    <section class="detail-section"><h3>Risk definition</h3><p>${esc(card.Risk_Definition_en)}</p><p lang="ko">${esc(card.Risk_Definition_ko)}</p></section>
    ${attributeSection}
    <section class="detail-section"><h3>Evidence reference</h3><a class="evidence-link" href="${esc(card.Evidence_URL)}" target="_blank" rel="noopener noreferrer">${esc(card.Evidence_Reference_Title)}</a><p>${referenceMeta}</p><blockquote>${esc(card.Evidence_Quote)}</blockquote><p class="source-note">${esc(card.Evidence_Quote_Location)}</p></section>
    <section class="detail-section"><h3>Future assessment fields</h3><div class="future-fields"><div class="future-field"><span>Probability</span></div><div class="future-field"><span>Severity</span></div></div></section>`;
  el('card-dialog').showModal();
}

async function start() {
  const response = await fetch('data/heart_l4_risk_cards.json');
  if (!response.ok) throw new Error(`Dataset request failed: ${response.status}`);
  state.cards = await response.json();
  state.cards.sort((a,b) => domainOrder[a.L1_Name_en] - domainOrder[b.L1_Name_en] || a.L3_ID.localeCompare(b.L3_ID) || a.L4_ID.localeCompare(b.L4_ID));
  state.filtered = state.cards;
  if (el('card-count')) el('card-count').textContent = state.cards.length.toLocaleString();
  if (el('l3-count')) el('l3-count').textContent = new Set(state.cards.map(card => card.L3_ID)).size.toLocaleString();
  populateFilters();
  renderCards();
}

el('search').addEventListener('input', applyFilters);
el('domain-filter').addEventListener('input', () => { state.l2 = ''; el('l3-filter').value = ''; applyFilters(); });
el('l3-filter').addEventListener('input', () => { state.l2 = ''; applyFilters(); });
el('taxonomy-tree').addEventListener('click', event => {
  const l1 = event.target.closest('[data-l1]');
  const l2 = event.target.closest('[data-l2]');
  const l3 = event.target.closest('[data-l3]');
  if (l1) { event.preventDefault(); el('domain-filter').value = l1.dataset.l1; state.l2 = ''; el('l3-filter').value = ''; }
  if (l2) { state.l2 = l2.dataset.l2; const card = state.cards.find(item => item.L2_ID === state.l2); el('domain-filter').value = card.L1_Name_en; el('l3-filter').value = ''; }
  if (l3) { const card = state.cards.find(item => item.L3_ID === l3.dataset.l3); el('domain-filter').value = card.L1_Name_en; state.l2 = ''; el('l3-filter').value = card.L3_ID; }
  if (l1 || l2 || l3) { applyFilters(); closeTreeOnMobile(); }
});
el('show-all').addEventListener('click', () => { el('domain-filter').value = ''; el('l3-filter').value = ''; state.l2 = ''; applyFilters(); closeTreeOnMobile(); });
el('tree-toggle').addEventListener('click', () => { const open = el('taxonomy-panel').classList.toggle('open'); el('tree-toggle').setAttribute('aria-expanded',String(open)); });
el('tree-close').addEventListener('click', closeTreeOnMobile);
document.querySelectorAll('a[href="#taxonomy-panel"]').forEach(link => link.addEventListener('click', () => {
  if (window.matchMedia('(max-width: 840px)').matches) {
    el('taxonomy-panel').classList.add('open');
    el('tree-toggle').setAttribute('aria-expanded','true');
  }
}));
el('load-more').addEventListener('click', () => { state.visible += 48; renderCards(); });
el('card-grid').addEventListener('click', event => {
  const button = event.target.closest('[data-card-id]');
  if (!button) return;
  openCard(state.cards.find(card => card.L4_ID === button.dataset.cardId));
});
el('close-dialog').addEventListener('click', () => el('card-dialog').close());
el('card-dialog').addEventListener('click', event => { if (event.target === el('card-dialog')) el('card-dialog').close(); });
start().catch(error => { el('card-grid').innerHTML = `<p>Unable to load the dataset. ${esc(error.message)}</p>`; });
