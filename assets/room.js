
(() => {
  const stage=document.querySelector('#room-stage'),still=document.querySelector('#room-still'),hint=document.querySelector('#room-hint');
  let world=null,loading=null,mode='push';
  const status=text=>{hint.textContent=text;};
  async function start(next='push'){
    mode=next;
    document.querySelectorAll('[data-room-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.roomMode===mode)));
    if(world){world.setMode(mode);return world;}
    if(loading)return loading;
    stage.setAttribute('aria-busy','true');status('Loading interaction…');
    loading=import('./room-world.js').then(m=>m.createRoom(stage,status)).then(value=>{
      world=value;window.RoomDemo=world;world.setMode(mode);still.hidden=true;stage.classList.add('is-live');return world;
    }).catch(error=>{status('Could not load. Tap Push to retry.');console.warn('Room interaction:',error.message);return null;}).finally(()=>{loading=null;stage.setAttribute('aria-busy','false');});
    return loading;
  }
  document.querySelectorAll('[data-room-mode]').forEach(b=>b.addEventListener('click',()=>start(b.dataset.roomMode)));
  stage.addEventListener('click',()=>{if(!world&&!loading)start();});
  document.querySelector('#room-reset').addEventListener('click',()=>{if(world)world.reset();});
})();
