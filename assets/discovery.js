/* Compare two archived trials on a shared clock measured in simulation counts. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const dialog = $('#exploration-dialog');
  const videos = [$('#success-video'), $('#comparison-video')];
  const play = $('#replay-play'), slider = $('#replay-progress'), status = $('#success-status');
  const ns = 'http://www.w3.org/2000/svg';
  const svgNode = (tag, attributes = {}) => {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, value));
    return node;
  };
  const guides = videos.map(video => {
    const svg = svgNode('svg', {viewBox:'0 0 1600 992', class:'discovery-guide', 'aria-hidden':'true'});
    video.after(svg);
    return {svg, data:null, tracks:[], frame:-1};
  });
  let guideRequest = null;
  const comparisons = {
    '07': {
      chapters: [1, 2],
      finding: 'The same ball rebounds much higher on red.',
      actions: ['Same ball · blue tile', 'Same ball · red tile'],
      outcomes: ['Barely rebounds after landing.', 'Bounces high after landing.'],
      conclusion: 'Same ball and launch impulse. Changing the surface changes the rebound.'
    },
    '06': {
      chapters: [0, 1],
      finding: 'The sideways force turns with the direction of motion.',
      actions: ['Push east', 'Push north'],
      outcomes: ['The path bends south.', 'The path bends east.'],
      conclusion: 'Change the launch direction: the path still bends clockwise.'
    },
    '14': {
      chapters: [0, 1],
      finding: 'Green moves later, even when red has been stopped.',
      actions: ['Push red north', 'Push red east, then hold it'],
      outcomes: ['Green moves north after about 12 counts.', 'Green still moves east while red is held.'],
      conclusion: 'Stopping red does not cancel green’s delayed response.'
    },
    '15': {
      chapters: [1, 2],
      finding: 'Pushing either ball pauses red’s northward force.',
      actions: ['Push red', 'Push distant blue'],
      outcomes: ['Red’s northward force returns after about 10 counts.', 'Red’s northward force returns on the same timer.'],
      conclusion: 'Watch red in both trials: acting on blue also resets red’s force.'
    }
  };
  let entry = null, trials = [], leader = 0, duration = 0;
  let wants = false, failed = false, version = 0, frame = 0, timer = 0, origin = null, pendingTime = null;
  const lead = () => videos[leader];
  const span = index => trials[index].end-trials[index].start;
  const clipDuration = index => Number.isFinite(videos[index].duration) ? videos[index].duration : trials[index].duration;
  const currentTime = () => pendingTime ?? (entry ? lead().currentTime/clipDuration(leader)*duration : 0);

  function drawGuides() {
    guides.forEach((guide, index) => {
      if (!guide.data) return;
      const frameIndex = Math.min(guide.data.tracks[0].points.length-1, Math.floor(videos[index].currentTime*guide.data.fps));
      if (frameIndex === guide.frame) return;
      guide.frame = frameIndex;
      guide.svg.dataset.frame = String(frameIndex);
      guide.tracks.forEach(({track, path, underlay, circle, label, box}) => {
        const points = track.points.slice(0, frameIndex+1), [x, y] = points.at(-1);
        const d = points.map((point, i) => `${i ? 'L' : 'M'}${point.join(',')}`).join('');
        path.setAttribute('d', d); underlay.setAttribute('d', d);
        circle.setAttribute('cx', x); circle.setAttribute('cy', y);
        const lx = Math.max(100, Math.min(1500, x));
        const ly = Math.max(60, y-track.radius-36);
        label.setAttribute('x', lx); label.setAttribute('y', ly);
        box.setAttribute('x', lx-100); box.setAttribute('y', ly-38);
      });
    });
  }
  function loadGuides() {
    const token = version;
    guides.forEach(guide => { guide.svg.replaceChildren(); guide.data = null; guide.frame = -1; });
    if (!guideRequest) guideRequest = fetch('data/discovery-guides.json').then(response => {
      if (!response.ok) throw new Error('Motion guides unavailable');
      return response.json();
    }).catch(() => { guideRequest = null; return null; });
    guideRequest.then(data => {
      if (!data || token !== version || !entry) return;
      guides.forEach((guide, index) => {
        guide.data = data[trials[index].video];
        if (!guide.data) return;
        guide.tracks = guide.data.tracks.map(track => {
          const group = svgNode('g', {'data-object':track.name, style:`--track-color:${track.color}`});
          const underlay = svgNode('path', {class:'discovery-trail-base'});
          const path = svgNode('path', {class:'discovery-trail'});
          const circle = svgNode('circle', {class:'discovery-target', r:track.radius+10});
          const box = svgNode('rect', {width:200, height:52, rx:12, class:'discovery-target-label'});
          const label = svgNode('text', {'text-anchor':'middle'});
          label.textContent = track.label;
          group.append(underlay, path, circle, box, label);
          guide.svg.append(group);
          return {track, path, underlay, circle, label, box};
        });
      });
      drawGuides();
    });
  }

  function paint() {
    if (!entry) return;
    const time = Math.min(duration, currentTime());
    slider.value = String(Math.round(time/duration*1000));
    $('#replay-time').textContent = `${time.toFixed(1)} / ${duration.toFixed(1)} counts`;
    dialog.dataset.time = time.toFixed(3);
    const playing = wants && !lead().paused;
    play.textContent = playing ? 'Ⅱ' : '▶';
    play.setAttribute('aria-label', failed ? 'Retry experiments' : playing ? 'Pause both experiments' : time >= duration-.03 ? 'Replay both experiments' : 'Play both experiments');
    drawGuides();
  }
  function cancelFrame() {
    cancelAnimationFrame(frame);
    frame = 0;
  }
  function configureRates() {
    if (!entry) return;
    // Preserve a common simulation time when the source clips used different
    // slow-motion rates. A shorter trial holds its final frame.
    videos.forEach((video, index) => {
      video.playbackRate = duration/clipDuration(leader)*clipDuration(index)/span(index);
    });
  }
  function seek(time) {
    pendingTime = time;
    videos.forEach((video, index) => {
      if (video.readyState > 0) video.currentTime = Math.min(time/span(index), 1)*clipDuration(index);
    });
    if (videos.every(video => video.readyState > 0)) pendingTime = null;
    paint();
  }
  function tick() {
    frame = 0;
    if (!entry || !dialog.open || !wants) return;
    const time = currentTime();
    videos.forEach((video, index) => {
      if (index === leader || video.readyState < 2 || video.seeking) return;
      const target = Math.min(time/span(index), 1)*clipDuration(index);
      if (Math.abs(video.currentTime-target) > .12) video.currentTime = target;
      if (time >= span(index)) video.pause();
    });
    paint();
    frame = requestAnimationFrame(tick);
  }
  function pause() {
    wants = false;
    clearTimeout(timer);
    videos.forEach(video => video.pause());
    cancelFrame();
    if (!failed) status.hidden = true;
    paint();
  }
  function fail() {
    if (!entry || !dialog.open) return;
    pause();
    failed = true;
    status.textContent = 'An experiment could not load. Press play to retry.';
    status.hidden = false;
    paint();
  }
  async function start() {
    if (!entry || !dialog.open) return;
    if (failed) {
      failed = false;
      pendingTime = 0;
      videos.forEach(video => video.load());
    }
    if (lead().ended || currentTime() >= duration-.03) seek(0);
    wants = true;
    const token = version;
    configureRates();
    status.textContent = 'Loading experiments…';
    status.hidden = videos.every(video => video.readyState >= 2);
    clearTimeout(timer);
    timer = setTimeout(() => { if (token === version && wants && videos.some(video => video.readyState < 2)) fail(); }, 20000);
    try {
      await Promise.all(videos.map((video, index) => currentTime() < span(index) ? video.play() : Promise.resolve()));
      if (token !== version) return;
      if (!wants || !dialog.open) { videos.forEach(video => video.pause()); return; }
      clearTimeout(timer);
      status.hidden = true;
      cancelFrame();
      tick();
    } catch (error) {
      if (token === version && wants && error.name !== 'AbortError') fail();
    }
    paint();
  }

  play.addEventListener('click', () => wants ? pause() : start());
  slider.addEventListener('input', () => {
    if (!entry) return;
    const time = Number(slider.value)/1000*duration;
    pause();
    seek(time);
  });
  videos.forEach(video => {
    video.addEventListener('loadedmetadata', () => {
      if (!entry) return;
      configureRates();
      if (pendingTime !== null) seek(pendingTime);
      paint();
    });
    video.addEventListener('timeupdate', paint);
    video.addEventListener('ended', () => { if (video === lead()) pause(); });
    video.addEventListener('error', fail);
  });
  $('#replay-fullscreen').addEventListener('click', async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await $('.exploration-player').requestFullscreen();
  });
  $('#exploration-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    version++;
    pause();
    entry = null;
    pendingTime = null;
    videos.forEach(video => { video.removeAttribute('src'); video.load(); });
    const target = origin?.isConnected && origin.getClientRects().length ? origin : $('.result-row[aria-pressed=true]');
    target?.focus({preventScroll:true});
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  document.addEventListener('longchang:presentation-open', pause);
  document.addEventListener('longchang:evidence-open', pause);
  document.addEventListener('longchang:case-film-play', pause);
  window.showDiscovery = id => {
    const next = (window.DISCOVERIES || []).find(item => item.id === id), comparison = comparisons[id];
    if (!next || !comparison) return;
    origin = document.activeElement;
    version++;
    pause();
    entry = next;
    trials = comparison.chapters.map(index => entry.chapters[index]);
    duration = Math.max(...trials.map((_, index) => span(index)));
    leader = trials.findIndex((_, index) => span(index) === duration);
    failed = false;
    pendingTime = 0;
    dialog.dataset.scene = id;
    $('#discovery-title').textContent = entry.name;
    $('#discovery-finding').textContent = comparison.finding;
    $('#discovery-source').textContent = `Scene ${id} · Recorded experiments · ${entry.model}`;
    $('#success-description').textContent = comparison.conclusion;
    videos.forEach((video, index) => {
      $(`#discovery-action-${index}`).textContent = comparison.actions[index];
      $(`#discovery-outcome-${index}`).textContent = comparison.outcomes[index];
      video.poster = trials[index].poster;
      video.src = trials[index].video;
      video.load();
    });
    slider.value = '0';
    loadGuides();
    paint();
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
    start();
  };
})();
