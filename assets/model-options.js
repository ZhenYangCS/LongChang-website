/* Visible, keyboard-accessible conditions shared by both explanatory models. */
(() => {
  'use strict';
  const colors = {red:'#c87967', blue:'#7399bd', green:'#73a688', ink:'#648577'};
  const ball = (x,y,color) => `<circle cx="${x}" cy="${y}" r="3.6" fill="${colors[color]}"/><circle cx="${x-1}" cy="${y-1}" r="1" fill="#fff" opacity=".55"/>`;
  const line = (path,color=colors.ink,extra='') => `<path d="${path}" fill="none" stroke="${color}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;
  function arrow(x,y,dx,dy,color=colors.ink) {
    const length=Math.hypot(dx,dy),ux=dx/length,uy=dy/length,bx=x+dx-ux*3,by=y+dy-uy*3;
    return line(`M${x} ${y}l${dx} ${dy}M${bx-uy*2} ${by+ux*2}L${x+dx} ${y+dy} ${bx+uy*2} ${by-ux*2}`,color);
  }
  function sketch(scene,value) {
    let art='';
    const tile = (yellow=false) => `<rect x="23" y="11" width="23" height="14" rx="1.5" fill="${yellow?'#ead59b':'#d2ded7'}" stroke="${yellow?'#c7ad67':'#9bb2a4'}" stroke-width=".8"/>`;
    const wall = () => `<rect x="43" y="5" width="4" height="22" rx="1" fill="#bccbc3"/>`;
    if(scene==='02'){
      const pair=value.split('-');art=ball(22,16,pair[0])+ball(42,16,pair[1]);
    }else if(scene==='03'){
      art=ball(21,16,'red')+ball(43,16,'blue');
      art+=value==='drop'?line('M12 8H52', '#b1c4b8', 'stroke-dasharray="2 3"')+arrow(21,21,0,7)+arrow(43,21,0,7):arrow(21,11,0,-8)+arrow(43,11,0,-8);
      if(value==='impulse')art+=line('M15 23h12M37 23h12');
    }else if(scene==='04'){
      let path='';for(let i=0;i<=30;i++){const x=8+i*1.6,y=16-7*Math.sin(i/30*Math.PI*2);path+=`${i?'L':'M'}${x} ${y}`;}
      const phase=Number(value);art=line(path,'#a6bbb0')+`<circle cx="${8+phase/6*48}" cy="${16-7*Math.sin(phase/6*Math.PI*2)}" r="3" fill="${colors.ink}"/>`;
    }else if(scene==='06'){
      const angle=Number(value)*Math.PI/180;art=arrow(32,16,13*Math.cos(angle),-11*Math.sin(angle))+ball(32,16,'red');
    }else if(scene==='09'||scene==='10'){
      art=tile(scene==='10');
      if(value==='above')art+=line('M34 7V20','#93a99c','stroke-dasharray="2 3"')+ball(34,5,'red');
      else if(value==='inside')art+=ball(34,18,'red');
      else{const y=value==='beside'?5:18;art+=ball(10,y,'red');if(value!=='outside')art+=arrow(16,y,15,0);}
    }else if(['11','12','13'].includes(scene)){
      if(value==='wall')art=ball(22,17,'red')+arrow(28,17,11,0)+wall();
      else if(value==='hold')art=ball(28,19,'red')+ball(35,19,'blue')+line('M22 11V7H41V11');
      else art=ball(23,18,'red')+ball(41,18,'blue')+(value==='repeat'?line('M18 9C22 1 44 1 48 9M45 5l3 4-5 0') : arrow(8,18,9,0));
    }else if(scene==='14'){
      art=ball(22,18,'red')+ball(44,18,'green');
      art+=value==='hold'?line('M15 12V7H29V12'):value==='moving'?arrow(44,12,0,-8,colors.green):arrow(8,18,8,0,colors.red);
    }else if(scene==='15'){
      art=ball(40,17,value==='red'?'red':'blue');
      art+=value==='zero'?`<text x="21" y="21" fill="${colors.ink}" font-size="13" font-family="sans-serif">0</text>`:arrow(17,17,16,0);
    }else if(scene==='evo-generate'){
      art=line('M10 21H54','#b0c3b7');for(const x of value==='once'?[16]:[16,32,48])art+=arrow(x,6,0,11)+`<circle cx="${x}" cy="21" r="2" fill="${colors.ink}"/>`;
    }else if(scene==='evo-mutate'){
      art=tile()+ball(value==='inside'?34:12,18,'blue');
    }else if(scene==='evo-compose'){
      art=ball(40,17,'blue')+(value==='later'?arrow(17,17,16,0):line('M18 17H27','#a2b7a9'));
    }
    return `<svg viewBox="0 0 64 32" aria-hidden="true" focusable="false">${art}</svg>`;
  }
  function create({host,id,label,options,value,scene,onChange}) {
    const group=document.createElement('fieldset');group.className='model-options';
    const legend=document.createElement('legend');legend.className='model-setting-label';legend.textContent=label;
    // Keep the model's existing value API for direct gestures and export tools.
    const state=document.createElement('input');state.type='hidden';state.id=id;
    const grid=document.createElement('div');grid.className='model-choice-grid';grid.style.setProperty('--choice-columns',Math.min(options.length,4));
    const inputs=options.map(([key,title])=>{
      const card=document.createElement('label');card.className='model-choice';card.dataset.choice=key;
      const input=document.createElement('input');input.type='radio';input.name=`${id}-choice`;input.value=key;
      const illustration=document.createElement('span');illustration.className='model-choice-art';illustration.innerHTML=sketch(scene,key);
      const text=document.createElement('span');text.className='model-choice-label';text.textContent=title;
      card.append(input,illustration,text);grid.append(card);return input;
    });
    const set=next=>{state.value=String(next);inputs.forEach(input=>{input.checked=input.value===String(next);});};
    group.addEventListener('change',event=>{if(event.target.matches('input[type=radio]')){set(event.target.value);onChange(event.target.value);}});
    state.addEventListener('change',()=>onChange(state.value));
    group.append(legend,state,grid);host.replaceChildren(group);set(value);
    return {set};
  }
  window.LongChangModelOptions=Object.freeze({create});
})();
