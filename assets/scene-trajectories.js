/* Motion guides projected from the same recorded states as the scene film. */
(() => {
  'use strict';
  const video = document.getElementById('physics-video');
  const poster = document.getElementById('studio-poster');
  const media = document.querySelector('.physics-media');
  if (!video || !media) return;
  const ns = 'http://www.w3.org/2000/svg';
  const make = (tag,attrs={}) => {
    const node=document.createElementNS(ns,tag);
    for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
    return node;
  };
  const svg=make('svg',{viewBox:'0 0 1440 960',class:'scene-trajectories','aria-hidden':'true',hidden:''});
  const defs=make('defs'), mask=make('mask',{id:'scene-trail-objects',maskUnits:'userSpaceOnUse',x:0,y:0,width:1440,height:960});
  const maskBase=make('rect',{x:0,y:0,width:1440,height:960,fill:'white'});
  const tracks=make('g',{class:'scene-trail-paths',mask:'url(#scene-trail-objects)'});
  const vectors=make('g',{class:'scene-trail-vectors',mask:'url(#scene-trail-objects)'});
  const actions=make('g',{class:'scene-trail-actions'});
  mask.append(maskBase);defs.append(mask);svg.append(defs,tracks,vectors,actions);media.append(svg);
  const legend=document.createElement('div');legend.className='scene-motion-key';legend.hidden=true;
  legend.setAttribute('aria-label','Motion guide legend');
  document.querySelector('.physics-video-frame').after(legend);
  let entry=null, recording=null, camera=null, request=null, generation=0, handle=null, frameIndex=-1, shown=false;
  let pending=null, cameraPromise=null, paths=[];
  let unit=1,geometryVersion=0,drawnGeometry=-1;
  let visibleBounds={left:0,top:0,right:1440,bottom:960};
  const cache=new Map();
  const dot=(a,b)=>a.reduce((sum,value,i)=>sum+value*b[i],0);
  const length=v=>Math.hypot(...v);
  const add=(a,b)=>a.map((value,i)=>value+b[i]);
  const scale=(v,n)=>v.map(value=>value*n);
  function updateGeometry() {
    const box=media.getBoundingClientRect(),frame=media.parentElement.getBoundingClientRect();
    if(!box.width)return;
    unit=1440/box.width;
    visibleBounds={left:Math.max(0,(frame.left-box.left)*unit),top:Math.max(0,(frame.top-box.top)*unit),right:Math.min(1440,(frame.right-box.left)*unit),bottom:Math.min(960,(frame.bottom-box.top)*unit)};
    svg.style.setProperty('--guide-unit',unit);
    geometryVersion++;
    if(recording)draw(frameIndex<0 ? video.currentTime : frameIndex/recording.fps);
  }
  function updateLegend() {
    legend.replaceChildren();legend.hidden=!shown || !entry;
    if(legend.hidden)return;
    const key=(text,kind,stroke)=>{
      const item=document.createElement('span'),mark=document.createElement('i');
      mark.className=kind;mark.style.color=stroke;mark.setAttribute('aria-hidden','true');
      item.append(mark,document.createTextNode(text));legend.append(item);
    };
    if(entry.proof){
      const reference=entry.proof.labels.find(label=>label[2]==='dashed');
      const actual=entry.proof.labels.find(label=>label[2]==='solid');
      if(reference&&actual){key('This world','',actual[1]);key('Ordinary physics','is-reference',reference[1]);}
      else legend.hidden=true;
    }else{
      key('Motion','','#647f89');
      if(recording?.timeline.some(frame=>Object.values(frame.oracle?.forces||{}).some(force=>length(force)>.05)))
        key('Force','is-force','#347b69');
    }
  }
  function project(position) {
    const delta=position.map((value,i)=>value-camera.position[i]);
    return [720+dot(delta,camera.right)*960/camera.span,480-dot(delta,camera.up)*960/camera.span];
  }
  function color(object) {
    const c=object.color || [.45,.55,.55];
    if (Math.max(...c.slice(0,3))-Math.min(...c.slice(0,3))<.15) return '#647f89';
    return ['#bd6655','#559574','#507fa7'][c.indexOf(Math.max(...c.slice(0,3)))];
  }
  function stop() {
    if (handle!==null) {
      if (video.cancelVideoFrameCallback) video.cancelVideoFrameCallback(handle);
      else cancelAnimationFrame(handle);
    }
    handle=null;
  }
  function schedule() {
    stop();
    if (!shown || document.hidden || video.paused || !recording) return;
    const next=(_,metadata)=>{handle=null;draw(video.paused ? video.currentTime : metadata?.mediaTime);schedule();};
    handle=video.requestVideoFrameCallback ? video.requestVideoFrameCallback(next) : requestAnimationFrame(next);
  }
  function resetGuides() {
    frameIndex=-1;tracks.replaceChildren();vectors.replaceChildren();actions.replaceChildren();
    mask.replaceChildren(maskBase);paths=[];svg.setAttribute('hidden','');
  }
  function prepare(data,viewCamera) {
    recording=data;camera=viewCamera;
    const history=new Map();
    for (const [index,frame] of (entry.proof ? [] : data.timeline).entries()) {
      for (const [name,object] of Object.entries(frame.objects)) {
        if (!history.has(name)) history.set(name,[]);
        const points=history.get(name),last=points.at(-1),point=project(object.position);
        if (!last || last.epoch!==frame.epoch || Math.hypot(point[0]-last.point[0],point[1]-last.point[1])>.2)
          points.push({index,epoch:frame.epoch,point});
      }
    }
    for (const [name,points] of history) {
      const path=make('path',{'data-object':name,class:'scene-motion-path',fill:'none'});
      const start=make('circle',{r:1.15,class:'scene-motion-origin'});
      const cutout=make('circle',{r:6,fill:'black'});
      tracks.append(path,start);mask.append(cutout);paths.push({name,points,path,start,cutout});
    }
    updateGeometry();updateLegend();draw();schedule();
  }
  async function load() {
    // Baked films keep their paths; all films receive legible launch cues.
    if (!shown || !entry || recording || pending || !video.hasAttribute('src')) return;
    const token=generation,selected=entry;
    request=new AbortController();
    const task=(async()=>{
      try {
        if (!cameraPromise) cameraPromise=fetch('data/shared-room.json').then(response=>{
          if (!response.ok) throw Error('Camera unavailable');return response.json();
        }).then(room=>room.camera).catch(error=>{cameraPromise=null;throw error;});
        let data=cache.get(selected.id);
        if (!data) {
          const response=await fetch(selected.details,{signal:request.signal});
          if (!response.ok) throw Error('Trajectory unavailable');data=await response.json();
          if (token!==generation) return;
          cache.set(selected.id,data);
          while(cache.size>3) cache.delete(cache.keys().next().value);
        }
        const viewCamera=await cameraPromise;
        if (token!==generation) return;
        prepare(data,viewCamera);
      } catch (error) {
        if (error.name!=='AbortError' && token===generation) svg.dataset.status='unavailable';
      } finally {if(token===generation)pending=null;}
    })();
    pending=task;await task;
  }
  function arrowShape(a,b,stroke,kind,root=vectors) {
    const dx=b[0]-a[0],dy=b[1]-a[1],n=Math.hypot(dx,dy);
    if(n<2*unit)return;
    const ux=dx/n,uy=dy/n,head=Math.min((kind==='action'?10:8)*unit,n*.4);
    const d=`M${a}L${b}`;
    const halo=make('path',{d,fill:'none',class:'scene-vector-halo'});
    const line=make('path',{d,fill:'none',stroke,class:'scene-motion-vector','data-vector':kind});
    const triangle=`M${b}L${b[0]-ux*head-uy*head*.48},${b[1]-uy*head+ux*head*.48}L${b[0]-ux*head+uy*head*.48},${b[1]-uy*head-ux*head*.48}Z`;
    const tip=make('path',{d:triangle,fill:stroke,class:'scene-vector-tip'});
    root.append(halo,line,tip);
  }
  function vector(position,direction,size,stroke,kind) {
    const magnitude=length(direction);if (magnitude<.01) return;
    const end=add(position,scale(direction,size/magnitude));
    const a=project(position),projected=project(end),dx=projected[0]-a[0],dy=projected[1]-a[1],n=Math.hypot(dx,dy);
    if (n<.1) return;
    // Direction is physical; annotation size stays readable on every screen.
    const visibleLength=Math.min(76*unit,Math.max(22*unit,n));
    const b=[a[0]+dx/n*visibleLength,a[1]+dy/n*visibleLength];
    arrowShape(a,b,stroke,kind);
    if (kind==='force') {
      const label=make('text',{x:b[0]+5*unit,y:b[1]-5*unit,class:'scene-motion-force-label'});
      label.textContent='F';vectors.append(label);
    }
  }
  function actionCue(event,frame,occupied) {
    const [command,name,azimuth,elevation]=event.command.split(' ');
    if(!['PUSH','THROW'].includes(command) || !event.positions_before?.[name])return;
    const angle=Number(azimuth)*Math.PI/180,tilt=command==='THROW' ? Number(elevation)*Math.PI/180 : 0;
    const direction=[Math.cos(angle)*Math.cos(tilt),Math.sin(angle)*Math.cos(tilt),Math.sin(tilt)];
    const origin=event.positions_before[name],p=project(origin),q=project(add(origin,direction));
    const n=Math.hypot(q[0]-p[0],q[1]-p[1]);if(n<.1)return;
    const dx=(q[0]-p[0])/n,dy=(q[1]-p[1])/n,box=visibleBounds,padding=7*unit;
    if(p[0]<box.left || p[0]>box.right || p[1]<box.top || p[1]>box.bottom)return;
    const room=(x,y)=>Math.min(x>0?(box.right-padding-p[0])/x:x<0?(box.left+padding-p[0])/x:Infinity,y>0?(box.bottom-padding-p[1])/y:y<0?(box.top+padding-p[1])/y:Infinity);
    const behind=room(-dx,-dy),ahead=room(dx,dy);
    let a,b;
    if(behind>=46*unit){
      const distance=Math.min(76*unit,behind);
      a=[p[0]-dx*distance,p[1]-dy*distance];b=[p[0]-dx*10*unit,p[1]-dy*10*unit];
    }else{
      const distance=Math.min(76*unit,ahead);if(distance<34*unit)return;
      a=[p[0]+dx*10*unit,p[1]+dy*10*unit];b=[p[0]+dx*distance,p[1]+dy*distance];
    }
    const cue=make('g',{class:'scene-action-cue','data-object':name});actions.append(cue);
    arrowShape(a,b,'#8a4d16','action',cue);
    const text=command==='PUSH'?'Push':'Throw',width=(text==='Push'?43:51)*unit,height=24*unit;
    const middle=[(a[0]+b[0])/2,(a[1]+b[1])/2];
    const bodies=Object.values(frame.objects).map(object=>{const point=project(object.position);return {left:point[0]-10*unit,right:point[0]+10*unit,top:point[1]-10*unit,bottom:point[1]+10*unit};});
    const overlaps=(a,b)=>a.left<b.right+4*unit&&a.right>b.left-4*unit&&a.top<b.bottom+4*unit&&a.bottom>b.top-4*unit;
    const candidates=[-21,21,-38,38].map(offset=>{
      const x=Math.max(box.left+padding+width/2,Math.min(box.right-padding-width/2,middle[0]-dy*offset*unit));
      const y=Math.max(box.top+padding+height/2,Math.min(box.bottom-padding-height/2,middle[1]+dx*offset*unit));
      return {x,y,left:x-width/2,right:x+width/2,top:y-height/2,bottom:y+height/2};
    });
    const label=candidates.find(candidate=>![...bodies,...occupied].some(other=>overlaps(candidate,other)))||candidates[0];
    occupied.push(label);
    const background=make('rect',{x:label.left,y:label.top,width,height,rx:5*unit,class:'scene-action-badge'});
    const caption=make('text',{x:label.x,y:label.y,class:'scene-motion-action-label'});caption.textContent=text;
    cue.append(background,caption);
  }
  function draw(mediaTime=video.currentTime) {
    if (!recording || !camera || !shown) {svg.setAttribute('hidden','');return;}
    const index=Math.max(0,Math.min(recording.timeline.length-1,Math.floor(mediaTime*recording.fps+1e-4)));
    const frame=recording.timeline[index];
    svg.toggleAttribute('hidden',!poster.hidden || video.seeking || frame.fade>0);
    if (index===frameIndex && drawnGeometry===geometryVersion) {
      if(entry.proof && !actions.childElementCount)svg.setAttribute('hidden','');
      return;
    }
    frameIndex=index;drawnGeometry=geometryVersion;svg.dataset.frame=String(index);svg.dataset.scene=entry.id;svg.dataset.status=entry.proof?'baked':'ready';
    vectors.replaceChildren();actions.replaceChildren();
    for (const item of paths) {
      const object=frame.objects[item.name];
      if (!object) {item.path.setAttribute('d','');continue;}
      const past=item.points.filter(point=>point.index<=index && point.epoch===frame.epoch);
      const current=project(object.position),stroke=color(object);
      const coordinates=past.map(sample=>sample.point);coordinates.push(current);
      item.path.setAttribute('d',coordinates.map((point,i)=>(i?'L':'M')+point.join(',')).join(''));
      item.path.setAttribute('stroke',stroke);
      item.start.setAttribute('cx',coordinates[0][0]);item.start.setAttribute('cy',coordinates[0][1]);item.start.setAttribute('fill',stroke);
      item.cutout.setAttribute('cx',current[0]);item.cutout.setAttribute('cy',current[1]);
      vector(object.position,object.velocity,Math.min(.9,length(object.velocity)*.2),stroke,'motion');
      const force=frame.oracle?.forces?.[item.name];
      if (force && length(force)>.05) vector(object.position,force,Math.min(.85,.22+length(force)*.07),'#347b69','force');
    }
    const occupied=[];
    for (const event of recording.events || []) {
      const elapsed=frame.time-(event.actual_time??event.time);
      // Short cues mark the intervention, while its trajectory remains visible.
      const next=(recording.events||[]).find(other=>other.command&&(other.actual_time??other.time)>(event.actual_time??event.time)+.002);
      const cueDuration=Math.min(recording.simulation_duration/recording.duration*Math.min(4.8,Math.max(1.4,video.playbackRate*1.1)),next?(next.actual_time??next.time)-(event.actual_time??event.time):Infinity);
      if (elapsed<0 || elapsed>cueDuration || !event.command) continue;
      actionCue(event,frame,occupied);
    }
    if(entry.proof && !actions.childElementCount)svg.setAttribute('hidden','');
  }
  function select() {
    generation++;request?.abort();pending=null;stop();resetGuides();recording=null;
    entry=window.SCENE_INDEX.find(scene=>scene.id===window.LongChangAtlas.currentScene());
    shown=document.getElementById('scene-detail').dataset.view==='physics';
    svg.dataset.status=entry?.proof ? 'baked' : 'idle';
    updateLegend();
    if (video.hasAttribute('src')) load();
  }
  function refresh() {draw();load();schedule();}
  video.addEventListener('play',refresh);video.addEventListener('playing',refresh);
  video.addEventListener('loadeddata',refresh);video.addEventListener('seeked',refresh);
  video.addEventListener('timeupdate',()=>{if(video.paused)draw();});video.addEventListener('pause',()=>{stop();draw();});
  video.addEventListener('seeking',()=>svg.setAttribute('hidden',''));
  video.addEventListener('ratechange',()=>{geometryVersion++;draw();});
  for (const id of ['physics-play','physics-reset']) document.getElementById(id).addEventListener('click',()=>{
    if(video.paused){stop();draw();}
  });
  new MutationObserver(()=>draw()).observe(poster,{attributes:true,attributeFilter:['hidden']});
  new MutationObserver(updateGeometry).observe(media,{attributes:true,attributeFilter:['style']});
  new ResizeObserver(updateGeometry).observe(media.parentElement);
  document.addEventListener('longchang:scene',select);
  document.addEventListener('longchang:atlas-view',()=>{
    shown=document.getElementById('scene-detail').dataset.view==='physics';
    updateLegend();
    if(shown)refresh();else{stop();svg.setAttribute('hidden','');}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else refresh();});
  select();
})();
