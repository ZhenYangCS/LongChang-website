
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
    video.controls = false;
    const start = film.querySelector('.case-film-start');
    const status = film.querySelector('.case-film-status');
    const retry = status.querySelector('button');
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

    function play() {
      if (film.closest('.case-panel').hidden || document.hidden) return;
      playRequested = true;
      video.controls = true;
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

        if (error.name !== 'AbortError' && playRequested) {
          clearStatus();
          start.hidden = false;
          playRequested = false;
        }
      });
    }

    start.addEventListener('click', play);
    retry.addEventListener('click', () => { clearStatus(); video.load(); play(); });
    document.addEventListener('longchang:case-select', event => {
      if(event.detail!==film.dataset.film)return;
      video.pause();video.currentTime=0;play();
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
    video.addEventListener('ended', () => { start.hidden = false; });
    video.addEventListener('error', failed);
    observer.observe(video);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) pauseAll(); });
  document.addEventListener('longchang:presentation-open', pauseAll);
  document.querySelector('#success-video')?.addEventListener('play', pauseAll);
})();
