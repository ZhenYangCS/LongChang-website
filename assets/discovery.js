/* One selected discovery, one continuous replay, and a changing caption. */
(() => {
  'use strict';
  const films=window.DISCOVERY_FILMS||[], $=q=>document.querySelector(q);
  const dialog=$('#exploration-dialog'),video=$('#success-video'),play=$('#replay-play'),slider=$('#replay-progress'),status=$('#success-status');
  let film=null,wants=false,version=0,frame=0,timer=0,failed=false,origin=null,pendingSeek=null;
  const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  function paint(){
    if(!film)return;
    const duration=Number.isFinite(video.duration)?video.duration:film.duration,t=pendingSeek===null?(video.currentTime||0):pendingSeek*duration;
    slider.value=String(Math.round(t/duration*1000));$('#replay-time').textContent=`${clock(t)} / ${clock(duration)}`;
    const segment=film.segments.find(part=>t<part.end-.001)||film.segments.at(-1);
    if($('#success-description').textContent!==segment.caption)$('#success-description').textContent=segment.caption;
    play.textContent=wants&&!video.paused?'Ⅱ':'▶';play.setAttribute('aria-label',failed?'Retry recorded exploration':wants&&!video.paused?'Pause recorded exploration':'Play recorded exploration');
  }
  function cancelFrame(){if(frame){if(video.cancelVideoFrameCallback)video.cancelVideoFrameCallback(frame);else cancelAnimationFrame(frame);}frame=0;}
  function tick(){frame=0;paint();if(film&&dialog.open&&!video.paused)frame=video.requestVideoFrameCallback?video.requestVideoFrameCallback(tick):requestAnimationFrame(tick);}
  function pause(){wants=false;clearTimeout(timer);video.pause();cancelFrame();if(!failed)status.hidden=true;paint();}
  function fail(){if(!film||!dialog.open)return;pause();failed=true;status.textContent='Video could not load. Press play to retry.';status.hidden=false;paint();}
  function start(){
    if(!film||!dialog.open)return;
    if(failed){failed=false;video.load();}
    if(video.ended)video.currentTime=0;
    wants=true;const token=version;
    if(video.readyState<2){status.textContent='Loading video…';status.hidden=false;}
    clearTimeout(timer);timer=setTimeout(()=>{if(token===version&&wants&&video.readyState<2)fail();},20000);
    video.play().then(()=>{if(token!==version)return;if(!wants||!dialog.open){video.pause();return;}clearTimeout(timer);status.hidden=true;cancelFrame();tick();}).catch(error=>{if(token===version&&wants&&error.name!=='AbortError')fail();});
  }
  play.addEventListener('click',()=>wants&&!video.paused?pause():start());
  slider.addEventListener('input',()=>{if(!film)return;const fraction=Number(slider.value)/1000;pause();if(video.readyState===0)pendingSeek=fraction;else video.currentTime=fraction*video.duration;paint();});
  video.addEventListener('loadedmetadata',()=>{if(pendingSeek!==null){video.currentTime=pendingSeek*video.duration;pendingSeek=null;}paint();});video.addEventListener('loadeddata',()=>{status.hidden=true;paint();});video.addEventListener('timeupdate',paint);
  video.addEventListener('playing',()=>{clearTimeout(timer);status.hidden=true;});
  video.addEventListener('ended',()=>{pause();paint();});video.addEventListener('error',fail);
  $('#replay-fullscreen').addEventListener('click',async()=>{const player=$('.exploration-player');if(document.fullscreenElement)await document.exitFullscreen();else await player.requestFullscreen();});
  $('#exploration-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
  dialog.addEventListener('close',()=>{version++;pause();film=null;pendingSeek=null;video.removeAttribute('src');video.load();const target=origin?.isConnected&&origin.getClientRects().length?origin:document.querySelector('.result-row[aria-pressed=true]');target?.focus({preventScroll:true});});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  document.addEventListener('longchang:presentation-open',pause);document.addEventListener('longchang:case-film-play',pause);
  window.showDiscovery=id=>{
    const next=films.find(item=>item.id===id);if(!next)return;
    origin=document.activeElement;version++;pause();film=next;failed=false;pendingSeek=null;
    $('#discovery-title').textContent=film.name;$('#discovery-finding').textContent=film.finding;
    $('#discovery-source').textContent=`Recorded example · ${film.model}`;
    video.poster=film.poster;video.src=film.video+'?v='+film.sha256.slice(0,12);video.load();slider.value='0';paint();
    if(!dialog.open)dialog.showModal();dialog.scrollTop=0;start();
  };
})();
