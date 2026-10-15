(() => {
  'use strict';
  const root = document.querySelector('#evolution');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const descriptions = {
    generate: {
      name: 'Change the force',
      law: 'Red and blue repel. A push pauses repulsion for 10 s.',
      rationale: 'The trace mistook a paused force for no force. This world tests the same error with repulsion.',
      full: 'Each ball accelerates horizontally away from the other at 1.5 bricks/s². At zero horizontal separation, the extra force is zero. Any nonzero push or throw restarts a shared 10-second pause; hand movement and zero impulses do not.',
      quote: 'Frozen design: “Replace solitary drift with paired repulsion that pauses after intervention, making an apparently ordinary separation test temporarily disable the tendency.”',
    },
    mutate: {
      name: 'Add a condition',
      law: 'Blue inside the square blocks red’s northward force.',
      rationale: 'Waiting corrected the source error; here, blue must also leave the square.',
      full: 'Red accelerates north at 1.5 bricks/s² only when the latest nonzero push or throw was at least 10 seconds ago AND blue is outside x ∈ [2.5, 3.5], y ∈ [2.5, 3.5]. The square includes its boundary and the test ignores height. Dragging by hand does not restart the pause.',
      quote: 'Frozen design: “Gate the original shy drift by blue’s position, so harmless-looking relocation can prolong negative observations without increasing the suppression interval.”',
    },
    compose: {
      name: 'Combine two rules',
      law: 'Red drifts north; green copies red’s launch velocity 12 s later.',
      rationale: 'A second effect can hide the paused drift that the source trace initially dismissed.',
      full: 'Red accelerates north at 1.5 bricks/s² outside the 10-second pause after any nonzero push or throw. Every red launch independently queues its full resulting 3D velocity for green, 12 seconds later. Later launches do not cancel copies; a copy does not restart the pause. Coincident copies use the latest originating launch.',
      quote: 'Frozen design: “Use separated paths so blue’s intervention delays red’s drift while green still copies red’s earlier southward motion.” Scene 14 supplies the second law; the shared error still comes from Scene 15, turns 30–31.',
    },
  };
  const video = $('#evo-demo-video'), tabs = [...document.querySelectorAll('[data-evolution]')];
  const model = window.LongChangEvolutionModel.create({host:$('#evo-explanation'), video});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let key = 'generate', view = 'demo', demoWanted = !reduced.matches, demoKey = null, demoFailed = false, demoTimer, revision = 0, seekTime = null;
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
    clearTimeout(demoTimer); demoFailed = true; video.pause();
    $('#evo-demo-error').hidden = false; $('#evo-demo-retry').hidden = false;
  }
  function loadDemo() {
    if (demoKey === key) return;
    clearTimeout(demoTimer); video.pause(); demoKey = key; demoFailed = false;
    $('#evo-demo-error').hidden = true; $('#evo-demo-retry').hidden = true;
    video.preload = 'auto'; video.src = `assets/videos/evolution-${key}.mp4`; video.load();
    const selected = key;
    demoTimer = setTimeout(() => { if (demoKey === selected && video.readyState < 2) fail(); }, 20000);
  }
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
    for (const [id, field] of [['name','name'],['law','law'],['rationale','rationale'],['full-rule','full'],['design-quote','quote']]) setText(`#evo-${id}`, d[field]);
    $('#evo-design-link').href = `data/evolution/${key}-design.json`;
    video.poster = `assets/images/evolution-${key}.webp`;
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
    live.setActive(view === 'experiment'); sync();
    document.dispatchEvent(new CustomEvent('longchang:evolution-view', {detail:{view}}));
  }
  function choose(selected) {
    if (selected === key || !descriptions[selected]) return;
    clearTimeout(demoTimer); video.pause(); revision++; demoKey = null; demoFailed = false; seekTime = null; demoWanted = !reduced.matches;
    video.removeAttribute('src'); video.load(); key = selected;
    $('#evo-demo-error').hidden = true; $('#evo-demo-retry').hidden = true;
    content(); live.select(); sync();
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
