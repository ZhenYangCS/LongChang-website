(() => {
  'use strict';
  const films = [...document.querySelectorAll('.case-film')];
  const template = document.querySelector('#case-playback-template');
  if (!template) return;
  const timeLabel = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  const pauseAll = () => players.forEach(player => player.pause());

  const players = films.map(film => {
    const video = film.querySelector('video');
    film.querySelector('.case-film-screen').after(template.content.cloneNode(true));
    video.controls = false;
    const controls = film.querySelector('.case-playback');
    const playButton = controls.querySelector('.case-play');
    const progress = controls.querySelector('.case-progress');
    const clock = controls.querySelector('.case-clock');
    const speed = controls.querySelector('.case-speed');
    video.defaultPlaybackRate = video.playbackRate = Number(speed.value);
    const fullscreen = controls.querySelector('.case-fullscreen');
    const status = film.querySelector('.case-film-status');
    const retry = status.querySelector('button');
    const storySteps = [...film.querySelectorAll('[data-case-stage]')];
    let playRequested = false;
    let loadFailed = false;
    let loadingMetadata = false;
    let pendingSeek = null;
    let scrubbing = false;
    let resumeAfterScrub = false;
    let loadingTimer;
    let frame;
    const active = () => !film.closest('.case-panel').hidden && !document.hidden;
    const duration = () => Number.isFinite(video.duration) ? video.duration : Number(film.dataset.duration);

    function update() {
      const total = duration();
      const current = pendingSeek !== null ? pendingSeek * total : video.currentTime;
      if (storySteps.length) {
        const step = storySteps.findLast(item => current >= Number(item.dataset.start)) || storySteps[0];
        storySteps.forEach(item => { item.hidden = item !== step; });
      }
      if (!scrubbing) progress.value = total ? current / total * 1000 : 0;
      progress.style.setProperty('--case-progress', `${Number(progress.value) / 10}%`);
      progress.setAttribute('aria-valuetext', `${timeLabel(current)} of ${timeLabel(total)}`);
      clock.textContent = `${timeLabel(current)} / ${timeLabel(total)}`;
      controls.classList.toggle('is-playing', !video.paused);
      playButton.setAttribute('aria-label', video.paused ? 'Play case study' : 'Pause case study');
      playButton.title = video.paused ? 'Play' : 'Pause';
    }

    function animate() {
      update();
      if (!video.paused && !video.ended) frame = requestAnimationFrame(animate);
    }

    function clearStatus() {
      clearTimeout(loadingTimer);
      loadFailed = false;
      status.hidden = true;
      retry.hidden = true;
    }

    function failed() {
      clearTimeout(loadingTimer);
      loadFailed = true;
      loadingMetadata = false;
      playRequested = false;
      resumeAfterScrub = false;
      video.pause();
      status.hidden = false;
      status.querySelector('span').textContent = 'The film could not load.';
      retry.hidden = false;
    }

    function showLoading() {
      clearStatus();
      status.querySelector('span').textContent = 'Loading film…';
      status.hidden = false;
      loadingTimer = setTimeout(failed, 15000);
    }

    function pause() {
      resumeAfterScrub = false;
      scrubbing = false;
      playRequested = false;
      video.pause();
      if (!loadFailed) clearStatus();
      update();
    }

    function play() {
      if (!active()) return;
      players.forEach(player => { if (player.video !== video) player.pause(); });
      playRequested = true;
      if (video.error) video.load();
      if (video.ended) video.currentTime = 0;
      if (video.readyState < 2) showLoading();
      video.play().catch(error => {
        if (error.name !== 'AbortError' && playRequested) {
          playRequested = false;
          if (video.error) failed(); else clearStatus();
          update();
        }
      });
    }

    function seek(fraction) {
      pendingSeek = fraction;
      if (video.readyState >= 1) {
        video.currentTime = fraction * duration();
        pendingSeek = null;
      } else if (!loadingMetadata) {
        loadingMetadata = true;
        video.preload = 'auto';
        video.load();
        showLoading();
      }
      update();
    }

    playButton.addEventListener('click', () => {
      if (video.paused && !playRequested) play(); else pause();
    });
    controls.querySelector('.case-reset').addEventListener('click', () => { seek(0); play(); });
    speed.addEventListener('change', () => { video.defaultPlaybackRate = video.playbackRate = Number(speed.value); });
    retry.addEventListener('click', () => { clearStatus(); video.load(); play(); });

    progress.addEventListener('pointerdown', event => {
      if (event.button !== 0) return;
      scrubbing = true;
      resumeAfterScrub = !video.paused || playRequested;
      video.pause();
      progress.setPointerCapture(event.pointerId);
    });
    progress.addEventListener('input', () => seek(Number(progress.value) / 1000));
    function finishScrub() {
      if (!scrubbing) return;
      scrubbing = false;
      const resume = resumeAfterScrub;
      resumeAfterScrub = false;
      update();
      if (resume) play();
    }
    progress.addEventListener('pointerup', finishScrub);
    progress.addEventListener('pointercancel', finishScrub);
    progress.addEventListener('lostpointercapture', finishScrub);
    progress.addEventListener('blur', finishScrub);

    fullscreen.hidden = !document.fullscreenEnabled && !video.webkitEnterFullscreen;
    fullscreen.addEventListener('click', async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else if (document.fullscreenEnabled) await film.requestFullscreen();
        else video.webkitEnterFullscreen();
      } catch (_) { /* The player remains usable if fullscreen is unavailable. */ }
    });
    document.addEventListener('fullscreenchange', () => {
      const expanded = document.fullscreenElement === film;
      fullscreen.setAttribute('aria-label', expanded ? 'Exit case study fullscreen' : 'Expand case study');
      fullscreen.title = expanded ? 'Exit fullscreen' : 'Fullscreen';
    });

    video.addEventListener('loadedmetadata', () => {
      loadingMetadata = false;
      if (pendingSeek !== null) seek(pendingSeek);
      update();
    });
    video.addEventListener('loadeddata', clearStatus);
    video.addEventListener('playing', () => {
      if (!active()) { pause(); return; }
      playRequested = true;
      clearStatus();
      players.forEach(player => { if (player.video !== video) player.pause(); });
      cancelAnimationFrame(frame);
      animate();
      document.dispatchEvent(new CustomEvent('longchang:case-film-play'));
    });
    video.addEventListener('pause', () => {
      playRequested = false;
      cancelAnimationFrame(frame);
      if (!loadFailed) clearStatus();
      update();
    });
    video.addEventListener('timeupdate', update);
    video.addEventListener('ended', update);
    video.addEventListener('error', failed);
    update();
    return {video, pause, select() { pause(); pendingSeek = 0; if (video.readyState >= 1) seek(0); play(); }};
  });

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) players.find(player => player.video === entry.target)?.pause();
    });
  });
  players.forEach(player => observer.observe(player.video));
  document.addEventListener('longchang:case-select', event => {
    pauseAll();
    const index = films.findIndex(film => film.dataset.film === event.detail);
    players[index]?.select();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pauseAll(); });
  document.addEventListener('longchang:presentation-open', pauseAll);
  document.querySelector('#success-video')?.addEventListener('play', pauseAll);
})();
