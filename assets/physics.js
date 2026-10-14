
(() => {
  'use strict';
  const $=s=>document.querySelector(s),items=window.SCENE_INDEX||[];if(!items.length)return;
  const video=$('#physics-video'),image=$('#studio-poster'),playButton=$('#physics-play'),speed=$('#physics-speed');
  let demo=null,wants=false,shown=false,source=false,version=0,timer=0,details=null,detailAbort=null,posterVisible=false,posterLoading=false,pending=null,progressFrame=0;
  const measurements=$('#oracle-measurements'),law=$('#scene-law'),chart=$('#oracle-chart');
  let chartGeometry=null;
  measurements.classList.add('video-data');
  const chartTime=document.createElement('span');chartTime.id='oracle-chart-time';chartTime.className='video-data-clock';chartTime.title='Simulation time in this video';
  $('#oracle-chart-wrap>div').classList.add('video-data-heading');$('#oracle-chart-wrap>div').append(chartTime);
  const measurementHeading=document.createElement('p');measurementHeading.className='measurement-heading';measurementHeading.hidden=true;
  const measurementNote=document.createElement('p');measurementNote.className='measurement-note';measurementNote.hidden=true;
  $('#physics-values').before(measurementHeading);$('#physics-values').after(measurementNote);
  $('#oracle-chart-wrap').before($('.physics-readout'));
  const speedReadout=document.createElement('div');speedReadout.className='scene-speed-readout';speedReadout.hidden=true;
  speedReadout.innerHTML='<span class="speed-caption" title="Forward speed, in bricks per count">Forward speed</span><span class="speed-red"><i aria-hidden="true"></i><output id="speed-red-value" aria-label="Red ball forward speed"></output></span><span class="speed-blue"><i aria-hidden="true"></i><output id="speed-blue-value" aria-label="Blue ball forward speed"></output></span>';
  $('#model-controls').after($('#analysis-formula'));$('#worlds .physics-playback').before(measurements);
  $('#demo-rule').append(law);$('.physics-playback').insertBefore(speedReadout,$('#physics-progress'));
  $('.atlas-playback').prepend($('#atlas-controls'));
  let measurementsVisible=false;
  function syncView(mode){
    law.hidden=mode!=='physics';$('#atlas-controls').hidden=mode!=='physics';
    if(mode==='physics'&&measurementsVisible)loadMeasurements();
    readoutVisibility();
  }
  function readoutVisibility(){
    const enabled=Boolean(demo?.speed_trace)&&$('.atlas-detail').dataset.view==='physics';speedReadout.hidden=!enabled;
    $('#atlas-physics-view').classList.toggle('has-speed-readout',enabled);
  }
  function measuredSpeed(){
    const trace=demo?.speed_trace;if(!trace)return;
    const values=trace.values[Math.min(trace.values.length-1,Math.max(0,Math.floor((video.currentTime||0)*trace.fps)))];
    for(const [i,color] of ['red','blue'].entries()){const output=$(`#speed-${color}-value`),value=values[i].toFixed(1);if(output.textContent!==value)output.textContent=value;}
  }
  const navigation=$('.atlas-bottomline>div');navigation.className='atlas-navigation';$('.atlas-topline').prepend(navigation);
  $('#oracle-chapters').hidden=true;$('#oracle-kind').hidden=true;$('#atlas-model-note').hidden=true;
  $('[data-atlas-view="physics"]').hidden=false;
  const overlay=document.createElement('button');overlay.id='scene-play-overlay';overlay.className='scene-play-overlay';overlay.textContent='▶ Play';overlay.setAttribute('aria-label','Play scene video');$('.physics-video-frame').append(overlay);
  const frame=$('.physics-video-frame');
  const proof=document.createElement('div');proof.className='scene-proof';proof.hidden=true;proof.setAttribute('aria-label','Demonstration evidence');
  proof.innerHTML='<strong class="proof-state"></strong><div class="proof-measurements"></div><i class="proof-timer" aria-hidden="true"></i>';
  frame.after(proof);let proofRow=-1;
  function configureProof(){
    const info=demo?.proof;proof.hidden=!info;proofRow=-1;
    proof.querySelector('.proof-measurements').replaceChildren();
    if(!info)return;
    const measure=document.createElement('span');measure.className='proof-measure';measure.textContent=info.measure;proof.querySelector('.proof-measurements').append(measure);
    for(const [name,color,kind] of info.labels){const pair=document.createElement('span');pair.className='proof-pair';pair.style.color=color;const marker=document.createElement('i');marker.className='proof-marker '+kind;marker.setAttribute('aria-hidden','true');const label=document.createElement('span');label.textContent=name;const value=document.createElement('output');pair.append(marker,label,value);proof.querySelector('.proof-measurements').append(pair);}
    proof.querySelector('.proof-timer').hidden=!info.timer;
  }
  function updateProof(){
    const info=demo?.proof;if(!info)return;const current=Math.floor((video.currentTime||0)*info.fps),rows=info.rows;let lo=0,hi=rows.length;
    while(lo<hi){const mid=(lo+hi)>>1;if(rows[mid][0]<=current)lo=mid+1;else hi=mid;}
    const index=Math.max(0,lo-1);if(index===proofRow)return;proofRow=index;
    const [,label,values,ratio]=rows[index];proof.querySelector('.proof-state').textContent=label;
    proof.querySelectorAll('output').forEach((node,i)=>node.textContent=values[i]||'');proof.style.setProperty('--timer-progress',Math.max(0,ratio)+'%');
  }
  const zoom=window.createSceneZoom(frame,video,image,{interactive:false});
  video.controls=false;video.preload='none';
  const media=()=>demo.room_background&&demo.detail_video?{url:demo.detail_video,hash:demo.detail_video_sha256,poster:demo.detail_poster,preview:demo.detail_preview}:{url:demo.video,hash:demo.video_sha256,poster:demo.studio_poster,preview:demo.preview};
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
  function animateProgress(_now,metadata){
    progressFrame=0;if(video.paused||!source)return;
    $('#physics-progress').value=Math.round(video.currentTime/demo.duration*1000);
    measuredSpeed();
    updateProof();
    updateChartCursor(metadata?.mediaTime);
    progressFrame=video.requestVideoFrameCallback?video.requestVideoFrameCallback(animateProgress):requestAnimationFrame(animateProgress);
  }
  function cancelProgress(){if(progressFrame){if(video.cancelVideoFrameCallback)video.cancelVideoFrameCallback(progressFrame);else cancelAnimationFrame(progressFrame);}progressFrame=0;}
  const clock=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  async function sharpenPoster(){
    if(!demo||posterLoading||!posterVisible)return;posterLoading=true;const token=version,next=new Image();next.src=media().poster;
    try{await next.decode();if(token===version&&!pending&&!image.hidden)image.src=next.src;}catch(_){ }
  }
  new IntersectionObserver(entries=>{posterVisible=entries[0].isIntersecting;if(posterVisible)sharpenPoster();},{rootMargin:'300px'}).observe($('.physics-video-frame'));
  function loading(value){$('.physics-video-frame').setAttribute('aria-busy',String(value));playButton.textContent=value?'…':video.paused?'▶':'II';overlay.textContent=value?'Loading…':'▶ Play';}
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
  function simTime(mediaTime=video.currentTime){const map=demo.time_map;for(let i=0;i<map.length-1;i++){const [a,x]=map[i],[b,y]=map[i+1];if(mediaTime<=b)return x+(y-x)*(mediaTime-a)/(b-a);}return map.at(-1)[1];}
  function progress(){
    if(!demo)return;
    measuredSpeed();
    updateProof();
    $('#physics-progress').value=Math.round(video.currentTime/demo.duration*1000);
    $('#physics-clock').textContent=demo.proof?`${simTime().toFixed(1)} s`:`${clock(video.currentTime)} / ${clock(demo.duration)}`;
    $('#physics-clock').title=demo.proof?'Simulation time':'Playback time';
    playButton.textContent=video.paused?'▶':'II';playButton.setAttribute('aria-label',video.paused?'Play scene video':'Pause scene video');
    let phase='';for(const [t,text]of demo.phases){if(t>video.currentTime)break;phase=text;}
    $('#simple-phase').textContent=phase;$('#simple-phase').hidden=Boolean(demo.proof)||!image.hidden||!phase;
    if(details&&measurementsVisible&&shown&&(video.paused||video.seeking))plot();
  }
  function select(id){
    const next=items.find(d=>d.id===id);if(!next)return;
    if(demo?.id===id)return;
    stop();version++;demo=next;details=null;chartGeometry=null;chart.replaceChildren();chart.dataset.drawn='';chartTime.textContent='';detailAbort?.abort();source=false;pending=null;posterLoading=false;
    $('#physics-values').replaceChildren();$('#physics-sample-label').textContent='';
    measurementHeading.hidden=measurementNote.hidden=true;$('#oracle-chart-wrap').hidden=true;
    if(video.hasAttribute('src')){video.removeAttribute('src');video.load();}
    configureProof();video.playbackRate=Number(speed.value);image.alt=demo.name;zoom.setScene(demo);poster();
    overlay.hidden=false;loading(false);$('#physics-error').hidden=true;
    $('.physics-video-frame').classList.remove('is-oracle','is-simple','is-clear');
    $('.physics-video-frame').classList.add(demo.presentation==='clear'?'is-clear':'is-simple');
    video.setAttribute('aria-label',`${demo.name}: demonstration of the hidden rule`);
    readoutVisibility();progress();
    if(shown&&measurementsVisible)loadMeasurements();
  }
  function measuredRows(entry,sample){
    const labels={
      'Oracle effect':'Extra effect','Red-pair attraction':'Red pair','Blue-pair attraction':'Blue pair',
      'Light red · mass 1':'Red · mass 1','Heavy blue · mass 4':'Blue · mass 4',
      'Red apex · stronger gravity':'Stronger gravity','Blue apex · weaker gravity':'Weaker gravity',
      'Impulse 2 → initial speed':'Impulse 2','Impulse 10 → initial speed':'Impulse 10',
      'Measured boundary multiplier':'Boundary multiplier','Instantaneous speed change':'Speed before → after',
      'Energy injected by the oracle':'Altered rule','Ordinary-physics reference':'Ordinary physics',
      'Measured speed multiplier':'Speed multiplier','Blue, at the oracle update':'Blue: before → after',
      'Distinct contacts counted':'Ball contacts','Echo countdown':'Copy in',
      'Extra northward force':'Northward force','Pause remaining':'Resumes in'
    };
    let heading={'02':'Added attraction','03':'Height (bricks)','04':'Maximum height (bricks)','07':'Rebound speed (% of impact speed)','08':'Launch speed · limit 2.2','10':'Energy added'}[entry.id]||'';
    let pending=false;
    const rows=sample.annotation.values.map(([key,raw],i)=>{
      let label=labels[key]||key,value=raw;
      if(entry.id==='07')label=i===0?'Red tile':'Blue tile';
      if(/Waiting|Awaiting|Not triggered/.test(value)){pending=true;value='—';}
      value=value.replace('None · ordinary control','None').replace('Right of motion · no work','Right of motion').replace('No active energy input','0').replace('Unaffected control','Unchanged').replace('Transfer applied','Copied');
      if(entry.id==='03')value=value.replace('z = ','');
      if(entry.id==='08')value=value.replace(/\s*<\s*2\.2/,'');
      if(entry.id==='12')value=value[0].toUpperCase()+value.slice(1);
      if(entry.id==='13'&&i===1){label='Upward kick';value=sample.annotation.active?'Both balls':'Not yet';}
      if(['14','15'].includes(entry.id))value=value.replace('counts','s');
      return [label,value];
    });
    return {heading,rows,note:pending?(entry.id==='07'?'— No impact yet.':entry.id==='04'?'— Peak not reached.':'— Not triggered yet.'):''};
  }
  function plot(){
    const entry=details,sample=entry.timeline[Math.min(entry.timeline.length-1,Math.floor(video.currentTime*entry.fps))];
    $('#physics-sample-label').textContent=`Simulation time · ${sample.time.toFixed(2)} s`;
    const display=measuredRows(entry,sample),list=$('#physics-values');
    measurementHeading.textContent=display.heading;measurementHeading.hidden=!display.heading;
    measurementNote.textContent=display.note;measurementNote.hidden=!display.note;
    while(list.children.length>display.rows.length)list.lastElementChild.remove();
    display.rows.forEach(([label,value],i)=>{
      let item=list.children[i];if(!item){item=document.createElement('div');item.append(document.createElement('span'),document.createElement('strong'));list.append(item);}
      const nodes=item.children;if(nodes[0].textContent!==label)nodes[0].textContent=label;if(nodes[1].textContent!==value)nodes[1].textContent=value;
    });
    const width=Math.max(240,Math.round(chart.clientWidth||320));
    const p=entry.plot,left=38,right=width-10,top=26,bottom=82,max=Math.max(.1,...p.series.flat()),min=entry.id==='12'?Math.min(...p.series.flat()):Math.min(0,...p.series.flat());
    const quantities={'01':'Height','02':'Attraction','03':'Height','04':'Gravity / g₀','05':'Red speed','06':'Northward force','07':'Vertical velocity','08':'Blue speed','09':'Red speed','10':'Added energy','11':'Blue speed','12':'Color','13':'Red height','14':'Green speed','15':'Northward force'};
    const unit=['04','12'].includes(entry.id)?'':(entry.oracle.unit||'').replace('bricks/count','bricks/s');
    const axisLabel=quantities[entry.id]+(unit?` (${unit})`:'');
    const xy=(x,y)=>[left+x/entry.simulation_duration*(right-left),bottom-(y-min)/(max-min||1)*(bottom-top)];
    const key=`${entry.id}:${width}`;
    chartGeometry={left,right,duration:entry.simulation_duration};
    if(chart.dataset.drawn!==key){let svg=`<text id="oracle-y-label" x="${left}" y="12" fill="#456553" font-size="11.5" font-weight="500">${axisLabel}</text><path d="M${left} ${top}V${bottom}H${right}" fill="none" stroke="#afc2b4"/>`;
    const ticks=entry.id==='12'?[min,max]:[min,min<0?0:(min+max)/2,max];
    for(const value of ticks){const y=xy(0,value)[1],label=entry.id==='12'?(value===min?'Blue':'Red'):Number(value.toPrecision(2));svg+=`<path d="M${left} ${y}H${right}" stroke="#e0e8e1"/><text x="32" y="${y+4}" text-anchor="end" fill="#71867c" font-size="12">${label}</text>`;}
    p.series.forEach((values,i)=>{const d=p.times.map((time,j)=>(j?'L':'M')+xy(time,values[j]).map(x=>x.toFixed(2)).join(' ')).join('');svg+=`<path d="${d}" stroke="${p.colors[i]}" stroke-width="2" fill="none"/>`;});
    svg+=`<g id="oracle-cursor" class="video-time-marker"><title>Current video time</title><path class="video-time-halo" d="M0 ${top}V${bottom}"/><path class="video-time-line" d="M0 ${top}V${bottom}"/><path class="video-time-head" d="M-4 ${top-6}H4L0 ${top}Z"/></g><text x="${left}" y="100" fill="#71867c" font-size="12">0</text><text x="${(left+right)/2}" y="100" text-anchor="middle" fill="#71867c" font-size="11">Simulation time (s)</text><text x="${right}" y="100" text-anchor="end" fill="#71867c" font-size="12">${entry.simulation_duration}</text>`;
    chart.setAttribute('viewBox',`0 0 ${width} 106`);
    chart.setAttribute('aria-label',`${axisLabel} versus simulation time in seconds.`);
    chart.dataset.quantity=entry.oracle.measure;chart.dataset.unit=unit;
    chart.innerHTML=svg;chart.dataset.drawn=key;
    $('#oracle-chart-legend').replaceChildren(...p.labels.map((label,i)=>{const item=document.createElement('span');item.textContent=label.replace('Ordinary physics reference','Ordinary physics').replace('Oracle active','Altered rule');item.style.color=p.colors[i];return item;}));
    $('#oracle-signal').textContent='Video data';
    }
    updateChartCursor();
  }
  function updateChartCursor(mediaTime){
    if(!details||!chartGeometry)return;
    const cursor=$('#oracle-cursor');if(!cursor)return;
    const {left,right,duration}=chartGeometry,t=Math.max(0,Math.min(duration,simTime(mediaTime)));
    cursor.setAttribute('transform',`translate(${left+t/duration*(right-left)},0)`);
    cursor.setAttribute('data-time',t.toFixed(3));
    cursor.querySelector('title').textContent=`Video simulation time: ${t.toFixed(2)} s`;
    const label=`t = ${t.toFixed(2)} s`;if(chartTime.textContent!==label)chartTime.textContent=label;
  }
  async function loadMeasurements(){
    if(!demo||details)return;const id=demo.id;detailAbort?.abort();detailAbort=new AbortController();
    try{const response=await fetch(demo.details,{signal:detailAbort.signal});if(!response.ok)throw Error();const data=await response.json();if(id!==demo.id)return;details=data;$('#oracle-chart').dataset.drawn='';$('#oracle-chart-wrap').hidden=false;plot();}
    catch(e){if(e.name!=='AbortError'){ $('#oracle-chart-wrap').hidden=false;$('#oracle-signal').textContent='Video data unavailable.'; }}
  }
  window.LongChangScenePlayer.playback({
    host: $('#atlas-physics-view'), prefix: 'physics', video,
    existing: $('#worlds .physics-playback'), speed: Number(speed.value),
    handlers: {
      toggle: () => { if(video.paused&&!wants)start();else stop(); },
      reset: () => { stop();if(source){pending=null;video.currentTime=0;}poster();overlay.hidden=false;progress(); },
      seek: fraction => {
        const destination=fraction*demo.duration;stop();
        if(!source)loadSource(destination);else{pending={time:destination};video.currentTime=destination;}
        overlay.hidden=true;progress();
      },
    },
  });
  overlay.addEventListener('click',start);
  video.addEventListener('loadedmetadata',()=>{video.playbackRate=Number(speed.value);if(pending)video.currentTime=pending.time;progress();});
  video.addEventListener('canplay',ready);
  video.addEventListener('playing',()=>{clearTimeout(timer);if(!pending)image.hidden=true;overlay.hidden=true;loading(false);progress();cancelProgress();animateProgress();});
  video.addEventListener('waiting',()=>{if(wants){loading(true);armTimeout();}});
  video.addEventListener('pause',()=>{cancelProgress();progress();});video.addEventListener('timeupdate',progress);video.addEventListener('seeked',()=>{if(pending)ready();else progress();});
  video.addEventListener('error',()=>{if(source)fail();});
  video.addEventListener('ended',()=>{wants=false;overlay.hidden=false;overlay.textContent='↺ Replay';progress();});
  document.addEventListener('fullscreenchange',()=>{
    video.controls=false;
  });
  document.addEventListener('longchang:atlas-view',e=>{shown=e.detail.view==='physics';syncView(e.detail.view);if(shown)select(e.detail.id);else{stop();}});
  document.addEventListener('longchang:scene',e=>select(e.detail.id));
  new IntersectionObserver(e=>{if(!e[0].isIntersecting&&source)stop();},{threshold:0}).observe($('#atlas-physics-view'));
  new IntersectionObserver(entries=>{measurementsVisible=entries[0].isIntersecting;if(measurementsVisible&&shown){loadMeasurements();if(details)plot();}},{rootMargin:'100px'}).observe(measurements);
  new ResizeObserver(()=>{if(details&&shown&&chart.clientWidth)plot();}).observe(chart);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  window.LongChangPhysics=Object.freeze({play:start});
  shown=$('.atlas-detail').dataset.view==='physics';syncView($('.atlas-detail').dataset.view);select(window.LongChangAtlas.currentScene());
})();
