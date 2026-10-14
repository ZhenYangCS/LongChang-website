/* Scene-specific models built with the 15 Worlds' drawing, clock and MathML. */
(() => {
  'use strict';
  function create({host:root,video}) {
  const $ = suffix => root.querySelector(`#evo-model-${suffix}`);
  const {base, point, line, text, polygon, ball} = window.LongChangMotion.draw;
  const uid = 'evolution-model', duration = 20, reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const modelCaption=document.createElement('p');modelCaption.id='evo-model-caption';
  const readout=root.querySelector('.atlas-scene-readout');readout.append(modelCaption);
  readout.setAttribute('role','note');readout.setAttribute('aria-label','Current model result');
  $('state').hidden=true;$('value').hidden=true;
  new ResizeObserver(()=>{
    const svg=$('canvas'),matrix=svg.getScreenCTM(),scale=matrix&&Math.hypot(matrix.a,matrix.b);
    if(scale>0){
      svg.style.setProperty('--model-hit-radius',`${Math.max(26,26/scale)}px`);
      svg.style.setProperty('--model-ball-radius',`${Math.max(14,7/scale)}px`);
      svg.style.setProperty('--model-ball-label',`${Math.max(14,10/scale)}px`);
      svg.style.setProperty('--model-text-size',`${Math.max(20,9/scale)}px`);
    }
  }).observe($('canvas'));
  const configs = {
    generate: {label:'Push schedule', initial:'once', options:[['once','Once at 0 s'],['repeat','Every 8 s']]},
    mutate: {label:'Blue position', initial:'inside', options:[['inside','Inside the square'],['outside','Outside the square']]},
    compose: {label:'Push blue', initial:'later', options:[['none','No second push'],['later','At 8 s']]},
  };
  const modelRules = {
    generate: 'Red and blue repel. Any nonzero push pauses repulsion for 10 s; another push restarts the pause.',
    mutate: 'Red drifts north after 10 s without a nonzero push, only while blue is outside the square. Moving blue by hand keeps the timer.',
    compose: 'Any nonzero push pauses red’s drift for 10 s. Each red launch also queues a separate velocity copy to green, 12 s later.',
  };
  const illustrationHelp = {
    generate:'Compare one push with repeated pushes.',
    mutate:'Move blue and watch the northward force.',
    compose:'Time blue’s push after red’s launch at 0 s.',
  };
  let id = document.querySelector('[data-evolution][aria-selected=true]').dataset.evolution;
  let value = configs[id].initial, time = 0, playing = !reduced.matches, visible = false, choices = null;
  function evaluate(scene, option, seconds) {
    const lastPush = scene === 'generate' && option === 'repeat' ? Math.floor(seconds/8)*8 : scene === 'compose' && option === 'later' && seconds >= 8 ? 8 : 0;
    const quietUntil = lastPush + 10, blocked = scene === 'mutate' && option === 'inside';
    return {lastPush, quietUntil, blocked, active:seconds >= quietUntil && !blocked, copyTime:scene === 'compose' ? 12 : null, copied:scene === 'compose' && seconds >= 12};
  }
  const arrow = (a,b,active) => line(a,b,active ? '#3b837b' : '#b8c9c0', `stroke-width="3" ${active ? `marker-end="url(#${uid}-arrow)"` : 'stroke-dasharray="4 5"'}`);
  function diagram(state) {
    let svg = base(uid);
    // Same time axis for every condition; only the stated exceptional force is shown.
    svg += text(92,37,'EXTRA FORCE', 'font-size="13" font-weight="500"');
    svg += text(67,62,'on', 'text-anchor="end" font-size="13"') + text(67,96,'off', 'text-anchor="end" font-size="13"');
    svg += line([84,58],[579,58],'#d6e3da') + line([84,92],[579,92],'#d6e3da');
    let path = '';
    for (let n=0; n<=200; n++) {
      const t=n/10, x=84+t/20*495, y=evaluate(id,value,t).active ? 58 : 92;
      path += `${n ? 'H' : 'M'}${x.toFixed(1)}${n ? 'V' : ','}${y}`;
    }
    svg += `<path d="${path}" stroke="#52856e" stroke-width="3" fill="none"/>`;
    const cursor = 84+time/20*495;
    svg += `<g class="evo-time-marker evo-model-cursor" transform="translate(${cursor},0)" data-time="${time.toFixed(3)}"><title>Model time: ${time.toFixed(1)} s</title><path class="evo-time-line" d="M0 43V103"/><path class="evo-time-head" d="M-6 39H6L0 47Z"/><circle class="evo-time-point" cx="0" cy="${state.active ? 58 : 92}" r="6"/></g>` + text(84,114,'0', 'font-size="12"') + text(579,114,'20 s','font-size="12" text-anchor="end"');
    if (id === 'generate') {
      const r=[2,3.7], b=[4.2,2.5];
      svg += arrow(point(...r,.35),point(.9,4.3,.35),state.active) + arrow(point(...b,.35),point(5.3,1.9,.35),state.active);
      svg += ball(uid,...r,.12,'red','R') + ball(uid,...b,.12,'blue','B');
      svg += text(320,332,state.active ? 'Repulsion on' : 'Repulsion paused','text-anchor="middle" font-size="17"');
    } else if (id === 'mutate') {
      svg += polygon([[2.5,2.5],[3.5,2.5],[3.5,3.5],[2.5,3.5]].map(p=>point(...p,.025)), '#b9c7c8', 'stroke="#8ea6a0" stroke-width="1.2"');
      const blueX = state.blocked ? 3 : 4.5;
      svg += arrow(point(1.6,2.9,.35),point(1.6,4.1,.35),state.active);
      svg += ball(uid,1.6,2.9,.12,'red','R');
      svg += `<g class="model-object" data-evo-model-blue><title>Click blue to move it inside or outside</title>${ball(uid,blueX,3,.12,'blue','B')}<circle class="model-hit" cx="${point(blueX,3,.12)[0]}" cy="${point(blueX,3,.12)[1]-13}" r="26"/></g>`;
      svg += text(320,333,state.blocked ? 'Blue blocks the force' : 'Blue is outside','text-anchor="middle" font-size="17"');
    } else {
      svg += arrow(point(1.8,3.5,.35),point(1.8,4.6,.35),state.active);
      if (state.copied) svg += arrow(point(3.4,3.5,.35),point(3.4,2.35,.35),true);
      svg += ball(uid,1.8,3.5,.12,'red','R') + ball(uid,3.4,3.5,.12,'green','G') + ball(uid,4.8,1.9,.12,'blue','B');
      const copyX=84+12/20*495;
      svg += `<circle cx="${copyX}" cy="92" r="4" fill="#6b9b7e"/>` + text(copyX,135,'copy at 12 s','text-anchor="middle" font-size="13"');
      svg += text(320,338,state.copied ? 'Green copied red’s launch velocity' : 'Green’s copy is queued','text-anchor="middle" font-size="16"');
    }
    return svg+'</g>';
  }
  function render() {
    const state = evaluate(id,value,time), remaining = Math.max(0,state.quietUntil-time);
    $('canvas').innerHTML = diagram(state);
    $('state').textContent = state.blocked ? 'Blue inside · force blocked' : state.active ? 'Extra force active' : 'Extra force paused';
    $('value').textContent = id === 'compose' ? `${state.copied ? 'Copy applied at 12 s' : `Green copies in ${(12-time).toFixed(1)} s`} · ${state.active ? 'drift on' : `drift in ${remaining.toFixed(1)} s`}` : state.blocked ? 'Moving blue by hand does not reset the timer.' : state.active ? 'Acceleration: 1.5 bricks/s²' : `Resumes in ${remaining.toFixed(1)} s`;
    modelCaption.textContent = id==='compose'
      ? state.copied ? state.active ? 'Velocity copied · drift on.' : `Copied · drift in ${remaining.toFixed(1)} s.` : `Drift ${state.active?'on':'paused'} · copy in ${(12-time).toFixed(1)} s.`
      : id==='mutate' ? state.blocked ? 'Blue inside: northward force blocked.' : state.active ? 'Blue outside: red drifts north.' : `Drift resumes in ${remaining.toFixed(1)} s.`
      : state.active ? 'The balls repel again.' : value==='repeat' ? 'Repeated pushes keep repulsion off.' : `Repulsion resumes in ${remaining.toFixed(1)} s.`;
    $('note').textContent = illustrationHelp[id];
    $('progress').value = Math.round(time*10); $('time').textContent = `${time.toFixed(1)} s`;
    $('play').textContent = playing ? 'II' : '▶';
    $('play').setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} explanatory model`);
  }
  const running = () => playing && visible && !root.hidden && !document.hidden && !document.querySelector('dialog[open]');
  const clock = window.LongChangScenePlayer.modelClock({running,tick(elapsed) { time=Math.min(duration,time+elapsed*4); if(time===duration)playing=false; render(); }});
  function select(scene, description) {
    $('rule').textContent = modelRules[scene];
    root.scrollTop=0;
    id=scene; value=configs[id].initial; time=0; playing=!reduced.matches;
    const config=configs[id];
    choices = window.LongChangModelOptions.create({host:$('settings'),id:'evo-model-parameter',label:config.label,options:config.options,value,scene:`evo-${id}`,onChange:parameter});
    $('canvas').setAttribute('aria-label', `${description?.name || id}: adjustable force and delay model`);
    window.LongChangMath.render($('formula'), `evo-${id}`);
    render(); clock.sync(); drawRecorded();
  }
  function parameter(next, {restart=true}={}) {
    if (!configs[id].options.some(([v])=>v===next)) return;
    value=next; choices.set(value);
    if(restart){time=0;playing=!reduced.matches;}
    render();clock.sync();
  }
  $('play').addEventListener('click',()=>{if(time>=duration)time=0;playing=!playing;render();clock.sync();});
  $('reset').addEventListener('click',()=>{time=0;playing=false;render();clock.sync();});
  $('progress').addEventListener('input',event=>{time=Math.max(0,Math.min(duration,Number(event.target.value)/10));playing=false;render();clock.sync();});
  $('canvas').addEventListener('click',event=>{if(id==='mutate'&&event.target.closest('[data-evo-model-blue]'))parameter(value==='inside'?'outside':'inside',{restart:false});});
  $('fullscreen').addEventListener('click',async()=>{if(document.fullscreenElement)await document.exitFullscreen();else await root.requestFullscreen();});
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;clock.sync();},{threshold:.05}).observe(root);
  document.addEventListener('visibilitychange',()=>clock.sync());
  for(const dialog of document.querySelectorAll('dialog'))new MutationObserver(()=>clock.sync()).observe(dialog,{attributes:true,attributeFilter:['open']});
  reduced.addEventListener('change',()=>{if(reduced.matches){playing=false;render();clock.sync();}});
  // This plot reads the stored native demonstration, never the adjustable model.
  const chart=root.querySelector('#evo-demo-chart'), chartStatus=root.querySelector('#evo-chart-status');
  const dataPanel=chart.closest('.evo-demo-data'),retry=dataPanel.querySelector('#evo-chart-retry');
  dataPanel.classList.add('video-data');
  const heading=document.createElement('div');heading.className='video-data-heading';
  const caption=document.createElement('span');caption.textContent='Video data · Recorded force';
  chartStatus.className='video-data-clock';chartStatus.setAttribute('aria-live','off');chartStatus.title='Simulation time in this video';
  chartStatus.textContent='Loading…';
  dataPanel.querySelector('h4').replaceWith(heading);heading.append(caption,chartStatus);
  video.closest('#evo-demo-view').append(dataPanel);
  let signals=null, loadingData=false, chartScene=null, recordedFrame=null;
  function drawRecorded(mediaTime=video.currentTime) {
    if(!signals)return;
    const width=Math.max(240,Math.round(chart.clientWidth||320));
    const signal=signals[id], left=38,right=width-10,top=10,bottom=66,max=Math.max(1.5,...signal.samples.map(row=>row[1]));
    const xy=(t,f)=>[left+t/signal.duration*(right-left),bottom-f/max*(bottom-top)];
    const key=`${id}:${width}`;
    if(chartScene!==key){
      const path=signal.samples.map(([t,f],i)=>(i?'L':'M')+xy(t,f).map(n=>n.toFixed(2)).join(' ')).join('');
      chart.setAttribute('viewBox',`0 0 ${width} 90`);
      chart.innerHTML=`<path d="M${left} ${top}V${bottom}H${right}" fill="none" stroke="#cbdad2"/><text x="32" y="${top+4}" text-anchor="end">${max.toFixed(1)}</text><text x="32" y="${bottom+4}" text-anchor="end">0</text><text x="${left}" y="84">0</text><text x="${right}" y="84" text-anchor="end">${signal.duration.toFixed(1)} s</text><path class="evo-recorded-series" d="${path}" fill="none" stroke="#577f69" stroke-width="2"/><g class="video-time-marker evo-time-marker evo-recorded-cursor"><title></title><path class="video-time-halo" d="M0 ${top}V${bottom}"/><path class="video-time-line evo-time-line" d="M0 ${top}V${bottom}"/><path class="video-time-head evo-time-head" d="M-4 ${top-6}H4L0 ${top}Z"/><circle class="evo-time-point" cx="0" r="3.5"/></g>`;
      chartScene=key;
    }
    const t=Math.max(0,Math.min(signal.duration,(mediaTime||0)/(Number.isFinite(video.duration)&&video.duration>0?video.duration:10)*signal.duration));
    let lo=0,hi=signal.samples.length;
    while(lo<hi){const mid=(lo+hi)>>1;if(signal.samples[mid][0]<=t)lo=mid+1;else hi=mid;}
    const force=signal.samples[Math.max(0,lo-1)][1],marker=chart.querySelector('.evo-recorded-cursor');
    marker.setAttribute('transform',`translate(${xy(t,force)[0]},0)`);
    marker.setAttribute('data-time',t.toFixed(3));
    marker.querySelector('.evo-time-point').setAttribute('cy',xy(t,force)[1]);
    marker.querySelector('title').textContent=`Video simulation time: ${t.toFixed(2)} s`;
    const label=`t = ${t.toFixed(2)} s`;
    if(chartStatus.textContent!==label)chartStatus.textContent=label;
  }
  function cancelRecordedFrame(){
    if(recordedFrame===null)return;
    if(video.cancelVideoFrameCallback)video.cancelVideoFrameCallback(recordedFrame);else cancelAnimationFrame(recordedFrame);
    recordedFrame=null;
  }
  function animateRecorded(_now,metadata){
    recordedFrame=null;drawRecorded(metadata?.mediaTime);
    if(signals&&!video.paused&&!video.ended&&!document.hidden&&!video.closest('[hidden]')){
      recordedFrame=video.requestVideoFrameCallback?video.requestVideoFrameCallback(animateRecorded):requestAnimationFrame(animateRecorded);
    }
  }
  function syncRecorded(){cancelRecordedFrame();animateRecorded();}
  async function loadData(){
    if(signals){drawRecorded();return;}if(loadingData)return;loadingData=true;
    retry.hidden=true;
    try{
      const response=await fetch('data/evolution-signals.json',{signal:AbortSignal.timeout(20000)});
      if(!response.ok)throw Error('Data unavailable');signals=await response.json();syncRecorded();
    }catch(_){chartStatus.textContent='Unavailable';retry.hidden=false;}
    finally{loadingData=false;}
  }
  retry.addEventListener('click',loadData);
  for(const event of ['timeupdate','seeking','seeked','loadedmetadata'])video.addEventListener(event,()=>{if(event!=='timeupdate'||video.paused||video.seeking)drawRecorded();});
  for(const event of ['playing','pause','ended','emptied'])video.addEventListener(event,syncRecorded);
  document.addEventListener('visibilitychange',syncRecorded);
  new IntersectionObserver(entries=>{if(entries[0].isIntersecting)loadData();},{rootMargin:'50px'}).observe(chart);
  new ResizeObserver(()=>{if(chart.clientWidth)drawRecorded();}).observe(chart);
  return Object.freeze({getState:()=>({id,value,time,playing,...evaluate(id,value,time)}),setParameter:parameter,setScene:select,setActive(active){root.hidden=!active;clock.sync();if(active)loadData();syncRecorded();}});
  }
  window.LongChangEvolutionModel=Object.freeze({create});
})();
