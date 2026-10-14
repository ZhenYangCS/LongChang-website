/* Scene-specific models built with the 15 Worlds' drawing, clock and MathML. */
(() => {
  'use strict';
  function create({host:root,video}) {
  const $ = suffix => root.querySelector(`#evo-model-${suffix}`);
  const {base, point, line, text, polygon, ball} = window.LongChangMotion.draw;
  const uid = 'evolution-model', duration = 20, reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const configs = {
    generate: {label:'Push schedule', initial:'once', options:[['once','Once at 0 s'],['repeat','Every 8 s']]},
    mutate: {label:'Blue position', initial:'inside', options:[['inside','Inside the square'],['outside','Outside the square']]},
    compose: {label:'Push blue', initial:'later', options:[['none','No second push'],['later','At 8 s']]},
  };
  let id = document.querySelector('[data-evolution][aria-selected=true]').dataset.evolution;
  let value = configs[id].initial, time = 0, playing = !reduced.matches, visible = false;
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
    svg += line([cursor,48],[cursor,99],'#9a795a','stroke-width="1.5"') + text(84,114,'0', 'font-size="12"') + text(579,114,'20 s','font-size="12" text-anchor="end"');
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
    $('note').textContent = id === 'compose' ? 'Red pushed at 0 s. Positions are schematic.' : id === 'mutate' ? 'A push at 0 s; positions are schematic.' : 'Force timing; positions are schematic.';
    $('progress').value = Math.round(time*10); $('time').textContent = `${time.toFixed(1)} s`;
    $('play').textContent = playing ? 'II' : '▶';
    $('play').setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} explanatory model`);
  }
  const running = () => playing && visible && !root.hidden && !document.hidden && !document.querySelector('dialog[open]');
  const clock = window.LongChangScenePlayer.modelClock({running,tick(elapsed) { time=Math.min(duration,time+elapsed*4); if(time===duration)playing=false; render(); }});
  function select(scene, description) {
    if (description) $('rule').textContent = description.full;
    root.scrollTop=0;
    id=scene; value=configs[id].initial; time=0; playing=!reduced.matches;
    const config=configs[id];
    $('settings').querySelector('label').textContent=config.label;
    $('parameter').innerHTML=config.options.map(([v,label])=>`<option value="${v}">${label}</option>`).join('');
    $('parameter').value=value;
    $('canvas').setAttribute('aria-label', `${description?.name || id}: adjustable force and delay model`);
    window.LongChangMath.render($('formula'), `evo-${id}`);
    render(); clock.sync(); drawRecorded();
  }
  function parameter(next, {restart=true}={}) {
    if (!configs[id].options.some(([v])=>v===next)) return;
    value=next; $('parameter').value=value;
    if(restart){time=0;playing=!reduced.matches;}
    render();clock.sync();
  }
  $('parameter').addEventListener('change', event=>parameter(event.target.value));
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
  let signals=null, loadingData=false, chartScene=null;
  function drawRecorded() {
    if(!signals)return;
    const signal=signals[id], left=35,right=306,top=17,bottom=105,max=Math.max(1.5,...signal.samples.map(row=>row[1]));
    const xy=(t,f)=>[left+t/signal.duration*(right-left),bottom-f/max*(bottom-top)];
    if(chartScene!==id){
      const path=signal.samples.map(([t,f],i)=>(i?'L':'M')+xy(t,f).map(n=>n.toFixed(2)).join(' ')).join('');
      chart.innerHTML=`<path d="M${left} ${top}V${bottom}H${right}" fill="none" stroke="#cbdad2"/><text x="28" y="${top+5}" text-anchor="end">${max.toFixed(1)}</text><text x="28" y="${bottom+4}" text-anchor="end">0</text><text x="${left}" y="124">0</text><text x="${right}" y="124" text-anchor="end">${signal.duration.toFixed(1)} s</text><path class="evo-recorded-series" d="${path}" fill="none" stroke="#577f69" stroke-width="2"/><path class="evo-recorded-cursor" d="M0 ${top}V${bottom}" stroke="#9c7957" stroke-width="1.5"/>`;
      chartScene=id;
    }
    const t=(video.currentTime||0)/(Number.isFinite(video.duration)?video.duration:10)*signal.duration;
    chart.querySelector('.evo-recorded-cursor').setAttribute('transform',`translate(${xy(t,0)[0]},0)`);
    chartStatus.textContent=`Demo time · ${t.toFixed(1)} s`;
  }
  async function loadData(){
    if(signals){drawRecorded();return;}if(loadingData)return;loadingData=true;
    root.querySelector('#evo-chart-retry').hidden=true;
    try{
      const response=await fetch('data/evolution-signals.json',{signal:AbortSignal.timeout(20000)});
      if(!response.ok)throw Error('Data unavailable');signals=await response.json();drawRecorded();
    }catch(_){chartStatus.textContent='Recorded data could not load.';root.querySelector('#evo-chart-retry').hidden=false;}
    finally{loadingData=false;}
  }
  root.querySelector('#evo-chart-retry').addEventListener('click',loadData);
  for(const event of ['timeupdate','seeked','loadedmetadata'])video.addEventListener(event,drawRecorded);
  new IntersectionObserver(entries=>{if(entries[0].isIntersecting)loadData();},{rootMargin:'50px'}).observe(chart);
  return Object.freeze({getState:()=>({id,value,time,playing,...evaluate(id,value,time)}),setParameter:parameter,setScene:select,setActive(active){root.hidden=!active;clock.sync();}});
  }
  window.LongChangEvolutionModel=Object.freeze({create});
})();
