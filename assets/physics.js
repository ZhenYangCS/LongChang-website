/* Native MuJoCo demonstrations; playback never modifies the source physics. */
(() => {
  'use strict';
  const demos=window.PHYSICS_DEMOS || [];
  const $=selector=>document.querySelector(selector);
  if(!demos.length)return;
  $('[data-atlas-view="physics"]').hidden=false;
  const video=$('#physics-video'),reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let demo=null,shown=false,visible=false,touring=false,changingByTour=false,wantsPlay=false,previewed=false;
  let frame=0;
  video.controls=false;
  const speed=object=>Math.hypot(...object.velocity);
  const color=object=>['red','green','blue'][object.color.slice(0,3).indexOf(Math.max(...object.color.slice(0,3)))];
  function tourLabel(){
    if(!shown)return;
    $('#atlas-tour').setAttribute('aria-pressed',String(touring));
    $('#atlas-tour').textContent=touring?'II Pause scene tour':'▶ Play all 15 scenes';
  }
  function updateCopy(t){
    if(!demo || !shown)return;
    $('#atlas-trigger-text').textContent=demo.setup;
    if(demo.oracle && demo.time_map){
      updateOracle(t);
      return;
    }
    $('#atlas-model-note').textContent='Scripted demonstration in the original MuJoCo scene. Preparation positions and interventions are documented. Recorded model explorations appear below.';
    const samples=demo.timeline;
    let sample=samples[0];
    for(const next of samples){if(next.time>t)break;sample=next;}
    $('#physics-sample-label').textContent=`MEASURED AT t = ${sample.time.toFixed(2)} COUNTS`;
    const objects=Object.values(sample.objects),id=Number(demo.id);
    const entries=demo.contacts.filter(event=>event.kind==='contact_start'&&event.time<=t);
    const exits=demo.contacts.filter(event=>event.kind==='contact_end'&&event.time<=t);
    let caption='',values=[];
    if(id===1){
      caption='The decorative tile adds no physical effect. Both balls follow the same vertical motion under matched release conditions.';
      values=[['Above gray tile',objects[0].position[2].toFixed(3)+' bricks'],['Above ordinary floor',objects[1].position[2].toFixed(3)+' bricks']];
    }else if(id===2){
      caption='The red pair converges under the attraction force. The blue pair remains at rest; it neither generates nor experiences that force.';
      values=[['Red pair separation',Math.abs(objects[0].position[0]-objects[1].position[0]).toFixed(3)+' bricks'],['Blue pair separation',Math.abs(objects[2].position[0]-objects[3].position[0]).toFixed(3)+' bricks']];
    }else if(id===3){
      caption=t<.6?'The balls begin at equal heights. Blue has four times the mass and half the downward acceleration.':'Red reaches the floor first. Ordinary contact remains active as the heavier blue ball continues falling.';
      values=[['Red · mass 1 · height',objects[0].position[2].toFixed(3)+' bricks'],['Blue · mass 4 · height',objects[1].position[2].toFixed(3)+' bricks']];
    }else if(id===4){
      caption=t<1.5?'Watch the gravity change before the first launch.':t<4.5?'Red receives an upward impulse of 4 at the strongest-gravity phase.':'Blue receives the same upward impulse at the weakest-gravity phase and rises higher.';
      values=[['Current gravity',(-sample.gravity[2]/9.81).toFixed(3)+' g₀'],['Launch phases','1.5 / 4.5 counts']];
    }else if(id===5){
      caption='Red’s stronger launch activates extra braking above speed 2.5. Blue starts below the threshold. Both also experience ordinary friction.';
      values=[['Red · impulse 8',speed(objects[0]).toFixed(3)+' bricks/count'],['Blue · impulse 2',speed(objects[1]).toFixed(3)+' bricks/count']];
    }else if(id===6){
      caption='The eastward launch curves south: the added horizontal force stays to the right of the instantaneous velocity. The trail follows sampled physical positions.';
      values=[['Eastward velocity',objects[0].velocity[0].toFixed(3)],['Northward velocity',objects[0].velocity[1].toFixed(3)]];
    }else if(id===7){
      caption=t<.52?'Both gray balls fall from the same height.':'The ball on red makes a substantial rebound; the ball on blue settles quickly. Neither the balls nor the surface parameters are changed for rendering.';
      values=[['Red tile · ball height',objects[0].position[2].toFixed(3)+' bricks'],['Blue tile · ball height',objects[1].position[2].toFixed(3)+' bricks']];
    }else if(id===8){
      caption='Five times the impulse produces much less than five times the speed. The original momentum–velocity rule keeps both launch speeds below 2.2.';
      values=[['Red · impulse 2',speed(objects[0]).toFixed(3)+' bricks/count'],['Blue · impulse 10',speed(objects[1]).toFixed(3)+' bricks/count']];
    }else if(id===9){
      const x=objects[0].position[0];
      caption=x<.5?'Red approaches the entry boundary.':x<3.5?'Entering the footprint multiplies velocity by 0.4. Friction continues to reduce motion inside.':'Leaving multiplies the remaining velocity by 2.5. It does not restore losses accumulated inside the region.';
      values=[['Horizontal position',x.toFixed(3)+' bricks'],['Eastward velocity',objects[0].velocity[0].toFixed(3)+' bricks/count']];
    }else if(id===10){
      caption=objects[0].position[0]<2?'Red moves east without an applied launch; the scene supplies the low-speed seed inside the yellow footprint. Blue is at rest outside.':'Red has left the active region. The added driving ends and ordinary friction slows it.';
      values=[['Red · inside then outside',speed(objects[0]).toFixed(3)+' bricks/count'],['Blue · outside',speed(objects[1]).toFixed(3)+' bricks/count']];
    }else if(id===11){
      caption=exits.length?'The red–blue contact has ended, triggering the ×1.8 update to their remaining velocities. Green is not affected.':entries.length?'The balls are in contact. The added boost is triggered at separation, not at initial contact.':'Red approaches blue. Green is an uninvolved control.';
      values=[['Ball–ball contact',exits.length?'Ended':entries.length?'Active':'Not yet'],['Green speed',speed(objects[2]).toFixed(3)+' bricks/count']];
    }else if(id===12){
      caption=entries.length===0?'Track object identities A and B as contact begins.':entries.length===1?'The first contact swaps colors. The same objects are separated and repositioned before the next trial.':'The second distinct contact swaps the colors back. Body identities remain unchanged throughout.';
      values=[['Object A',color(objects[0])],['Object B',color(objects[1])]];
    }else if(id===13){
      caption=entries.length<3?'Separate contacts are counted. Between trials the balls are repositioned without resetting their history.':'The third distinct contact sets both upward velocities to 4. The resulting jumps and landings are simulated with ordinary gravity and contact.';
      values=[['Qualifying contacts',String(entries.length)+' / 3'],['Red · height',objects[0].position[2].toFixed(3)+' bricks']];
    }else if(id===14){
      caption=t<.2?'Red is launched; its post-command velocity is scheduled for transfer.':t<12?'Red is held stationary. Holding it does not cancel the scheduled event, and green continues waiting.':'At count 12, green receives the stored velocity even though red has been held almost the entire time.';
      values=[['Scheduled transfer',t<12?(12-t).toFixed(2)+' counts left':'Applied at count 12'],['Green speed',speed(objects[1]).toFixed(3)+' bricks/count']];
    }else{
      caption=t<2?'Red’s extra northward force is initially active.':t<12?'The nonzero push on blue has paused red’s extra force. Existing motion still responds to ordinary friction.':'Ten counts have passed since the push on blue. Red’s extra northward force returns.';
      values=[['Extra force',t<2||t>=12?'Active':(12-t).toFixed(2)+' counts paused'],['Red northward velocity',objects[0].velocity[1].toFixed(3)+' bricks/count']];
    }
    $('#atlas-observation').textContent=caption;
    $('#physics-values').innerHTML=values.map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
  }
  function updateOracle(t){
    const fps=demo.fps||12;
    const index=Math.min(demo.timeline.length-1,Math.floor(video.currentTime*fps));
    const sample=demo.timeline[index],description=sample.annotation;
    $('#atlas-model-note').textContent='New controlled experiment. Scene laws are preserved; the matched reference disables only the altered program. Glass enclosure and lighting follow the paper’s Figure 1.';
    $('#physics-sample-label').textContent=`MEASURED AT t = ${sample.time.toFixed(2)} COUNTS`;
    $('#atlas-observation').textContent=description.heading+' '+(demo.plot.labels[1].includes('reference')?'The gray trace uses the same preparation and actions with only the altered program disabled.':'The two colored traces compare the matched objects shown in this experiment.');
    $('#physics-values').innerHTML=description.values.map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
    $('#oracle-live-state').textContent=description.heading;
    $('#oracle-overlay').dataset.active=String(description.active);
    $('#oracle-status').textContent='Revealed in the demonstration';
    $('#oracle-chapters').querySelectorAll('button').forEach((b,i)=>{
      const next=demo.chapters[i+1]?.time??Infinity;
      b.setAttribute('aria-pressed',String(video.currentTime>=demo.chapters[i].time&&video.currentTime<next));
    });
    const plot=demo.plot,width=640,height=165,left=36,right=622,top=20,bottom=138;
    const minimum=Math.min(0,...plot.series.flat()),maximum=Math.max(.1,...plot.series.flat());
    const pad=(maximum-minimum)*.1,low=minimum-pad,high=maximum+pad;
    const xy=(time,value)=>[left+(right-left)*time/demo.simulation_duration,bottom-(bottom-top)*(value-low)/(high-low)];
    let svg='';
    for(let i=0;i<3;i++){
      const value=low+(high-low)*i/2,y=xy(0,value)[1];
      svg+=`<path d="M${left} ${y}H${right}" stroke="#dce7dc"/><text x="1" y="${y+3}" fill="#92a389" font-size="8">${value.toFixed(1)}</text>`;
    }
    plot.series.forEach((values,i)=>{
      const points=plot.times.map((time,j)=>xy(time,values[j]));
      if(demo.id==='12'){
        for(let j=0;j<points.length-1;j++)svg+=`<rect x="${points[j][0]}" y="${40+i*45}" width="${Math.max(1,points[j+1][0]-points[j][0])}" height="27" fill="${values[j]>.5?'#cc8972':'#799fc3'}"/>`;
        svg+=`<text x="${left+6}" y="${58+i*45}" fill="white" font-size="10">${'AB'[i]}</text>`;
        return;
      }
      const all=points.map((p,j)=>(j?'L':'M')+p.map(v=>v.toFixed(2)).join(' ')).join('');
      const past=points.filter((_,j)=>plot.times[j]<=t+.00001);
      const d=past.map((p,j)=>(j?'L':'M')+p.map(v=>v.toFixed(2)).join(' ')).join('');
      svg+=`<path d="${all}" fill="none" stroke="#d4dfd4" stroke-width="1"/><path d="${d}" fill="none" stroke="${plot.colors[i]}" stroke-width="2.3" ${plot.labels[i].includes('reference')?'stroke-dasharray="5 4"':''}/>`;
    });
    const cursor=xy(t,0)[0];
    svg+=`<path d="M${cursor} ${top}V${bottom}" stroke="#789b70"/><text x="${left}" y="160" fill="#91a287" font-size="8">0</text><text x="${right}" y="160" text-anchor="end" fill="#91a287" font-size="8">${demo.simulation_duration} counts</text>`;
    $('#oracle-chart').innerHTML=svg;
  }
  function progress(){
    if(!demo)return;
    const fraction=Number.isFinite(video.duration)&&video.duration>0?video.currentTime/video.duration:0;
    const fps=demo.fps||24,totalFrames=Math.round(demo.duration*fps);
    const currentFrame=Math.min(totalFrames-1,Math.floor(video.currentTime*fps));
    const t=demo.time_map?demo.timeline[Math.min(currentFrame,demo.timeline.length-1)].time:Math.round(currentFrame/(totalFrames-1)*demo.simulation_duration/.02)*.02;
    $('#physics-progress').value=Math.round(fraction*1000);
    $('#physics-clock').textContent=t.toFixed(2)+' counts';
    $('#physics-play').textContent=video.paused?'▶':'II';
    $('#physics-play').setAttribute('aria-label',`${video.paused?'Play':'Pause'} physics demonstration`);
    updateCopy(t);
  }
  function pause(){wantsPlay=false;video.pause();cancelAnimationFrame(frame);progress();}
  function play(){
    wantsPlay=true;
    if(!shown||!visible||document.hidden||$('#motion-dialog').open)return;
    if(video.ended)video.currentTime=0;
    if(video.readyState<2)return;
    video.play().then(progress).catch(()=>{wantsPlay=false;progress();});
  }
  function load(id,autoplay=false){
    const next=demos.find(d=>d.id===id);if(!next)return;
    if(demo?.id!==id){
      video.pause();demo=next;
      const revision=demo.video_sha256?'?v='+demo.video_sha256.slice(0,12):'';
      video.poster=demo.poster+revision;video.src=demo.video+revision;video.load();
      video.setAttribute('aria-label',`Scene ${demo.id}: ${demo.name}. Scripted demonstration of the original physical laws.`);
      const enhanced=Boolean(demo.oracle&&demo.time_map);
      $('.physics-video-frame').classList.toggle('is-oracle',enhanced);
      $('#oracle-overlay').hidden=!enhanced;
      $('#oracle-chapters').hidden=!enhanced;
      $('#oracle-chart-wrap').hidden=!enhanced;
      if(enhanced){
        $('#scene-law').open=true;
        $('#oracle-chapters').innerHTML=demo.chapters.map((chapter,i)=>`<button data-oracle-chapter="${i}" aria-pressed="false"><small>0${i+1}</small>${chapter.label}</button>`).join('');
        $('#oracle-chapters').querySelectorAll('button').forEach((button,i)=>button.addEventListener('click',()=>{touring=false;video.loop=true;pause();video.currentTime=demo.chapters[i].time;progress();tourLabel();}));
        $('#oracle-chart-legend').textContent=demo.plot.labels.join(' / ');
      }
      $('#physics-download').href=demo.video;$('#physics-record').href=demo.record;
      $('#oracle-signal-download').hidden=!demo.signal_figure;
      if(demo.signal_figure)$('#oracle-signal-download').href=demo.signal_figure;
      $('#physics-error').hidden=true;
    }
    video.loop=!touring&&Boolean(demo.time_map);
    wantsPlay=autoplay || touring;
    progress();tourLabel();if(wantsPlay)play();
  }
  $('#physics-play').addEventListener('click',()=>{if(video.paused)play();else{touring=false;pause();tourLabel();}});
  $('#physics-reset').addEventListener('click',()=>{touring=false;pause();video.currentTime=0;progress();tourLabel();});
  $('#physics-progress').addEventListener('input',event=>{
    if(!Number.isFinite(video.duration))return;
    const destination=Number(event.target.value)/1000*video.duration;
    touring=false;video.loop=Boolean(demo.time_map);
    pause();video.currentTime=destination;progress();tourLabel();
  });
  $('#physics-fullscreen').addEventListener('click',async()=>{
    try {if(document.fullscreenElement)await document.exitFullscreen();else await $('.physics-video-frame').requestFullscreen();}
    catch(_){video.controls=true;}
  });
  document.addEventListener('fullscreenchange',()=>{video.controls=document.fullscreenElement===$('.physics-video-frame');});
  ['timeupdate','seeked','loadedmetadata','play','pause'].forEach(event=>video.addEventListener(event,progress));
  video.addEventListener('loadeddata',()=>{progress();if(wantsPlay)play();});
  video.addEventListener('error',()=>{$('#physics-error').hidden=false;pause();});
  video.addEventListener('ended',()=>{
    if(touring){changingByTour=true;window.showWorld(String(Number(demo.id)%15+1).padStart(2,'0'));changingByTour=false;play();}
    else progress();
  });
  document.addEventListener('longchang:atlas-view',event=>{
    shown=event.detail.view==='physics';
    if(shown)load(event.detail.id,touring);else{touring=false;pause();}
  });
  document.addEventListener('longchang:scene',event=>{
    if(!changingByTour)touring=false;
    load(event.detail.id,!reduced.matches&&shown);tourLabel();
  });
  document.querySelectorAll('#scene-picker button').forEach(button=>button.addEventListener('click',()=>{touring=false;tourLabel();}));
  new IntersectionObserver(entries=>{
    visible=entries[0].isIntersecting;
    if(visible&&!previewed&&!reduced.matches){previewed=true;wantsPlay=true;}
    if(!visible)video.pause();else if(wantsPlay)play();
  },{threshold:.1}).observe($('#atlas-physics-view'));
  document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();else if(wantsPlay)play();});
  document.addEventListener('longchang:presentation-open',()=>video.pause());
  reduced.addEventListener('change',event=>{if(event.matches){touring=false;pause();tourLabel();}});
  window.LongChangPhysics=Object.freeze({toggleTour(){
    touring=!touring;
    video.loop=!touring&&Boolean(demo?.time_map);
    if(touring){changingByTour=true;window.showWorld('01');changingByTour=false;video.currentTime=0;play();}
    else pause();
    tourLabel();
  }});
  shown=$('.atlas-detail').dataset.view==='physics';
  demos.forEach(d=>{if(d.studio_poster){const thumbnail=$(`#scene-tab-${d.id} img`);if(thumbnail)thumbnail.src=d.studio_poster;}});
  load(window.LongChangAtlas.currentScene(),false);
})();
