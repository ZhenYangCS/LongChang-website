/* The 15 Worlds and Scene Evolution share these controls and live lifecycle. */
(() => {
  'use strict';
  const icon = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  function playback({host, prefix, video, handlers, speed = 1, existing = null}) {
    const bar = existing || document.createElement('div');
    if (!existing) {
      bar.className = 'physics-playback';
      bar.innerHTML = `<button id="${prefix}-play" class="round-control" aria-label="Play demonstration">▶</button><button id="${prefix}-reset" class="round-control" aria-label="Restart demonstration">↺</button><label class="sr-only" for="${prefix}-progress">Demonstration progress</label><input id="${prefix}-progress" type="range" min="0" max="1000" value="0"><span id="${prefix}-clock">0:00</span><select id="${prefix}-speed" aria-label="Playback speed"><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select><button id="${prefix}-fullscreen" class="round-control" aria-label="Expand demonstration">${icon}</button>`;
      host.append(bar);
    }
    bar.dataset.component = 'scene-playback';
    const get = suffix => bar.querySelector(`#${prefix}-${suffix}`);
    const controls = Object.fromEntries(['play','reset','progress','clock','speed','fullscreen'].map(key => [key, get(key)]));
    controls.speed.value = String(speed);
    controls.play.addEventListener('click', handlers.toggle);
    controls.reset.addEventListener('click', handlers.reset);
    controls.progress.addEventListener('input', event => handlers.seek(Number(event.target.value)/1000));
    controls.speed.addEventListener('change', () => { video.playbackRate = Number(controls.speed.value); });
    controls.fullscreen.addEventListener('click', async () => {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await host.requestFullscreen(); }
      catch (_) { video.controls = true; }
    });
    return {bar, ...controls, update(duration = video.duration) {
      const time = video.currentTime || 0, clock = t => `${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
      controls.progress.value = duration ? Math.round(time/duration*1000) : 0;
      controls.clock.textContent = `${clock(time)} / ${clock(Number.isFinite(duration) ? duration : 0)}`;
      controls.play.textContent = video.paused ? '▶' : 'II';
      controls.play.setAttribute('aria-label', video.paused ? 'Play demonstration' : 'Pause demonstration');
    }};
  }
  function live({host, prefix = 'scene-live', getScene, loadSimulation, fullscreen = host.parentElement, modeAttribute = 'data-scene-mode', autoPlay = false, onWorld = () => {}, onFrame = () => {}}) {
    const stage = document.createElement('div'); stage.id = `${prefix}-stage`; stage.className = 'scene-live-stage';
    const poster = document.createElement('img'); poster.className = 'scene-live-poster'; poster.alt = 'Scene preview'; stage.append(poster); host.prepend(stage);
    const bar = document.createElement('div'); bar.className = 'scene-live-playback'; bar.dataset.component = 'scene-live';
    bar.innerHTML = `<div id="${prefix}-controls" class="scene-live-controls"><div class="room-tools" role="group" aria-label="Interact with the scene"><button ${modeAttribute}="push" aria-pressed="true" title="Launch an object">Push</button><button ${modeAttribute}="drag" aria-pressed="false" title="Lift and move an object">Drag</button><button ${modeAttribute}="view" aria-pressed="false" title="Change the viewing angle">Rotate</button><button id="${prefix}-reset" aria-label="Reset the scene">↺</button></div></div><button id="${prefix}-play" class="round-control" aria-label="Run live physics">▶</button><span id="${prefix}-hint" class="scene-live-hint" role="status"></span><span id="${prefix}-clock" class="scene-live-clock">0.0 s</span><select id="${prefix}-speed" class="scene-live-speed" aria-label="Live physics speed"><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4" selected>4×</option></select><button id="${prefix}-fullscreen" class="round-control" aria-label="Expand live physics">${icon}</button>`;
    host.after(bar);
    const $ = key => bar.querySelector(`#${prefix}-${key}`);
    let world = null, worldId = null, mode = 'push', version = 0, loading = null, active = false, wanted = autoPlay, inViewport = false;
    const allowed = () => active && inViewport && !document.hidden && !document.querySelector('dialog[open]');
    const status = text => { $('hint').textContent = text; stage.dataset.loadLabel = text; };
    function labels(time = world?.getState().time || 0) {
      $('clock').textContent = `${time.toFixed(1)} s`;
      $('play').textContent = world?.isRunning() ? 'II' : '▶';
      $('play').setAttribute('aria-label', world?.isRunning() ? 'Pause live physics' : 'Run live physics');
      $('play').setAttribute('aria-pressed', String(Boolean(world?.isRunning())));
    }
    function sync() {
      if (world) { if (wanted && allowed()) world.play(); else world.pause(); }
      labels();
    }
    function destroy() {
      version++; loading = null; world?.destroy(); world = null; worldId = null; wanted = autoPlay;
      onWorld(null); stage.setAttribute('aria-busy', 'false'); labels(0);
    }
    async function open() {
      const item = getScene();
      if (world && worldId === item.id) return world;
      if (loading) return loading;
      const token = ++version;
      stage.setAttribute('aria-busy', 'true'); status('Loading interaction…'); poster.src = item.poster; poster.hidden = false;
      loading = (async () => {
        let simulation = null;
        try {
          const [{createRoom}, response] = await Promise.all([import('./room-world.js'), fetch(item.url, {signal:AbortSignal.timeout(20000)})]);
          if (!response.ok) throw Error('Scene unavailable');
          const config = await response.json(); if (token !== version) return null;
          simulation = await loadSimulation(config, text => { if (token === version) status(text); });
          if (token !== version) { simulation.destroy(); return null; }
          const next = await createRoom(stage, text => { if (token === version) status(text); }, {simulation, speed:Number($('speed').value), onFrame:time => { if (token === version) { labels(time); onFrame(time, simulation); } }});
          if (token !== version) { next.destroy(); return null; }
          world = next; worldId = item.id; onWorld(world); poster.hidden = true;
          stage.querySelector('.room-canvas').setAttribute('aria-describedby', `${prefix}-hint`);
          world.setMode(mode); sync(); return world;
        } catch (error) {
          simulation?.destroy();
          if (token === version) status('Could not load. Tap Push to retry.');
          return null;
        } finally {
          if (token === version) { loading = null; stage.setAttribute('aria-busy', 'false'); }
        }
      })();
      return loading;
    }
    for (const button of bar.querySelectorAll(`[${modeAttribute}]`)) button.addEventListener('click', async () => {
      mode = button.getAttribute(modeAttribute);
      for (const b of bar.querySelectorAll(`[${modeAttribute}]`)) b.setAttribute('aria-pressed', String(b === button));
      if (world) world.setMode(mode);
      else { const next = await open(); if (next && active) next.setMode(mode); }
    });
    $('play').addEventListener('click', async () => {
      if (world?.isRunning()) wanted = false;
      else { wanted = true; await open(); }
      sync();
    });
    $('reset').addEventListener('click', () => { wanted = false; world?.reset(); labels(0); });
    $('speed').addEventListener('change', () => world?.setSpeed(Number($('speed').value)));
    $('fullscreen').addEventListener('click', async () => {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await fullscreen.requestFullscreen(); }
      catch (_) { status(matchMedia('(pointer:coarse)').matches?'Pinch to zoom.':'Hold Ctrl/⌘ and scroll to zoom.'); }
    });
    stage.addEventListener('pointerdown', () => { if (mode !== 'view') wanted = true; }, true);
    stage.addEventListener('keydown', event => { if (event.key.startsWith('Arrow')) wanted = true; }, true);
    stage.addEventListener('pointerup', () => queueMicrotask(() => labels()));
    new IntersectionObserver(entries => { inViewport = entries[0].isIntersecting; sync(); }).observe(host);
    document.addEventListener('visibilitychange', sync);
    for (const dialog of document.querySelectorAll('dialog')) new MutationObserver(sync).observe(dialog, {attributes:true, attributeFilter:['open']});
    return {stage, bar, open, current:() => world, sync,
      setActive(value) { active = value; bar.hidden = !active; if (active) open(); sync(); },
      select() { if (getScene().id !== worldId) { destroy(); if (active) open(); } },
      destroy,
    };
  }
  function modelClock({running, tick}) {
    let frame = 0, previous = 0;
    const stop = () => { cancelAnimationFrame(frame); frame = 0; };
    const animate = now => {
      frame = 0;
      if (!running()) return;
      const elapsed = Math.min(.08, (now - previous) / 1000); previous = now;
      tick(elapsed);
      if (running() && !frame) frame = requestAnimationFrame(animate);
    };
    return {stop, sync() {
      stop();
      if (running()) { previous = performance.now(); frame = requestAnimationFrame(animate); }
    }};
  }
  window.LongChangScenePlayer = Object.freeze({playback, live, modelClock});
})();
