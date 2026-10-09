(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  function activeIds(data, filters) {
    let ids = new Set(data.points.map(point => point.id));
    for (const [collection, value] of [['scenarios', filters.scenario], ['clusters', filters.cluster], ['keywords', filters.keyword]]) {
      if (value) {
        const member = data[collection].find(item => item.id === value);
        const subset = new Set(member?.ids || []);
        ids = new Set([...ids].filter(id => subset.has(id)));
      }
    }
    return ids;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {activeIds, escape};
  if (typeof document === 'undefined') return;

  const get = id => document.getElementById(id);
  const colors = {'L1_G':'#3867d6', 'L1_A':'#138a72', 'L1_P':'#c44a3d'};
  const filters = {scenario:'', cluster:'', keyword:''};
  let data, cards, byId, visible = 16, loading, enabledIds = new Set(), locations = new Map();

  function switchTab(semantic) {
    get('semantic-space').hidden = !semantic;
    get('explore').hidden = semantic;
    get('semantic-space-tab').setAttribute('aria-selected', String(semantic));
    get('risk-cards-tab').setAttribute('aria-selected', String(!semantic));
    get('semantic-space-tab').tabIndex = semantic ? 0 : -1;
    get('risk-cards-tab').tabIndex = semantic ? -1 : 0;
    history.replaceState(null, '', semantic ? '#semantic-space' : '#explore');
    if (semantic) load();
    get(semantic ? 'semantic-space' : 'explore').scrollIntoView({block:'start', behavior:'instant'});
  }
  get('semantic-space-tab').addEventListener('click', () => switchTab(true));
  get('risk-cards-tab').addEventListener('click', () => switchTab(false));
  document.querySelector('.explorer-tabs').addEventListener('keydown', event => {
    if (['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
      event.preventDefault();
      const semantic = event.key === 'End' || (event.key !== 'Home' && event.target.id === 'risk-cards-tab');
      switchTab(semantic);
      get(semantic ? 'semantic-space-tab' : 'risk-cards-tab').focus();
    }
  });
  document.querySelectorAll('a[href="#semantic-space"]').forEach(link => link.addEventListener('click', () => switchTab(true)));
  document.querySelectorAll('a[href="#explore"],a[href="#taxonomy-panel"]').forEach(link => link.addEventListener('click', () => switchTab(false)));
  get('semantic-reset').addEventListener('click', () => {
    Object.assign(filters, {scenario:'', cluster:'', keyword:''});
    visible = 16;
    if (data) render();
  });
  get('semantic-context').addEventListener('change', () => data && draw());
  get('semantic-more').addEventListener('click', () => {visible += 16; renderList();});

  async function load() {
    if (data) {draw(); return;}
    if (loading) return;
    get('semantic-status').textContent = 'Loading the risk text projection…';
    loading = true;
    try {
      const [spaceResponse, cardResponse] = await Promise.all([fetch('data/semantic_space.json'), fetch('data/heart_l4_risk_cards.json')]);
      if (!spaceResponse.ok || !cardResponse.ok) throw new Error('The semantic-space data could not be loaded.');
      const cardText = await cardResponse.text();
      const space = await spaceResponse.json();
      const sourceCards = JSON.parse(cardText);
      if (globalThis.crypto?.subtle) {
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(cardText));
        const hash = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2,'0')).join('');
        if (hash !== space.source_sha256) throw new Error('The projection is out of date with the current risk cards.');
      }
      const lookup = new Map(sourceCards.map(card => [card.L4_ID, card]));
      if (space.points.length !== sourceCards.length || space.points.some(point => !lookup.has(point.id))) throw new Error('Projection/card IDs do not match.');
      data = space; cards = sourceCards; byId = lookup;
      buildControls();
      get('semantic-method-stats').textContent = `${data.card_count} unchanged risk cards; 12 text-derived communities and 4 overlapping application communities. Coordinates remain fixed when filters change. This is a lexical text space, not a contextual language-model embedding.`;
      render();
    } catch (error) {
      get('semantic-status').textContent = error.message;
      get('semantic-status').setAttribute('role', 'alert');
    } finally {loading = false;}
  }

  function buildControls() {
    get('semantic-scenarios').innerHTML = data.scenarios.map(item => `<button class="semantic-community" type="button" aria-pressed="false" data-scenario="${escape(item.id)}"><strong>${escape(item.name)}</strong><small lang="ko">${escape(item.name_ko)}</small><small>${item.ids.length} potentially relevant risks</small></button>`).join('');
    get('semantic-clusters').innerHTML = data.clusters.map(item => `<button class="semantic-community" type="button" aria-pressed="false" data-cluster="${escape(item.id)}">${escape(item.name)} <small>${item.ids.length} risks</small></button>`).join('');
    get('semantic-keywords').innerHTML = `<button type="button" aria-pressed="true" data-keyword="">All keywords</button>` + data.keywords.map(item => `<button type="button" aria-pressed="false" data-keyword="${escape(item.id)}">${escape(item.name)}</button>`).join('');
    for (const [container, kind] of [['semantic-scenarios','scenario'],['semantic-clusters','cluster'],['semantic-keywords','keyword']]) {
      get(container).addEventListener('click', event => {
        const button = event.target.closest(`[data-${kind}]`);
        if (!button || button.disabled) return;
        const value = button.dataset[kind];
        filters[kind] = filters[kind] === value ? '' : value;
        if (kind === 'scenario') {filters.cluster = ''; filters.keyword = '';}
        visible = 16;
        render();
      });
    }
  }

  function render() {
    enabledIds = activeIds(data, filters);
    const scenario = data.scenarios.find(item => item.id === filters.scenario);
    const cluster = data.clusters.find(item => item.id === filters.cluster);
    const keyword = data.keywords.find(item => item.id === filters.keyword);
    const labels = [scenario?.name, cluster?.name, keyword?.name].filter(Boolean);
    get('semantic-selection-name').textContent = labels.join(' / ') || 'All risk cards';
    get('semantic-selection-description').textContent = scenario?.description || 'Explore all existing L4 cards through their risk text. Select a community or keyword to focus the space.';
    get('semantic-status').textContent = `${enabledIds.size} active risks of ${data.card_count}. Inactive risks ${get('semantic-context').checked ? 'remain as pale context' : 'are hidden'}.`;
    for (const kind of ['scenario','cluster','keyword']) {
      document.querySelectorAll(`[data-${kind}]`).forEach(button => button.setAttribute('aria-pressed', String(button.dataset[kind] === filters[kind])));
    }
    const withoutKeyword = activeIds(data, {...filters, keyword:''});
    document.querySelectorAll('[data-keyword]').forEach(button => {
      const item = data.keywords.find(keyword => keyword.id === button.dataset.keyword);
      button.disabled = item ? !item.ids.some(id => withoutKeyword.has(id)) : false;
    });
    draw(); renderList();
  }

  function draw() {
    const svg = get('semantic-plot');
    const width = Math.max(280, svg.getBoundingClientRect().width || 960);
    const height = width < 600 ? 420 : Math.min(600, Math.round(width * .65));
    const left = 56, right = width - 24, top = 32, bottom = height - 58;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    const xs = data.points.map(point => point.x), ys = data.points.map(point => point.y);
    const lowX = Math.min(...xs), highX = Math.max(...xs), lowY = Math.min(...ys), highY = Math.max(...ys);
    const padX = (highX - lowX) * .08, padY = (highY - lowY) * .08;
    const minX = lowX - padX, maxX = highX + padX, minY = lowY - padY, maxY = highY + padY;
    const sx = x => left + (x - minX) / (maxX - minX) * (right-left);
    const sy = y => bottom - (y - minY) / (maxY - minY) * (bottom-top);
    locations = new Map(data.points.map(point => [point.id, {x:sx(point.x),y:sy(point.y)}]));
    let markup = '<title>Text-based L4 risk space</title><desc>Existing risk cards projected from their English text. Filtering changes activation, not positions or taxonomy assignments.</desc>';
    const ticks = width < 600 ? 2 : 4;
    for (let index = 0; index <= ticks; index++) {
      const x = left + (right-left) * index / ticks, y = bottom - (bottom-top) * index / ticks;
      markup += `<line class="semantic-grid-line" x1="${x}" y1="${top}" x2="${x}" y2="${bottom}"/><line class="semantic-grid-line" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/><text class="semantic-tick" x="${x}" y="${bottom+20}" text-anchor="middle">${(minX + (maxX-minX)*index/ticks).toFixed(1)}</text><text class="semantic-tick" x="${left-8}" y="${y+4}" text-anchor="end">${(minY + (maxY-minY)*index/ticks).toFixed(1)}</text>`;
    }
    markup += `<text class="semantic-axis-label" x="${(left+right)/2}" y="${height-10}" text-anchor="middle">t-SNE dimension 1 (display units)</text><text class="semantic-axis-label" transform="translate(14,${(top+bottom)/2}) rotate(-90)" text-anchor="middle">t-SNE dimension 2 (display units)</text>`;
    if (enabledIds.size <= 150) {
      for (const [a,b] of data.edges) {
        if (!enabledIds.has(a) || !enabledIds.has(b)) continue;
        const p = locations.get(a), q = locations.get(b);
        markup += `<line class="semantic-edge" x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}"/>`;
      }
    }
    const showContext = get('semantic-context').checked;
    const points = [...data.points].sort((a,b) => Number(enabledIds.has(a.id)) - Number(enabledIds.has(b.id)));
    for (const point of points) {
      const active = enabledIds.has(point.id);
      if (!active && !showContext) continue;
      const card = byId.get(point.id), p = locations.get(point.id);
      const radius = active ? (enabledIds.size > 150 ? 3.5 : 5.2) : 2.4;
      markup += `<circle class="semantic-point ${active ? 'active' : 'inactive'}" data-risk="${escape(point.id)}" cx="${p.x}" cy="${p.y}" r="${radius}" fill="${colors[card.L1_ID]}"><title>${escape(point.id + ': ' + card.L4_Name_en)}</title></circle>`;
    }
    svg.innerHTML = markup;
    svg.setAttribute('aria-label', `${enabledIds.size} active L4 risks in the text projection. Use the active-risk list below for keyboard access.`);
    svg.dataset.activeCount = String(enabledIds.size);
    get('semantic-tooltip').hidden = true;
    get('semantic-status').textContent = `${enabledIds.size} active risks of ${data.card_count}. Inactive risks ${showContext ? 'remain as pale context' : 'are hidden'}.`;
  }

  function renderList() {
    const active = cards.filter(card => enabledIds.has(card.L4_ID)).sort((a,b) => a.L4_ID.localeCompare(b.L4_ID));
    get('semantic-list-count').textContent = `${Math.min(visible, active.length)} of ${active.length} shown`;
    get('semantic-risk-list').innerHTML = active.slice(0, visible).map(card => `<button type="button" class="semantic-risk-item" data-card="${escape(card.L4_ID)}"><code>${escape(card.L4_ID)} · ${escape(card.L1_Name_en)}</code><strong>${escape(card.L4_Name_en)}</strong><span lang="ko">${escape(card.L4_Name_ko)}</span><span>${escape(card.L3_Name_en)}</span></button>`).join('') || '<p>No risks match this combination. Choose another keyword or reset the filters.</p>';
    get('semantic-more').hidden = active.length <= visible;
  }
  get('semantic-risk-list').addEventListener('click', event => {
    const button = event.target.closest('[data-card]');
    if (button) openCard(byId.get(button.dataset.card));
  });
  get('semantic-plot').addEventListener('click', event => {
    const point = event.target.closest('[data-risk]');
    if (point && enabledIds.has(point.dataset.risk)) {openCard(byId.get(point.dataset.risk)); return;}
    const svg = get('semantic-plot'), bounds = svg.getBoundingClientRect(), box = svg.viewBox.baseVal;
    const x = (event.clientX - bounds.left) / bounds.width * box.width;
    const y = (event.clientY - bounds.top) / bounds.height * box.height;
    let nearest, distance = window.matchMedia('(pointer:coarse)').matches ? 22 : 10;
    for (const id of enabledIds) {
      const location = locations.get(id), current = Math.hypot(location.x-x, location.y-y);
      if (current < distance) {nearest = id; distance = current;}
    }
    if (nearest) openCard(byId.get(nearest));
  });
  get('semantic-plot').addEventListener('pointermove', event => {
    const point = event.target.closest('[data-risk]'), tooltip = get('semantic-tooltip');
    if (!point || !enabledIds.has(point.dataset.risk)) {tooltip.hidden = true; return;}
    const card = byId.get(point.dataset.risk);
    tooltip.innerHTML = `<strong>${escape(card.L4_Name_en)}</strong><span>${escape(card.L4_ID)} · ${escape(card.L1_Name_en)} · ${escape(card.L3_Name_en)}</span><span>Click to open the risk card</span>`;
    tooltip.hidden = false;
    const bounds = get('semantic-plot').getBoundingClientRect();
    tooltip.style.left = `${Math.max(8, Math.min(event.clientX-bounds.left+14, bounds.width-tooltip.offsetWidth-8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(event.clientY-bounds.top+14, bounds.height-tooltip.offsetHeight-8))}px`;
  });
  get('semantic-plot').addEventListener('pointerleave', () => {get('semantic-tooltip').hidden = true;});
  new ResizeObserver(() => {if (data && !get('semantic-space').hidden) draw();}).observe(get('semantic-plot').parentElement);
  if (location.hash === '#semantic-space') switchTab(true);
})();
