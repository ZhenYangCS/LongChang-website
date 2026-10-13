(() => {
  'use strict';
  const cases = window.DISCOVERIES;
  if (!cases?.length) return;
  const $ = q => document.querySelector(q);
  const $$ = q => [...document.querySelectorAll(q)];
  const esc = v => String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let selected=0,chapter=0;
  const video=$('#success-video'),slider=$('#replay-progress'),play=$('#replay-play');
  let wantsVideo=false,videoAnimation=0;
  let pendingSource=null;

  function setTab(button) {
    button.closest('[role="tablist"]').querySelectorAll('[role="tab"]').forEach(b=>{
      b.setAttribute('aria-selected',String(b===button));b.tabIndex=b===button?0:-1;
    });
  }
  function keyboardTabs(root,choose) {
    root.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
      const buttons=[...root.querySelectorAll('[role="tab"]')],i=buttons.indexOf(document.activeElement);
      if(i<0)return;e.preventDefault();
      const n=e.key==='Home'?0:e.key==='End'?buttons.length-1:(i+(e.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;
      choose(buttons[n]);buttons[n].focus();
    });
  }
  function videoProgress() {
    const c=cases[selected].chapters[chapter];
    const fraction=Number.isFinite(video.duration)&&video.duration>0?video.currentTime/video.duration:0;
    slider.value=String(Math.round(fraction*1000));$('#replay-percent').textContent=`${Math.round(fraction*100)}%`;
    $('#success-clock').textContent=`${(c.start+fraction*(c.end-c.start)).toFixed(2)} counts`;
    if(!video.paused)videoAnimation=requestAnimationFrame(videoProgress);
  }
  function pauseVideo() {
    wantsVideo=false;video.pause();cancelAnimationFrame(videoAnimation);
    play.innerHTML='<span aria-hidden="true">▶</span>';play.setAttribute('aria-label','Play recorded experiment');
  }
  function startVideo() {
    wantsVideo=true;
    if(pendingSource){video.preload='auto';video.src=pendingSource;pendingSource=null;video.load();}
    if(video.readyState<2){play.textContent='…';return;}
    if(video.ended||video.currentTime>=video.duration-.04)video.currentTime=0;
    video.playbackRate=Number($('#replay-speed').value);
    video.play().then(()=>{
      if(!wantsVideo){video.pause();return;}
      play.innerHTML='<span aria-hidden="true">II</span>';play.setAttribute('aria-label','Pause recorded experiment');
      cancelAnimationFrame(videoAnimation);videoProgress();
    }).catch(()=>{pauseVideo();});
  }
  function loadVideo(c) {
    pauseVideo();video.poster=c.poster;
    video.removeAttribute('src');video.load();
    pendingSource=c.video;video.preload='none';
  }
  video.addEventListener('loadedmetadata',videoProgress);
  $('#replay-speed').addEventListener('change',()=>{video.playbackRate=Number($('#replay-speed').value);});
  video.addEventListener('loadeddata',()=>{videoProgress();if(wantsVideo)startVideo();});
  video.addEventListener('ended',()=>{pauseVideo();videoProgress();});
  video.addEventListener('error',pauseVideo);
  play.addEventListener('click',()=>video.paused&&!wantsVideo?startVideo():pauseVideo());
  slider.addEventListener('input',()=>{
    const value=Number(slider.value)/1000;pauseVideo();
    if(Number.isFinite(video.duration))video.currentTime=Math.min(video.duration-.025,value*video.duration);
    videoProgress();
  });
  $('#replay-reset').addEventListener('click',()=>{pauseVideo();video.currentTime=0;videoProgress();});
  $('#replay-fullscreen').addEventListener('click',async()=>{
    try { if(document.fullscreenElement)await document.exitFullscreen();else await video.closest('.success-video-frame').requestFullscreen(); } catch(_){video.controls=true;}
  });
  document.addEventListener('fullscreenchange',()=>{video.controls=document.fullscreenElement===video.closest('.success-video-frame');});
  new IntersectionObserver(e=>{if(!e[0].isIntersecting)pauseVideo();}).observe(video);

  function chooseChapter(button) {
    chapter=Number(button.dataset.chapter);setTab(button);
    const c=cases[selected].chapters[chapter];
    $('#success-evidence').setAttribute('aria-labelledby',button.id);
    $('#success-chapter-title').textContent=c.title;$('#success-description').textContent=c.description;
    $('#success-note').textContent=c.note;$('#success-note-source').textContent=`Original note · Turn ${c.noteTurn}`;
    $('#success-turns').textContent=`Turns ${c.turns[0]}–${c.turns[c.turns.length-1]}`;
    $('#success-clock').textContent=`${c.start.toFixed(2)} counts`;
    $('#success-note').closest('details').open=false;
    slider.value='0';$('#replay-percent').textContent='0%';loadVideo(c);
  }
  $('#success-picker').innerHTML=cases.map((c,i)=>`<button id="success-tab-${c.id}" role="tab" aria-controls="discovery-workbench" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-discovery="${i}"><span>SCENE ${c.id}</span><strong>${esc(c.short)}</strong></button>`).join('');
  function chooseDiscovery(button) {
    selected=Number(button.dataset.discovery);setTab(button);pauseVideo();
    const c=cases[selected];
    $('#discovery-workbench').setAttribute('aria-labelledby',button.id);
    $('#discovery-index').textContent=`Scene ${c.id}`;
    $('#discovery-world-link').href=`?scene=${c.id}#worlds`;
    $('#discovery-title').textContent=c.name;$('#discovery-question').textContent=c.intro;
    $('#discovery-run').textContent=`Astra · repeat ${c.repeat} · ${c.turns} turns`;
    $('#discovery-conclusion').textContent=c.conclusion;$('#success-final-note').textContent=c.finalNote;
    $('#success-final-note').closest('details').open=false;
    $('#success-source-label').textContent=`GPT-6-Astra · 100-turn budget · C and S passed · judge: ${c.judge}`;
    $('#success-chapters').innerHTML=c.chapters.map((s,i)=>`<button id="evidence-chapter-${i}" role="tab" aria-controls="success-evidence" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-chapter="${i}"><span>0${i+1}</span>${esc(s.title)}</button>`).join('');
    $$('#success-chapters button').forEach(b=>b.addEventListener('click',()=>chooseChapter(b)));
    chooseChapter($('#evidence-chapter-0'));
  }
  $$('#success-picker button').forEach(b=>b.addEventListener('click',()=>chooseDiscovery(b)));
  keyboardTabs($('#success-picker'),chooseDiscovery);keyboardTabs($('#success-chapters'),chooseChapter);
  window.showDiscovery=id=>{
    const b=$(`#success-tab-${id}`);if(!b)return;chooseDiscovery(b);
    const dialog=$('#exploration-dialog');if(dialog&&!dialog.open)dialog.showModal();
    const archive=$('#successful-explorations');archive.open=true;
    for(let parent=archive.parentElement;parent;parent=parent.parentElement){if(parent.tagName==='DETAILS')parent.open=true;}
    archive.scrollIntoView({behavior:reduced?'instant':'smooth',block:'start'});
    b.focus({preventScroll:true});
  };
  $('#successful-explorations').addEventListener('toggle',e=>{if(!e.target.open)pauseVideo();});
  $('#exploration-close')?.addEventListener('click',()=>$('#exploration-dialog').close());
  $('#exploration-dialog')?.addEventListener('close',pauseVideo);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseVideo();});
  document.addEventListener('longchang:presentation-open',pauseVideo);
  document.addEventListener('longchang:case-film-play',pauseVideo);
  chooseDiscovery($('#success-tab-07'));
})();
