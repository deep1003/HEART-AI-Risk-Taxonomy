(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
  const fmt = value => Number(value).toLocaleString('en-US');
  const percent = value => `${(value*100).toFixed(1)}%`;
  const domainPalettes = {L1_G:['#2546b8','#3155cc','#4263eb','#5878e4','#7390ee'],L1_A:['#a94f0c','#bf6010','#d87518','#e58c33','#eda451'],L1_P:['#126438','#187843','#16854b','#29995d','#43ac72']};
  function domainColor(node){
    const family=node.id.replace(/_[^_]+$/,'');
    const hash=Array.from(family).reduce((value,char)=>(value*31+char.charCodeAt(0))>>>0,0);
    const palette=domainPalettes[node.domain];return palette[hash%palette.length];
  }
  const domainNames = {L1_G:'General AI',L1_A:'Agentic AI',L1_P:'Physical AI'};
  let data, selected = null, activeChannel = 'AIID', incidentLimit = 15, selectionToken = 0;
  const incidentCache = new Map();
  let annualData;
  const selectedYear={AIM:null,AIID:null};
  function channelData(channel){
    if(selectedYear[channel]===null)return data.channels[channel];
    return annualData[channel].years[selectedYear[channel]]||{n:0,nodes:[],edges:[],node_count:0,edge_count:0,cross_rate:0,overview:{ids:[],edges:[]}};
  }
  const baseZoom = 1.25;
  const defaultZoom = channel => ({k:baseZoom,x:channel==='AIM'?-45:-35,y:channel==='AIM'?-40:-30});
  const zoom = {AIM:defaultZoom('AIM'),AIID:defaultZoom('AIID')};
  const channelMaps = {}, allCards = new Map();
  function radius(activations, channel) {
    return Math.sqrt(6.25+317.75*activations/data.max_activations)*(channel==='AIID'?1.25:1);
  }
  const aimLayouts = new Map();
  function aimPositions(mode,nodes,original){
    if(aimLayouts.has(mode))return aimLayouts.get(mode);
    const ordered=[...nodes].sort((a,b)=>a.id.localeCompare(b.id));
    const points=Object.fromEntries(ordered.map(n=>[n.id,[(original[n.id][0]-600)*1.12+600,(original[n.id][1]-340)*1.12+340]]));
    for(let pass=0;pass<100;pass++){
      for(let i=0;i<ordered.length;i++)for(let j=i+1;j<ordered.length;j++){
        const a=ordered[i],b=ordered[j],p=points[a.id],q=points[b.id];
        const dx=q[0]-p[0],dy=q[1]-p[1],distance=Math.hypot(dx,dy)||.001;
        const minimum=radius(a.activations)+radius(b.activations)+20;
        if(distance>=minimum)continue;
        const shift=(minimum-distance)*.35,ux=dx/distance,uy=dy/distance;
        p[0]-=ux*shift;p[1]-=uy*shift;q[0]+=ux*shift;q[1]+=uy*shift;
      }
    }
    aimLayouts.set(mode,points);return points;
  }
  function edgePath(p,q) {
    const dx=q[0]-p[0],dy=q[1]-p[1];
    return `M ${p[0]} ${p[1]} Q ${(p[0]+q[0])/2-dy*.22} ${(p[1]+q[1])/2+dx*.22} ${q[0]} ${q[1]}`;
  }
  function view(channel) {
    const c=channelData(channel),mode=byId('incident-view').value,layout=selectedYear[channel]===null?data.layouts.overview:data.layouts.all,key=mode+'-'+(selectedYear[channel]||'all');
    if(mode==='all')return {nodes:c.nodes,edges:c.edges,positions:channel==='AIM'?aimPositions(key,c.nodes,data.layouts.all):data.layouts.all,label:'Full channel network'};
    const ids=new Set(c.overview.ids),links=new Set(c.overview.edges.map(p=>p.join('|')));
    return {nodes:c.nodes.filter(n=>ids.has(n.id)),edges:c.edges.filter(e=>links.has([e.source,e.target].join('|'))),positions:channel==='AIM'?aimPositions(key,c.nodes.filter(n=>ids.has(n.id)),layout):layout,label:'Overview'};
  }
  function matches(node){
    const query=byId('incident-search').value.trim().toLowerCase(),domain=byId('incident-domain').value;
    return (!domain||node.domain===domain)&&(!query||`${node.id} ${node.name} ${node.name_ko} ${node.definition}`.toLowerCase().includes(query));
  }
  function renderGraph(channel){
    const graph=view(channel),panel=byId(`panel-${channel}`),group=panel.querySelector('.network-content');
    const opacity=node=>matches(node)?1:.12;
    let markup='';
    const sortedEdges=[...graph.edges].sort((a,b)=>a.count-b.count);
    for(const e of sortedEdges){
      const p=graph.positions[e.source],q=graph.positions[e.target];
      if(!p||!q)continue;
      const source=channelMaps[channel].get(e.source),target=channelMaps[channel].get(e.target);
      const active=matches(source)&&matches(target);
      const strength=Math.sqrt(e.per_1000/data.max_edge_rate);
      markup+=`<path class="incident-edge" d="${edgePath(p,q)}" style="stroke-width:${.45+3*strength};opacity:${active?.17+.37*strength:.035}"/>`;
    }
    for(const node of [...graph.nodes].sort((a,b)=>a.degree-b.degree)){
      const pos=graph.positions[node.id];if(!pos)continue;
      const r=radius(node.activations,channel),alpha=opacity(node);
      if(node.id===data.bridge)markup+=`<circle class="incident-halo" cx="${pos[0]}" cy="${pos[1]}" r="${r+4}" style="opacity:${alpha}"/>`;
      if(node.id===selected)markup+=`<circle class="incident-halo selected" cx="${pos[0]}" cy="${pos[1]}" r="${r+7}"/>`;
      markup+=`<circle class="incident-node" data-id="${escape(node.id)}" cx="${pos[0]}" cy="${pos[1]}" r="${r}" fill="${escape(node.color)}" opacity="${alpha}" role="button" tabindex="0" aria-pressed="${node.id===selected}" aria-label="${escape(node.id+' · '+node.name+' · '+fmt(node.activations)+' observed incidents')}"><title>${escape(node.name)}</title></circle>`;

    }
    group.innerHTML=markup+'<g class="network-labels" aria-hidden="true"></g>';
    panel.querySelector('.display-count').textContent=`${graph.label} · ${fmt(graph.nodes.length)} cards · ${fmt(graph.edges.length)} ties`;
    for(const circle of group.querySelectorAll('.incident-node')){
      circle.addEventListener('click',()=>select(circle.dataset.id,channel));
      circle.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(circle.dataset.id,channel);}});
      circle.addEventListener('pointerenter',event=>showTip(channel,circle.dataset.id,event));
      circle.addEventListener('pointermove',event=>showTip(channel,circle.dataset.id,event));
      circle.addEventListener('pointerleave',()=>hideTip(channel));
      circle.addEventListener('focus',()=>showTip(channel,circle.dataset.id));
      circle.addEventListener('blur',()=>hideTip(channel));
    }
    updateChannelStats(channel);
    applyZoom(channel);
  }
  function applyZoom(channel){
    const z=zoom[channel],panel=byId(`panel-${channel}`);
    panel.querySelector('.network-content').setAttribute('transform',`translate(${600+z.x} ${340+z.y}) scale(${z.k}) translate(-600 -340)`);
    panel.querySelector('.zoom-level').textContent=`${Math.round(z.k/baseZoom*100)}%`;
    renderLabels(channel);
  }
  function wrapName(name,limit=30){
    const lines=[];let line='';
    for(const word of name.split(/\s+/)){if(line&&(line+' '+word).length>limit){lines.push(line);line=word;}else line+=(line?' ':'')+word;}
    if(line)lines.push(line);return lines;
  }
  function renderLabels(channel){
    const panel=byId(`panel-${channel}`),layer=panel.querySelector('.network-labels'),z=zoom[channel];
    if(!layer)return;
    if(z.k<=1.05&&!byId('incident-labels').checked){layer.innerHTML='';return;}
    const graph=view(channel),svg=panel.querySelector('svg'),rect=svg.getBoundingClientRect();
    const scale=Math.max(.1,Math.min(rect.width/1200,rect.height/680)),font=12/(scale*z.k),lineHeight=font*1.18;
    const screen=p=>[(p[0]-600)*z.k+600+z.x,(p[1]-340)*z.k+340+z.y];
    const visible=graph.nodes.filter(n=>{const p=screen(graph.positions[n.id]);return p[0]>0&&p[0]<1200&&p[1]>0&&p[1]<680;});
    const ranked=[...visible].filter(n=>matches(n)||n.id===selected).sort((a,b)=>Number(b.id===selected)-Number(a.id===selected)||b.degree-a.degree||a.id.localeCompare(b.id));
    const limit=z.k>=2.8?ranked.length:z.k>=1.8?35:12,placed=[];let markup='',count=0;
    for(const node of ranked){
      if(count>=limit)break;
      const p=graph.positions[node.id],r=radius(node.activations,channel),lines=wrapName(node.name),w=Math.max(...lines.map(l=>l.length))*font*.55+font*.6,h=lines.length*lineHeight+font*.4,gap=font*.65;
      const options=[{x:p[0]+r+gap,y:p[1]-h/2},{x:p[0]-w/2,y:p[1]-r-gap-h},{x:p[0]-r-gap-w,y:p[1]-h/2},{x:p[0]-w/2,y:p[1]+r+gap}];
      const box=options.find(b=>{
        const lo=screen([b.x,b.y]),hi=screen([b.x+w,b.y+h]);
        if(lo[0]<8||lo[1]<8||hi[0]>1192||hi[1]>672)return false;
        if(placed.some(q=>b.x<q.x+q.w&&b.x+w>q.x&&b.y<q.y+q.h&&b.y+h>q.y))return false;
        return !visible.some(other=>{const q=graph.positions[other.id],rr=radius(other.activations,channel)+font*.2;const x=Math.max(b.x,Math.min(q[0],b.x+w)),y=Math.max(b.y,Math.min(q[1],b.y+h));return Math.hypot(x-q[0],y-q[1])<rr;});
      });
      if(!box)continue;placed.push({...box,w,h});count++;
      markup+=`<text class="incident-node-label" data-label-id="${escape(node.id)}" x="${box.x}" y="${box.y+font}" style="font-size:${font}px;stroke-width:${font*.3}px">${lines.map((line,i)=>`<tspan x="${box.x}" dy="${i?lineHeight:0}">${escape(line)}</tspan>`).join('')}</text>`;
    }
    layer.innerHTML=markup;
  }
  function showTip(channel,id,event){
    const panel=byId(`panel-${channel}`),stage=panel.querySelector('.network-stage'),tip=panel.querySelector('.incident-tip'),node=channelMaps[channel].get(id);
    tip.innerHTML=`<code>${escape(node.id)}</code><strong>${escape(node.name)}</strong><span>${escape(domainNames[node.domain])} · ${fmt(node.degree)} neighbors<br>${fmt(node.activations)} observed incidents</span>`;
    tip.hidden=false;
    const rect=stage.getBoundingClientRect(),x=event?event.clientX-rect.left:rect.width/2,y=event?event.clientY-rect.top:rect.height/2;
    tip.style.left=`${Math.max(8,Math.min(x+14,rect.width-tip.offsetWidth-8))}px`;
    tip.style.top=`${Math.max(8,Math.min(y+14,rect.height-tip.offsetHeight-8))}px`;
  }
  function hideTip(channel){byId(`panel-${channel}`).querySelector('.incident-tip').hidden=true;}
  function select(id,channel=activeChannel){
    selected=id;activeChannel=channelMaps[channel].has(id)?channel:(channel==='AIM'?'AIID':'AIM');incidentLimit=15;
    byId('incident-workspace').classList.add('has-selection');byId('incident-selection').scrollTop=0;
    for(const ch of ['AIM','AIID']){hideTip(ch);renderGraph(ch);}
    renderSelection();
  }
  function clearSelection(){
    selectionToken++;selected=null;byId('incident-workspace').classList.remove('has-selection');renderOverview();
    for(const ch of ['AIM','AIID'])renderGraph(ch);
  }
  function renderOverview(){
    const box=byId('incident-selection');
    const descriptions={L1_G:'Model outputs, information, privacy, and broader social harms.',L1_A:'Planning, tool use, autonomous action, and human oversight.',L1_P:'Physical sensing, control, hardware, and embodied interaction.'};
    const domainRows=['L1_G','L1_A','L1_P'].map(domain=>{
      const colors=[...new Set([...allCards.values()].filter(n=>n.domain===domain).map(n=>n.color))].sort();
      const samples=Array.from({length:Math.min(9,colors.length)},(_,i)=>colors[Math.round(i*(colors.length-1)/Math.max(1,Math.min(9,colors.length)-1))]);
      return `<div class="overview-domain"><h3><i style="background:${data.domain_colors[domain]}"></i>${domainNames[domain]}<span>${data.inventory.domains[domain]} cards</span></h3><p>${descriptions[domain]}</p><div class="overview-shades" aria-label="${domainNames[domain]} L3 color examples">${samples.map(color=>`<i style="background:${color}"></i>`).join('')}</div></div>`;
    }).join('');
    box.innerHTML=`<div class="selection-heading"><div><span>AI risk incidents</span><h2>Overview</h2></div></div><div class="selection-body overview-body"><p class="overview-instruction">Select a node to read its L4 risk name and the related incident titles, descriptions, and source links here.</p><div class="overview-inventory"><strong>622</strong><span>L4 risk cards · 55 L3 families</span></div><h3 class="overview-section-title">Node colors</h3>${domainRows}<p class="overview-color-note">Blue identifies General AI, orange identifies Agentic AI, and green identifies Physical AI. Shades distinguish L3 families within each domain and do not encode severity, occurrence rates, or semantic distance.</p><h3 class="overview-section-title">Reading the networks</h3><ul class="overview-encodings"><li><strong>Node size</strong><span>Larger circles have more observed incident records. Each graph uses a count-to-area scale with a minimum visible size. AIID node radii are enlarged by 25% for readability, so compare counts in the detail panel across channels. Counts refer to records associated with each card, not population incidence rates.</span></li><li><strong>Curved links</strong><span>Cards retrieved for the same incident. Thicker links indicate more co-activations per 1,000 channel incidents.</span></li><li><strong class="overview-bridge-title"><i></i>Red ring</strong><span>Automated-driving control-transfer failure, the highlighted bridge between domains.</span></li><li><strong>Zoom</strong><span>Use + and − to enlarge or reduce the graph. Key risk names are visible at the default 100% view; more names appear as you zoom in.</span></li></ul><p class="overview-color-note">The two graphs keep OECD AIM and AIID separate. Their records reveal reported candidate risks rather than population incidence or causal pathways.</p></div>`;
    box.scrollTop=0;
  }
  async function incidentData(channel){
    if(!incidentCache.has(channel))incidentCache.set(channel,fetch(`data/incidents/channels/incidents-${channel}.json?v=20261025-details-1`).then(r=>{if(!r.ok)throw new Error('Incident records unavailable');return r.json();}).catch(error=>{incidentCache.delete(channel);throw error;}));
    return incidentCache.get(channel);
  }
  async function renderSelection(){
    if(!selected)return;
    const id=selected,ch=activeChannel,token=++selectionToken,card=allCards.get(id),box=byId('incident-selection'),oldScroll=box.scrollTop;
    const metrics=channelMaps[ch].get(id);
    box.innerHTML=`<div class="selection-heading"><div><span>Selected L4 risk</span><h2>${escape(card.name)}</h2></div><button type="button" class="close-selection" aria-label="Show overview">Overview</button></div><div class="selection-body"><div class="selected-meta"><code>${escape(card.id)}</code><span>${escape(domainNames[card.domain])}</span></div><p class="selected-korean" lang="ko">${escape(card.name_ko)}</p><details class="selected-definition"><summary>Risk definition</summary><p>${escape(card.definition)}</p></details><div class="incident-source-tabs" role="group" aria-label="Incident source">${['AIM','AIID'].map(channel=>{const n=channelMaps[channel].get(id)?.activations||0;return `<button type="button" data-source="${channel}" aria-pressed="${channel===ch}" ${n?'':'disabled'}>${channel==='AIM'?'OECD AIM':'AIID'} <span>${fmt(n)}</span></button>`;}).join('')}</div><div class="selected-centrality" aria-label="Selected-period network centrality"><div><span>Degree centrality</span><strong>${metrics.degree_centrality.toFixed(4)} <em class="centrality-rank">#${metrics.degree_rank} / ${channelData(ch).node_count}</em></strong><small>${fmt(metrics.degree)} distinct neighbors</small></div><div><span>Betweenness centrality</span><strong>${metrics.betweenness_centrality.toFixed(4)} <em class="centrality-rank">#${metrics.betweenness_rank} / ${channelData(ch).node_count}</em></strong><small>Normalized shortest-path score</small></div></div><p class="centrality-note">Calculated on the ${selectedYear[ch]||'all-years'} ${ch==='AIM'?'OECD AIMD':'AIID'} network of ${fmt(channelData(ch).node_count)} activated cards, using unweighted links. Ranks are descending; ties share the same rank.</p><div id="incident-list"><p role="status">Loading source incident summaries…</p></div></div>`;
    box.querySelector('.close-selection').addEventListener('click',clearSelection);
    box.querySelectorAll('[data-source]').forEach(button=>button.addEventListener('click',()=>{activeChannel=button.dataset.source;incidentLimit=15;box.scrollTop=0;renderSelection();}));
    try{
      const source=await incidentData(ch);if(token!==selectionToken||selected!==id||activeChannel!==ch)return;
      const ids=(source.by_card[id]||[]).filter(i=>selectedYear[ch]===null||Number(source.records[i].date.slice(0,4))===selectedYear[ch]),shown=ids.slice(0,incidentLimit),list=byId('incident-list');
      list.innerHTML=`<p class="incident-list-summary">${fmt(ids.length)} observed incident${ids.length===1?'':'s'} · newest first</p><ol class="incident-record-list">${shown.map(index=>{const record=source.records[index];return `<li><article><time datetime="${escape(record.date)}">${escape(record.date||'Date not supplied')}</time><h3><a href="${escape(record.url)}" target="_blank" rel="noopener noreferrer">${escape(record.title)} <span aria-hidden="true">↗</span></a></h3><p class="incident-record-description">${escape(record.description)}</p>${record.description.length>260?'<button type="button" class="expand-incident" aria-expanded="false">Read full description</button>':''}<a class="incident-source-link" href="${escape(record.url)}" target="_blank" rel="noopener noreferrer">${ch==='AIM'?'View on OECD AIM':'View on AIID'} ↗</a></article></li>`;}).join('')}</ol><p class="incident-list-progress">Showing ${fmt(shown.length)} of ${fmt(ids.length)}</p>${shown.length<ids.length?'<button class="load-more-incidents" type="button">Show 15 more incidents</button>':''}<p class="incident-attribution">${escape(source.attribution)}</p>`;
      list.querySelectorAll('.expand-incident').forEach(button=>button.addEventListener('click',()=>{const expanded=button.getAttribute('aria-expanded')!=='true';button.setAttribute('aria-expanded',String(expanded));button.previousElementSibling.classList.toggle('expanded',expanded);button.textContent=expanded?'Collapse description':'Read full description';}));
      list.querySelector('.load-more-incidents')?.addEventListener('click',()=>{incidentLimit+=15;renderSelection();});
      if(incidentLimit>15)box.scrollTop=oldScroll;
    }catch(error){if(token===selectionToken)byId('incident-list').innerHTML='<p role="alert">Incident summaries could not load. Select the card again to retry.</p>';}
  }
  function renderMatches(){
    const query=byId('incident-search').value.trim(),box=byId('incident-matches');
    if(!query){box.innerHTML='';return;}
    const found=[...allCards.values()].filter(matches).sort((a,b)=>Number(b.id.toLowerCase()===query.toLowerCase())-Number(a.id.toLowerCase()===query.toLowerCase())||b.activations-a.activations).slice(0,5);
    box.innerHTML=found.length?found.map(c=>`<button type="button" data-match="${escape(c.id)}">${escape(c.name)}</button>`).join(''):'<p>No matching activated card. Try another ID or term.</p>';
    box.querySelectorAll('[data-match]').forEach(button=>button.addEventListener('click',()=>select(button.dataset.match)));
  }
  function updateChannelStats(channel){
    const c=channelData(channel),panel=byId(`panel-${channel}`);
    panel.querySelector('.channel-count').textContent=`${fmt(c.n)} incidents${selectedYear[channel]===null?'':' · '+selectedYear[channel]}`;
    panel.querySelector('.channel-stats').innerHTML=`<strong>${fmt(c.node_count)}</strong> activated cards · <strong>${fmt(c.edge_count)}</strong> ties · <strong>${percent(c.cross_rate)}</strong> cross-domain incidents`;
  }
  function changeYear(channel,year){
    selectedYear[channel]=year;
    channelMaps[channel]=new Map(channelData(channel).nodes.map(n=>[n.id,n]));
    clearSelection();
    renderYearNavigation(channel);renderGraph(channel);
  }
  function renderYearNavigation(channel){
    const meta=annualData[channel],years=Array.from({length:meta.max_year-meta.min_year+1},(_,i)=>meta.min_year+i),current=selectedYear[channel],peak=Math.max(...Object.values(meta.years).map(c=>c.n));
    const width=1000,step=width/years.length;
    const bars=years.map((year,i)=>{const n=meta.years[year]?.n||0,h=n/peak*65;return `<g class="year-bar" data-year="${year}" role="button" tabindex="0" aria-label="${year}, ${fmt(n)} observed incidents"><rect x="${i*step+1}" y="${70-h}" width="${Math.max(1,step-2)}" height="${Math.max(1,h)}" fill="${current===year?'#233d75':'#a7b7d2'}"/><title>${year} · ${fmt(n)} observed incidents</title>${i===0||i===years.length-1||(year%5===0&&i<years.length-2)?`<text x="${i*step+step/2}" y="87" text-anchor="middle">${year}</text>`:''}</g>`;}).join('');
    const el=byId(`panel-${channel}`).querySelector('.year-navigation');
    if(el.querySelector('input')){
      const slider=el.querySelector('input');slider.value=current===null?0:current-meta.min_year+1;slider.setAttribute('aria-valuetext',current||'All years');
      el.querySelector('output').textContent=current===null?'All years':current+' · '+fmt(channelData(channel).n)+' incidents';
      el.querySelectorAll('[data-year]').forEach(bar=>bar.querySelector('rect').setAttribute('fill',Number(bar.dataset.year)===current?'#233d75':'#a7b7d2'));return;
    }
    el.innerHTML=`<div class="year-navigation-heading"><strong>Observed incidents by year</strong><output>${current===null?'All years':current+' · '+fmt(channelData(channel).n)+' incidents'}</output><button type="button" class="all-years">All years</button></div><svg class="year-histogram" viewBox="0 0 1000 94" aria-label="${channel} annual observed incident counts">${bars}</svg><label class="year-slider-label">Year <input type="range" min="0" max="${years.length}" value="${current===null?0:current-meta.min_year+1}" step="1" aria-label="Select ${channel} year" aria-valuetext="${current||'All years'}"></label>`;
    el.querySelector('input').addEventListener('input',event=>{const value=Number(event.target.value);changeYear(channel,value===0?null:meta.min_year+value-1);});
    el.querySelector('.all-years').addEventListener('click',()=>changeYear(channel,null));
    el.querySelectorAll('[data-year]').forEach(bar=>{bar.addEventListener('click',()=>changeYear(channel,Number(bar.dataset.year)));bar.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();changeYear(channel,Number(bar.dataset.year));}});});
  }
  function mount(){
    byId('incident-networks').innerHTML=['AIID','AIM'].map(channel=>{
      const c=data.channels[channel];
      return `<section class="channel-panel" id="panel-${channel}" aria-labelledby="heading-${channel}"><div class="channel-heading"><div><h2 id="heading-${channel}">${channel==='AIM'?'OECD AIMD':'AI Incident Database (AIID)'}</h2><p>${channel==='AIM'?'Primary channel · news-based reporting':'Secondary channel · editorially curated'}<br>Snapshot ${c.snapshot} · event years ${c.year_min}–${c.year_max}</p><p class="channel-stats"></p></div><span class="channel-count">${fmt(c.n)} incidents</span></div><div class="network-toolbar"><span class="display-count"></span><div><span class="zoom-level" aria-live="polite">100%</span><button data-zoom="in" type="button" aria-label="Zoom in ${channel}">+</button><button data-zoom="out" type="button" aria-label="Zoom out ${channel}">−</button><button data-zoom="fit" type="button" aria-label="Fit ${channel} network">Fit</button></div></div><div class="network-stage"><svg viewBox="0 0 1200 680" aria-labelledby="heading-${channel}" aria-describedby="description-${channel}"><desc id="description-${channel}">Risk-card co-activation network. Colored circles represent General, Agentic, and Physical risks; larger nodes have more observed incident records. Curved links indicate cards retrieved for the same reported incident. Nodes are keyboard accessible.</desc><g class="network-content"></g></svg><div class="incident-tip" role="tooltip" hidden></div></div><div class="year-navigation" data-channel="${channel}"></div></section>`;
    }).join('');
    byId('incident-networks').setAttribute('aria-busy','false');
    for(const channel of ['AIM','AIID']){
      const panel=byId(`panel-${channel}`),svg=panel.querySelector('svg');let drag=null;
      panel.querySelectorAll('[data-zoom]').forEach(button=>button.addEventListener('click',()=>{
        const z=zoom[channel];if(button.dataset.zoom==='fit')zoom[channel]=defaultZoom(channel);else z.k=Math.max(.6,Math.min(5,z.k*(button.dataset.zoom==='in'?1.25:.8)));applyZoom(channel);
      }));
      svg.addEventListener('pointerdown',event=>{if(event.target.closest('.incident-node')||event.pointerType==='touch')return;drag={clientX:event.clientX,clientY:event.clientY,x:zoom[channel].x,y:zoom[channel].y};svg.setPointerCapture(event.pointerId);svg.classList.add('is-panning');});
      svg.addEventListener('pointermove',event=>{if(!drag)return;const rect=svg.getBoundingClientRect();zoom[channel].x=drag.x+(event.clientX-drag.clientX)*1200/rect.width;zoom[channel].y=drag.y+(event.clientY-drag.clientY)*680/rect.height;applyZoom(channel);});
      svg.addEventListener('pointerup',()=>{drag=null;svg.classList.remove('is-panning');});svg.addEventListener('pointercancel',()=>{drag=null;svg.classList.remove('is-panning');});
      svg.addEventListener('wheel',event=>{if(!(event.ctrlKey||event.metaKey))return;event.preventDefault();zoom[channel].k=Math.max(.6,Math.min(5,zoom[channel].k*(event.deltaY<0?1.1:.9)));applyZoom(channel);},{passive:false});
      renderYearNavigation(channel);
      renderGraph(channel);
    }
    byId('incident-network-metrics').innerHTML=`<table><caption>Full-network metrics used in the paper</caption><thead><tr><th>Channel</th><th>Cards</th><th>Ties</th><th>Cross-domain ties</th><th>Permutation O/E</th><th>Domain assortativity</th></tr></thead><tbody>${['AIM','AIID'].map(ch=>{const c=data.channels[ch];return `<tr><td>${ch}</td><td>${fmt(c.node_count)}</td><td>${fmt(c.edge_count)}</td><td>${percent(c.cross_edge_rate)}</td><td>${c.permutation_OE.toFixed(2)}</td><td>${c.assortativity.toFixed(2)}</td></tr>`;}).join('')}</tbody></table>`;
    byId('incident-data-table').innerHTML=`<table><caption>All activated cards by channel, ordered by degree</caption><thead><tr><th>Channel</th><th>Card ID</th><th>Risk name</th><th>Domain</th><th>Degree</th><th>Observed incident count</th></tr></thead><tbody>${['AIM','AIID'].flatMap(ch=>[...data.channels[ch].nodes].sort((a,b)=>b.degree-a.degree||a.id.localeCompare(b.id)).map(n=>`<tr><td>${ch}</td><td><code>${escape(n.id)}</code></td><td>${escape(n.name)}</td><td>${escape(domainNames[n.domain])}</td><td>${fmt(n.degree)}</td><td>${fmt(n.activations)}</td></tr>`)).join('')}</tbody></table>`;
  }
  async function start(){
    try{
      const response=await fetch('data/incidents/channels/networks.json?v=20261025-channels-17');
      if(!response.ok)throw new Error('Network data unavailable');data=await response.json();
      const yearlyResponse=await fetch('data/incidents/channels/years.json?v=20261025-years-1');
      if(!yearlyResponse.ok)throw new Error('Annual network data unavailable');annualData=await yearlyResponse.json();
      for(const meta of Object.values(annualData))for(const c of Object.values(meta.years))for(const n of c.nodes)n.color=domainColor(n);
      data.max_activations=Math.max(...Object.values(data.channels).flatMap(c=>c.nodes.map(n=>n.activations)));
      data.domain_colors={L1_G:'#4263eb',L1_A:'#d87518',L1_P:'#16854b'};
      for(const c of Object.values(data.channels))for(const node of c.nodes)node.color=domainColor(node);
      for(const c of Object.values(data.channels)){
        for(const node of c.nodes){
          node.degree_rank=1+c.nodes.filter(other=>other.degree>node.degree).length;
          const score=Number(node.betweenness_centrality.toFixed(12));
          node.betweenness_rank=1+c.nodes.filter(other=>Number(other.betweenness_centrality.toFixed(12))>score).length;
        }
      }
      for(const channel of ['AIM','AIID']){
        channelMaps[channel]=new Map(data.channels[channel].nodes.map(n=>[n.id,n]));
        for(const node of data.channels[channel].nodes)if(!allCards.has(node.id))allCards.set(node.id,node);
      }
      mount();
      renderOverview();
      window.addEventListener('resize',()=>{for(const channel of ['AIM','AIID'])renderLabels(channel);});
      byId('incident-search').addEventListener('input',()=>{renderMatches();for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-domain').addEventListener('change',()=>{renderMatches();for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-labels').addEventListener('change',()=>{for(const channel of ['AIM','AIID'])renderGraph(channel);});
      byId('incident-view').addEventListener('change',()=>{clearSelection();for(const channel of ['AIM','AIID']){zoom[channel]=defaultZoom(channel);renderGraph(channel);}});
      byId('incident-reset').addEventListener('click',()=>{clearSelection();byId('incident-search').value='';byId('incident-domain').value='';byId('incident-view').value='overview';byId('incident-labels').checked=false;renderMatches();for(const channel of ['AIM','AIID']){zoom[channel]=defaultZoom(channel);renderGraph(channel);}});
    }catch(error){byId('incident-networks').innerHTML='<p role="alert">The networks could not load. Reload this page or use the aggregate downloads under the methods section.</p>';byId('incident-networks').setAttribute('aria-busy','false');console.error(error);}
  }
  start();
})();
