
(() => {
  const stage=document.querySelector('#room-stage'),still=document.querySelector('#room-still'),hint=document.querySelector('#room-hint');
  let world=null,loading=null,mode='drag',pending=null;
  const status=text=>{hint.textContent=text;stage.dataset.loadLabel=text;};
  const sample=e=>({pointerId:e.pointerId,pointerType:e.pointerType,button:e.button,clientX:e.clientX,clientY:e.clientY,shiftKey:e.shiftKey});
  async function start(next=mode){
    mode=next;
    document.querySelectorAll('[data-room-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.roomMode===mode)));
    if(world){world.setMode(mode);return world;}
    if(loading)return loading;
    stage.setAttribute('aria-busy','true');status('Loading interaction…');
    loading=import('./room-world.js').then(m=>m.createRoom(stage,status)).then(value=>{
      world=value;window.RoomDemo=world;world.setMode(mode);still.hidden=true;stage.classList.add('is-live');
      // Continue a held first gesture once the canvas is ready. Never replay
      // an action after the visitor has already released the pointer.
      if(pending){const gesture=pending;pending=null;world.beginInteraction(gesture.start);world.moveInteraction(gesture.latest);}
      return world;
    }).catch(error=>{status('Could not load. Tap Push to retry.');console.warn('Room interaction:',error.message);return null;}).finally(()=>{loading=null;stage.setAttribute('aria-busy','false');});
    return loading;
  }
  document.querySelectorAll('[data-room-mode]').forEach(b=>b.addEventListener('click',()=>start(b.dataset.roomMode)));
  document.querySelector('#interactive-figure').addEventListener('pointerenter',()=>{if(!world)start();},{passive:true});
  document.querySelector('#interactive-figure').addEventListener('focusin',()=>{if(!world)start();});
  stage.addEventListener('pointerdown',e=>{
    if(world||e.button!==0||!e.isPrimary)return;
    e.preventDefault();pending={start:sample(e),latest:sample(e)};stage.setPointerCapture(e.pointerId);start();
  });
  stage.addEventListener('pointermove',e=>{if(pending?.start.pointerId===e.pointerId)pending.latest=sample(e);},{passive:true});
  const clearPending=()=>{pending=null;};
  stage.addEventListener('pointerup',clearPending);stage.addEventListener('pointercancel',clearPending);stage.addEventListener('lostpointercapture',clearPending);window.addEventListener('blur',clearPending);
  document.querySelector('#room-reset').addEventListener('click',()=>{if(world)world.reset();});
})();
