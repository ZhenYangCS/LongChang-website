
window.createSceneZoom = (frame, video, poster) => {
  'use strict';
  const layer=document.createElement('div');layer.className='physics-media';
  const background=document.createElement('img');background.className='physics-room-background';background.alt='';background.loading='lazy';background.decoding='async';background.hidden=true;
  layer.append(background,poster,video);frame.prepend(layer);
  const toggle=document.createElement('button');toggle.id='physics-view';toggle.className='physics-view';
  toggle.innerHTML='<span class="room-context"><img loading="lazy" alt="Full room"><span class="focus-rectangle"></span></span><span class="view-label">Detail ↗</span>';
  const controls=document.createElement('div');controls.className='scene-zoom-tools';controls.hidden=true;
  controls.innerHTML='<div class="scene-zoom-buttons" role="group" aria-label="Zoom controls"><button id="scene-zoom-out" aria-label="Zoom out">−</button><button id="scene-zoom-reset" aria-label="Fit the whole room">1.0×</button><button id="scene-zoom-in" aria-label="Zoom in">+</button></div><span id="scene-zoom-hint">Scroll to zoom · Drag to pan</span>';
  frame.append(toggle,controls);frame.tabIndex=0;
  const rect=toggle.querySelector('.focus-rectangle'),out=controls.querySelector('#scene-zoom-out'),inside=controls.querySelector('#scene-zoom-in'),resetButton=controls.querySelector('#scene-zoom-reset');
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  const pointers=new Map();let editing=false,scale=1,cx=.5,cy=.5,width=0,height=0,fitWidth=0,fitHeight=0,aspect=1.5,focus=[.5,.5],crop=[0,0,1440,960],fitFocus=false,useDetail=false;
  function paint(){
    if(!width||!height)return;
    const w=fitWidth*scale,h=fitHeight*scale;
    cx=w<=width ? .5 : clamp(cx,width/(2*w),1-width/(2*w));
    cy=h<=height ? .5 : clamp(cy,height/(2*h),1-height/(2*h));
    layer.style.transform=`translate3d(${width/2-cx*w}px,${height/2-cy*h}px,0) scale(${scale})`;
    const left=clamp(cx-width/(2*w),0,1),top=clamp(cy-height/(2*h),0,1);
    const right=clamp(cx+width/(2*w),0,1),bottom=clamp(cy+height/(2*h),0,1);
    Object.assign(rect.style,{left:left*100+'%',top:top*100+'%',width:(right-left)*100+'%',height:(bottom-top)*100+'%'});
    resetButton.textContent=scale.toFixed(1)+'×';out.disabled=scale<=1;inside.disabled=scale>=6;
    frame.dataset.zoom=scale.toFixed(4);
  }
  function resize(){
    width=frame.clientWidth;height=frame.clientHeight;
    fitWidth=Math.min(width,height*aspect);fitHeight=fitWidth/aspect;
    if(fitFocus&&width&&height){scale=clamp(Math.min(width/(fitWidth*(crop[2]-crop[0])/1440),height/(fitHeight*(crop[3]-crop[1])/960)),1,6);[cx,cy]=focus;}
    layer.style.width=fitWidth+'px';layer.style.height=fitHeight+'px';paint();
  }
  function mode(value){
    editing=value;frame.dataset.framing=value?'detail':'room';controls.hidden=!value;
    toggle.setAttribute('aria-pressed',String(value));
    toggle.setAttribute('aria-label',value?'Return to the whole room':'Explore details: zoom and pan');
    toggle.querySelector('.view-label').textContent=value?'Room ↗':'Detail ↗';
    frame.setAttribute('aria-label',value?'Scene detail: scroll or pinch to zoom, drag to pan. Double-click or press 0 to fit the room.':'Scene demonstration');
    controls.querySelector('#scene-zoom-hint').textContent=matchMedia('(pointer:coarse)').matches?'Pinch to zoom · Drag to pan':'Scroll to zoom · Drag to pan';
  }
  function clearPointers(){
    for(const id of pointers.keys())if(frame.hasPointerCapture(id))frame.releasePointerCapture(id);
    pointers.clear();frame.classList.remove('is-panning');
  }
  function reset(){clearPointers();fitFocus=false;scale=1;cx=cy=.5;mode(false);resize();}
  function showDetail(){mode(true);fitFocus=true;resize();}
  function zoom(next,x=width/2,y=height/2){
    if(!fitWidth||!fitHeight)return;
    fitFocus=false;
    next=clamp(next,1,6);

    cx+=(x-width/2)/fitWidth*(1/scale-1/next);
    cy+=(y-height/2)/fitHeight*(1/scale-1/next);
    scale=next;paint();
  }
  function local(e){const box=frame.getBoundingClientRect();return {x:e.clientX-box.left,y:e.clientY-box.top};}
  function gesture(){
    const p=[...pointers.values()];
    return p.length>1?{x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2,d:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)}:{...p[0],d:0};
  }
  toggle.addEventListener('click',()=>{
    if(editing){reset();return;}showDetail();frame.focus({preventScroll:true});
  });
  out.addEventListener('click',()=>zoom(scale/1.25));inside.addEventListener('click',()=>zoom(scale*1.25));resetButton.addEventListener('click',reset);
  frame.addEventListener('wheel',e=>{
    if(!editing||e.target.closest('button'))return;
    e.preventDefault();const p=local(e),unit=e.deltaMode===1?16:e.deltaMode===2?height:1;
    zoom(scale*Math.exp(-clamp(e.deltaY*unit,-250,250)*.0025),p.x,p.y);
  },{passive:false});
  frame.addEventListener('pointerdown',e=>{
    if(!editing||e.target.closest('button,input,select,a')||e.button!==0)return;
    e.preventDefault();frame.focus({preventScroll:true});pointers.set(e.pointerId,local(e));frame.setPointerCapture(e.pointerId);frame.classList.add('is-panning');
  });
  frame.addEventListener('pointermove',e=>{
    if(!pointers.has(e.pointerId))return;
    fitFocus=false;
    e.preventDefault();const before=gesture();pointers.set(e.pointerId,local(e));const after=gesture();
    if(before.d>0&&after.d>0)zoom(scale*after.d/before.d,before.x,before.y);
    cx-=(after.x-before.x)/(fitWidth*scale);cy-=(after.y-before.y)/(fitHeight*scale);paint();
  });
  function release(e){pointers.delete(e.pointerId);if(frame.hasPointerCapture(e.pointerId))frame.releasePointerCapture(e.pointerId);if(!pointers.size)frame.classList.remove('is-panning');}
  frame.addEventListener('pointerup',release);frame.addEventListener('pointercancel',release);frame.addEventListener('lostpointercapture',release);
  frame.addEventListener('dblclick',e=>{if(editing&&!e.target.closest('button')){e.preventDefault();reset();}});
  frame.addEventListener('keydown',e=>{
    if(!editing||e.target!==frame||e.ctrlKey||e.metaKey||e.altKey)return;
    if(['+','=','-','0','Home','Escape','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))e.preventDefault();else return;
    if(['0','Home','Escape'].includes(e.key)){reset();return;}
    if(e.key==='+'||e.key==='=')zoom(scale*1.25);
    else if(e.key==='-')zoom(scale/1.25);
    else{fitFocus=false;cx+=({'ArrowLeft':-48,'ArrowRight':48}[e.key]||0)/(fitWidth*scale);cy+=({'ArrowUp':-48,'ArrowDown':48}[e.key]||0)/(fitHeight*scale);paint();}
  });
  new ResizeObserver(resize).observe(frame);
  video.addEventListener('loadedmetadata',()=>{if(video.videoWidth&&video.videoHeight){aspect=useDetail?1.5:video.videoWidth/video.videoHeight;resize();}});

  document.addEventListener('fullscreenchange',resize);
  reset();
  return {setScene(scene){
    aspect=1.5;crop=scene.detail_crop||[0,0,1440,960];focus=[(crop[0]+crop[2])/2880,(crop[1]+crop[3])/1920];
    useDetail=Boolean(scene.room_background&&scene.detail_video);background.hidden=!useDetail;
    if(useDetail)background.src=scene.room_background;
    const [l,t,r,b]=useDetail?crop:[0,0,1440,960];


    for(const element of [video,poster])Object.assign(element.style,{inset:'auto',left:l/1440*100+'%',top:t/960*100+'%',width:(r-l)/1440*100+'%',height:(b-t)/960*100+'%'});
    if(scene.context_poster)toggle.querySelector('img').src=scene.context_poster;
    reset();showDetail();
  }};
};
