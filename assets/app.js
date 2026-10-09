const state = { cards: [], filtered: [], visible: 48 };
const el = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

function hierarchy(card) {
  return `${card.L1_ID} ${card.L1_Name_en} (${card.L1_Name_ko}) › ${card.L2_ID} ${card.L2_Name_en} (${card.L2_Name_ko}) › ${card.L3_ID} ${card.L3_Name_en} (${card.L3_Name_ko})`;
}

function populateFilters() {
  const domains = [...new Set(state.cards.map(card => card.L1_Name_en))].sort();
  const categories = [...new Map(state.cards.map(card => [card.L3_ID, `${card.L3_ID} ${card.L3_Name_en} (${card.L3_Name_ko})`])).entries()].sort((a,b) => a[1].localeCompare(b[1]));
  el('domain-filter').insertAdjacentHTML('beforeend', domains.map(value => `<option>${esc(value)}</option>`).join(''));
  el('l3-filter').insertAdjacentHTML('beforeend', categories.map(([id,label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join(''));
}

function applyFilters() {
  const query = el('search').value.trim().toLocaleLowerCase();
  const domain = el('domain-filter').value;
  const l3 = el('l3-filter').value;
  state.filtered = state.cards.filter(card => {
    if (domain && card.L1_Name_en !== domain) return false;
    if (l3 && card.L3_ID !== l3) return false;
    if (!query) return true;
    const text = [card.L4_ID, card.L4_Name_en, card.L4_Name_ko, card.Risk_Definition_en, card.Risk_Definition_ko, card.L3_Name_en, card.L3_Name_ko, card.Evidence_Reference_Title].join(' ').toLocaleLowerCase();
    return text.includes(query);
  });
  state.visible = 48;
  renderCards();
}

function renderCards() {
  const cards = state.filtered.slice(0, state.visible);
  el('card-grid').innerHTML = cards.map(card => `
    <button class="risk-card" type="button" data-card-id="${esc(card.L4_ID)}">
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
    <div class="card-meta"><span class="badge">${esc(card.L4_ID)}</span><span class="badge domain">${esc(card.L1_Name_en)}</span></div>
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
  state.filtered = state.cards;
  el('card-count').textContent = state.cards.length.toLocaleString();
  el('l3-count').textContent = new Set(state.cards.map(card => card.L3_ID)).size.toLocaleString();
  populateFilters();
  renderCards();
}

['search','domain-filter','l3-filter'].forEach(id => el(id).addEventListener('input', applyFilters));
el('load-more').addEventListener('click', () => { state.visible += 48; renderCards(); });
el('card-grid').addEventListener('click', event => {
  const button = event.target.closest('[data-card-id]');
  if (!button) return;
  openCard(state.cards.find(card => card.L4_ID === button.dataset.cardId));
});
el('close-dialog').addEventListener('click', () => el('card-dialog').close());
el('card-dialog').addEventListener('click', event => { if (event.target === el('card-dialog')) el('card-dialog').close(); });
start().catch(error => { el('card-grid').innerHTML = `<p>Unable to load the dataset. ${esc(error.message)}</p>`; });
