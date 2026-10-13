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

  function wireTabs(root, choose) {
    root.addEventListener('keydown', event => {
      const vertical=root.getAttribute('aria-orientation')==='vertical';
      const grid=root.id==='scene-picker';
      if (!['ArrowLeft','ArrowRight','Home','End',...(vertical||grid?['ArrowUp','ArrowDown']:[])].includes(event.key)) return;
      const tabs = $$('[role="tab"]', root);
      const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      event.preventDefault();
      const step=grid&&['ArrowUp','ArrowDown'].includes(event.key)?3:1;
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (i + (['ArrowRight','ArrowDown'].includes(event.key) ? step : -step) + tabs.length) % tabs.length;
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


  // Scene atlas.
  $('#scene-picker').innerHTML = data.scenes.map(s=>`<button id="scene-tab-${s.id}" role="tab" aria-selected="${s.id==='15'}" aria-controls="scene-detail" tabindex="${s.id==='15'?0:-1}" data-scene="${s.id}"><span>${s.id}</span>${esc(s.name)}</button>`).join('');
  function chooseScene(button) {
    const scene = data.scenes.find(s=>s.id===button.dataset.scene);
    selectTab(button);
    $('#scene-detail').setAttribute('aria-labelledby',button.id);
    $('#scene-name').textContent = scene.name;
    $('#scene-description').textContent = scene.description;
    $('#scene-image').src = scene.image;
    $('#scene-image').alt = `Recorded initial state of Scene ${scene.id}: ${scene.name}`;
    $('#scene-law-text').textContent = scene.law;
    document.dispatchEvent(new CustomEvent('longchang:scene', {detail:scene}));
  }
  $$('#scene-picker button').forEach(b=>b.addEventListener('click',()=>chooseScene(b)));
  wireTabs($('#scene-picker'),chooseScene);
  window.showWorld = id => { const button = $('#scene-tab-'+id); if(button) chooseScene(button); };
  chooseScene($('#scene-tab-07'));

  // One choice per case: select it and watch the complete film.
  function chooseCase(button) {
    selectTab(button);
    $$('.case-panel').forEach(panel=>{
      panel.hidden=panel.id!==button.dataset.case+'-case';
      if(panel.hidden)$$('video',panel).forEach(video=>video.pause());
    });
    document.dispatchEvent(new CustomEvent('longchang:case-select',{detail:button.dataset.case}));
  }
  $$('.case-tabs button').forEach(b=>b.addEventListener('click',()=>chooseCase(b)));
  wireTabs($('.case-tabs'),chooseCase);
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
  for(const id of ['worlds','framework','results']){
    new IntersectionObserver(entries=>{
      if(entries[0].isIntersecting)navLinks.forEach(a=>{
        const current=a.hash===`#${id}`;
        a.classList.toggle('active',current);
        if(current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');
      });
    },{rootMargin:'-15% 0px -65% 0px'}).observe($(`#${id}`));
  }
})();
