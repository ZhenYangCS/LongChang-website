/* One live MuJoCo scene at a time, loaded only when Try it is selected. */
(() => {
  const $=s=>document.querySelector(s),host=$('#atlas-motion-view');
  const stage=document.createElement('div');stage.id='scene-live-stage';
  const poster=document.createElement('img');poster.className='scene-live-poster';poster.alt='Scene preview';stage.append(poster);host.prepend(stage);
  const playback=document.createElement('div');playback.className='scene-live-playback';playback.hidden=true;
  playback.innerHTML='<button id="scene-live-play" class="round-control" aria-label="Pause live physics">Ⅱ</button><span id="scene-live-hint" role="status"></span><span id="scene-live-clock">0.0 s</span><select id="scene-live-speed" aria-label="Live physics speed"><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4" selected>4×</option></select><button id="scene-live-fullscreen" class="round-control" aria-label="Expand live physics">⛶</button>';
  host.after(playback);
  const controls=document.createElement('div');controls.id='scene-live-controls';controls.hidden=true;
  controls.innerHTML='<div class="room-tools" role="group" aria-label="Interact with the scene"><button data-scene-mode="push" aria-pressed="true">Push</button><button data-scene-mode="drag" aria-pressed="false">Drag</button><button data-scene-mode="view" aria-pressed="false">Rotate</button><button id="scene-live-reset" aria-label="Reset the scene">↺</button></div>';
  playback.insertBefore(controls,$('#scene-live-hint'));
  let world=null,worldId=null,mode='push',version=0,loading=false,visible=false,lastClock=-1;
  const status=text=>{$('#scene-live-hint').textContent=text;};
  function clock(time){const now=Math.floor(time*10);if(now!==lastClock){lastClock=now;$('#scene-live-clock').textContent=(now/10).toFixed(1)+' s';}}
  function playLabel(){const playing=world?.isRunning();$('#scene-live-play').textContent=playing?'Ⅱ':'▶';$('#scene-live-play').setAttribute('aria-label',playing?'Pause live physics':'Run live physics');}
  function destroy(){version++;loading=false;world?.destroy();world=null;worldId=null;window.SceneRoom=null;stage.setAttribute('aria-busy','false');}
  async function open(){
    const id=window.LongChangAtlas.currentScene();
    if(world&&worldId===id){world.setMode(mode);playLabel();return;}
    if(loading)return;
    loading=true;const token=++version;stage.setAttribute('aria-busy','true');status('Loading interaction…');
    const item=window.SCENE_INDEX.find(e=>e.id===id);poster.src=item.studio_poster;poster.hidden=false;
    try{
      const [{createSceneSimulation},{createRoom},response]=await Promise.all([import('./scene-physics.js'),import('./room-world.js'),fetch(`data/interactive-scenes/${id}.json`,{signal:AbortSignal.timeout(20000)})]);
      if(!response.ok)throw Error('Scene unavailable');const config=await response.json();if(token!==version)return;
      const simulation=await createSceneSimulation(config,text=>{if(token===version)status(text);});
      if(token!==version){simulation.destroy();return;}
      const next=await createRoom(stage,status,{simulation,speed:Number($('#scene-live-speed').value),onFrame:time=>{clock(time);if(world)playLabel();}});
      if(token!==version){next.destroy();return;}
      world=next;worldId=id;window.SceneRoom=world;poster.hidden=true;world.setMode(mode);if(visible)world.play();playLabel();
    }catch(error){if(token===version){status('Could not load. Tap Push to retry.');console.warn('Live scene:',error.message);}}
    finally{if(token===version){loading=false;stage.setAttribute('aria-busy','false');}}
  }
  function view(){
    visible=$('.atlas-detail').dataset.view==='motion';controls.hidden=playback.hidden=!visible;
    if(visible)open();else{world?.pause();playLabel();}
  }
  controls.querySelectorAll('[data-scene-mode]').forEach(button=>button.addEventListener('click',()=>{
    mode=button.dataset.sceneMode;controls.querySelectorAll('[data-scene-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    if(world)world.setMode(mode);else open();
  }));
  $('#scene-live-play').addEventListener('click',()=>{if(!world){open();return;}if(world.isRunning())world.pause();else world.play();playLabel();});
  $('#scene-live-speed').addEventListener('change',()=>world?.setSpeed(Number($('#scene-live-speed').value)));
  $('#scene-live-reset').addEventListener('click',()=>{world?.reset();clock(0);playLabel();});
  stage.addEventListener('pointerup',()=>{queueMicrotask(playLabel);});
  $('#scene-live-fullscreen').addEventListener('click',async()=>{
    try{if(document.fullscreenElement)await document.exitFullscreen();else await $('.atlas-visual').requestFullscreen();}catch(_){status('Use Rotate, then scroll to zoom.');}
  });
  document.addEventListener('longchang:scene',()=>{
    if(worldId!==window.LongChangAtlas.currentScene()){destroy();lastClock=-1;clock(0);if(visible)open();}
  });
  document.addEventListener('longchang:atlas-view',view);
  window.LongChangSceneLive=Object.freeze({open,current:()=>world});view();
})();
