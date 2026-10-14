
(() => {
  const stage=document.querySelector('#room-stage'),still=document.querySelector('#room-still'),hint=document.querySelector('#room-hint');
  let world=null,loading=null,mode='drag',pending=null;
  const status=text=>{hint.textContent=text;stage.dataset.loadLabel=text;};
  const sample=e=>{const r=stage.getBoundingClientRect();return {pointerId:e.pointerId,pointerType:e.pointerType,button:e.button,x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height,shiftKey:e.shiftKey};};
  const restore=e=>{const r=stage.getBoundingClientRect();return {...e,clientX:r.left+e.x*r.width,clientY:r.top+e.y*r.height};};
  const clearPending=()=>{pending=null;};
  async function start(next=mode){
    mode=next;
    document.querySelectorAll('[data-room-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.roomMode===mode)));
    if(world){world.setMode(mode);return world;}
    if(loading)return loading;
    stage.setAttribute('aria-busy','true');status('Loading interaction…');
    loading=import('./room-world.js').then(m=>m.createRoom(stage,status)).then(value=>{
      world=value;window.RoomDemo=world;world.setMode(mode);still.hidden=true;stage.classList.add('is-live');
      // A completed push is an intended impulse. A released drag is cancelled.
      const r=stage.getBoundingClientRect(),available=!document.hidden&&r.bottom>0&&r.top<innerHeight&&!document.querySelector('dialog[open]');
      if(pending&&available){const gesture=pending;pending=null;if(gesture.released&&gesture.kind==='push')world.applyPushGesture(restore(gesture.start),restore(gesture.latest));else{world.beginInteraction(restore(gesture.start));world.moveInteraction(restore(gesture.latest));}}
      else clearPending();
      return world;
    }).catch(error=>{clearPending();status('Could not load. Tap Push to retry.');console.warn('Room interaction:',error.message);return null;}).finally(()=>{loading=null;stage.setAttribute('aria-busy','false');});
    return loading;
  }
  document.querySelectorAll('[data-room-mode]').forEach(b=>b.addEventListener('click',()=>{clearPending();start(b.dataset.roomMode);}));
  document.querySelector('#interactive-figure').addEventListener('pointerenter',()=>{if(!world)start();},{passive:true});
  document.querySelector('#interactive-figure').addEventListener('focusin',()=>{if(!world)start();});
  stage.addEventListener('pointerdown',e=>{
    if(!e.isPrimary){clearPending();return;}if(world||e.button!==0)return;
    e.preventDefault();pending={kind:mode,start:sample(e),latest:sample(e),released:false};stage.setPointerCapture(e.pointerId);start();
  });
  stage.addEventListener('pointermove',e=>{if(pending?.start.pointerId===e.pointerId)pending.latest=sample(e);},{passive:true});
  stage.addEventListener('pointerup',e=>{if(pending?.start.pointerId!==e.pointerId)return;if(pending.kind==='push'){pending.latest=sample(e);pending.released=true;}else clearPending();});
  stage.addEventListener('pointercancel',clearPending);stage.addEventListener('lostpointercapture',()=>{if(!pending?.released)clearPending();});window.addEventListener('blur',clearPending);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearPending();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')clearPending();});
  document.querySelector('#room-reset').addEventListener('click',()=>{clearPending();if(world)world.reset();});
})();
