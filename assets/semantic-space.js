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
  function nodeRadius(strength, minimum, maximum) {
    const ratio = maximum > minimum ? Math.max(0,Math.min(1,(strength-minimum)/(maximum-minimum))) : .5;
    return Math.sqrt(9 + (225-9)*ratio);
  }
  function edgePath(p, q) {
    const dx = q.x - p.x, dy = q.y - p.y;
    const cx = (p.x + q.x)/2 - dy*.22;
    const cy = (p.y + q.y)/2 + dx*.22;
    return `M ${p.x} ${p.y} Q ${cx} ${cy} ${q.x} ${q.y}`;
  }
  function labelCandidates(points, active, level=1) {
    const ranked=points.filter(point=>active.has(point.id)).sort((a,b)=>b.strength-a.strength || a.id.localeCompare(b.id));
    if(level>=3.5)return ranked;
    const limit=level>=2.5?4:level>=1.5?2:1, counts=new Map();
    return ranked.filter(point=>{
      const count=counts.get(point.cluster)||0;
      if(count>=limit)return false;
      counts.set(point.cluster,count+1);return true;
    });
  }
  function zoomViewport(currentZoom, currentPan, factor, anchor, centre) {
    const next=Math.max(.5,Math.min(5,currentZoom*factor)), ratio=next/currentZoom;
    return {zoom:next,pan:{x:anchor.x-centre.x-(anchor.x-centre.x-currentPan.x)*ratio,
                          y:anchor.y-centre.y-(anchor.y-centre.y-currentPan.y)*ratio}};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {activeIds, escape, nodeRadius, edgePath, labelCandidates, zoomViewport};
  if (typeof document === 'undefined') return;

  const get = id => document.getElementById(id);
  function showInlineCard(card) {
    const attributes = [card.Facet ? `Facet: ${card.Facet}` : '', card.Act_Type ? `Act-type: ${card.Act_Type}` : ''].filter(Boolean);
    const evidence = typeof renderEvidence === 'function' ? renderEvidence(card) :
      (card.Evidence_URL ? `<a class="evidence-link" href="${escape(card.Evidence_URL)}" target="_blank" rel="noopener noreferrer">${escape(card.Evidence_Reference_Title)}</a><p>${escape([card.Evidence_Reference_Authors,card.Evidence_Reference_Year,card.Evidence_Reference_Type].filter(Boolean).join(' · '))}</p><blockquote>${escape(card.Evidence_Quote)}</blockquote><p class="source-note">${escape(card.Evidence_Quote_Location)}</p>` : '<p>No reference available.</p>');
    get('semantic-card-content').innerHTML = `<div class="card-meta"><span class="badge">${escape(card.L4_ID)}</span><span class="badge domain">${escape(card.L1_Name_en)}</span></div><h2 id="semantic-card-title">${escape(card.L4_Name_en)} (${escape(card.L4_Name_ko)})</h2><div class="hierarchy">${escape(hierarchy(card))}</div><section class="detail-section"><h3>Risk definition</h3><p>${escape(card.Risk_Definition_en)}</p><p lang="ko">${escape(card.Risk_Definition_ko)}</p></section>${attributes.length ? `<section class="detail-section"><h3>L4 attributes</h3><div class="attributes">${attributes.map(item=>`<span class="badge">${escape(item)}</span>`).join('')}</div></section>` : ''}<section class="detail-section"><h3>Evidence references</h3>${evidence}</section><section class="detail-section"><h3>Future assessment fields</h3><div class="future-fields"><div class="future-field"><span>Probability</span></div><div class="future-field"><span>Severity</span></div></div></section>`;
    get('semantic-card-detail').hidden = false;
    get('semantic-tooltip').hidden = true;
  }
  get('semantic-card-close').addEventListener('click',()=>{get('semantic-card-detail').hidden=true; selectedId=''; draw();});
  const filters = {scenario:'', cluster:'', keyword:''};
  let data, cards, byId, visible = 16, loading, enabledIds = new Set(), locations = new Map();
  const baseZoom = 1.1;
  let zoom = 1, pan = {x:0,y:0}, selectedId = '', drag;

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
    if (event.target.getAttribute('role') === 'tab' && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
      event.preventDefault();
      const semantic = event.key === 'Home' || (event.key !== 'End' && event.target.id === 'risk-cards-tab');
      switchTab(semantic);
      get(semantic ? 'semantic-space-tab' : 'risk-cards-tab').focus();
    }
  });
  document.querySelectorAll('a[href="#semantic-space"]').forEach(link => link.addEventListener('click', () => switchTab(true)));
  document.querySelectorAll('a[href="#explore"],a[href="#taxonomy-panel"]').forEach(link => link.addEventListener('click', () => switchTab(false)));
  get('semantic-reset').addEventListener('click', () => {
    Object.assign(filters, {scenario:'', cluster:'', keyword:''});
    zoom = 1; pan = {x:0,y:0}; selectedId = '';
    visible = 16;
    if (data) render();
  });
  get('semantic-more').addEventListener('click', () => {visible += 16; renderList();});

  async function load() {
    if (data) {draw(); return;}
    if (loading) return;
    get('semantic-status').textContent = 'Loading the risk text projection…';
    loading = true;
    try {
      const [spaceResponse, cardResponse] = await Promise.all([fetch('data/semantic_space.json?v=solid-l4-colours-20261010'), fetch('data/heart_l4_risk_cards.json')]);
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
      get('semantic-method-stats').textContent = `${data.card_count} unchanged risk cards; ${data.clusters.length} human-defined L3 colour groups; ${data.edges.length.toLocaleString()} weighted links. Embeddings: BGE-M3, ${data.method.embedding_dimensions} dimensions; Ollama ${data.method.ollama_version}; model digest ${data.method.model_revision}. L1 anchors, L3 definitions and within-L3 L4 semantic variation determine solid node colours; ForceAtlas2 determines layout. Darker does not mean higher risk. Louvain communities remain diagnostic metadata, not displayed colour groups or new taxonomy assignments.`;
      render();
    } catch (error) {
      get('semantic-status').textContent = error.message;
      get('semantic-status').setAttribute('role', 'alert');
    } finally {loading = false;}
  }

  function buildControls() {
    get('semantic-scenarios').innerHTML = data.scenarios.map(item => `<button class="semantic-community" type="button" aria-pressed="false" data-scenario="${escape(item.id)}"><strong>${escape(item.name)}</strong><small lang="ko">${escape(item.name_ko)}</small><small>${item.ids.length} potentially relevant risks</small></button>`).join('');
    get('semantic-clusters').innerHTML = ['L1_G','L1_A','L1_P'].map(domain=>{
      const categories=data.clusters.filter(item=>item.L1_ID===domain);
      return `<section class="semantic-l1-group"><h4><i class="community-dot" style="background:${escape(data.l1_colors[domain])}"></i>${escape(categories[0].L1_Title_en)}</h4>${[...new Set(categories.map(item=>item.L2_ID))].map(area=>`<div class="semantic-l2-group"><h5>${escape(categories.find(item=>item.L2_ID===area).L2_Title_en)}</h5>${categories.filter(item=>item.L2_ID===area).map(item=>`<button class="semantic-community" type="button" aria-pressed="false" data-cluster="${escape(item.id)}"><i class="community-dot" style="background:${escape(item.color)}"></i>${escape(item.name)}<small>${escape(item.id)} · ${item.ids.length} risks</small></button>`).join('')}</div>`).join('')}</section>`;
    }).join('');
    get('semantic-clusters').parentElement.open = false;
    const strengths = data.points.map(point=>point.strength);
    get('semantic-legend').innerHTML = Object.entries(data.l1_colors).map(([id,color])=>`<span class="semantic-domain-key"><i class="community-dot" style="background:${escape(color)}"></i>${escape(data.clusters.find(item=>item.L1_ID===id).L1_Title_en)}</span>`).join(' ') + `<p>Colour: individual L4 semantic shades within 47 L3 categories and 3 L1 anchors. Boundary mixtures show proximity, not assignment uncertainty; darker does not mean higher risk. Shades are approximate, not a distance-preserving map. Size: weighted degree, ${Math.min(...strengths).toFixed(2)}–${Math.max(...strengths).toFixed(2)}. Pale nodes: inactive.</p>`;
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
    const definitionPanel = get('semantic-keyword-definition');
    definitionPanel.hidden = !keyword;
    definitionPanel.innerHTML = keyword ? `<h4>${escape(keyword.name)} · Concept definition</h4><p>${escape(keyword.definition)}</p>${keyword.url ? `<blockquote>“${escape(keyword.quote)}”</blockquote><p><a href="${escape(keyword.url)}" target="_blank" rel="noopener noreferrer">${escape(keyword.reference_title)}</a> · ${escape(keyword.quote_location)}</p>` : ''}<details><summary>Concept scope and mapping method</summary><p class="source-note">${escape(keyword.scope)}</p><p class="source-note">${keyword.mapping_mode === 'taxonomy' ? 'Existing human-approved L1 assignments. No similarity-based reassignment.' : `Operational synthesis based on the cited source, not a verbatim source definition. BGE-M3 definition-to-card cosine retrieval; threshold ${escape(keyword.threshold)} with documented AI-specialist scope corrections. Exploratory relevance, not validated classification accuracy.`}</p></details>` : '';
    get('semantic-selection-description').innerHTML = escape(scenario?.description || 'A connected semantic network of the current L4 cards. Select a community or keyword, zoom, or drag the background to explore.') + (scenario?.source_url ? [{url:scenario.source_url,label:scenario.source_label},...(scenario.additional_sources||[])].map(source=>` <a href="${escape(source.url)}" target="_blank" rel="noopener noreferrer">${escape(source.label)}</a>`).join(' · ') : '');
    get('semantic-status').textContent = `${enabledIds.size} active risks of ${data.card_count}. Inactive risks remain as pale context.`;
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
    const height = width < 600 ? 460 : Math.min(760, Math.max(580, Math.round(width * .72)));
    const left = 28, right = width - 28, top = 28, bottom = height - 28;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    const xs = data.points.map(point => point.x), ys = data.points.map(point => point.y);
    const lowX = Math.min(...xs), highX = Math.max(...xs), lowY = Math.min(...ys), highY = Math.max(...ys);
    const scale = Math.min((right-left)/(highX-lowX), (bottom-top)/(highY-lowY)) * .85;
    const sx = x => width/2 + (x-(lowX+highX)/2)*scale;
    const sy = y => height/2 - (y-(lowY+highY)/2)*scale;
    locations = new Map(data.points.map(point => [point.id, {x:sx(point.x),y:sy(point.y)}]));
    let markup = '<desc>Transformer-embedding neighbours, Louvain communities and ForceAtlas2 layout. Edges are not causal paths. Filtering does not change taxonomy assignments.</desc>';
    for (let index = 0; index <= 8; index++) {
      const x = left + (right-left)*index/8, y = top + (bottom-top)*index/8;
      markup += `<line class="semantic-grid-line" x1="${x}" y1="${top}" x2="${x}" y2="${bottom}"/><line class="semantic-grid-line" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/>`;
    }
    markup += '<g id="semantic-network-layer">';
    for (const [a,b,weight] of data.edges) {
      if (!enabledIds.has(a) || !enabledIds.has(b)) continue;
      const p = locations.get(a), q = locations.get(b);
      const incident = a === selectedId || b === selectedId;
      markup += `<path class="semantic-edge${incident?' selected-edge':''}" data-source="${escape(a)}" data-target="${escape(b)}" d="${edgePath(p,q)}" fill="none" stroke-linecap="round" style="opacity:${incident?.7:.08+weight*.12};stroke-width:${incident?1.8:.4+weight*.5}"/>`;
    }
    const showContext = true;
    const strengths = data.points.map(point=>point.strength);
    const minStrength = Math.min(...strengths), maxStrength = Math.max(...strengths);
    const points = [...data.points].sort((a,b) => Number(enabledIds.has(a.id)) - Number(enabledIds.has(b.id)));
    for (const point of points) {
      const active = enabledIds.has(point.id);
      if (!active && !showContext) continue;
      const card = byId.get(point.id), p = locations.get(point.id);
      const radius = nodeRadius(point.strength,minStrength,maxStrength);
      const cluster = data.clusters.find(item=>item.id===point.cluster);
      if (point.id===selectedId && active) markup += `<circle class="semantic-halo" cx="${p.x}" cy="${p.y}" r="${radius+5}"/>`;
      markup += `<circle class="semantic-point ${active ? 'active' : 'inactive'}" data-risk="${escape(point.id)}" aria-label="${escape(point.id + ': ' + card.L4_Name_en)}" cx="${p.x}" cy="${p.y}" r="${radius}" fill="${escape(point.color)}"/>`;
    }
    markup += '</g><g id="semantic-label-layer"></g>';
    svg.innerHTML = markup;
    transformNetwork();
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
    if (button) {selectedId=button.dataset.card; draw(); showInlineCard(byId.get(selectedId));}
  });
  get('semantic-plot').addEventListener('click', event => {
    if (drag?.moved) {drag=null; return;}
    const point = event.target.closest('[data-risk]');
    if (point && enabledIds.has(point.dataset.risk)) {selectedId=point.dataset.risk; draw(); showInlineCard(byId.get(selectedId)); return;}
    const svg = get('semantic-plot'), bounds = svg.getBoundingClientRect(), box = svg.viewBox.baseVal;
    const x = ((event.clientX - bounds.left) / bounds.width * box.width - pan.x - box.width/2)/(zoom*baseZoom)+box.width/2;
    const y = ((event.clientY - bounds.top) / bounds.height * box.height - pan.y - box.height/2)/(zoom*baseZoom)+box.height/2;
    let nearest, distance = window.matchMedia('(pointer:coarse)').matches ? 22 : 10;
    for (const id of enabledIds) {
      const location = locations.get(id), current = Math.hypot(location.x-x, location.y-y);
      if (current < distance) {nearest = id; distance = current;}
    }
    if (nearest) {selectedId=nearest; draw(); showInlineCard(byId.get(nearest));}
  });
  get('semantic-plot').addEventListener('pointermove', event => {
    const point = event.target.closest('[data-risk]'), tooltip = get('semantic-tooltip');
    if (!point || !enabledIds.has(point.dataset.risk)) {tooltip.hidden = true; return;}
    const card = byId.get(point.dataset.risk);
    const node=data.points.find(item=>item.id===card.L4_ID), cluster=data.clusters.find(item=>item.id===node.cluster);
    tooltip.innerHTML = `<strong>${escape(card.L4_Name_en)}</strong><span>${escape(card.L4_ID)} · ${escape(card.L1_Name_en)} · ${escape(card.L3_Name_en)}</span><span>L3: ${escape(cluster.name)} · ${node.degree} links · Weighted degree: ${node.strength.toFixed(3)}</span><span>Click to open the risk card</span>`;
    tooltip.hidden = false;
    const bounds = get('semantic-plot').parentElement.getBoundingClientRect();
    tooltip.style.left = `${Math.max(8, Math.min(event.clientX-bounds.left+14, bounds.width-tooltip.offsetWidth-8))}px`;
    tooltip.style.top = `${Math.max(8, Math.min(event.clientY-bounds.top+14, bounds.height-tooltip.offsetHeight-8))}px`;
  });
  get('semantic-plot').addEventListener('pointerleave', () => {get('semantic-tooltip').hidden = true;});
  function transformNetwork() {
    const layer=get('semantic-network-layer'), svg=get('semantic-plot');
    if (!layer) return;
    const box=svg.viewBox.baseVal;
    layer.setAttribute('transform',`translate(${pan.x+box.width/2},${pan.y+box.height/2}) scale(${zoom*baseZoom}) translate(${-box.width/2},${-box.height/2})`);
    svg.dataset.zoom=String(zoom);
    renderNodeLabels();
  }
  function renderNodeLabels() {
    const svg=get('semantic-plot'), layer=get('semantic-label-layer');
    if (!layer) return;
    const {width,height}=svg.viewBox.baseVal;
    const context=document.createElement('canvas').getContext('2d');
    context.font='650 13px system-ui';
    const boxes=[], strengths=data.points.map(point=>point.strength);
    let markup='';
    const onScreen=data.points.filter(point=>{
      const p=locations.get(point.id),x=pan.x+width/2+(p.x-width/2)*zoom*baseZoom,y=pan.y+height/2+(p.y-height/2)*zoom*baseZoom;
      return x>=12&&x<=width-12&&y>=12&&y<=height-12;
    });
    for (const point of labelCandidates(onScreen,enabledIds,zoom)) {
      const p=locations.get(point.id);
      const x=pan.x+width/2+(p.x-width/2)*zoom*baseZoom;
      const y=pan.y+height/2+(p.y-height/2)*zoom*baseZoom;
      if(x<12||x>width-12||y<12||y>height-12) continue;
      const words=byId.get(point.id).L4_Name_en.split(/\s+/), lines=[];
      let line='';
      for(const word of words){
        if(context.measureText((line+' '+word).trim()).width>(zoom>=3.5?260:220) && line){lines.push(line);line=word;}else line=(line+' '+word).trim();
      }
      if(line)lines.push(line);
      const lineLimit=zoom>=3.5?3:2;
      if(lines.length>lineLimit){lines.splice(lineLimit);lines[lineLimit-1]=lines[lineLimit-1].replace(/\s+\S*$/,'')+'…';}
      const w=Math.max(...lines.map(text=>context.measureText(text).width))+10, h=lines.length*17+8;
      const r=nodeRadius(point.strength,Math.min(...strengths),Math.max(...strengths))*zoom*baseZoom+7;
      const placements=[{x:x+r,y:y-h/2},{x:x-r-w,y:y-h/2},{x:x-w/2,y:y-r-h},{x:x-w/2,y:y+r},
                        {x:x+r,y:y-r-h},{x:x-r-w,y:y-r-h},{x:x+r,y:y+r},{x:x-r-w,y:y+r}];
      const box=placements.map(pos=>({...pos,w,h})).find(b=>b.x>=8&&b.y>=8&&b.x+w<=width-8&&b.y+h<=height-8&&
        !boxes.some(other=>b.x<other.x+other.w+6&&b.x+b.w+6>other.x&&b.y<other.y+other.h+6&&b.y+b.h+6>other.y));
      if(!box)continue;
      boxes.push(box);
      const endX=Math.max(box.x,Math.min(x,box.x+w)),endY=Math.max(box.y,Math.min(y,box.y+h));
      markup+=`<g class="semantic-node-label" data-risk="${escape(point.id)}" role="button" tabindex="0" aria-label="Open risk card: ${escape(byId.get(point.id).L4_Name_en)}"><line x1="${x}" y1="${y}" x2="${endX}" y2="${endY}"/>${lines.map((text,i)=>`<text x="${box.x+5}" y="${box.y+17+i*17}">${escape(text)}</text>`).join('')}</g>`;
    }
    layer.innerHTML=markup;
  }
  function zoomAt(factor,x,y){
    const svg=get('semantic-plot'),box=svg.viewBox.baseVal;
    const next=zoomViewport(zoom,pan,factor,{x,y},{x:box.width/2,y:box.height/2});
    zoom=next.zoom;pan=next.pan;transformNetwork();get('semantic-tooltip').hidden=true;
  }
  get('semantic-plot').setAttribute('tabindex','0');
  get('semantic-plot').setAttribute('aria-describedby','semantic-navigation-help');
  get('semantic-plot').addEventListener('wheel',event=>{
    if(!data)return;
    event.preventDefault();
    const svg=get('semantic-plot'),bounds=svg.getBoundingClientRect(),box=svg.viewBox.baseVal;
    const units=event.deltaMode===1?16:event.deltaMode===2?bounds.height:1;
    const delta=Math.max(-200,Math.min(200,event.deltaY*units));
    zoomAt(Math.exp(-delta*.003),(event.clientX-bounds.left)*box.width/bounds.width,
           (event.clientY-bounds.top)*box.height/bounds.height);
  },{passive:false});
  get('semantic-plot').addEventListener('dblclick',event=>{
    if(event.target.closest('[data-risk]'))return;
    zoom=1;pan={x:0,y:0};transformNetwork();
  });
  get('semantic-plot').addEventListener('pointerdown',event=>{
    if(event.target.closest('[data-risk]') || event.pointerType==='touch') return;
    drag={x:event.clientX,y:event.clientY,px:pan.x,py:pan.y,moved:false};
    event.currentTarget.setPointerCapture(event.pointerId);
  });
  get('semantic-plot').addEventListener('pointermove',event=>{
    if(!drag || !event.buttons) return;
    const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
    if(Math.hypot(dx,dy)>4) drag.moved=true;
    pan={x:drag.px+dx,y:drag.py+dy};transformNetwork();
  });
  get('semantic-plot').addEventListener('keydown',event=>{
    if(['+','=','-','Home'].includes(event.key)){
      event.preventDefault();
      const box=get('semantic-plot').viewBox.baseVal;
      if(event.key==='Home'){zoom=1;pan={x:0,y:0};transformNetwork();}
      else zoomAt(event.key==='-'?1/1.25:1.25,box.width/2,box.height/2);
      return;
    }
    const point=event.target.closest('.semantic-node-label[data-risk]');
    if(point && ['Enter',' '].includes(event.key)){event.preventDefault();selectedId=point.dataset.risk;draw();showInlineCard(byId.get(selectedId));}
  });
  new ResizeObserver(() => {if (data && !get('semantic-space').hidden) draw();}).observe(get('semantic-plot').parentElement);
  window.addEventListener('hashchange',()=>{
    if(location.hash==='#semantic-space' && get('semantic-space').hidden) switchTab(true);
    else if(['#explore','#taxonomy-panel'].includes(location.hash) && get('explore').hidden) switchTab(false);
  });
  if (['#explore','#taxonomy-panel'].includes(location.hash)) switchTab(false);
  else if (!location.hash || location.hash === '#semantic-space') switchTab(true);
  else load();
})();
