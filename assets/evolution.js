
(() => {
  'use strict';
  const root=document.querySelector('#evolution-demos');
  const button=document.querySelector('#evolution-play');
  if(!root||!button)return;
  const videos=[...root.querySelectorAll('video')];
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let wanted=!reduced.matches,visible=false,revision=0,loadPromise=null,failed=false;
  const allowed=()=>wanted&&visible&&!document.hidden&&!document.querySelector('dialog[open]');

  function label() {
    button.textContent=failed?'Retry demos':wanted?'Pause demos':'Play demos';
    button.setAttribute('aria-label',failed?'Retry all three evolution demos':wanted?'Pause all three evolution demos':'Play all three evolution demos');
    button.setAttribute('aria-pressed',String(wanted));
  }

  function ready(video) {
    if(video.readyState>=2&&!video.error)return Promise.resolve();
    return new Promise((resolve,reject)=>{
      let timer;
      const clean=()=>{clearTimeout(timer);video.removeEventListener('loadeddata',done);video.removeEventListener('error',error);};
      const done=()=>{clean();resolve();};
      const error=()=>{clean();reject(new Error('Demo could not load'));};
      video.addEventListener('loadeddata',done);
      video.addEventListener('error',error);
      timer=setTimeout(error,15000);
      video.preload='auto';video.src=video.dataset.src;video.load();
    });
  }

  async function sync() {
    const ticket=++revision;
    label();
    if(!allowed()){videos.forEach(video=>video.pause());return;}
    try {
      if(!loadPromise)loadPromise=Promise.all(videos.map(ready));
      await loadPromise;
      if(ticket!==revision||!allowed())return;
      await Promise.all(videos.map(video=>video.play()));
      if(!allowed())videos.forEach(video=>video.pause());
    } catch(error) {
      loadPromise=null;
      if(ticket!==revision)return;
      videos.forEach(video=>video.pause());
      failed=true;wanted=false;label();
    }
  }

  button.addEventListener('click',()=>{wanted=!wanted;failed=false;sync();});
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();},{threshold:.08}).observe(root);
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',()=>{wanted=!reduced.matches;sync();});
  for(const dialog of document.querySelectorAll('dialog'))new MutationObserver(sync).observe(dialog,{attributes:true,attributeFilter:['open']});
  for(const video of videos)video.addEventListener('error',()=>{
    if(video.readyState>=2){failed=true;wanted=false;sync();}
  });
  label();
})();
