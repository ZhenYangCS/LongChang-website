/* Fast first paint: posters now, video and measurements only on request. */
(() => {
  'use strict';
  const $=s=>document.querySelector(s),items=window.SCENE_INDEX||[];if(!items.length)return;
  const video=$('#physics-video'),image=$('#studio-poster'),playButton=$('#physics-play'),speed=$('#physics-speed');
  let demo=null,wants=false,touring=false,byTour=false,shown=false,source=false,version=0,timer=0,details=null,detailAbort=null,posterVisible=false,posterLoading=false,pending=null,progressFrame=0;
  const measurements=$('#oracle-measurements'),law=$('#scene-law');
  const foot=document.createElement('div');foot.className='scene-foot';
  law.addEventListener('toggle',()=>{measurements.open=law.open;});
  law.append(measurements);foot.append(law,$('.physics-downloads'));$('.atlas-body').after(foot);
  foot.append($('#atlas-controls'));
  const originalLink=document.createElement('a');originalLink.className='original-download';originalLink.textContent='Image ↓';originalLink.setAttribute('download','');foot.append(originalLink);
  const originalCaption=document.createElement('p');originalCaption.className='original-caption';originalCaption.textContent='Recorded initial layout';$('#atlas-initial-view').after(originalCaption);
  function syncView(mode){
    law.hidden=mode!=='physics';$('.physics-downloads').hidden=mode!=='physics';$('#atlas-controls').hidden=mode!=='motion';
    originalLink.hidden=originalCaption.hidden=mode!=='initial';originalLink.href=$('#scene-image').src;
  }
  const navigation=$('.atlas-bottomline>div');navigation.className='atlas-navigation';$('.atlas-topline .world-meta').after(navigation);
  $('#oracle-chapters').hidden=true;$('#oracle-kind').hidden=true;$('#atlas-model-note').hidden=true;
  $('[data-atlas-view="physics"]').hidden=false;
  const overlay=document.createElement('button');overlay.id='scene-play-overlay';overlay.className='scene-play-overlay';overlay.textContent='▶ Play';overlay.setAttribute('aria-label','Play scene video');$('.physics-video-frame').append(overlay);
  const frame=$('.physics-video-frame');
  const zoom=window.createSceneZoom(frame,video,image);
  video.controls=false;video.preload='none';
  const media=()=>({url:demo.video,hash:demo.video_sha256,poster:demo.studio_poster,preview:demo.preview});
  function poster(){image.src=media().preview||media().poster;image.hidden=false;posterLoading=false;sharpenPoster();}
  function armTimeout(){clearTimeout(timer);timer=setTimeout(()=>{if(pending||(wants&&video.readyState<2))fail();},20000);}
  function loadSource(time=0){
    pending={time};source=true;const m=media();video.src=m.url+'?v='+m.hash.slice(0,12);video.load();loading(true);armTimeout();
  }
  function ready(){
    if(!source||video.readyState<2||video.seeking)return;
    if(pending){if(Math.abs(video.currentTime-pending.time)>.06){video.currentTime=pending.time;return;}pending=null;image.hidden=true;overlay.hidden=true;}
    loading(false);clearTimeout(timer);progress();if(wants&&video.paused)start();
  }
  function animateProgress(){
    progressFrame=0;if(video.paused||!source)return;
    $('#physics-progress').value=Math.round(video.currentTime/demo.duration*1000);
    progressFrame=video.requestVideoFrameCallback?video.requestVideoFrameCallback(animateProgress):requestAnimationFrame(animateProgress);
  }
  function cancelProgress(){if(progressFrame){if(video.cancelVideoFrameCallback)video.cancelVideoFrameCallback(progressFrame);else cancelAnimationFrame(progressFrame);}progressFrame=0;}
  const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  async function sharpenPoster(){
    if(!demo||posterLoading||!posterVisible)return;posterLoading=true;const token=version,next=new Image();next.src=media().poster;
    try{await next.decode();if(token===version&&!pending&&!image.hidden)image.src=next.src;}catch(_){/* Keep the embedded preview if the high-resolution image is unavailable. */}
  }
  new IntersectionObserver(entries=>{posterVisible=entries[0].isIntersecting;if(posterVisible)sharpenPoster();},{rootMargin:'300px'}).observe($('.physics-video-frame'));
  function tourLabel(){$('#atlas-tour').textContent=touring?'Ⅱ Pause tour':'▶ Play all 15 scenes';$('#atlas-tour').setAttribute('aria-pressed',String(touring));}
  function loading(value){$('.physics-video-frame').setAttribute('aria-busy',String(value));playButton.textContent=value?'…':video.paused?'▶':'Ⅱ';overlay.textContent=value?'Loading…':'▶ Play';}
  function stop(){wants=false;video.pause();cancelProgress();clearTimeout(timer);loading(false);progress();}
  function fail(){pending=null;stop();video.removeAttribute('src');video.load();source=false;image.hidden=false;overlay.hidden=false;overlay.textContent='↻ Retry';$('#physics-error').textContent='Video unavailable. Tap Retry.';$('#physics-error').hidden=false;}
  function start(){
    wants=true;$('#physics-error').hidden=true;
    if(!source){loadSource();return;}
    loading(video.readyState<2);armTimeout();
    if(video.readyState<2||pending)return;
    if(video.ended)video.currentTime=0;
    video.playbackRate=Number(speed.value);const token=version;
    video.play().catch(e=>{if(token===version&&e.name!=='AbortError')fail();});
  }
  function simTime(){const map=demo.time_map;for(let i=0;i<map.length-1;i++){const [a,x]=map[i],[b,y]=map[i+1];if(video.currentTime<=b)return x+(y-x)*(video.currentTime-a)/(b-a);}return map.at(-1)[1];}
  function progress(){
    if(!demo)return;
    $('#physics-progress').value=Math.round(video.currentTime/demo.duration*1000);
    $('#physics-clock').textContent=`${clock(video.currentTime)} / ${clock(demo.duration)}`;
    playButton.textContent=video.paused?'▶':'Ⅱ';playButton.setAttribute('aria-label',video.paused?'Play scene video':'Pause scene video');
    let phase='';for(const [t,text]of demo.phases){if(t>video.currentTime)break;phase=text;}
    $('#simple-phase').textContent=phase;$('#simple-phase').hidden=!image.hidden||!phase;
    if(details&&measurements.open)plot();
  }
  function select(id){
    const next=items.find(d=>d.id===id);if(!next)return;
    if(demo?.id===id)return;
    stop();version++;demo=next;details=null;detailAbort?.abort();source=false;pending=null;posterLoading=false;
    if(video.hasAttribute('src')){video.removeAttribute('src');video.load();}
    video.playbackRate=Number(speed.value);image.alt=demo.name;zoom.setScene(demo);poster();
    overlay.hidden=false;loading(false);$('#physics-error').hidden=true;
    $('.physics-video-frame').classList.remove('is-oracle','is-simple','is-clear');
    $('.physics-video-frame').classList.add(demo.presentation==='clear'?'is-clear':'is-simple');
    video.setAttribute('aria-label',`${demo.name}: demonstration of the hidden rule`);
    law.open=false;measurements.open=false;$('#physics-download').href=demo.download_video||demo.video;$('#physics-record').href=demo.record;
    $('#oracle-signal-download').hidden=true;progress();tourLabel();
  }
  function plot(){
    const t=simTime(),entry=details,sample=entry.timeline[Math.min(entry.timeline.length-1,Math.floor(video.currentTime*entry.fps))];
    $('#physics-sample-label').textContent=`t = ${sample.time.toFixed(2)} s`;
    $('#physics-values').innerHTML=sample.annotation.values.map(([k,v])=>`<div><span>${k}</span><strong>${v}</strong></div>`).join('');
    const p=entry.plot,left=35,right=625,top=15,bottom=135,max=Math.max(.1,...p.series.flat()),min=Math.min(0,...p.series.flat());
    const xy=(x,y)=>[left+x/entry.simulation_duration*(right-left),bottom-(y-min)/(max-min||1)*(bottom-top)];
    if(!$('#oracle-chart').dataset.drawn){let svg='';p.series.forEach((values,i)=>{const d=p.times.map((time,j)=>(j?'L':'M')+xy(time,values[j]).map(x=>x.toFixed(2)).join(' ')).join('');svg+=`<path d="${d}" stroke="${p.colors[i]}" stroke-width="2" fill="none"/>`;});
    svg+=`<path id="oracle-cursor" d="M0 ${top}V${bottom}" stroke="#567a69"/><text x="${left}" y="158" fill="#71867c" font-size="10">0</text><text x="${right}" y="158" text-anchor="end" fill="#71867c" font-size="10">${entry.simulation_duration} s</text>`;
    $('#oracle-chart').innerHTML=svg;$('#oracle-chart').dataset.drawn='true';}
    $('#oracle-cursor').setAttribute('transform',`translate(${xy(t,0)[0]},0)`);$('#oracle-chart-legend').textContent=p.labels.join(' / ');$('#oracle-signal').textContent=entry.oracle.measure;
  }
  measurements.addEventListener('toggle',async()=>{
    if(!measurements.open||details)return;const id=demo.id;detailAbort=new AbortController();
    try{const response=await fetch(demo.details,{signal:detailAbort.signal});if(!response.ok)throw Error();const data=await response.json();if(id!==demo.id)return;details=data;$('#oracle-chart').dataset.drawn='';$('#oracle-chart-wrap').hidden=false;plot();}
    catch(e){if(e.name!=='AbortError')$('#physics-sample-label').textContent='Measurements unavailable. Reopen to retry.';}
  });
  playButton.addEventListener('click',()=>{if(video.paused&&!wants)start();else{touring=false;stop();tourLabel();}});
  overlay.addEventListener('click',start);
  $('#physics-reset').addEventListener('click',()=>{touring=false;stop();if(source){pending=null;video.currentTime=0;}poster();overlay.hidden=false;progress();tourLabel();});
  $('#physics-progress').addEventListener('input',event=>{
    const destination=Number(event.target.value)/1000*demo.duration;touring=false;stop();
    if(!source)loadSource(destination);else{pending={time:destination};video.currentTime=destination;}
    overlay.hidden=true;progress();tourLabel();
  });
  speed.addEventListener('change',()=>{video.playbackRate=Number(speed.value);});
  video.addEventListener('loadedmetadata',()=>{video.playbackRate=Number(speed.value);if(pending)video.currentTime=pending.time;progress();});
  video.addEventListener('canplay',ready);
  video.addEventListener('playing',()=>{clearTimeout(timer);if(!pending)image.hidden=true;overlay.hidden=true;loading(false);progress();cancelProgress();animateProgress();});
  video.addEventListener('waiting',()=>{if(wants){loading(true);armTimeout();}});
  video.addEventListener('pause',()=>{cancelProgress();progress();});video.addEventListener('timeupdate',progress);video.addEventListener('seeked',()=>{if(pending)ready();else progress();});
  video.addEventListener('error',()=>{if(source)fail();});
  video.addEventListener('ended',()=>{wants=false;if(touring){byTour=true;window.showWorld(String(Number(demo.id)%15+1).padStart(2,'0'));byTour=false;start();}else{overlay.hidden=false;overlay.textContent='↺ Replay';progress();}});
  $('#physics-fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('#atlas-physics-view').requestFullscreen();}catch(_){start();video.controls=true;}});
  document.addEventListener('fullscreenchange',()=>{video.controls=false;});
  document.addEventListener('longchang:atlas-view',e=>{shown=e.detail.view==='physics';syncView(e.detail.view);if(shown)select(e.detail.id);else{touring=false;stop();tourLabel();}});
  document.addEventListener('longchang:scene',e=>{if(!byTour)touring=false;select(e.detail.id);tourLabel();});
  new IntersectionObserver(e=>{if(!e[0].isIntersecting&&source)stop();},{threshold:0}).observe($('#atlas-physics-view'));
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  window.LongChangPhysics=Object.freeze({play:start,toggleTour(){touring=!touring;if(touring){byTour=true;window.showWorld('01');byTour=false;start();}else stop();tourLabel();}});
  shown=$('.atlas-detail').dataset.view==='physics';syncView($('.atlas-detail').dataset.view);select(window.LongChangAtlas.currentScene());
})();
