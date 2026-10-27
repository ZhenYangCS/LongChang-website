(() => {
  'use strict';
  const root = document.querySelector('#evolution');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const media = window.EVOLUTION_MEDIA;
  const descriptions = {
    generate: {
      name: 'Repulsion with a pause',
      lineage: 'Generated from Scene 15 · Northward force',
      law: 'Replace red’s northward force with mutual red–blue repulsion; keep the 10 s pause after a push or throw.',
    },
    mutate: {
      name: 'Northward force with a spatial condition',
      lineage: 'Refined from Scene 15 · Northward force',
      law: 'Keep the 10 s pause, and also block red’s northward force while blue is inside the gray square.',
    },
    compose: {
      name: 'Northward force + velocity copy',
      lineage: 'Combined from Scene 15 · Northward force + Scene 14 · Velocity copy',
      law: 'Red keeps its paused northward force; green also copies red’s launch velocity 12 s later.',
    },
  };
  const video = $('#evo-demo-video'), tabs = [...document.querySelectorAll('[data-evolution]')];
  const discovery = Object.fromEntries(['generate','mutate','compose'].map((id,index)=>[id,Math.round(window.LONGCHANG.evolution[index+2].D*3/100)]));
  for (const tab of tabs) {
    const score=document.createElement('span');score.className='evo-choice-discovery';
    score.innerHTML=`<span>Discovery</span><strong>${discovery[tab.dataset.evolution]} / 3</strong>`;
    tab.append(score);
  }
  const model = window.LongChangEvolutionModel.create({host:$('#evo-explanation'), video});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let key = 'generate', view = 'demo', demoWanted = !reduced.matches, demoKey = null, demoFailed = false, demoPreparing = false, demoTimer, revision = 0, seekTime = null;
  const setText = (id, text) => { const node = $(id); if (node.textContent !== text) node.textContent = text; };
  const allowed = () => {
    const rect = $('#evo-visual').getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < innerHeight && !document.hidden && !document.querySelector('dialog[open]');
  };
  const live = window.LongChangScenePlayer.live({
    host: $('#evo-experiment-view'), prefix: 'evo', modeAttribute: 'data-evo-mode', fullscreen: $('#evo-visual'),
    getScene: () => ({id:key, poster:`assets/images/interactive-room-${key}.webp`, url:`data/evolution/${key}.json`}),
    async loadSimulation(config, status) {
      const {createEvolutionSimulation} = await import('./evolution-physics.js');
      return createEvolutionSimulation(config, status);
    },
  });
  const interactiveTab = root.querySelector('[data-evo-view=experiment]');
  interactiveTab.addEventListener('pointerenter', live.prepare, {passive:true});
  interactiveTab.addEventListener('focus', live.prepare);
  const demo = window.LongChangScenePlayer.playback({
    host: $('#evo-demo-view'), prefix: 'evo-demo', video, speed: 4,
    handlers: {
      toggle() { demoWanted = !demoWanted || video.paused; sync(); },
      reset() { demoWanted = false; video.pause(); seekTime = null; if (video.readyState) video.currentTime = 0; demo.update(); },
      seek(fraction) { demoWanted = false; video.pause(); seekTime = fraction * (video.duration || 10); loadDemo(); if (video.readyState) { video.currentTime = seekTime; seekTime = null; } demo.update(); },
    },
  });
  function fail() {
    clearTimeout(demoTimer);
    if (demoPreparing) {
      demoPreparing = false; demoKey = null;
      video.removeAttribute('src'); video.preload = 'none'; video.load();
      return;
    }
    demoFailed = true; video.pause();
    $('#evo-demo-error').hidden = false; $('#evo-demo-retry').hidden = false;
  }
  function loadDemo(background = false) {
    if (demoKey === key) { if (!background) demoPreparing = false; return; }
    clearTimeout(demoTimer); video.pause(); demoKey = key; demoFailed = false;
    demoPreparing = background;
    $('#evo-demo-error').hidden = true; $('#evo-demo-retry').hidden = true;
    video.preload = 'auto'; video.src = media[key].video; video.load();
    const selected = key;
    demoTimer = setTimeout(() => { if (demoKey === selected && video.readyState < 2) fail(); }, 20000);
  }
  const prepareNearby = window.LongChangResources.prepareOnApproach($('#evo-demo-view'), () => {
    if (view === 'demo') loadDemo(true);
  });
  function sync() {
    const ticket = ++revision;
    if (view === 'demo' && allowed()) {
      loadDemo();
      if (demoWanted && !demoFailed) video.play().then(() => {
        if (view !== 'demo' || !allowed()) video.pause();
      }).catch(error => {
        if (ticket !== revision || error.name === 'AbortError') return;
        if (error.name === 'NotAllowedError') demoWanted = false; else fail();
      });
      else video.pause();
    } else video.pause();
    demo.update(10);
  }
  function content() {
    const d = descriptions[key];
    model.setScene(key, d);
    for (const field of ['name','lineage','law']) setText(`#evo-${field}`, d[field]);
    setText('#evo-mobile-discovery',`Discovery: ${discovery[key]} / 3 runs · GPT-6-Astra`);
    video.poster = media[key].poster;
    video.setAttribute('aria-label', `Scripted demonstration: ${d.name}`);
    $('#evo-detail').setAttribute('aria-labelledby', `evo-tab-${key}`);
    $('#evo-mobile-select').value = key;
    for (const tab of tabs) { const active = tab.dataset.evolution === key; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; }
  }
  function setView(selected) {
    if (!['demo','experiment'].includes(selected)) return;
    view = selected;
    const nativeView = view === 'demo' ? 'physics' : 'motion';
    $('#evo-detail').dataset.view = nativeView; $('.evo-workspace').dataset.view = nativeView;
    for (const button of document.querySelectorAll('[data-evo-view]')) button.setAttribute('aria-pressed', String(button.dataset.evoView === view));
    $('#evo-demo-view').hidden = view !== 'demo'; $('#evo-experiment-view').hidden = view !== 'experiment';
    model.setActive(view === 'demo');
    $('#evo-explanation').hidden = view !== 'demo';
    live.setActive(view === 'experiment'); sync(); prepareNearby();
    document.dispatchEvent(new CustomEvent('longchang:evolution-view', {detail:{view}}));
  }
  function choose(selected) {
    if (selected === key || !descriptions[selected]) return;
    clearTimeout(demoTimer); video.pause(); revision++; demoKey = null; demoFailed = false; seekTime = null; demoWanted = !reduced.matches;
    video.removeAttribute('src'); video.load(); key = selected;
    $('#evo-demo-error').hidden = true; $('#evo-demo-retry').hidden = true;
    content(); live.select(); sync(); prepareNearby();
    document.dispatchEvent(new CustomEvent('longchang:evolution-scene', {detail:{id:key}}));
  }
  for (const tab of tabs) {
    tab.addEventListener('click', () => choose(tab.dataset.evolution));
    tab.addEventListener('keydown', event => {
      const index = tabs.indexOf(tab); let next;
      if (['ArrowRight','ArrowDown'].includes(event.key)) next = (index+1)%tabs.length;
      if (['ArrowLeft','ArrowUp'].includes(event.key)) next = (index+tabs.length-1)%tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length-1;
      if (next !== undefined) { event.preventDefault(); choose(tabs[next].dataset.evolution); tabs[next].focus(); }
    });
  }
  for (const button of document.querySelectorAll('[data-evo-view]')) button.addEventListener('click', () => setView(button.dataset.evoView));
  root.addEventListener('click', event => {
    const source = event.target.closest('[data-evo-source]');
    if (source) window.showWorld(source.dataset.evoSource);
  });
  $('#evo-mobile-select').addEventListener('change', event => choose(event.target.value));
  $('#evo-demo-retry').addEventListener('click', () => { demoKey = null; demoWanted = true; sync(); });
  video.addEventListener('loadeddata', () => { clearTimeout(demoTimer); demo.update(); });
  video.addEventListener('loadedmetadata', () => { video.playbackRate = Number(demo.speed.value); if (seekTime !== null) { video.currentTime = seekTime; seekTime = null; } demo.update(); });
  video.addEventListener('error', () => { if (video.error && demoKey) fail(); });
  video.addEventListener('play', () => { if (view === 'demo' && allowed()) demoWanted = true; else video.pause(); demo.update(); });
  video.addEventListener('pause', () => { if (view === 'demo' && allowed() && video.paused && !demoFailed) demoWanted = false; demo.update(); });
  video.addEventListener('timeupdate', () => demo.update());
  video.addEventListener('seeked', () => demo.update());
  document.addEventListener('fullscreenchange', () => { video.controls = false; });
  new IntersectionObserver(sync, {threshold:.05}).observe($('#evo-visual'));
  document.addEventListener('visibilitychange', sync);
  for (const dialog of document.querySelectorAll('dialog')) new MutationObserver(sync).observe(dialog, {attributes:true, attributeFilter:['open']});
  reduced.addEventListener('change', () => { if (reduced.matches) { demoWanted = false; sync(); } });
  window.LongChangEvolution = Object.freeze({current:live.current, select:choose, setView, view:() => view, modelState:model.getState});
  content(); setView('demo');
})();
