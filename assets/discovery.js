(() => {
  'use strict';
  const cases = window.DISCOVERIES;
  if (!cases?.length) return;
  const $ = q => document.querySelector(q);
  const $$ = q => [...document.querySelectorAll(q)];
  const esc = v => String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let selected=0,chapter=0;
  const video=$('#success-video'),slider=$('#replay-progress'),play=$('#replay-play');
  let videoGeneration=0,videoLoading=false,wantsVideo=false,videoAnimation=0;
  const cache=new Map();

  function setTab(button) {
    button.closest('[role="tablist"]').querySelectorAll('[role="tab"]').forEach(b=>{
      b.setAttribute('aria-selected',String(b===button));b.tabIndex=b===button?0:-1;
    });
  }
  function keyboardTabs(root,choose) {
    root.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
      const buttons=[...root.querySelectorAll('[role="tab"]')],i=buttons.indexOf(document.activeElement);
      if(i<0)return;e.preventDefault();
      const n=e.key==='Home'?0:e.key==='End'?buttons.length-1:(i+(e.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;
      choose(buttons[n]);buttons[n].focus();
    });
  }
  function videoProgress() {
    const c=cases[selected].chapters[chapter];
    const fraction=Number.isFinite(video.duration)&&video.duration>0?video.currentTime/video.duration:0;
    slider.value=String(Math.round(fraction*1000));$('#replay-percent').textContent=`${Math.round(fraction*100)}%`;
    $('#success-clock').textContent=`${(c.start+fraction*(c.end-c.start)).toFixed(2)} counts`;
    if(!video.paused)videoAnimation=requestAnimationFrame(videoProgress);
  }
  function pauseVideo() {
    wantsVideo=false;video.pause();cancelAnimationFrame(videoAnimation);
    play.innerHTML='<span aria-hidden="true">▶</span>';play.setAttribute('aria-label','Play recorded experiment');
  }
  function startVideo() {
    wantsVideo=true;
    if(videoLoading||video.readyState<2){play.textContent='…';return;}
    if(video.ended||video.currentTime>=video.duration-.04)video.currentTime=0;
    video.play().then(()=>{
      play.innerHTML='<span aria-hidden="true">II</span>';play.setAttribute('aria-label','Pause recorded experiment');
      cancelAnimationFrame(videoAnimation);videoProgress();
    }).catch(()=>{pauseVideo();});
  }
  async function loadVideo(c) {
    const generation=++videoGeneration;videoLoading=true;pauseVideo();video.poster=c.poster;
    video.removeAttribute('src');video.load();
    let src=c.video;
    if(location.protocol!=='file:'){
      if(!cache.has(src))cache.set(src,fetch(src).then(r=>{if(!r.ok)throw new Error('Video unavailable');return r.blob();}).then(b=>URL.createObjectURL(b)));
      try{src=await cache.get(src);}catch(_){cache.delete(c.video);}
    }
    if(generation!==videoGeneration)return;
    video.src=src;video.load();videoLoading=false;
  }
  video.addEventListener('loadedmetadata',videoProgress);
  video.addEventListener('loadeddata',()=>{videoProgress();if(wantsVideo)startVideo();});
  video.addEventListener('ended',()=>{pauseVideo();videoProgress();});
  video.addEventListener('error',pauseVideo);
  play.addEventListener('click',()=>video.paused&&!wantsVideo?startVideo():pauseVideo());
  slider.addEventListener('input',()=>{
    const value=Number(slider.value)/1000;pauseVideo();
    if(Number.isFinite(video.duration))video.currentTime=Math.min(video.duration-.025,value*video.duration);
    videoProgress();
  });
  $('#replay-reset').addEventListener('click',()=>{pauseVideo();video.currentTime=0;videoProgress();});
  new IntersectionObserver(e=>{if(!e[0].isIntersecting)pauseVideo();}).observe(video);

  function chooseChapter(button) {
    chapter=Number(button.dataset.chapter);setTab(button);
    const c=cases[selected].chapters[chapter];
    $('#success-chapter-title').textContent=c.title;$('#success-description').textContent=c.description;
    $('#success-note').textContent=c.note;$('#success-note-source').textContent=`Original note · Turn ${c.noteTurn}`;
    $('#success-turns').textContent=`Turns ${c.turns[0]}–${c.turns[c.turns.length-1]}`;
    $('#success-clock').textContent=`${c.start.toFixed(2)} counts`;
    $('#success-note').closest('details').open=false;
    slider.value='0';$('#replay-percent').textContent='0%';loadVideo(c);
  }
  $('#success-picker').innerHTML=cases.map((c,i)=>`<button id="success-tab-${c.id}" role="tab" aria-controls="discovery-workbench" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-discovery="${i}"><span>SCENE ${c.id} · SUCCESSFUL RUN</span><strong>${esc(c.short)}</strong></button>`).join('');
  function chooseDiscovery(button) {
    selected=Number(button.dataset.discovery);setTab(button);pauseVideo();
    const c=cases[selected];
    $('#discovery-workbench').setAttribute('aria-labelledby',button.id);
    $('#discovery-index').textContent=`Scene ${c.id} / ${c.mechanism==='bounce'?'Surface restitution':c.mechanism==='curve'?'Velocity-dependent deflection':c.mechanism==='echo'?'Delayed velocity replacement':'Launch-suppressed drift'}`;
    $('#discovery-title').textContent=c.name;$('#discovery-question').textContent=c.intro;
    $('#discovery-run').textContent=`Astra · repeat ${c.repeat} · ${c.turns} turns`;
    $('#discovery-conclusion').textContent=c.conclusion;$('#success-final-note').textContent=c.finalNote;
    $('#success-final-note').closest('details').open=false;
    $('#success-source-label').textContent=`GPT-6-Astra · 100-turn budget · C and S passed · judge: ${c.judge}`;
    $('#success-chapters').innerHTML=c.chapters.map((s,i)=>`<button id="evidence-chapter-${i}" role="tab" aria-controls="success-description" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-chapter="${i}"><span>0${i+1}</span>${esc(s.title)}</button>`).join('');
    $$('#success-chapters button').forEach(b=>b.addEventListener('click',()=>chooseChapter(b)));
    chooseChapter($('#evidence-chapter-0'));setupLab();
  }
  $$('#success-picker button').forEach(b=>b.addEventListener('click',()=>chooseDiscovery(b)));
  keyboardTabs($('#success-picker'),chooseDiscovery);keyboardTabs($('#success-chapters'),chooseChapter);
  window.showDiscovery=id=>{
    const b=$(`#success-tab-${id}`);if(!b)return;chooseDiscovery(b);
    $('#explore').scrollIntoView({behavior:reduced?'instant':'smooth',block:'start'});
  };
  // A successful heatmap cell can open the corresponding evidence story.
  $('#heatmap').addEventListener('click',e=>{
    const b=e.target.closest('.heat-cell');if(!b||b.dataset.level==='0')return;
    const label=b.getAttribute('aria-label')||'';
    const scene=label.match(/Scene (\d+)/)?.[1];
    if(label.startsWith('GPT-6-Astra')&&label.includes('Discovery:')&&cases.some(c=>c.id===scene))window.showDiscovery(scene);
  });
  const label=$('.heatmap-key-note');if(label)label.textContent='Select an Astra discovery to open its experiment';

  // Idealized law illustrations. These are explicitly separate from archived
  // evidence; no generated trajectory is presented as an experimental record.
  const canvas=$('#law-canvas');
  let lab={t:0,playing:false,value:2,direction:0,mode:'free',swapped:false,until:10,redY:264,redV:0,lastPush:''};
  let labAnimation=0,lastTick=0,lastDraw=0,labVisible=false,autoPreviewed=false;
  const defs=`<defs><radialGradient id="sphere-gray" cx="32%" cy="24%"><stop stop-color="#fcfefe"/><stop offset=".32" stop-color="#b9c7cc"/><stop offset="1" stop-color="#677e86"/></radialGradient><radialGradient id="sphere-red" cx="30%" cy="25%"><stop stop-color="#f9b7a8"/><stop offset=".3" stop-color="#d87d68"/><stop offset="1" stop-color="#b45447"/></radialGradient><radialGradient id="sphere-blue" cx="30%" cy="25%"><stop stop-color="#b4d0ed"/><stop offset=".3" stop-color="#739dd0"/><stop offset="1" stop-color="#496e9e"/></radialGradient><radialGradient id="sphere-green" cx="30%" cy="25%"><stop stop-color="#c7e8d3"/><stop offset=".3" stop-color="#82ba99"/><stop offset="1" stop-color="#47866b"/></radialGradient><pattern id="lab-grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#dde9e3" stroke-width=".7"/></pattern><marker id="lab-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0 6 3 0 6" fill="#79a08f"/></marker></defs>`;
  const sphere=(x,y,color,r=13,label='')=>`<circle cx="${x}" cy="${y}" r="${r}" fill="url(#sphere-${color})"/>${label?`<text x="${x}" y="${y+4}" text-anchor="middle" style="font-size:9px;fill:white">${label}</text>`:''}`;
  const txt=(x,y,text,cls='',anchor='start')=>`<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${text}</text>`;
  const path=(d,color,dash='')=>`<path d="${d}" fill="none" stroke="${color}" stroke-width="2" ${dash?`stroke-dasharray="${dash}"`:''}/>`;
  function setReadout(text){if($('#lab-readout').textContent!==text)$('#lab-readout').textContent=text;}
  function stopLab(){lab.playing=false;cancelAnimationFrame(labAnimation);updateLabButton();}
  function updateLabButton(){const b=$('#lab-play');if(b)b.textContent=lab.playing?'Pause illustration':lab.t>0?'↺ Replay illustration':({bounce:'▶ Drop both',curve:'▶ Launch',echo:'▶ Run experiment',drift:'▶ Observe'}[cases[selected].mechanism]);}
  function resetLab(){stopLab();lab.t=0;lab.until=10;lab.redY=264;lab.redV=0;lab.lastPush='';renderLab();}
  function startLab(){
    if(lab.t>0)resetLab();lab.playing=true;lastTick=performance.now();lastDraw=0;updateLabButton();labAnimation=requestAnimationFrame(labTick);
  }
  function labTick(now){
    if(!lab.playing)return;
    const mechanism=cases[selected].mechanism,rate=['echo','drift'].includes(mechanism)?2.5:1;
    const dt=Math.min(.05,(now-lastTick)/1000)*rate;lastTick=now;lab.t+=dt;
    if(mechanism==='drift'){
      const active=lab.t>=lab.until;lab.redV+=(active?8:0)*dt-lab.redV*.8*dt;
      lab.redY=Math.max(78,lab.redY-lab.redV*dt);
    }
    if(now-lastDraw>30){renderLab();lastDraw=now;}
    const duration={bounce:6,curve:4.5,echo:17,drift:32}[mechanism];
    if(lab.t>=duration){stopLab();renderLab();}else labAnimation=requestAnimationFrame(labTick);
  }
  function bounceHeight(height,e,t){
    const g=9.8,fall=Math.sqrt(2*height/g);if(t<=fall)return Math.max(0,height-.5*g*t*t);
    let rest=t-fall,v=e*Math.sqrt(2*g*height),n=0;
    while(rest>2*v/g&&v>.005&&n++<80){rest-=2*v/g;v*=e;}
    return v>.005?Math.max(0,v*rest-.5*g*rest*rest):0;
  }
  function renderBounce(){
    const h=lab.value,t=lab.t,red=bounceHeight(h,.9,t),blue=bounceHeight(h,.15,t),floor=267,scale=60;
    let s=defs+txt(150,39,'Red surface','law-label','middle')+txt(350,39,'Blue surface','law-label','middle');
    s+=`<path d="M62 ${floor-h*scale}H447" stroke="#c5d7cc" stroke-dasharray="4 5"/>`+txt(60,floor-h*scale-10,`${h.toFixed(1)} bricks`,'law-small');
    [150,350].forEach((x,i)=>{const v=i?blue:red;s+=`<ellipse cx="${x}" cy="${floor+4}" rx="${Math.max(8,17-v*2)}" ry="3" fill="#547569" opacity=".13"/><rect x="${x-66}" y="${floor}" width="132" height="13" rx="3" fill="${i?'#adc3dd':'#dfb0a3'}"/><path d="M${x-66} ${floor+13}h132" stroke="${i?'#7297bd':'#bd7c6b'}"/>`;s+=sphere(x,floor-13-v*scale,'gray',13,(i!==Number(lab.swapped))?'B':'A');});
    s+=txt(150,305,'e = 0.90','law-small','middle')+txt(350,305,'e = 0.15','law-small','middle');
    s+=txt(475,67,`${t.toFixed(2)} counts`,'law-small','end');
    setReadout(`First rebound from ${h.toFixed(1)} bricks: red ${(h*.81).toFixed(2)} · blue ${(h*.0225).toFixed(3)} bricks. Swapping ball identities leaves the surface effect unchanged.`);
    return s;
  }
  function renderCurve(){
    const t=lab.t,v=lab.value,w=1.2,a=lab.direction*Math.PI/180,vx=v*Math.cos(a),vy=v*Math.sin(a),scale=17;
    const at=t=>[250+scale*(vx*Math.sin(w*t)+vy*(1-Math.cos(w*t)))/w,168-scale*(vy*Math.sin(w*t)-vx*(1-Math.cos(w*t)))/w];
    const count=Math.max(2,Math.ceil(t*35));
    const points=Array.from({length:count},(_,i)=>at(t*i/(count-1)));
    const [x,y]=at(t),velx=vx*Math.cos(w*t)+vy*Math.sin(w*t),vely=vy*Math.cos(w*t)-vx*Math.sin(w*t);
    let s=defs+'<rect x="25" y="38" width="450" height="275" rx="8" fill="url(#lab-grid)"/>';
    s+=path(`M250 168L${250+155*Math.cos(a)} ${168-155*Math.sin(a)}`,'#c2ccc9','5 5');
    s+=path(points.map((p,i)=>`${i?'L':'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' '),'#75998a');
    s+=`<circle cx="250" cy="168" r="3" fill="#7b9690"/><path d="M${x} ${y}l${velx/v*39} ${-vely/v*39}" stroke="#79a08f" stroke-width="1.5" marker-end="url(#lab-arrow)"/>`;
    s+=sphere(x,y,'red',12)+txt(40,28,'TOP VIEW · SIDE-FORCE CONTRIBUTION','law-small')+txt(460,28,`${t.toFixed(2)} counts`,'law-small','end');
    s+=txt(40,300,'Dashed: no side force','law-small');
    setReadout(`Change the launch direction: the path still turns clockwise. Here aₓ = 1.2vᵧ and aᵧ = −1.2vₓ; the side force changes direction, not speed.`);
    return s;
  }
  function renderEcho(){
    const t=lab.t,v=lab.value,hold=lab.mode==='hold'?.35:Infinity;
    const travel=t=>{const u=Math.max(0,Math.min(t,v/.8));return v*u-.4*u*u;};
    const red=80+travel(Math.min(t,hold))*24,green=80+travel(t-12)*24;
    const kick=lab.mode==='moving',gy=kick?245-Math.min(Math.max(0,t-9.5),2.5)*23:245;
    const remaining=Math.max(0,12-t);
    let s=defs+txt(38,37,'Launch red; store its velocity.','law-label');
    s+=`<path d="M60 105H446M60 245H446" stroke="#d6e3db" stroke-dasharray="4 5"/>`;
    s+=txt(450,85,'RED','law-small','end')+txt(450,280,'GREEN','law-small','end');
    s+=sphere(red,105,'red')+sphere(green,gy,'green');
    if(lab.mode==='hold'&&t>=hold)s+=`<rect x="${red-21}" y="84" width="42" height="42" rx="8" fill="none" stroke="#91a59e" stroke-dasharray="3 3"/>`+txt(red,144,'held','law-small','middle');
    if(kick&&t>=9.5)s+=path(`M80 245V${gy}`,'#90b59f','3 4');
    if(t>=12)s+=`<path d="M${green+17} ${gy}h34" stroke="#79a08f" stroke-width="1.7" marker-end="url(#lab-arrow)"/>`;
    s+=`<rect x="202" y="155" width="178" height="49" rx="7" fill="${t<12?'#e5eee8':'#dcece0'}"/>`;
    s+=txt(291,176,t<12?'VELOCITY SCHEDULED':'VELOCITY COPIED','law-small','middle')+txt(291,193,t<12?`${remaining.toFixed(1)} counts remaining`:'green takes the stored velocity','','middle');
    s+=txt(470,320,`t = ${t.toFixed(1)} counts`,'law-small','end');
    setReadout(lab.mode==='hold'?'Holding red after launch does not cancel the scheduled velocity copy. Green still responds at 12 counts.':kick?'At the echo, green’s northward velocity is replaced by the stored eastward velocity—not added to it.':'A red launch schedules a velocity copy after 12 counts. Try stopping red, or giving green a different velocity before the echo.');
    return s;
  }
  function renderDrift(){
    const t=lab.t,remaining=Math.max(0,lab.until-t),active=remaining===0;
    let s=defs+'<rect x="26" y="30" width="448" height="279" rx="8" fill="url(#lab-grid)"/>';
    s+=txt(250,23,'NORTH ↑','law-small','middle');
    s+=`<path d="M250 278V58" stroke="#ccdcd1" stroke-dasharray="3 5"/>`;
    if(active){s+=`<path d="M250 ${lab.redY-18}v-34" stroke="#79a08f" stroke-width="2.2" marker-end="url(#lab-arrow)"/>`;}
    s+=sphere(250,lab.redY,'red')+sphere(397,250,'blue');
    if(lab.lastPush&&t-lab.pushAt<1)s+=`<circle cx="${lab.lastPush==='red'?250:397}" cy="${lab.lastPush==='red'?lab.redY:250}" r="${18+(t-lab.pushAt)*25}" fill="none" stroke="#8fae9c" opacity="${1-(t-lab.pushAt)}"/>`;
    s+=`<rect x="47" y="67" width="128" height="97" rx="9" fill="#f9fcfa" stroke="#d5e2d9"/>`;
    s+=txt(111,89,active?'EXTRA FORCE ON':'EXTRA FORCE PAUSED','law-small','middle');
    s+=txt(111,129,active?'↑':remaining.toFixed(1),'law-clock','middle');
    s+=txt(111,150,active?'northward drive':'counts until return','law-small','middle');
    s+=txt(450,295,`t = ${t.toFixed(1)} counts`,'law-small','end');
    setReadout(t<(lab.zeroUntil||0)?'Zero-impulse push: the timer is unchanged. Only a nonzero push or throw restarts the pause.':active?'Red’s extra northward force is active. Push either ball and watch the 10-count pause restart.':`A nonzero push pauses red’s extra force until t = ${lab.until.toFixed(1)}. Another push restarts the 10-count interval; a zero push does not.`);
    return s;
  }
  function renderLab(){canvas.innerHTML=({bounce:renderBounce,curve:renderCurve,echo:renderEcho,drift:renderDrift}[cases[selected].mechanism])();updateLabButton();}
  function setupLab(){
    stopLab();lab={t:0,playing:false,value:2,direction:0,mode:'free',swapped:false,until:10,redY:264,redV:0,lastPush:''};
    const mechanism=cases[selected].mechanism;
    if(mechanism==='echo')lab.value=3;
    let controls='';
    if(mechanism==='bounce')controls='<label for="lab-value"><span>Release height</span><input id="lab-value" type="range" min="1" max="3" step=".1" value="2"><output id="lab-value-output" for="lab-value">2.0 bricks</output></label>';
    if(mechanism==='curve')controls='<label for="lab-select"><span>Launch direction</span><select id="lab-select"><option value="0">East →</option><option value="90">North ↑</option><option value="180">West ←</option><option value="270">South ↓</option></select></label><label for="lab-value"><span>Launch speed</span><input id="lab-value" type="range" min="1" max="4" step=".5" value="2"><output id="lab-value-output" for="lab-value">2.0</output></label>';
    if(mechanism==='echo')controls='<label for="lab-select"><span>Test setup</span><select id="lab-select"><option value="free">Let red move freely</option><option value="hold">Hold red just after launch</option><option value="moving">Launch green north before the echo</option></select></label>';
    controls+='<button id="lab-play" class="lab-primary">▶ Try the law</button>';
    if(mechanism==='bounce')controls+='<button id="lab-swap">Swap ball identities</button>';
    if(mechanism==='drift')controls+='<button data-push="red">Push red</button><button data-push="blue">Push blue</button><button id="lab-zero">Zero push</button>';
    controls+='<button id="lab-reset" aria-label="Reset law illustration">↺ Reset</button>';
    $('#lab-controls').innerHTML=controls;
    $('#illustration-note').textContent={bounce:'Idealized vertical drops using the published restitution ratios; h after rebound = e²h. This is a law illustration, not a recorded run.',curve:'Illustration of the horizontal side-force contribution, with ordinary friction omitted. The experimental trajectories are shown alongside.',echo:'Illustration of the 12-count velocity transfer. Ordinary slowing is simplified; the clock runs 2.5× faster for viewing.',drift:'Illustration of the extra northward force and its pause; ordinary motion is simplified. The clock runs 2.5× faster for viewing.'}[mechanism];
    canvas.setAttribute('aria-label',cases[selected].name+' Interactive, idealized law illustration.');
    $('#lab-play').addEventListener('click',()=>lab.playing?stopLab():startLab());
    $('#lab-reset').addEventListener('click',resetLab);
    $('#lab-value')?.addEventListener('input',e=>{lab.value=Number(e.target.value);$('#lab-value-output').textContent=lab.value.toFixed(1)+(mechanism==='bounce'?' bricks':'');resetLab();});
    $('#lab-select')?.addEventListener('change',e=>{if(mechanism==='curve')lab.direction=Number(e.target.value);else lab.mode=e.target.value;resetLab();startLab();});
    $('#lab-swap')?.addEventListener('click',()=>{lab.swapped=!lab.swapped;resetLab();startLab();});
    $$('[data-push]').forEach(b=>b.addEventListener('click',()=>{lab.until=lab.t+10;lab.lastPush=b.dataset.push;lab.pushAt=lab.t;renderLab();if(!lab.playing){lab.playing=true;lastTick=performance.now();labAnimation=requestAnimationFrame(labTick);}}));
    $('#lab-zero')?.addEventListener('click',()=>{lab.zeroUntil=lab.t+5;renderLab();});
    renderLab();
  }
  new IntersectionObserver(entries=>{
    labVisible=entries[0].isIntersecting;
    if(!labVisible)stopLab();
    else if(!autoPreviewed&&!reduced){autoPreviewed=true;startLab();}
  },{threshold:.2}).observe(canvas);

  // The framework diagram advances through meaningful stages, and each stage
  // can be selected directly. Pause outside the viewport or when requested.
  const steps=$$('.cycle-step'),arrows=$$('.cycle-arrow');
  const descriptions=[
    'The designer specifies objects and altered laws. These laws are hidden from the explorer.',
    'The explorer chooses a question, acts on the world and builds apparatus when needed. Designs are reviewed before installation.',
    'The judge checks the explanation against the law and the recorded experiments. Discovery requires both correctness and support.',
    'Unresolved questions and corrected errors guide generation, refinement and composition. Accepted worlds start the next cycle.'
  ];
  let phase=0,cycleEnabled=!reduced,cycleVisible=false,cycleInterval;
  function setPhase(i){
    phase=i;$('.cycle').classList.add('is-animated');
    steps.forEach((s,j)=>{s.classList.toggle('is-active',i===j);s.setAttribute('aria-pressed',String(i===j));});
    arrows.forEach((a,j)=>a.classList.toggle('is-flowing',j===i&&cycleEnabled&&cycleVisible));
    $('#cycle-stage').textContent=steps[i].querySelector('.cycle-number').textContent;
    $('#cycle-explanation').textContent=descriptions[i];
  }
  function updateCycle(){
    clearInterval(cycleInterval);
    if(cycleEnabled&&cycleVisible)cycleInterval=setInterval(()=>setPhase((phase+1)%4),3000);
    $('#cycle-play').textContent=cycleEnabled?'II':'▶';$('#cycle-play').setAttribute('aria-label',cycleEnabled?'Pause framework animation':'Play framework animation');setPhase(phase);
  }
  steps.forEach((s,i)=>{
    s.setAttribute('role','button');s.tabIndex=0;s.setAttribute('aria-label',s.querySelector('h3').textContent);
    const choose=()=>{cycleEnabled=false;setPhase(i);updateCycle();};
    s.addEventListener('click',choose);s.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});
  });
  $('#cycle-play').addEventListener('click',()=>{cycleEnabled=!cycleEnabled;updateCycle();});
  new IntersectionObserver(e=>{cycleVisible=e[0].isIntersecting;updateCycle();},{threshold:.2}).observe($('.cycle'));
  document.addEventListener('visibilitychange',()=>{if(document.hidden){pauseVideo();stopLab();clearInterval(cycleInterval);}else updateCycle();});
  chooseDiscovery($('#success-tab-07'));setPhase(0);
})();
