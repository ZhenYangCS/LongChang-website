


(() => {
  'use strict';
  const root = document.getElementById('framework-flow');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const $$ = selector => [...root.querySelectorAll(selector)];
  const map = $('#fw-map'), svg = $('#fw-connections');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const stacked = matchMedia('(max-width: 900px)');
  const nodeElements = new Map($$('[data-node]').map(node => [node.dataset.node, node]));
  const phases = [
    {kicker:'01 / CONSTRUCT', title:'Build the world.', description:'Define altered physics, then test and review the scene.', input:'Scene design', output:'Validated world + hidden law', nodes:['designer','scenes'], edges:['design']},
    {kicker:'02 / EXPLORE', title:'Explore freely.', description:'Choose questions and experiments, without tasks or hints.', input:'Observations', output:'Questions + experiments', nodes:['scenes','world','explorer','traces'], edges:['enter','observe','act','record']},
    {kicker:'03 / BUILD', title:'Build an instrument.', description:'Review apparatus designs; install tools or return feedback.', input:'Apparatus design', output:'Instrument or feedback', nodes:['explorer','world','tools','traces'], edges:['act','build','install','record']},
    {kicker:'04 / EVALUATE', title:'Check the discovery.', description:'Check claims against hidden laws and recorded evidence.', input:'Report + law + traces', output:'Correctness + support', nodes:['report','judge','assessment','traces','scenes'], edges:['report','claims','law','evidence','assess']},
    {kicker:'05 / EVOLVE', title:'Shape the next world.', description:'Generate, refine or combine scenes using exploration evidence.', input:'Scenes + evidence', output:'New scene designs', nodes:['traces','evolution','designer'], edges:['feedback','evolve']}
  ];
  const details = {
    designer:{phase:0,title:'Design and validate.',description:'Define objects and laws; revise failed tests or reviews.',input:'Design + feedback',output:'Validated scene'},
    scenes:{phase:0,title:'Keep the law hidden.',description:'The explorer receives the world; the judge receives its law.',input:'Validated scene',output:'World → explorer; law → judge'},
    world:{phase:1,title:'Observe the response.',description:'Actions return positions, motion and instrument readings.',input:'Physical actions',output:'Text observations'},
    explorer:{phase:1,title:'Choose what to test.',description:'Choose questions, test explanations, and design tools.',input:'Observations + notes',output:'Hypotheses + experiments'},
    tools:{phase:2,title:'Review and install.',description:'Review apparatus designs; install accepted tools or return feedback.',input:'Apparatus design',output:'Instrument or feedback'},
    traces:{phase:4,title:'Retain every turn.',description:'Keep all observations, actions and feedback for evaluation and evolution.',input:'All exploration turns',output:'Evidence'},
    report:{phase:3,title:'Support every claim.',description:'Cite recorded turns and preserve uncertainty.',input:'Exploration record',output:'Claims + citations'},
    judge:{phase:3,title:'Evaluate independently.',description:'The judge compares each claim with the hidden law and full record.',input:'Report + law + traces',output:'Correctness + support'},
    assessment:{phase:3,title:'Require both checks.',description:'Both correctness and evidence support must pass.',input:'C + S',output:'Discovery if both pass'},
    evolution:{phase:4,title:'Create the next challenge.',description:'Generate, refine or combine scenes using exploration evidence.',input:'Laws + evidence',output:'New scene designs'}
  };
  const edges = [
    {id:'design',from:'designer',to:'scenes',kind:'construction',label:'Compile & review'},
    {id:'enter',from:'scenes',to:'world',kind:'construction'},
    {id:'observe',from:'world',to:'explorer',label:'Observations'},
    {id:'act',from:'explorer',to:'world',label:'Actions'},
    {id:'build',from:'explorer',to:'tools'},
    {id:'install',from:'tools',to:'world',label:'Install'},
    {id:'record',from:'explorer',to:'traces',label:'All turns'},
    {id:'report',from:'explorer',to:'report',kind:'evaluation'},
    {id:'claims',from:'report',to:'judge',kind:'evaluation',label:'Claims'},
    {id:'law',from:'scenes',to:'judge',kind:'law',label:'Hidden law · evaluation only'},
    {id:'evidence',from:'traces',to:'judge',kind:'evaluation'},
    {id:'assess',from:'judge',to:'assessment',kind:'evaluation',label:'C + S'},
    {id:'feedback',from:'traces',to:'evolution',kind:'feedback',label:'Exploration evidence'},
    {id:'evolve',from:'evolution',to:'designer',kind:'feedback'}
  ];
  const colors = {workflow:'#6c9187',construction:'#6d8ead',evaluation:'#927ba3',law:'#b08d4e',feedback:'#6d8ead'};
  const ns = 'http://www.w3.org/2000/svg';
  function element(tag, attrs = {}, text) {
    const node = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key,value]) => node.setAttribute(key,value));
    if (text) node.textContent = text;
    return node;
  }
  const defs = element('defs');
  Object.entries(colors).forEach(([kind,color]) => {
    const marker = element('marker',{id:`fw-arrow-${kind}`,viewBox:'0 0 8 8',refX:'7',refY:'4',markerWidth:'6',markerHeight:'6',orient:'auto',markerUnits:'userSpaceOnUse'});
    marker.append(element('path',{d:'M1 1 7 4 1 7',fill:'none',stroke:color,'stroke-width':'1.3','stroke-linecap':'round','stroke-linejoin':'round'}));
    defs.append(marker);
  });
  svg.append(defs);
  edges.forEach(edge => {
    const kind = edge.kind || 'workflow';
    edge.group = element('g',{'class':'fw-edge','data-edge':edge.id,'data-kind':kind,'data-from':edge.from,'data-to':edge.to});
    edge.path = element('path',{'class':'fw-track','marker-end':`url(#fw-arrow-${kind})`});
    edge.halo = element('circle',{'class':'fw-packet-halo',r:'5.5'});
    edge.dot = element('circle',{'class':'fw-packet',r:'2.8'});
    edge.group.append(edge.path,edge.halo,edge.dot);
    if (edge.label) {
      edge.labelGroup = element('g',{'class':'fw-edge-label'});
      edge.labelText = element('text',{},edge.label);
      edge.labelGroup.append(edge.labelText);
      edge.group.append(edge.labelGroup);
    }
    svg.append(edge.group);
  });



  function rounded(points, radius = 10) {
    let d = `M${points[0].join(',')}`;
    for (let i = 1; i < points.length - 1; i++) {
      const previous = points[i-1], corner = points[i], next = points[i+1];
      const before = Math.hypot(corner[0]-previous[0],corner[1]-previous[1]);
      const after = Math.hypot(next[0]-corner[0],next[1]-corner[1]);
      if (!before || !after) continue;
      const r = Math.min(radius,before/2,after/2);
      const a = corner.map((v,j) => v+(previous[j]-v)*r/before);
      const b = corner.map((v,j) => v+(next[j]-v)*r/after);
      d += `L${a.join(',')}Q${corner.join(',')} ${b.join(',')}`;
    }
    return d+`L${points.at(-1).join(',')}`;
  }
  function placeLabel(edge, anchor) {
    edge.labelGroup.style.display = anchor ? '' : 'none';
    if (!anchor) return;


    edge.labelText.textContent = edge.label;
    if (anchor.lines) {
      edge.labelText.replaceChildren(...anchor.lines.map((line,index) => element('tspan',{x:0,dy:index ? 13 : 0},line)));
    } else if (anchor.maxWidth && edge.labelText.getComputedTextLength() > anchor.maxWidth) {
      edge.labelText.replaceChildren();
      edge.label.split(' ').forEach((word,index) => {
        edge.labelText.append(element('tspan',{x:0,dy:index ? 12 : 0},word));
      });
    }
    const box = edge.labelText.getBBox(), gap = 11;
    const x = anchor.side==='right' ? anchor.x+gap-box.x : anchor.side==='left' ? anchor.x-gap-box.x-box.width : anchor.x-box.x-box.width/2;
    const y = anchor.side ? anchor.y-box.y-box.height/2 : anchor.y-gap-box.y-box.height;
    edge.labelGroup.setAttribute('transform',`translate(${x},${y})`);
  }
  let geometryReady = false;
  function layout() {
    const bounds = map.getBoundingClientRect();
    if (!bounds.width) return;
    svg.setAttribute('viewBox',`0 0 ${bounds.width} ${bounds.height}`);
    const boxes = Object.fromEntries([...nodeElements].map(([id,node]) => {
      const r = node.getBoundingClientRect();
      return [id,{l:r.left-bounds.left,r:r.right-bounds.left,t:r.top-bounds.top,b:r.bottom-bounds.top,x:r.left-bounds.left+r.width/2,y:r.top-bounds.top+r.height/2}];
    }));
    const b = boxes, middle = (b.world.r+b.explorer.l)/2;
    const observeY = b.world.t-24, actY = b.world.b+24;
    const routes = {
      design:{points:[[b.designer.x,b.designer.b],[b.scenes.x,b.scenes.t]],label:{x:b.designer.x,y:(b.designer.b+b.scenes.t)/2,side:'right'}},
      observe:{points:[[b.world.x,b.world.t],[b.world.x,observeY],[b.explorer.x,observeY],[b.explorer.x,b.explorer.t]],label:{x:middle,y:observeY}},
      act:{points:[[b.explorer.x,b.explorer.b],[b.explorer.x,actY],[b.world.x,actY],[b.world.x,b.world.b]],label:{x:middle,y:actY}},
      build:{points:[[middle,actY],[middle,b.tools.t]]},
      install:{points:[[b.tools.l,b.tools.y],[b.world.l+16,b.tools.y],[b.world.l+16,b.world.b]],label:{x:b.world.l+16,y:(actY+b.tools.t)/2,side:'right'}},
      record:{points:[[b.explorer.r-10,b.explorer.b],[b.explorer.r-10,b.traces.t-12],[b.traces.x,b.traces.t-12],[b.traces.x,b.traces.t]],label:{x:b.explorer.r-10,y:(actY+b.tools.t)/2,side:'left'}},
      claims:{points:[[b.report.x,b.report.b],[b.judge.x,b.judge.t]],label:{x:b.report.x,y:(b.report.b+b.judge.t)/2,side:'left'}},
      assess:{points:[[b.judge.x,b.judge.b],[b.assessment.x,b.assessment.t]],label:{x:b.judge.x,y:(b.judge.b+b.assessment.t)/2,side:'right'}}
    };
    if (!stacked.matches) {
      const entryX = (b.scenes.r+b.world.l)/2;
      const explorationRight = $('.fw-exploration').getBoundingClientRect().right-bounds.left;
      const evaluationLeft = $('.fw-evaluation').getBoundingClientRect().left-bounds.left;
      const evidenceX = (explorationRight+evaluationLeft)/2;
      const lawX = bounds.width-11, lawY = b.designer.t-26;
      const returnX = 12;
      Object.assign(routes,{
        enter:{points:[[b.scenes.r,b.scenes.y],[entryX,b.scenes.y],[entryX,b.world.y],[b.world.l,b.world.y]]},
        report:{points:[[b.explorer.r,b.explorer.y],[b.report.l,b.report.y]]},
        law:{points:[[b.scenes.r,b.scenes.t+18],[entryX-10,b.scenes.t+18],[entryX-10,lawY],[lawX,lawY],[lawX,b.judge.y],[b.judge.r,b.judge.y]],label:{x:lawX,y:b.judge.t-22,side:'left',lines:['Hidden law','Evaluation only']}},
        evidence:{points:[[b.traces.r,b.traces.y],[evidenceX,b.traces.y],[evidenceX,b.judge.y],[b.judge.l,b.judge.y]]},
        feedback:{points:[[b.traces.l,b.traces.y],[b.evolution.r,b.evolution.y]],label:{x:(b.traces.l+b.evolution.r)/2,y:b.traces.y,maxWidth:b.traces.l-b.evolution.r-24}},
        evolve:{points:[[b.evolution.l,b.evolution.y],[returnX,b.evolution.y],[returnX,b.designer.y],[b.designer.l,b.designer.y]]}
      });
    } else {
      const right = bounds.width-8, left = 8;
      const enterY = b.world.t-56, enterX = b.world.l+(b.world.r-b.world.l)*.26;
      const reportY = b.report.t-15;
      Object.assign(routes,{
        enter:{points:[[b.scenes.r,b.scenes.y],[right-9,b.scenes.y],[right-9,enterY],[enterX,enterY],[enterX,b.world.t]]},
        report:{points:[[b.explorer.r,b.explorer.y],[right-9,b.explorer.y],[right-9,reportY],[b.report.x,reportY],[b.report.x,b.report.t]]},
        law:{points:[[b.scenes.r,b.scenes.t+18],[right,b.scenes.t+18],[right,b.judge.y],[b.judge.r,b.judge.y]],label:{x:right,y:b.judge.t-22,side:'left',lines:['Hidden law','Evaluation only']}},
        evidence:{points:[[b.traces.x,b.traces.b],[b.traces.x,b.traces.b+12],[left+16,b.traces.b+12],[left+16,b.judge.y],[b.judge.l,b.judge.y]]},
        feedback:{points:[[b.traces.l,b.traces.y],[left,b.traces.y],[left,b.evolution.y],[b.evolution.l,b.evolution.y]]},
        evolve:{points:[[b.evolution.x,b.evolution.t],[b.evolution.x,b.evolution.t-16],[left+8,b.evolution.t-16],[left+8,b.designer.y],[b.designer.l,b.designer.y]]}
      });
    }
    edges.forEach(edge => {
      const route = routes[edge.id];
      edge.path.setAttribute('d',rounded(route.points));
      edge.length = edge.path.getTotalLength();
      if (edge.labelGroup) placeLabel(edge,route.label);
    });
    geometryReady = true;
    drawPackets();
  }

  let phase = 0, selectedNode = null, elapsed = 0, phaseElapsed = 0, pinned = false, lastTime = null, frame = null;
  let enabled = !reducedMotion.matches, visible = false, modalOpen = false;
  const playbackRate = 1.6;
  const phaseDuration = 6400;
  function displayDetail(detail, userInitiated) {
    $('#fw-detail').setAttribute('aria-live',userInitiated ? 'polite' : 'off');
    $('#fw-detail-title').textContent = detail.title;
    $('#fw-detail-description').textContent = detail.description;
    $('#fw-detail-input').textContent = detail.input;
    $('#fw-detail-output').textContent = detail.output;
  }
  function renderSelection(userInitiated = false) {
    const current = phases[phase];
    const activeEdges = selectedNode ? edges.filter(edge => edge.from===selectedNode || edge.to===selectedNode).map(edge => edge.id) : current.edges;
    const activeNodes = selectedNode ? new Set([selectedNode,...edges.filter(edge => activeEdges.includes(edge.id)).flatMap(edge => [edge.from,edge.to])]) : new Set(current.nodes);
    nodeElements.forEach((node,id) => {
      node.classList.toggle('is-active',activeNodes.has(id));
      node.setAttribute('aria-pressed',String(id===selectedNode));
    });
    edges.forEach(edge => {
      edge.active = activeEdges.includes(edge.id);
      edge.group.classList.toggle('is-active',edge.active);
    });
    $$('[data-fw-stage]').forEach(button => button.setAttribute('aria-pressed',String(Number(button.dataset.fwStage)===phase)));
    root.dataset.phase = String(phase);
    root.dataset.selection = selectedNode || '';
    root.dataset.mode = pinned ? 'focus' : 'cycle';
    displayDetail(selectedNode ? details[selectedNode] : current,userInitiated);
    drawPackets();
  }
  function drawPackets() {
    if (!geometryReady) return;
    edges.forEach((edge,index) => {
      if (!edge.active) return;

      const duration = Math.max(850,edge.length*2.25);
      const progress = (elapsed/duration+index*.13)%1;
      const point = edge.path.getPointAtLength(progress*edge.length);
      [edge.dot,edge.halo].forEach(node => {
        node.setAttribute('cx',point.x.toFixed(2));
        node.setAttribute('cy',point.y.toFixed(2));
      });
    });
  }
  function tick(time) {
    if (lastTime !== null) {
      const delta = Math.min(time-lastTime,100)*playbackRate;
      elapsed += delta;
      if (!pinned) phaseElapsed += delta;
    }
    lastTime = time;
    if (!pinned && phaseElapsed >= phaseDuration) {
      phaseElapsed %= phaseDuration;
      phase = (phase+1)%phases.length;
      selectedNode = null;
      renderSelection();
    }
    drawPackets();
    frame = requestAnimationFrame(tick);
  }
  function updatePlayback() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null; lastTime = null;
    const running = enabled && visible && !document.hidden && !modalOpen;
    root.dataset.playing = String(running);
    $('#fw-play').setAttribute('aria-label',enabled ? 'Pause data flow' : 'Play data flow');
    $('#fw-play span').textContent = enabled ? 'Pause' : 'Play';
    $('#fw-play path').setAttribute('d',enabled ? 'M6 4v10M12 4v10' : 'm6 3 8 6-8 6Z');
    if (running) frame = requestAnimationFrame(tick);
  }
  function select(phaseIndex,node = null) {
    pinned = true;
    phase = phaseIndex; selectedNode = node; phaseElapsed = 0;
    renderSelection(true); updatePlayback();
  }
  nodeElements.forEach((node,id) => node.addEventListener('click',() => select(details[id].phase,id)));
  const stageButtons = $$('[data-fw-stage]');
  stageButtons.forEach(button => button.addEventListener('click',() => select(Number(button.dataset.fwStage))));
  $('.fw-stages').addEventListener('keydown',event => {
    const index = stageButtons.indexOf(document.activeElement);
    if (index < 0 || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key==='Home' ? 0 : event.key==='End' ? stageButtons.length-1 : (index+(event.key==='ArrowRight' ? 1 : -1)+stageButtons.length)%stageButtons.length;
    stageButtons[next].focus(); select(next);
  });
  $('#fw-play').addEventListener('click',() => {
    enabled = !enabled;
    updatePlayback();
  });
  $('#fw-reset').addEventListener('click',() => {
    phase = 0; selectedNode = null; elapsed = 0; phaseElapsed = 0; pinned = false;
    renderSelection(true); updatePlayback();
  });
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    updatePlayback();
  },{threshold:0}).observe(map);
  new ResizeObserver(layout).observe(map);
  document.fonts.ready.then(layout);
  document.addEventListener('visibilitychange',updatePlayback);

  const dialogs = [...document.querySelectorAll('dialog')];
  const dialogObserver = new MutationObserver(() => {
    modalOpen = dialogs.some(dialog => dialog.open);
    updatePlayback();
  });
  dialogs.forEach(dialog => dialogObserver.observe(dialog,{attributes:true,attributeFilter:['open']}));
  reducedMotion.addEventListener('change',() => {
    if (reducedMotion.matches) enabled = false;
    updatePlayback();
  });
  renderSelection(); layout(); updatePlayback();
})();
