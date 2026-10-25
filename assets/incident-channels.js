(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const fmt = value => Number(value).toLocaleString('en-US');
  const percent = value => `${(value*100).toFixed(1)}%`;
  const domainNames = {L1_G:'General AI',L1_A:'Agentic AI',L1_P:'Physical AI'};
  let data, selected = null;
  const zoom = {AIM:{k:1,x:0,y:0},AIID:{k:1,x:0,y:0}};
  const channelMaps = {}, allCards = new Map();
  let focusPositions = {};
  function radius(degree) { return Math.sqrt(16+(289-16)*degree/data.max_degree); }
  function edgePath(p,q) {
    const dx=q[0]-p[0],dy=q[1]-p[1];
    return `M ${p[0]} ${p[1]} Q ${(p[0]+q[0])/2-dy*.22} ${(p[1]+q[1])/2+dx*.22} ${q[0]} ${q[1]}`;
  }
  function neighbors(channel,id) {
    return data.channels[channel].edges.filter(e=>e.source===id||e.target===id).map(e=>({...e,id:e.source===id?e.target:e.source})).sort((a,b)=>b.count-a.count||a.id.localeCompare(b.id));
  }
  function buildFocus() {
    if(!selected)return;
    const ids=new Set([selected]);
    for(const channel of ['AIM','AIID'])neighbors(channel,selected).slice(0,20).forEach(e=>ids.add(e.id));
    const surrounding=[...ids].filter(id=>id!==selected).sort((a,b)=>allCards.get(a).domain.localeCompare(allCards.get(b).domain)||a.localeCompare(b));
    focusPositions={[selected]:[600,340]};
    surrounding.forEach((id,i)=>{
      const angle=-Math.PI/2+2*Math.PI*i/surrounding.length;
      focusPositions[id]=[600+475*Math.cos(angle),340+260*Math.sin(angle)];
    });
  }
  function view(channel) {
    const c=data.channels[channel],mode=byId('incident-view').value;
    if(selected){
      const ids=new Set(Object.keys(focusPositions).filter(id=>channelMaps[channel].has(id)));
      return {nodes:c.nodes.filter(n=>ids.has(n.id)),edges:c.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),positions:focusPositions,label:'Focused neighborhood'};
    }
    if(mode==='all')return {nodes:c.nodes,edges:c.edges,positions:data.layouts.all,label:'Full channel network'};
    const ids=new Set(c.overview.ids),links=new Set(c.overview.edges.map(p=>p.join('|')));
    return {nodes:c.nodes.filter(n=>ids.has(n.id)),edges:c.edges.filter(e=>links.has([e.source,e.target].join('|'))),positions:data.layouts.overview,label:'Overview'};
  }
  function matches(node){
    const query=byId('incident-search').value.trim().toLowerCase(),domain=byId('incident-domain').value;
    return (!domain||node.domain===domain)&&(!query||`${node.id} ${node.name} ${node.name_ko} ${node.definition}`.toLowerCase().includes(query));
  }
  function renderGraph(channel){
    const graph=view(channel),panel=byId(`panel-${channel}`),group=panel.querySelector('.network-content');
    const neighboring=selected?new Set(neighbors(channel,selected).map(n=>n.id)):null;
    const opacity=node=>selected?(node.id===selected||neighboring.has(node.id)?1:.1):matches(node)?1:.12;
    let markup='';
    const sortedEdges=[...graph.edges].sort((a,b)=>a.count-b.count);
    for(const e of sortedEdges){
      const p=graph.positions[e.source],q=graph.positions[e.target];
      if(!p||!q)continue;
      const isSelected=selected&&(e.source===selected||e.target===selected);
      const source=channelMaps[channel].get(e.source),target=channelMaps[channel].get(e.target);
      const active=selected?isSelected:matches(source)&&matches(target);
      const strength=Math.sqrt(e.per_1000/data.max_edge_rate);
      markup+=`<path class="incident-edge" d="${edgePath(p,q)}" style="stroke-width:${.45+3*strength};opacity:${active?(isSelected?.72:.17+.37*strength):.035};${isSelected?'stroke:#455a7b':''}"/>`;
    }
    for(const node of [...graph.nodes].sort((a,b)=>a.degree-b.degree)){
      const pos=graph.positions[node.id];if(!pos)continue;
      const r=radius(node.degree),alpha=opacity(node);
      if(node.id===data.bridge)markup+=`<circle class="incident-halo" cx="${pos[0]}" cy="${pos[1]}" r="${r+4}" style="opacity:${alpha}"/>`;
      if(node.id===selected)markup+=`<circle class="incident-halo selected" cx="${pos[0]}" cy="${pos[1]}" r="${r+7}"/>`;
      markup+=`<circle class="incident-node" data-id="${escape(node.id)}" cx="${pos[0]}" cy="${pos[1]}" r="${r}" fill="${escape(node.color)}" opacity="${alpha}" role="button" tabindex="0" aria-pressed="${node.id===selected}" aria-label="${escape(node.id+' · '+node.name+' · '+fmt(node.activations)+' mapped incidents')}"><title>${escape(node.name)}</title></circle>`;
      if(byId('incident-labels').checked&&(selected?node.id===selected:graph.nodes.filter(matches).sort((a,b)=>b.degree-a.degree).slice(0,5).some(n=>n.id===node.id))){
        const label=node.name.length>40?node.name.slice(0,37)+'…':node.name;
        markup+=`<text class="incident-node-label" x="${pos[0]}" y="${pos[1]-r-10}" text-anchor="middle">${escape(label)}</text>`;
      }
    }
    group.innerHTML=markup;
    panel.querySelector('.display-count').textContent=`${graph.label} · ${fmt(graph.nodes.length)} cards · ${fmt(graph.edges.length)} ties`;
    for(const circle of group.querySelectorAll('.incident-node')){
      circle.addEventListener('click',()=>select(circle.dataset.id));
      circle.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(circle.dataset.id);}});
      circle.addEventListener('pointerenter',event=>showTip(channel,circle.dataset.id,event));
      circle.addEventListener('pointermove',event=>showTip(channel,circle.dataset.id,event));
      circle.addEventListener('pointerleave',()=>hideTip(channel));
      circle.addEventListener('focus',()=>showTip(channel,circle.dataset.id));
      circle.addEventListener('blur',()=>hideTip(channel));
    }
    applyZoom(channel);
  }
  function applyZoom(channel){const z=zoom[channel];byId(`panel-${channel}`).querySelector('.network-content').setAttribute('transform',`translate(${600+z.x} ${340+z.y}) scale(${z.k}) translate(-600 -340)`);}
  function showTip(channel,id,event){
    const panel=byId(`panel-${channel}`),stage=panel.querySelector('.network-stage'),tip=panel.querySelector('.incident-tip'),node=channelMaps[channel].get(id);
    tip.innerHTML=`<code>${escape(node.id)}</code><strong>${escape(node.name)}</strong><span>${escape(domainNames[node.domain])} · ${fmt(node.degree)} neighbors<br>${fmt(node.activations)} mapped incidents</span>`;
    tip.hidden=false;
    const rect=stage.getBoundingClientRect(),x=event?event.clientX-rect.left:rect.width/2,y=event?event.clientY-rect.top:rect.height/2;
    tip.style.left=`${Math.max(8,Math.min(x+14,rect.width-tip.offsetWidth-8))}px`;
    tip.style.top=`${Math.max(8,Math.min(y+14,rect.height-tip.offsetHeight-8))}px`;
  }
  function hideTip(channel){byId(`panel-${channel}`).querySelector('.incident-tip').hidden=true;}
  function select(id){
    selected=selected===id?null:id;buildFocus();
    for(const channel of ['AIM','AIID']){zoom[channel]={k:1,x:0,y:0};hideTip(channel);renderGraph(channel);}
    renderSelection();
  }
  function renderSelection(){
    const box=byId('incident-selection');
    if(!selected){box.innerHTML='<h2>Explore a risk</h2><p>Select a node or search for a card to inspect its definition and channel-specific connections.</p>';return;}
    const card=allCards.get(selected);
    box.innerHTML=`<div class="selected-meta"><code>${escape(card.id)}</code><span>${escape(domainNames[card.domain])}</span><span>${escape(card.family)}</span></div><h2>${escape(card.name)}</h2><p lang="ko">${escape(card.name_ko)}</p><p class="selected-definition">${escape(card.definition)}</p><div class="selection-channels">${['AIM','AIID'].map(channel=>{
      const node=channelMaps[channel].get(selected),links=neighbors(channel,selected);
      return `<div><h3>${channel==='AIM'?'OECD AIM':'AIID'}</h3>${node?`<p>${fmt(node.activations)} mapped incidents · ${fmt(node.degree)} distinct neighbors. Strongest co-activations follow.</p><div class="neighbor-list">${links.slice(0,5).map(n=>`<button type="button" data-neighbor="${escape(n.id)}"><span>${escape(allCards.get(n.id).name)}</span><small>${fmt(n.count)} incidents</small></button>`).join('')}</div>`:'<p>No top-three assignment in this channel.</p>'}</div>`;
    }).join('')}</div><p><button class="clear-selection" type="button">Return to channel overview</button></p>`;
    box.querySelector('.clear-selection').addEventListener('click',()=>select(selected));
    box.querySelectorAll('[data-neighbor]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.neighbor)));
  }
  function renderMatches(){
    const query=byId('incident-search').value.trim(),box=byId('incident-matches');
    if(!query){box.innerHTML='';return;}
    const found=[...allCards.values()].filter(matches).sort((a,b)=>Number(b.id.toLowerCase()===query.toLowerCase())-Number(a.id.toLowerCase()===query.toLowerCase())||b.activations-a.activations).slice(0,5);
    box.innerHTML=found.length?found.map(c=>`<button type="button" data-match="${escape(c.id)}">${escape(c.name)}</button>`).join(''):'<p>No matching activated card. Try another ID or term.</p>';
    box.querySelectorAll('[data-match]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.match)));
  }
  function mount(){
    byId('incident-networks').innerHTML=['AIM','AIID'].map(channel=>{
      const c=data.channels[channel];
      return `<section class="channel-panel" id="panel-${channel}" aria-labelledby="heading-${channel}"><div class="channel-heading"><div><h2 id="heading-${channel}">${channel==='AIM'?'OECD AIM':'AI Incident Database'}</h2><p>${channel==='AIM'?'Primary channel · news-based reporting':'Secondary channel · editorially curated'}<br>Snapshot ${c.snapshot} · event years ${c.year_min}–${c.year_max}</p></div><span class="channel-count">${fmt(c.n)} incidents</span></div><div class="network-toolbar"><span class="display-count"></span><div><button data-zoom="in" type="button" aria-label="Zoom in ${channel}">+</button><button data-zoom="out" type="button" aria-label="Zoom out ${channel}">−</button><button data-zoom="fit" type="button" aria-label="Fit ${channel} network">Fit</button></div></div><div class="network-stage"><svg viewBox="0 0 1200 680" aria-labelledby="heading-${channel}" aria-describedby="description-${channel}"><desc id="description-${channel}">Risk-card co-activation network. Colored circles represent General, Agentic, and Physical risks; larger nodes have more distinct neighbors. Curved links indicate cards retrieved for the same reported incident. Nodes are keyboard accessible.</desc><g class="network-content"></g></svg><div class="incident-tip" role="tooltip" hidden></div></div><div class="network-foot"><span><strong>${fmt(c.node_count)}</strong> activated cards</span><span><strong>${fmt(c.edge_count)}</strong> distinct ties</span><span><strong>${percent(c.cross_rate)}</strong> cross-domain incidents</span></div></section>`;
    }).join('');
    byId('incident-networks').setAttribute('aria-busy','false');
    for(const channel of ['AIM','AIID']){
      const panel=byId(`panel-${channel}`),svg=panel.querySelector('svg');let drag=null;
      panel.querySelectorAll('[data-zoom]').forEach(button=>button.addEventListener('click',()=>{
        const z=zoom[channel];if(button.dataset.zoom==='fit')zoom[channel]={k:1,x:0,y:0};else z.k=Math.max(.6,Math.min(5,z.k*(button.dataset.zoom==='in'?1.25:.8)));applyZoom(channel);
      }));
      svg.addEventListener('pointerdown',event=>{if(event.target.closest('.incident-node')||event.pointerType==='touch')return;drag={clientX:event.clientX,clientY:event.clientY,x:zoom[channel].x,y:zoom[channel].y};svg.setPointerCapture(event.pointerId);svg.classList.add('is-panning');});
      svg.addEventListener('pointermove',event=>{if(!drag)return;const rect=svg.getBoundingClientRect();zoom[channel].x=drag.x+(event.clientX-drag.clientX)*1200/rect.width;zoom[channel].y=drag.y+(event.clientY-drag.clientY)*680/rect.height;applyZoom(channel);});
      svg.addEventListener('pointerup',()=>{drag=null;svg.classList.remove('is-panning');});svg.addEventListener('pointercancel',()=>{drag=null;svg.classList.remove('is-panning');});
      svg.addEventListener('wheel',event=>{if(!(event.ctrlKey||event.metaKey))return;event.preventDefault();zoom[channel].k=Math.max(.6,Math.min(5,zoom[channel].k*(event.deltaY<0?1.1:.9)));applyZoom(channel);},{passive:false});
      renderGraph(channel);
    }
    byId('incident-network-metrics').innerHTML=`<table><caption>Full-network metrics used in the paper</caption><thead><tr><th>Channel</th><th>Cards</th><th>Ties</th><th>Cross-domain ties</th><th>Permutation O/E</th><th>Domain assortativity</th></tr></thead><tbody>${['AIM','AIID'].map(ch=>{const c=data.channels[ch];return `<tr><td>${ch}</td><td>${fmt(c.node_count)}</td><td>${fmt(c.edge_count)}</td><td>${percent(c.cross_edge_rate)}</td><td>${c.permutation_OE.toFixed(2)}</td><td>${c.assortativity.toFixed(2)}</td></tr>`;}).join('')}</tbody></table>`;
    byId('incident-data-table').innerHTML=`<table><caption>All activated cards by channel, ordered by degree</caption><thead><tr><th>Channel</th><th>Card ID</th><th>Risk name</th><th>Domain</th><th>Degree</th><th>Mapped incidents</th></tr></thead><tbody>${['AIM','AIID'].flatMap(ch=>[...data.channels[ch].nodes].sort((a,b)=>b.degree-a.degree||a.id.localeCompare(b.id)).map(n=>`<tr><td>${ch}</td><td><code>${escape(n.id)}</code></td><td>${escape(n.name)}</td><td>${escape(domainNames[n.domain])}</td><td>${fmt(n.degree)}</td><td>${fmt(n.activations)}</td></tr>`)).join('')}</tbody></table>`;
  }
  async function start(){
    try{
      const response=await fetch('data/incidents/channels/networks.json?v=20261025-channels-2');
      if(!response.ok)throw new Error('Network data unavailable');data=await response.json();
      for(const channel of ['AIM','AIID']){
        channelMaps[channel]=new Map(data.channels[channel].nodes.map(n=>[n.id,n]));
        for(const node of data.channels[channel].nodes)if(!allCards.has(node.id))allCards.set(node.id,node);
      }
      mount();
      byId('incident-search').addEventListener('input',()=>{renderMatches();for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-domain').addEventListener('change',()=>{renderMatches();for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-labels').addEventListener('change',()=>{for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-view').addEventListener('change',()=>{selected=null;for(const channel of ['AIM','AIID']){zoom[channel]={k:1,x:0,y:0};renderGraph(channel);}renderSelection();});
      byId('incident-reset').addEventListener('click',()=>{selected=null;byId('incident-search').value='';byId('incident-domain').value='';byId('incident-view').value='overview';byId('incident-labels').checked=false;renderMatches();renderSelection();for(const channel of ['AIM','AIID']){zoom[channel]={k:1,x:0,y:0};renderGraph(channel);}});
    }catch(error){byId('incident-networks').innerHTML='<p role="alert">The networks could not load. Reload this page or use the aggregate downloads under the methods section.</p>';byId('incident-networks').setAttribute('aria-busy','false');console.error(error);}
  }
  start();
})();
