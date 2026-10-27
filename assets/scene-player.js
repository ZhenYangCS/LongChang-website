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
    const poster = document.createElement('img'); poster.className = 'scene-live-poster'; poster.alt = 'Scene preview'; poster.draggable = false; stage.append(poster); host.prepend(stage);
    const bar = document.createElement('div'); bar.className = 'scene-live-playback'; bar.dataset.component = 'scene-live';
    bar.innerHTML = `<div id="${prefix}-controls" class="scene-live-controls"><div class="room-tools" role="group" aria-label="Interact with the scene"><button ${modeAttribute}="push" aria-pressed="false" title="Launch an object">Push</button><button ${modeAttribute}="drag" aria-pressed="true" title="Lift and move an object">Drag</button><button ${modeAttribute}="view" aria-pressed="false" title="Change the viewing angle">Rotate</button><button id="${prefix}-reset" aria-label="Reset the scene">↺</button></div></div><button id="${prefix}-play" class="round-control" aria-label="Run live physics">▶</button><span id="${prefix}-hint" class="scene-live-hint" role="status"></span><span id="${prefix}-clock" class="scene-live-clock">0.0 s</span><select id="${prefix}-speed" class="scene-live-speed" aria-label="Live physics speed"><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4" selected>4×</option></select><button id="${prefix}-fullscreen" class="round-control" aria-label="Expand live physics">${icon}</button>`;
    host.after(bar);
    const $ = key => bar.querySelector(`#${prefix}-${key}`);
    let world = null, worldId = null, mode = 'drag', version = 0, loading = null, active = false, wanted = autoPlay, pending = null, published = false;
    for (const button of bar.querySelectorAll(`[${modeAttribute}]`)) button.setAttribute('aria-pressed', String(button.getAttribute(modeAttribute) === mode));
    const allowed = () => {
      const rect = host.getBoundingClientRect();
      return active && rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < innerHeight && !document.hidden && !document.querySelector('dialog[open]');
    };
    const status = text => { $('hint').textContent = text; stage.dataset.loadLabel = text; };
    let lastClock = null, lastRunning = null;
    function labels(time = world?.getTime?.() ?? world?.getState().time ?? 0) {
      const clock = `${time.toFixed(1)} s`, running = Boolean(world?.isRunning());
      if (clock !== lastClock) { $('clock').textContent = clock; lastClock = clock; }
      if (running !== lastRunning) {
        $('play').textContent = running ? 'II' : '▶';
        $('play').setAttribute('aria-label', running ? 'Pause live physics' : 'Run live physics');
        $('play').setAttribute('aria-pressed', String(running));
        lastRunning = running;
      }
    }
    function sync() {
      if (!allowed()) clearPending();
      if (world) { if (wanted && allowed()) world.play(); else world.pause(); }
      labels();
    }
    const sample = event => {
      const rect = stage.getBoundingClientRect();
      return {pointerId:event.pointerId, pointerType:event.pointerType, button:event.button, shiftKey:event.shiftKey, x:(event.clientX-rect.left)/rect.width, y:(event.clientY-rect.top)/rect.height};
    };
    const restore = point => {
      const rect = stage.getBoundingClientRect();
      return {...point, clientX:rect.left+point.x*rect.width, clientY:rect.top+point.y*rect.height};
    };
    function clearPending(event) {
      if (!pending || (event?.pointerId !== undefined && event.pointerId !== pending.start.pointerId)) return;
      const pointer = pending.start.pointerId; pending = null;
      if (stage.hasPointerCapture(pointer)) stage.releasePointerCapture(pointer);
    }
    function handoff() {
      if (!pending || !world || !allowed()) return;
      const gesture = pending; pending = null;
      // Transfer only a pointer that is still held. A finished click is never replayed.
      try {
        if (gesture.released && gesture.kind === 'push') world.applyPushGesture(restore(gesture.start), restore(gesture.latest));
        else { world.beginInteraction(restore(gesture.start)); world.moveInteraction(restore(gesture.latest)); }
      }
      finally { if (stage.hasPointerCapture(gesture.start.pointerId)) stage.releasePointerCapture(gesture.start.pointerId); }
    }
    function publish() { if (active && world && !published) { published = true; onWorld(world); } }
    function destroy() {
      clearPending(); version++; loading = null; world?.destroy(); world = null; worldId = null; wanted = autoPlay;
      if (published) onWorld(null); published = false; stage.setAttribute('aria-busy', 'false'); labels(0);
    }
    const prepareNearby = window.LongChangResources.prepareOnApproach(fullscreen, () => Promise.all([
      window.LongChangResources.interaction(),
      window.LongChangResources.json(getScene().url),
    ]));
    async function open() {
      const item = getScene();
      if (world && worldId === item.id) return world;
      if (loading) return loading;
      const token = ++version;
      stage.setAttribute('aria-busy', 'true'); status('Loading interaction…'); poster.src = item.poster; poster.hidden = false;
      loading = (async () => {
        let simulation = null;
        try {
          const [{createRoom}, config] = await Promise.all([
            window.LongChangResources.interaction(text => { if (token === version) status(text); }),
            window.LongChangResources.json(item.url),
          ]);
          if (token !== version) return null;
          simulation = await loadSimulation(config, text => { if (token === version) status(text); });
          if (token !== version) { simulation.destroy(); return null; }
          const next = await createRoom(stage, text => { if (token === version) status(text); }, {simulation, speed:Number($('speed').value), onInteraction:() => { if (token === version && active) wanted = true; }, onFrame:time => { if (token === version) { labels(time); onFrame(time, simulation); } }});
          if (token !== version) { next.destroy(); return null; }
          world = next; worldId = item.id; publish(); poster.hidden = true;
          stage.querySelector('.room-canvas').setAttribute('aria-describedby', `${prefix}-hint`);
          world.setMode(mode); sync();
          // Synchronize lifecycle before grabbing; pausing afterwards would drop the hand.
          try { handoff(); } catch (_) { clearPending(); status('Drag an object up to lift.'); }
          return world;
        } catch (error) {
          simulation?.destroy();
          if (token === version) { clearPending(); status('Could not load. Tap Drag to retry.'); }
          return null;
        } finally {
          if (token === version) { loading = null; stage.setAttribute('aria-busy', 'false'); }
        }
      })();
      return loading;
    }
    for (const button of bar.querySelectorAll(`[${modeAttribute}]`)) button.addEventListener('click', async () => {
      clearPending();
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
    $('reset').addEventListener('click', () => { clearPending(); wanted = false; world?.reset(); labels(0); });
    $('speed').addEventListener('change', () => world?.setSpeed(Number($('speed').value)));
    $('fullscreen').addEventListener('click', async () => {
      try { if (document.fullscreenElement) await document.exitFullscreen(); else await fullscreen.requestFullscreen(); }
      catch (_) { status(matchMedia('(pointer:coarse)').matches?'Pinch to zoom.':'Hold Ctrl/⌘ and scroll to zoom.'); }
    });
    stage.addEventListener('pointerdown', event => {
      if (!event.isPrimary) { clearPending(); return; }
      if (world || !active || event.button !== 0 || mode === 'view') return;
      event.preventDefault(); pending = {kind:mode, start:sample(event), latest:sample(event), released:false};
      stage.setPointerCapture(event.pointerId); open();
    });
    stage.addEventListener('pointermove', event => { if (pending?.start.pointerId === event.pointerId) pending.latest = sample(event); }, {passive:true});
    stage.addEventListener('pointerup', event => {
      if (pending?.start.pointerId !== event.pointerId) return;
      if (pending.kind === 'push') { pending.latest = sample(event); pending.released = true; if (world) handoff(); }
      else clearPending(event);
    });
    stage.addEventListener('pointercancel', clearPending);
    stage.addEventListener('lostpointercapture', event => { if (!pending?.released) clearPending(event); });
    window.addEventListener('blur', clearPending);
    document.addEventListener('keydown', event => { if (event.key === 'Escape') clearPending(); });
    stage.addEventListener('pointerup', () => queueMicrotask(() => labels()));
    new IntersectionObserver(sync).observe(host);
    // A show-and-scroll in the same frame can skip an intersection transition.
    // Recheck actual geometry after scrolling, including nested scroll areas.
    let scrollFrame = 0;
    document.addEventListener('scroll', () => {
      if (!scrollFrame) scrollFrame = requestAnimationFrame(() => { scrollFrame = 0; sync(); });
    }, {capture:true, passive:true});
    document.addEventListener('visibilitychange', sync);
    for (const dialog of document.querySelectorAll('dialog')) new MutationObserver(sync).observe(dialog, {attributes:true, attributeFilter:['open']});
    return {stage, bar, open, prepare:open, current:() => world, sync,
      setActive(value) { active = value; bar.hidden = !active; if (active) { publish(); open(); } else clearPending(); sync(); },
      select() { if (getScene().id !== worldId) { destroy(); if (active) open(); else prepareNearby(); } },
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
