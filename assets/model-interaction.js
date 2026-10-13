
(() => {
  'use strict';
  const svg=document.querySelector('#atlas-canvas'),atlas=window.LongChangAtlas;
  let gesture=null,ignoreClick=false;
  const active=()=>!document.querySelector('#demo-explanation').hidden;
  const local=event=>new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
  function resizeTargets(){
    const matrix=svg.getScreenCTM(),scale=matrix&&Math.hypot(matrix.a,matrix.b);
    if(scale>0)svg.style.setProperty('--model-hit-radius',`${Math.max(23,(matchMedia('(pointer:coarse)').matches?26:20)/scale)}px`);
  }
  new ResizeObserver(resizeTargets).observe(svg);
  function pickBall(event){
    const matrix=svg.getScreenCTM(),scale=Math.hypot(matrix.a,matrix.b),reach=Math.max(23*scale,event.pointerType==='touch'?26:20);
    let ball=null,nearest=reach;
    for(const hit of svg.querySelectorAll('.model-hit')){
      const point=new DOMPoint(Number(hit.getAttribute('cx')),Number(hit.getAttribute('cy'))).matrixTransform(matrix),distance=Math.hypot(point.x-event.clientX,point.y-event.clientY);
      if(distance<=nearest){nearest=distance;ball=hit.closest('[data-model-ball]');}
    }
    return ball;
  }
  function sync(){
    const state=atlas.getState(),kind=state.gesture||'replay';svg.dataset.gesture=kind;
    const labels={height:'Drag ball to set height',strength:state.id==='05'?'Drag to set speed':'Drag to set impulse',direction:'Drag to aim',phase:'Phase · click the curve'};
    document.querySelector('#atlas-controls label').textContent=labels[kind]||state.label;
    document.querySelector('#atlas-parameter').setAttribute('aria-label',state.label);
    resizeTargets();
  }
  function finish(event,cancel=false){
    if(!gesture||event.pointerId!==gesture.pointerId)return;
    const saved=gesture;gesture=null;svg.classList.remove('is-adjusting');
    if(svg.hasPointerCapture(saved.pointerId))svg.releasePointerCapture(saved.pointerId);
    if(saved.state.id!==atlas.currentScene())return;
    if(cancel){ignoreClick=true;atlas.restore(saved.state);}
    else{ignoreClick=saved.moved;atlas.replay();}
  }
  svg.tabIndex=-1;
  svg.addEventListener('pointerdown',event=>{
    ignoreClick=false;
    if(gesture&&event.pointerId!==gesture.pointerId){finish({pointerId:gesture.pointerId},true);return;}
    if(!active()||event.button!==0||!event.isPrimary)return;
    const ball=pickBall(event),state=atlas.getState();
    if(!ball||!['height','strength','direction'].includes(state.gesture))return;
    event.preventDefault();svg.focus({preventScroll:true});
    const start=local(event);
    gesture={pointerId:event.pointerId,state,start,clientX:event.clientX,clientY:event.clientY,pickOffset:start.y-Number(ball.dataset.cy),floorY:Number(ball.dataset.floorY),moved:false};
    svg.setPointerCapture(event.pointerId);svg.classList.add('is-adjusting');atlas.pause();
  });
  svg.addEventListener('pointermove',event=>{
    if(!gesture||event.pointerId!==gesture.pointerId)return;
    if(Math.hypot(event.clientX-gesture.clientX,event.clientY-gesture.clientY)<4&&!gesture.moved)return;
    event.preventDefault();gesture.moved=true;
    const p=local(event),dx=p.x-gesture.start.x,dy=p.y-gesture.start.y;let next;
    if(gesture.state.gesture==='height')next=(gesture.floorY-(p.y-gesture.pickOffset))/62;
    else if(gesture.state.gesture==='strength')next=Number(gesture.state.value)+(dx*43+dy*22)/Math.hypot(43,22)*(gesture.state.id==='05'?.025:.04);
    else{
      const x=(dx/43+dy/22)/2,y=(dy/22-dx/43)/2;
      next=String((Math.round(Math.atan2(-y,x)*180/Math.PI/90)*90+360)%360);
    }
    atlas.setParameter(next,{preview:true});
  });
  svg.addEventListener('pointerup',event=>finish(event));
  svg.addEventListener('pointercancel',event=>finish(event,true));
  svg.addEventListener('lostpointercapture',event=>finish(event,true));
  document.addEventListener('pointerup',event=>finish(event));
  document.addEventListener('pointercancel',event=>finish(event,true));
  const cancel=()=>{if(gesture)finish({pointerId:gesture.pointerId},true);};
  window.addEventListener('blur',cancel);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)cancel();});
  svg.addEventListener('keydown',event=>{if(event.key==='Escape'&&gesture){event.preventDefault();finish({pointerId:gesture.pointerId},true);}});
  svg.addEventListener('click',event=>{
    if(!active())return;if(ignoreClick){ignoreClick=false;return;}
    const state=atlas.getState(),p=local(event);
    if(state.gesture==='phase'&&p.x>=90&&p.x<=280&&p.y>=54&&p.y<=145){
      const phase=(p.x-90)/190*6,distance=v=>Math.min(Math.abs(v-phase),6-Math.abs(v-phase)),nearest=[0,1.5,4.5].reduce((a,b)=>distance(a)<distance(b)?a:b);
      atlas.setParameter(String(nearest));
    }else atlas.replay();
  });
  document.addEventListener('longchang:scene',()=>{if(gesture)finish({pointerId:gesture.pointerId},true);ignoreClick=false;sync();});
  document.addEventListener('longchang:atlas-view',()=>{if(!active()&&gesture)finish({pointerId:gesture.pointerId},true);sync();});
  sync();
})();
