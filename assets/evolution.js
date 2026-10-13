(() => {
  'use strict';
  const $ = selector => document.querySelector(selector), stage = $('#evo-stage');
  if (!stage) return;
  const descriptions = {
    generate: {
      kind: 'Generation · From Scene 15', name: 'Change the force',
      law: 'Red and blue repel. A push pauses repulsion for 10 s.',
      rationale: 'The trace mistook a paused force for no force. This world tests the same error with repulsion.',
      full: 'Each ball accelerates horizontally away from the other at 1.5 bricks/s². At zero horizontal separation, the extra force is zero. Any nonzero push or throw restarts a shared 10-second pause; hand movement and zero impulses do not.',
      quote: 'Frozen design: “Replace solitary drift with paired repulsion that pauses after intervention, making an apparently ordinary separation test temporarily disable the tendency.”',
      initial: 'Repulsion active',
    },
    mutate: {
      kind: 'Refinement · From Scene 15', name: 'Add a condition',
      law: 'Blue inside the square blocks red’s northward force.',
      rationale: 'Waiting corrected the source error; here, blue must also leave the square.',
      full: 'Red accelerates north at 1.5 bricks/s² only when the latest nonzero push or throw was at least 10 seconds ago AND blue is outside x ∈ [2.5, 3.5], y ∈ [2.5, 3.5]. The square includes its boundary and the test ignores height. Dragging by hand does not restart the pause.',
      quote: 'Frozen design: “Gate the original shy drift by blue’s position, so harmless-looking relocation can prolong negative observations without increasing the suppression interval.”',
      initial: 'Blue inside · red’s force blocked',
    },
    compose: {
      kind: 'Composition · From Scenes 15 + 14', name: 'Combine two rules',
      law: 'Red drifts north; green copies red’s launch velocity 12 s later.',
      rationale: 'A second effect can hide the paused drift that the source trace initially dismissed.',
      full: 'Red accelerates north at 1.5 bricks/s² outside the 10-second pause after any nonzero push or throw. Every red launch independently queues its full resulting 3D velocity for green, 12 seconds later. Later launches do not cancel copies; a copy does not restart the pause. Coincident copies use the latest originating launch.',
      quote: 'Frozen design: “Use separated paths so blue’s intervention delays red’s drift while green still copies red’s earlier southward motion.” Scene 14 supplies the second law; the shared error still comes from Scene 15, turns 30–31.',
      initial: 'Red’s northward force active',
    },
  };
  const instructions = {push: 'Drag, then release to push.', drag: 'Drag up to lift; Shift-drag to slide. Release to drop.', view: 'Drag to rotate; scroll or pinch to zoom.'};
  const tabs = [...document.querySelectorAll('[data-evolution]')], reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const video = $('#evo-demo-video');
  let key = 'generate', view = 'demo', mode = 'push', world = null, simulation = null, loading = null, version = 0;
  let visible = false, wanted = false, demoWanted = !reduced.matches, demoKey = null, demoFailed = false;
  let demoRevision = 0, demoTimer;
  const setText = (id, text) => { const node = $(id); if (node.textContent !== text) node.textContent = text; };
  const status = text => setText('#evo-hint', text);
  const allowed = () => visible && !document.hidden && !document.querySelector('dialog[open]');
  function label() {
    const playing = Boolean(world?.isRunning());
    setText('#evo-play', playing ? 'Ⅱ' : '▶');
    $('#evo-play').setAttribute('aria-label', playing ? 'Pause evolved world' : 'Run evolved world');
    $('#evo-play').setAttribute('aria-pressed', String(playing));
  }
  function readout(time = 0) {
    setText('#evo-clock', `${time.toFixed(1)} s`);
    if (simulation) {
      const info = simulation.info(), remaining = Math.max(0, info.quietUntil - time);
      const force = key === 'generate' ? 'Repulsion' : 'Red’s force';
      setText('#evo-force', remaining > 0 ? `${force} paused · ${remaining.toFixed(1)} s${info.blocked ? ' · blue inside' : ''}` : info.blocked ? 'Blue inside · red’s force blocked' : `${force} active`);
      $('#evo-copy').hidden = key !== 'compose';
      if (key === 'compose') setText('#evo-copy', info.pending.length ? `Green copies in ${Math.max(0, info.pending[0] - time).toFixed(1)} s` : 'No velocity copy pending');
    }
    label();
  }
  function pauseDemo() {
    video.pause();
  }
  function demoError() {
    clearTimeout(demoTimer); demoFailed = true; pauseDemo();
    $('#evo-demo-error').hidden = false;
  }
  function loadDemo() {
    if (demoKey === key) return;
    clearTimeout(demoTimer); pauseDemo();
    demoKey = key; demoFailed = false; $('#evo-demo-error').hidden = true;
    video.preload = 'auto'; video.src = `assets/videos/evolution-${key}.mp4`;
    video.load();
    const selected = key;
    demoTimer = setTimeout(() => { if (demoKey === selected && video.readyState < 2) demoError(); }, 20000);
  }
  function sync() {
    if (world) { if (wanted && view === 'experiment' && allowed()) world.play(); else world.pause(); }
    const ticket = ++demoRevision;
    if (view === 'demo' && allowed()) {
      loadDemo();
      if (demoWanted && !demoFailed) video.play().then(() => {
        if (view !== 'demo' || !allowed()) pauseDemo();
      }).catch(error => {
        if (ticket !== demoRevision || error.name === 'AbortError') return;
        if (error.name === 'NotAllowedError') demoWanted = false;
        else demoError();
      });
      else pauseDemo();
    } else pauseDemo();
    label();
  }
  function content() {
    const d = descriptions[key];
    for (const [id, field] of [['kind','kind'],['name','name'],['law','law'],['rationale','rationale'],['full-rule','full'],['design-quote','quote']]) setText(`#evo-${id}`, d[field]);
    setText('#evo-force', d.initial);
    $('#evo-copy').hidden = key !== 'compose'; setText('#evo-copy', 'No velocity copy pending');
    $('#evo-design-link').href = `data/evolution/${key}-design.json`;
    $('#evo-poster').src = `assets/images/evolution-${key}.webp`;
    $('#evo-poster').alt = `Preview of ${d.name.toLowerCase()}`;
    video.poster = `assets/images/evolution-${key}.webp`;
    video.setAttribute('aria-label', `Scripted demonstration: ${d.name}`);
    $('#evo-detail').setAttribute('aria-labelledby', `evo-tab-${key}`);
    for (const tab of tabs) { const active = tab.dataset.evolution === key; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; }
    status(instructions[mode]);
  }
  async function open() {
    if (world) return world;
    if (loading) return loading;
    const ticket = version, selected = key;
    stage.setAttribute('aria-busy', 'true'); $('#evo-start').disabled = true; $('#evo-start').hidden = false;
    setText('#evo-start', 'Loading experiment…');
    loading = (async () => {
      let nextSimulation = null;
      try {
        const [{createEvolutionSimulation}, {createRoom}, response] = await Promise.all([
          import('./evolution-physics.js'), import('./room-world.js'), fetch(`data/evolution/${selected}.json`, {signal: AbortSignal.timeout(20000)}),
        ]);
        if (!response.ok) throw Error('Scene unavailable');
        const config = await response.json();
        if (ticket !== version) return null;
        nextSimulation = await createEvolutionSimulation(config, text => { if (ticket === version) status(text); });
        if (ticket !== version) { nextSimulation.destroy(); return null; }
        simulation = nextSimulation;
        const next = await createRoom(stage, text => { if (ticket === version) status(text); }, {
          simulation, speed: Number($('#evo-speed').value), onFrame: time => { if (ticket === version) readout(time); },
        });
        if (ticket !== version) { next.destroy(); return null; }
        world = next; nextSimulation = null;
        $('#evo-poster').hidden = true; $('#evo-start').hidden = true;
        const canvas = stage.querySelector('.room-canvas');
        canvas.setAttribute('aria-label', `${descriptions[key].name}: push or drag objects; arrow keys push the selected object.`);
        canvas.setAttribute('aria-describedby', 'evo-hint');
        world.setMode(mode); readout(0); sync();
        return world;
      } catch (error) {
        nextSimulation?.destroy();
        if (ticket === version) {
          simulation = null; wanted = false;
          status('Could not load the experiment. Select Retry to try again.');
          setText('#evo-start', 'Retry experiment'); $('#evo-start').hidden = false;
        }
        return null;
      } finally {
        if (ticket === version) { loading = null; stage.setAttribute('aria-busy', 'false'); $('#evo-start').disabled = false; label(); }
      }
    })();
    return loading;
  }
  function setView(selected) {
    if (!['demo', 'experiment'].includes(selected)) return;
    view = selected;
    for (const button of document.querySelectorAll('[data-evo-view]')) button.setAttribute('aria-pressed', String(button.dataset.evoView === view));
    $('#evo-demo-view').hidden = view !== 'demo';
    $('#evo-experiment-view').hidden = view !== 'experiment';
    $('.evo-try').hidden = view !== 'demo';
    setText('#evo-scope', 'Scripted demonstration.');
    $('#evo-scope').hidden = view !== 'demo';
    if (view === 'experiment' && visible) open();
    sync();
  }
  function choose(selected) {
    if (selected === key || !descriptions[selected]) return;
    version++; world?.destroy(); world = null; simulation = null; loading = null; wanted = false;
    clearTimeout(demoTimer); pauseDemo(); demoRevision++; demoKey = null; demoFailed = false; demoWanted = !reduced.matches;
    // Release the previous clip even when the user changes worlds in Experiment.
    video.removeAttribute('src'); video.load(); $('#evo-demo-error').hidden = true;
    key = selected; $('#evo-poster').hidden = false; $('#evo-start').hidden = false; $('#evo-start').disabled = false;
    setText('#evo-start', 'Loading experiment…'); stage.setAttribute('aria-busy', 'false');
    content(); readout(0); if (visible && view === 'experiment') open(); sync();
  }
  async function play() {
    const ticket = version, next = await open(); if (!next || ticket !== version || view !== 'experiment') return;
    wanted = true; sync();
  }
  for (const tab of tabs) {
    tab.addEventListener('click', () => choose(tab.dataset.evolution));
    tab.addEventListener('keydown', event => {
      const index = tabs.indexOf(tab); let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); choose(tabs[next].dataset.evolution); tabs[next].focus(); }
    });
  }
  for (const button of document.querySelectorAll('[data-evo-view]')) button.addEventListener('click', () => setView(button.dataset.evoView));
  for (const button of document.querySelectorAll('[data-evo-mode]')) button.addEventListener('click', async () => {
    mode = button.dataset.evoMode;
    for (const b of document.querySelectorAll('[data-evo-mode]')) b.setAttribute('aria-pressed', String(b === button));
    status(instructions[mode]);
    const ticket = version, next = await open(); if (next && ticket === version) next.setMode(mode);
  });
  stage.addEventListener('pointerdown', event => { if (event.target.classList.contains('room-canvas') && mode !== 'view') wanted = true; }, true);
  stage.addEventListener('keydown', event => { if (event.target.classList.contains('room-canvas') && event.key.startsWith('Arrow')) wanted = true; }, true);
  stage.addEventListener('pointerup', () => queueMicrotask(label));
  $('#evo-start').addEventListener('click', () => open());
  $('#evo-play').addEventListener('click', () => { if (!world || !wanted) play(); else { wanted = false; sync(); } });
  $('#evo-reset').addEventListener('click', () => { wanted = false; world?.reset(); readout(0); status(instructions[mode]); });
  $('#evo-speed').addEventListener('change', () => world?.setSpeed(Number($('#evo-speed').value)));
  $('#evo-try').addEventListener('click', () => setView('experiment'));
  $('#evo-demo-retry').addEventListener('click', () => { demoKey = null; demoWanted = true; sync(); });
  video.addEventListener('loadeddata', () => { clearTimeout(demoTimer); });
  video.addEventListener('error', () => { if (video.error && demoKey) demoError(); });
  video.addEventListener('play', () => { if (view === 'demo' && allowed()) demoWanted = true; else pauseDemo(); });
  video.addEventListener('pause', () => {
    if (view === 'demo' && allowed() && video.paused && !demoFailed) demoWanted = false;
  });
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible && view === 'experiment' && !world) open();
    sync();
  }, {threshold: .05}).observe($('#evo-visual'));
  document.addEventListener('visibilitychange', sync);
  for (const dialog of document.querySelectorAll('dialog')) new MutationObserver(sync).observe(dialog, {attributes: true, attributeFilter: ['open']});
  reduced.addEventListener('change', () => { if (reduced.matches) { wanted = false; demoWanted = false; sync(); } });
  window.LongChangEvolution = Object.freeze({current: () => world, select: choose, setView, view: () => view});
  content(); setView('demo');
})();
