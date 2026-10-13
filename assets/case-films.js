/* Three recorded films. Native video controls handle playback and fullscreen. */
(() => {
  'use strict';
  const films = [...document.querySelectorAll('.case-film')];
  const videos = films.map(film => film.querySelector('video'));
  const pauseAll = () => videos.forEach(video => video.pause());
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => { if (!entry.isIntersecting) entry.target.pause(); });
  });

  for (const film of films) {
    const video = film.querySelector('video');
    const start = film.querySelector('.case-film-start');
    const status = film.querySelector('.case-film-status');
    const retry = status.querySelector('button');
    const chapters = [...film.querySelectorAll('[data-film-seek]')];
    const caption = film.querySelector('.case-film-caption');
    let pendingTime = null;
    let playRequested = false;
    let loadFailed = false;
    let loadingTimer;

    function clearStatus() {
      clearTimeout(loadingTimer);
      loadFailed = false;
      status.hidden = true;
      retry.hidden = true;
    }

    function failed() {
      clearTimeout(loadingTimer);
      loadFailed = true;
      playRequested = false;
      video.pause();
      status.hidden = false;
      status.querySelector('span').textContent = 'The film could not load.';
      retry.hidden = false;
      start.hidden = true;
    }

    function progress() {
      const current = chapters.filter(button => Number(button.dataset.filmSeek) <= video.currentTime + .05).at(-1) || chapters[0];
      chapters.forEach(button => button.setAttribute('aria-pressed', String(button === current)));
      caption.textContent = current.dataset.filmCaption;
    }

    function play() {
      if (film.closest('.case-panel').hidden || document.hidden) return;
      playRequested = true;
      start.hidden = true;
      videos.forEach(other => { if (other !== video) other.pause(); });
      if (video.error) video.load();
      if (video.ended) video.currentTime = 0;
      if (video.readyState < 2) {
        status.querySelector('span').textContent = 'Loading film…';
        status.hidden = false;
        retry.hidden = true;
        clearTimeout(loadingTimer);
        loadingTimer = setTimeout(failed, 15000);
      }
      video.play().catch(error => {
        // A tab change or seek may interrupt a pending play request.
        if (error.name !== 'AbortError' && playRequested) {
          clearStatus();
          start.hidden = false;
          playRequested = false;
        }
      });
    }

    start.addEventListener('click', play);
    retry.addEventListener('click', () => { clearStatus(); video.load(); play(); });
    chapters.forEach(button => button.addEventListener('click', () => {
      pendingTime = Number(button.dataset.filmSeek);
      if (video.readyState >= 1) {
        video.currentTime = pendingTime;
        pendingTime = null;
      }
      play();
    }));
    video.addEventListener('loadedmetadata', () => {
      if (pendingTime !== null) {
        video.currentTime = Math.min(pendingTime, Math.max(0, video.duration - .05));
        pendingTime = null;
      }
    });
    video.addEventListener('playing', () => {
      if (film.closest('.case-panel').hidden || document.hidden) { video.pause(); return; }
      playRequested = true;
      start.hidden = true;
      clearStatus();
      videos.forEach(other => { if (other !== video) other.pause(); });
      document.dispatchEvent(new CustomEvent('longchang:case-film-play'));
    });
    video.addEventListener('pause', () => {
      playRequested = false;
      if (loadFailed) clearTimeout(loadingTimer); else clearStatus();
    });
    video.addEventListener('ended', () => { start.hidden = false; progress(); });
    video.addEventListener('error', failed);
    video.addEventListener('timeupdate', progress);
    observer.observe(video);
    progress();
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) pauseAll(); });
  document.addEventListener('longchang:presentation-open', pauseAll);
  document.querySelector('#success-video')?.addEventListener('play', pauseAll);
})();
