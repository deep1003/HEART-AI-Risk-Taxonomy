(async()=>{
  const [metrics,comparisons]=await Promise.all([
    fetch('data/embedding_input_ablation_metrics.json').then(r=>r.json()),
    fetch('data/embedding_input_ablation_comparisons.json').then(r=>r.json())
  ]);
  const NS='http://www.w3.org/2000/svg';
  const el=(name,attrs={},text='')=>{const n=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;return n};
  const conditions=['en_title','en_title_definition','ko_title','ko_title_definition'];
  const conditionLabel={en_title:'EN title',en_title_definition:'EN title + definition',ko_title:'KO title',ko_title_definition:'KO title + definition'};
  const modelLabel={bge_m3:'BGE-M3',e5_base:'E5-base'};
  const taxonomyLabel={heart:'HEART',mit:'MIT'};
  const pct=v=>`${(100*v).toFixed(2)}%`;

  function barChart(svgId,taxonomy){
    const svg=document.getElementById(svgId), W=680,H=430,m={l:58,r:20,t:28,b:90},pw=W-m.l-m.r,ph=H-m.t-m.b,max=.65;
    [0,.1,.2,.3,.4,.5,.6].forEach(t=>{const y=m.t+ph-(t/max)*ph;svg.append(el('line',{x1:m.l,y1:y,x2:W-m.r,y2:y,class:'ablation-grid'}));svg.append(el('text',{x:m.l-10,y:y+4,'text-anchor':'end',class:'ablation-axis'},`${Math.round(t*100)}%`))});
    const groupW=pw/conditions.length,barW=32;
    conditions.forEach((c,i)=>{
      ['bge_m3','e5_base'].forEach((model,j)=>{const row=metrics.find(x=>x.taxonomy===taxonomy&&x.model===model&&x.condition===c);const x=m.l+i*groupW+groupW/2+(j?8:-barW-8),h=row.top1_accuracy/max*ph,y=m.t+ph-h;svg.append(el('rect',{x,y,width:barW,height:h,rx:4,fill:j?'#d9972f':'#3568dc'}));svg.append(el('text',{x:x+barW/2,y:y-7,'text-anchor':'middle',class:'ablation-value'},`${(100*row.top1_accuracy).toFixed(1)}`))});
      const x=m.l+i*groupW+groupW/2;const label=conditionLabel[c].split(' ');const t=el('text',{x,y:H-58,'text-anchor':'middle',class:'ablation-axis'});if(c.includes('definition')){t.append(el('tspan',{x,dy:0},`${label[0]} title +`));t.append(el('tspan',{x,dy:16},'definition'))}else t.textContent=conditionLabel[c];svg.append(t)
    });
    svg.append(el('text',{x:18,y:m.t+ph/2,transform:`rotate(-90 18 ${m.t+ph/2})`,'text-anchor':'middle',class:'ablation-axis'},'Top-1 agreement'));
  }

  function effectChart(){
    const svg=document.getElementById('definition-effect-chart'),rows=comparisons.filter(x=>x.comparison==='definition_added'),W=1100,H=560,m={l:310,r:90,t:38,b:55},pw=W-m.l-m.r,min=.10,max=.30;
    [.10,.15,.20,.25,.30].forEach(v=>{const x=m.l+(v-min)/(max-min)*pw;svg.append(el('line',{x1:x,y1:m.t,x2:x,y2:H-m.b,class:'ablation-grid'}));svg.append(el('text',{x,y:H-26,'text-anchor':'middle',class:'ablation-axis'},`${Math.round(v*100)} pp`))});
    rows.forEach((r,i)=>{const y=m.t+32+i*54,x1=m.l+(r.delta_ci95[0]-min)/(max-min)*pw,x2=m.l+(r.delta_ci95[1]-min)/(max-min)*pw,x=m.l+(r.delta_b_minus_a-min)/(max-min)*pw;svg.append(el('text',{x:m.l-18,y:y+4,'text-anchor':'end',class:'ablation-label'},`${taxonomyLabel[r.taxonomy]} · ${modelLabel[r.model]} · ${r.language.toUpperCase()}`));svg.append(el('line',{x1,y1:y,x2,y2:y,class:'ablation-ci'}));svg.append(el('circle',{cx:x,cy:y,r:7,class:'ablation-point'}));svg.append(el('text',{x:x2+12,y:y+4,class:'ablation-value'},`+${(100*r.delta_b_minus_a).toFixed(2)} pp`))});
  }

  const tbody=document.getElementById('metrics-body');
  metrics.sort((a,b)=>a.taxonomy.localeCompare(b.taxonomy)||a.model.localeCompare(b.model)||conditions.indexOf(a.condition)-conditions.indexOf(b.condition)).forEach(r=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${taxonomyLabel[r.taxonomy]}</td><td>${modelLabel[r.model]}</td><td>${conditionLabel[r.condition]}</td><td>${pct(r.top1_accuracy)}</td><td>${pct(r.top1_ci_low)}–${pct(r.top1_ci_high)}</td><td>${pct(r.top3_accuracy)}</td><td>${r.mrr.toFixed(3)}</td><td>${r.macro_f1.toFixed(3)}</td>`;tbody.append(tr)});
  barChart('heart-accuracy-chart','heart');barChart('mit-accuracy-chart','mit');effectChart();
})().catch(error=>{console.error(error);document.body.dataset.loadError='true'});
