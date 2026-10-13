


(() => {
  'use strict';
  const data = window.LONGCHANG;
  if (!data) return;
  const $ = (q, root = document) => root.querySelector(q);
  const $$ = (q, root = document) => [...root.querySelectorAll(q)];
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

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


  const navLinks=$$('.site-header nav a');
  new IntersectionObserver(entries=>{
    if(entries[0].isIntersecting)navLinks.forEach(a=>{a.classList.remove('active');a.removeAttribute('aria-current');});
  },{rootMargin:'-15% 0px -65% 0px'}).observe($('.publication-hero'));
  new IntersectionObserver(entries=>{
    entries.filter(e=>e.isIntersecting).forEach(e=>navLinks.forEach(a=>{
      const current=a.hash===`#${e.target.id}`;
      a.classList.toggle('active',current);
      if(current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');
    }));
  },{rootMargin:'-15% 0px -65% 0px'}).observe($('#explore'));
  for(const id of ['worlds','framework','results','controlled','evolution']){
    new IntersectionObserver(entries=>{
      if(entries[0].isIntersecting)navLinks.forEach(a=>{
        const current=a.hash===`#${id}`;
        a.classList.toggle('active',current);
        if(current)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');
      });
    },{rootMargin:'-15% 0px -65% 0px'}).observe($(`#${id}`));
  }
})();
