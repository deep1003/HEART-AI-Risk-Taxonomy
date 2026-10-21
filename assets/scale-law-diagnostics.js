(() => {
  'use strict';
  const ns = 'http://www.w3.org/2000/svg';
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const fmt = (value, digits=2) => Number(value).toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits});
  const percent = value => `${fmt(100*value,1)}%`;
  let data, limit = 10;

  function logScale(value, minimum, maximum, low, high) {
    return low + (Math.log(value)-Math.log(minimum))/(Math.log(maximum)-Math.log(minimum))*(high-low);
  }

  function drawCCDF(id, metric) {
    const svg=document.getElementById(id), points=metric.ccdf.filter(item=>item.x>0&&item.p_ge_x>0);
    const width=620,height=420,left=74,right=28,top=28,bottom=64;
    const minX=Math.min(...points.map(p=>p.x)),maxX=Math.max(...points.map(p=>p.x));
    const minY=Math.min(...points.map(p=>p.p_ge_x)),maxY=1;
    const sx=x=>logScale(x,minX,maxX,left,width-right);
    const sy=y=>height-bottom-logScale(y,minY,maxY,0,height-bottom-top);
    let html='<title>Empirical complementary cumulative distribution and fitted power-law tail</title>';
    for(let i=0;i<=4;i++){
      const tx=Math.exp(Math.log(minX)+(Math.log(maxX)-Math.log(minX))*i/4),x=sx(tx);
      const ty=Math.exp(Math.log(minY)+(Math.log(maxY)-Math.log(minY))*i/4),y=sy(ty);
      html+=`<line class="chart-gridline" x1="${x}" y1="${top}" x2="${x}" y2="${height-bottom}"/><text class="chart-tick" x="${x}" y="${height-bottom+22}" text-anchor="middle">${fmt(tx,tx<10?1:0)}</text>`;
      html+=`<line class="chart-gridline" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/><text class="chart-tick" x="${left-10}" y="${y+4}" text-anchor="end">${ty>=.1?fmt(ty,2):ty.toExponential(0)}</text>`;
    }
    html+=`<line class="chart-axis" x1="${left}" y1="${height-bottom}" x2="${width-right}" y2="${height-bottom}"/><line class="chart-axis" x1="${left}" y1="${top}" x2="${left}" y2="${height-bottom}"/>`;
    html+=`<text class="chart-axis-title" x="${(left+width-right)/2}" y="${height-18}" text-anchor="middle">${metric.measurement} · log scale</text><text class="chart-axis-title" transform="translate(18 ${(top+height-bottom)/2}) rotate(-90)" text-anchor="middle">P(X ≥ x) · log scale</text>`;
    html+=`<polyline class="chart-series" points="${points.map(p=>`${sx(p.x)},${sy(p.p_ge_x)}`).join(' ')}"/>`;
    for(const p of points) html+=`<circle class="chart-point" cx="${sx(p.x)}" cy="${sy(p.p_ge_x)}" r="2.5"/>`;
    const tailFraction=metric.n_tail/data.node_count;
    const yAtXmin=points.find(p=>p.x>=metric.xmin)?.p_ge_x||tailFraction;
    const fitted=[];
    for(let i=0;i<=60;i++){
      const x=Math.exp(Math.log(metric.xmin)+(Math.log(maxX)-Math.log(metric.xmin))*i/60);
      fitted.push([sx(x),sy(yAtXmin*Math.pow(x/metric.xmin,1-metric.alpha))]);
    }
    html+=`<line class="chart-cutoff" x1="${sx(metric.xmin)}" y1="${top}" x2="${sx(metric.xmin)}" y2="${height-bottom}"/><polyline class="chart-fit" points="${fitted.map(p=>p.join(',')).join(' ')}"/><text class="chart-tick" x="${Math.min(sx(metric.xmin)+7,width-130)}" y="${top+16}">xₘᵢₙ = ${fmt(metric.xmin,metric.xmin%1?2:0)}</text>`;
    svg.innerHTML=html;
    return tailFraction;
  }

  function truncated(text,max=35){return text.length>max?`${text.slice(0,max-1)}…`:text;}
  function drawRanking(){
    const rows=data.rankings.slice(0,limit),svg=document.getElementById('ranking-chart');
    const width=1100,left=330,right=72,top=36,rowH=58,bottom=46,height=top+rows.length*rowH+bottom;
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const maxDegree=Math.max(...rows.map(r=>r.degree)),sx=x=>left+x/maxDegree*(width-left-right);
    let html='<title>Highest-connectivity L4 cards and the L1 domains of their semantic neighbours</title>';
    for(let i=0;i<=4;i++){const v=maxDegree*i/4,x=sx(v);html+=`<line class="rank-grid" x1="${x}" y1="${top-14}" x2="${x}" y2="${height-bottom+5}"/><text class="rank-axis" x="${x}" y="${height-15}" text-anchor="middle">${Math.round(v)}</text>`;}
    rows.forEach((row,index)=>{
      const y=top+index*rowH, label=truncated(row.name_en,42);
      html+=`<text class="rank-label" x="18" y="${y+17}">${index+1}. ${esc(label)}</text><text class="rank-id" x="38" y="${y+36}">${esc(row.id)} · ${esc(row.l1_name)}</text>`;
      let offset=left;
      for(const [domain,klass] of [['General AI','general'],['Agentic AI','agentic'],['Physical AI','physical']]){
        const value=row.neighbor_domains[domain],barWidth=sx(value)-left;
        if(value>0){html+=`<rect class="bar-${klass}" x="${offset}" y="${y+4}" width="${barWidth}" height="28" rx="${barWidth===sx(row.degree)-left?6:0}"><title>${esc(domain)} neighbours: ${value}</title></rect>`;offset+=barWidth;}
      }
      html+=`<text class="rank-value" x="${Math.min(sx(row.degree)+8,width-right+4)}" y="${y+23}">${row.degree}</text>`;
    });
    html+=`<text class="rank-axis" x="${(left+width-right)/2}" y="${height-2}" text-anchor="middle">Incident semantic links</text>`;
    svg.innerHTML=html;
    document.getElementById('ranking-body').innerHTML=rows.map((row,index)=>`<tr><td>${index+1}</td><td><code>${esc(row.id)}</code><span class="risk-name">${esc(row.name_en)}</span><span class="risk-name-ko" lang="ko">${esc(row.name_ko)}</span></td><td><span class="domain-pill">${esc(row.l1_name)}</span></td><td>${row.degree}</td><td>${fmt(row.strength,3)}</td><td>${percent(row.cross_domain_share)}</td></tr>`).join('');
  }

  function metricText(metric, tailFraction){
    const preference=metric.log_likelihood_ratio_powerlaw_vs_lognormal<0?'lognormal sign favoured':'power-law sign favoured';
    return `Tail n = ${metric.n_tail} (${percent(tailFraction)}), α = ${fmt(metric.alpha,2)}, KS = ${fmt(metric.ks,3)}, bootstrap p = ${fmt(metric.bootstrap_p,3)}. Power law vs lognormal R = ${fmt(metric.log_likelihood_ratio_powerlaw_vs_lognormal,3)}, Vuong p = ${fmt(metric.vuong_p,3)} (${preference}, not distinguishable).`;
  }

  async function load(){
    try{
      const response=await fetch('data/scale_law_diagnostics.json?v=20261021');
      if(!response.ok)throw new Error('Diagnostics data could not be loaded.');
      data=await response.json();
      document.getElementById('node-count').textContent=data.node_count.toLocaleString();
      document.getElementById('edge-count').textContent=data.edge_count.toLocaleString();
      document.getElementById('cross-share').textContent=percent(data.cross_domain.edge_share);
      document.getElementById('cross-domain-count').textContent=`${data.cross_domain.edge_count.toLocaleString()} of ${data.edge_count.toLocaleString()} links (${percent(data.cross_domain.edge_share)}) cross L1 domains.`;
      document.getElementById('hero-verdict').innerHTML='<span>Statistical conclusion</span><strong>Restricted tails are compatible with a power law, but the full L4 network is not established as scale free.</strong>';
      const degreeFraction=drawCCDF('degree-chart',data.degree),strengthFraction=drawCCDF('strength-chart',data.strength);
      document.getElementById('degree-result').textContent=metricText(data.degree,degreeFraction);
      document.getElementById('strength-result').textContent=metricText(data.strength,strengthFraction);
      drawRanking();
    }catch(error){
      document.getElementById('hero-verdict').innerHTML=`<span>Load error</span><strong>${esc(error.message)}</strong>`;
    }
  }

  document.querySelector('.rank-toggle').addEventListener('click',event=>{
    const button=event.target.closest('[data-limit]');if(!button||!data)return;
    limit=Number(button.dataset.limit);
    document.querySelectorAll('[data-limit]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
    drawRanking();
  });
  load();
})();
