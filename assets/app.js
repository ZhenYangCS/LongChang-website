/* All data comes from the frozen paper export in data/paper.js.
 * No analytics, remote runtime libraries or API calls are used.
 */
(() => {
  'use strict';
  const data = window.LONGCHANG;
  if (!data) return;
  const $ = (q, root = document) => root.querySelector(q);
  const $$ = (q, root = document) => [...root.querySelectorAll(q)];
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => value == null ? '—' : Number(value).toFixed(1);
  const metricNames = {D:'Discovery', C:'Law correctness', S:'Evidence support'};

  function wireTabs(root, choose) {
    root.addEventListener('keydown', event => {
      if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
      const tabs = $$('[role="tab"]', root);
      const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      choose(tabs[next]);
      tabs[next].focus();
    });
  }
  function selectTab(button) {
    const parent = button.closest('[role="tablist"]');
    $$('[role="tab"]', parent).forEach(tab => {
      const selected = tab === button;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
  }

  const notes = data.evidence;

  // Scene atlas.
  $('#scene-picker').innerHTML = data.scenes.map(s=>`<button id="scene-tab-${s.id}" role="tab" aria-selected="${s.id==='15'}" aria-controls="scene-detail" tabindex="${s.id==='15'?0:-1}" data-scene="${s.id}"><span>${s.id}</span>${esc(s.name)}</button>`).join('');
  function chooseScene(button) {
    const scene = data.scenes.find(s=>s.id===button.dataset.scene);
    selectTab(button);
    $('#scene-detail').setAttribute('aria-labelledby',button.id);
    $('#scene-number').textContent = `WORLD ${scene.id} / 15`;
    $('#scene-family').textContent = scene.family;
    $('#scene-name').textContent = scene.name;
    $('#scene-description').textContent = scene.description;
    $('#scene-image').src = scene.image;
    $('#scene-image').alt = `Recorded initial state of Scene ${scene.id}: ${scene.name}`;
    $('#scene-law-text').textContent = scene.law;
    $('#scene-law').open = false;
    document.dispatchEvent(new CustomEvent('longchang:scene', {detail:scene}));
  }
  $$('#scene-picker button').forEach(b=>b.addEventListener('click',()=>chooseScene(b)));
  wireTabs($('#scene-picker'),chooseScene);
  window.showWorld = id => { const button = $('#scene-tab-'+id); if(button) chooseScene(button); };
  chooseScene($('#scene-tab-01'));

  // Main comparison: shared 0–100% scale across metrics and models.
  function renderModels(metric='all') {
    const metrics = metric==='all' ? ['D','C','S'] : [metric];
    let html = '<div class="chart-axis" aria-hidden="true"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>';
    html += data.models.map(m=>`<div class="chart-model-row ${metric==='all'?'':'single'} ${m.name==='GPT-6-Astra'?'featured':''}"><div class="chart-model-label">${esc(m.name)}</div><div class="chart-lanes">${metrics.map(key=>`<div class="chart-lane" aria-label="${esc(m.name)}: ${metricNames[key]} ${fmt(m[key])}%"><i class="chart-bar metric-${key}" data-value="${m[key]}" style="width:${m[key]}%"></i><span class="chart-bar-number ${m[key]>92?'inside':''}" style="--value:${m[key]}">${fmt(m[key])}</span></div>`).join('')}</div></div>`).join('');
    $('#model-chart').innerHTML = html;
    $$('[data-metric]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.metric===metric)));
  }
  $$('[data-metric]').forEach(b=>b.addEventListener('click',()=>renderModels(b.dataset.metric)));
  renderModels();

  function renderHeatmap(metric='D') {
    const scenes = data.scenes.filter(s=>s.id!=='01');
    $('#heatmap').innerHTML = `<table class="heatmap-table"><caption class="sr-only">${metricNames[metric]}: passing runs out of three, by model and scene</caption><thead><tr><th scope="col">Model / Scene</th>${scenes.map(s=>`<th scope="col" title="${esc(s.name)}">${s.id}</th>`).join('')}</tr></thead><tbody>${data.models.map(m=>`<tr><th scope="row">${esc(m.name)}</th>${scenes.map(s=>{const v=m.scenes[s.id][metric];const label=`${m.name} · Scene ${s.id}: ${s.name}. ${metricNames[metric]}: ${v} of 3 runs (${(v/3*100).toFixed(1)}%).`;return `<td><button class="heat-cell" ${m.name==='GPT-6-Astra'&&metric==='D'&&v>0?`data-success-scene="${s.id}"`:""} data-level="${v}" data-tooltip="${esc(label)}" aria-label="${esc(label)}">${v||'·'}</button></td>`;}).join('')}</tr>`).join('')}</tbody></table>`;
    $$('[data-heat]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.heat===metric)));
  }
  $$('[data-heat]').forEach(b=>b.addEventListener('click',()=>renderHeatmap(b.dataset.heat)));
  renderHeatmap();
  const tooltip = $('#chart-tooltip');
  function showTooltip(target,x,y) {
    tooltip.textContent = target.dataset.tooltip;
    tooltip.hidden = false;
    const r = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.max(10,Math.min(x+12,innerWidth-r.width-12))}px`;
    tooltip.style.top = `${Math.max(10,Math.min(y+12,innerHeight-r.height-12))}px`;
  }
  document.addEventListener('pointerover',event=>{const target=event.target.closest('[data-tooltip]');if(target)showTooltip(target,event.clientX,event.clientY);});
  document.addEventListener('pointerout',event=>{if(event.target.closest('[data-tooltip]'))tooltip.hidden=true;});
  document.addEventListener('focusin',event=>{const target=event.target.closest('[data-tooltip]');if(target){const r=target.getBoundingClientRect();showTooltip(target,r.left,r.bottom);}});
  document.addEventListener('focusout',()=>{tooltip.hidden=true;});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')tooltip.hidden=true;});
  window.addEventListener('scroll',()=>{tooltip.hidden=true;},{passive:true});

  const fields=['D','C','S','R','L','ES','CS','CF','AF'];
  const units={D:' (%)',C:' (%)',S:' (%)',ES:' (%)',CF:' (%)',AF:' (%)'};
  $('#full-results-table').innerHTML = `<caption>Model performance and exploration behavior</caption><thead><tr><th scope="col">Model</th>${fields.map(k=>`<th scope="col">${k}${units[k]||''}</th>`).join('')}</tr></thead><tbody>${data.models.map(m=>`<tr class="${m.name==='GPT-6-Astra'?'featured':''}"><th scope="row">${esc(m.name)}</th>${fields.map(k=>`<td>${m[k]==null?'—':(['R','CS'].includes(k)?m[k]:fmt(m[k]))}</td>`).join('')}</tr>`).join('')}</tbody>`;
  const interventions = [
    {label:'01 / TASK GUIDANCE',title:'Give inquiry a direction.',text:'A law-discovery task, an altered-physics notice and a scene-specific clue help the model identify the laws.',a:data.controlled[0],b:data.controlled[1],aLabel:'Free',bLabel:'Guided',takeaway:'+11.9 percentage points in discovery',foot:'100 turns · evidence support stays at 97.6%.'},
    {label:'02 / EXPLORATION BUDGET',title:'More time is not enough.',text:'A larger turn limit offers little value when the explorer stops with questions still unresolved.',a:data.controlled[2],b:data.controlled[3],aLabel:'100 turns',bLabel:'500 turns',takeaway:'No improvement with a larger budget',foot:'No context compaction · mean turns used: 42.2 vs 41.4.'},
    {label:'03 / APPARATUS ACCESS',title:'Make room for tools.',text:'Access to construction lets the explorer create new ways to intervene and measure.',a:data.controlled[5],b:data.controlled[4],aLabel:'Disabled',bLabel:'Enabled',takeaway:'+11.9 percentage points with access',foot:'100 turns · the explorer chooses whether to build.'}
  ];
  $('#interventions').innerHTML=interventions.map(c=>`<article class="intervention-card"><span class="intervention-index">${c.label}</span><h4>${c.title}</h4><p>${c.text}</p><div class="mini-compare">${[[c.a,c.aLabel],[c.b,c.bLabel]].map(([v,label])=>`<div class="compare-row"><span>${label}</span><div class="compare-track"><i class="compare-fill" style="width:${v.D/40*100}%"></i></div><strong>${fmt(v.D)}%</strong></div>`).join('')}<div class="intervention-foot">Discovery rate · shared scale 0–40%</div></div><div class="intervention-takeaway">${c.takeaway}</div><small class="intervention-foot">${c.foot}</small></article>`).join('');
  const controlFields=['D','C','S','L','AF'];
  $('#controlled-table').innerHTML=`<caption>GPT-6-Astra controlled comparisons</caption><thead><tr><th scope="col">Condition</th>${controlFields.map(k=>`<th scope="col">${k}${k==='L'?'':' (%)'}</th>`).join('')}</tr></thead><tbody>${data.controlled.map((row,i)=>`${i%2===0?`<tr><th colspan="6" style="text-align:left">${['Task guidance · 100 turns','Turn budget · no compaction','Apparatus access · 100 turns'][i/2]}</th></tr>`:''}<tr><th scope="row">${esc(row.name)}</th>${controlFields.map(k=>`<td>${fmt(row[k])}</td>`).join('')}</tr>`).join('')}</tbody>`;

  // Case studies keep the original notes distinct from editorial explanations.
  $('#color-quote').textContent=notes.color.notes['43'];
  $('#tool-quote').textContent=notes.apparatus.notes['24'];
  $('#question-astra-quote').textContent=notes.question.notes['25'];
  $('#question-gemini-quote').textContent=notes.checklist.steps.find(s=>s.turn===3).note;
  function chooseCase(button) {
    selectTab(button);
    $$('.case-panel').forEach(panel=>{
      panel.hidden=panel.id!==button.dataset.case+'-case';
      if(panel.hidden)$$('video',panel).forEach(video=>video.pause());
    });
  }
  $$('.case-tabs button').forEach(b=>b.addEventListener('click',()=>chooseCase(b)));
  wireTabs($('.case-tabs'),chooseCase);
  document.addEventListener('longchang:presentation-open',()=>$$('.question-comparison video').forEach(v=>v.pause()));
  new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)entry.target.pause();})).observe($('#question-astra-video'));
  new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)entry.target.pause();})).observe($('#question-gemini-video'));
  $('#scale-chart').innerHTML=notes.apparatus.pan_readings.map(v=>`<div class="scale-value"><span>${esc(v.condition)}</span><strong>${fmt(v.travel).replace('-','−')}</strong><small>Turn ${v.turn}</small></div>`).join('');
  $('#evolution-chart').innerHTML=`<p style="font-size:9px;margin-bottom:12px">Discovery rate (%) · 3 runs per scene · scale 0–100%</p>${data.evolution.map((e,i)=>`<div class="evolution-bar-row ${i>1?'evolved':''}"><span>${esc(e.name)}</span><div class="evolution-bar-track"><i style="width:${e.D}%"></i></div><strong>${fmt(e.D)}%</strong></div>`).join('')}`;

  // Subtle, stable navigation state; no scroll-triggered motion is required.
  const navLinks=$$('.site-header nav a');
  new IntersectionObserver(entries=>{
    entries.filter(e=>e.isIntersecting).forEach(e=>navLinks.forEach(a=>{
      const current=a.hash===`#${e.target.id}`;
      a.classList.toggle('active',current);
      if(current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');
    }));
  },{rootMargin:'-15% 0px -65% 0px'}).observe($('#explore'));
  for(const id of ['worlds','framework','results','materials']){
    new IntersectionObserver(entries=>{
      if(entries[0].isIntersecting)navLinks.forEach(a=>{
        const current=a.hash===`#${id}`;
        a.classList.toggle('active',current);
        if(current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');
      });
    },{rootMargin:'-15% 0px -65% 0px'}).observe($(`#${id}`));
  }
})();
