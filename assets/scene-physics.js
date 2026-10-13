/* Browser implementation of scenes/base_15.json programs, using native MuJoCo
 * contacts, geometry, masses and integration. No staged animation trajectories. */
import {getMujoco} from './mujoco-runtime.js';

export async function createSceneSimulation(config,status=()=>{}) {
  const mj=await getMujoco(status),model=mj.MjModel.from_xml_string(config.xml),data=new mj.MjData(model);
  const bodies={},free=[],p=config.parameters,id=Number(config.id),floor=model.geom('floor');const floorId=floor.id;floor.delete();
  for(let b=1;b<model.nbody;b++){
    const accessor=model.body(b),name=accessor.name;accessor.delete();
    const joint=model.body_jntadr[b];if(joint>=0&&model.jnt_type[joint]===0){const body={id:b,name,q:model.jnt_qposadr[joint],d:model.body_dofadr[b],g:model.body_geomadr[b],mass:model.body_mass[b]};bodies[name]=body;free.push(body);}
  }
  const initialRGBA=Array.from(model.geom_rgba);let touching=new Set(),insideBefore=new Map(),previous=new Map(),pending=[],count=0,quietUntil=0,grip=null;
  const velocity=b=>Array.from(data.qvel.subarray(b.d,b.d+3)),pos=b=>data.xpos.subarray(b.id*3,b.id*3+3);
  const inside=(a,c,h)=>Math.abs(a[0]-c[0])<h&&Math.abs(a[1]-c[1])<h;
  const sphere=b=>model.body_geomnum[b.id]===1&&model.geom_type[b.g]===2;
  const palette={red:[.9,.1,.1],blue:[.1,.1,.9],green:[.1,.8,.2],yellow:[.9,.9,.1],brown:[.6,.4,.2],gray:[.55,.55,.55]};
  function color(b){const rgb=model.geom_rgba.subarray(b.g*4,b.g*4+3);return Object.keys(palette).sort((a,c)=>Math.hypot(...palette[a].map((x,i)=>x-rgb[i]))-Math.hypot(...palette[c].map((x,i)=>x-rgb[i])))[0];}
  function contacts(){
    const result=[],list=data.contact;
    for(let i=0;i<data.ncon;i++){const c=list.get(i);result.push({a:model.geom_bodyid[c.geom1],b:model.geom_bodyid[c.geom2],g1:c.geom1,g2:c.geom2,pos:Array.from(c.pos)});c.delete();}
    list.delete();return result;
  }
  function pairs(list,ids){const allowed=new Set(ids),result=new Set();for(const c of list)if(c.a!==c.b&&allowed.has(c.a)&&allowed.has(c.b))result.add([c.a,c.b].sort((a,b)=>a-b).join(':'));return result;}
  function rule(){
    if(id===2){
      const reds=free.filter(b=>sphere(b)&&color(b)==='red');
      for(let i=0;i<reds.length;i++)for(let j=i+1;j<reds.length;j++){
        const a=reds[i],b=reds[j],delta=Array.from(pos(b),(x,k)=>x-pos(a)[k]),r=Math.max(Math.hypot(...delta),p.RMIN);
        for(let k=0;k<3;k++){const f=p.K*delta[k]/r**3;data.xfrc_applied[a.id*6+k]+=f;data.xfrc_applied[b.id*6+k]-=f;}
      }
    }else if(id===3){for(const b of free)data.xfrc_applied[b.id*6+2]+=b.mass*9.81*(1-Math.sqrt(p.M0/b.mass));}
    else if(id===4)model.opt.gravity.set([0,0,-9.81*(1+p.AMP*Math.sin(2*Math.PI*data.time/p.PERIOD))]);
    else if(id===5){for(const name of ['red_ball','blue_ball','box']){const b=bodies[name],v=velocity(b),s=Math.hypot(...v);if(s>p.VC)for(let k=0;k<3;k++)data.xfrc_applied[b.id*6+k]-=p.K*(s-p.VC)*v[k]/s;}}
    else if(id===6){for(const name of ['red_ball','blue_ball']){const b=bodies[name],[x,y]=velocity(b);if(Math.abs(x)+Math.abs(y)>.001){data.xfrc_applied[b.id*6]+=p.OMEGA*y;data.xfrc_applied[b.id*6+1]-=p.OMEGA*x;}}}
    else if(id===7){
      const current=new Set(),allowed=new Set([bodies.gray_ball_1.id,bodies.gray_ball_2.id]);
      for(const c of contacts()){
        if(c.g1!==floorId&&c.g2!==floorId)continue;const bid=c.g1===floorId?c.b:c.a;
        if(!allowed.has(bid)||current.has(bid))continue;current.add(bid);
        const b=free.find(b=>b.id===bid),vz=data.qvel[b.d+2];
        if(!touching.has(bid)&&vz<-.000001){const e=inside(c.pos,p.RED_PAD,p.HALF)?p.E_RED:inside(c.pos,p.BLUE_PAD,p.HALF)?p.E_BLUE:null;if(e!==null)data.qvel[b.d+2]=-vz*e;}
      }touching=current;
    }else if(id===8){
      for(const b of free){
        const prev=previous.get(b.id)||[0,0,0],v=velocity(b),delta=v.map((x,k)=>x-prev[k]);
        if(delta.some(x=>x!==0)){
          const fraction=Math.min(prev.reduce((s,x)=>s+x*x,0)/p.VMAX**2,1-Number.EPSILON),momentum=prev.map((x,k)=>x/(1-fraction)+delta[k]),magnitude=Math.hypot(...momentum);
          const speed=magnitude?Math.min(2*magnitude/(1+Math.sqrt(1+4*(magnitude/p.VMAX)**2)),p.VMAX-Number.EPSILON*p.VMAX):0;
          for(let k=0;k<3;k++)data.qvel[b.d+k]=magnitude?momentum[k]*speed/magnitude:0;
        }previous.set(b.id,velocity(b));
      }
    }else if(id===9||id===10){
      for(const name of ['red_ball','blue_ball']){
        const b=bodies[name],within=inside(pos(b),p.PAD,p.HALF);
        if(id===9){const was=insideBefore.get(b.id)||false;if(within!==was)for(let k=0;k<6;k++)data.qvel[b.d+k]*=within?p.ALPHA:1/p.ALPHA;insideBefore.set(b.id,within);}
        else if(within){const s=Math.hypot(...velocity(b));if(s<p.SEED)data.qvel[b.d]=p.SEED;else if(s<p.CAP)for(let k=0;k<3;k++)data.qvel[b.d+k]*=p.GAIN;}
      }
    }else if(id>=11&&id<=13){
      const selected=id===12?free.filter(sphere):['red_ball','blue_ball',...(id===11?['green_ball']:[])].map(n=>bodies[n]);
      const current=pairs(contacts(),selected.map(b=>b.id));
      if(id===11){const affected=new Set();for(const pair of touching)if(!current.has(pair))for(const bid of pair.split(':').map(Number))affected.add(bid);for(const bid of affected){const b=free.find(b=>b.id===bid);for(let k=0;k<3;k++)data.qvel[b.d+k]*=p.BOOST;}}
      else for(const pair of [...current].filter(pair=>!touching.has(pair)).sort()){
        const [a,b]=pair.split(':').map(Number).map(bid=>free.find(b=>b.id===bid));
        if(id===12){const rgba=Array.from(model.geom_rgba.subarray(a.g*4,a.g*4+4));model.geom_rgba.set(model.geom_rgba.subarray(b.g*4,b.g*4+4),a.g*4);model.geom_rgba.set(rgba,b.g*4);}
        else{count++;if(count%3===0){data.qvel[a.d+2]=p.KICK;data.qvel[b.d+2]=p.KICK;}}
      }touching=current;
    }else if(id===14){const due=pending.filter(e=>e.time<=data.time);if(due.length){data.qvel.set(due.at(-1).v,bodies[p.echo].d);pending=pending.filter(e=>e.time>data.time);}}
    else if(id===15&&data.time>=quietUntil){const b=bodies.red_ball;data.xfrc_applied[b.id*6+1]+=p.DRIFT*b.mass;}
  }
  function reset(){
    mj.mj_resetData(model,data);data.qpos.set(config.initial_qpos);data.qvel.set(config.initial_qvel);model.geom_rgba.set(initialRGBA);model.opt.gravity.set([0,0,-9.81]);
    touching=new Set();insideBefore=new Map();previous=new Map();pending=[];count=0;quietUntil=0;grip=null;
    mj.mj_forward(model,data);rule();mj.mj_forward(model,data);data.xfrc_applied.fill(0);
  }
  function step(external=false){
    if(!external){data.xfrc_applied.fill(0);data.qfrc_applied.fill(0);}rule();
    // Match Workshop.apply: scene forces first, then a mass-scaled grip using
    // the current gravity. Moving the hand never counts as a launch.
    if(grip){
      const b=bodies[grip.name],g=config.grip,desired=grip.target.map((x,k)=>(x-pos(b)[k])*8),length=Math.hypot(...desired);
      if(length>g.move_speed)for(let k=0;k<3;k++)desired[k]*=g.move_speed/length;
      const gravity=model.opt.gravity,v=velocity(b),force=desired.map((x,k)=>2*Math.sqrt(g.stiffness*b.mass)*(x-v[k])-b.mass*gravity[k]),magnitude=Math.hypot(...force);
      if(magnitude>g.force_limit)for(let k=0;k<3;k++)force[k]*=g.force_limit/magnitude;
      for(let k=0;k<3;k++)data.xfrc_applied[b.id*6+k]+=force[k];
    }
    mj.mj_step(model,data);
    for(const b of free)for(let k=0;k<3;k++){const lo=k===2?0:-6,hi=k===2?12:6;if(data.qpos[b.q+k]<lo||data.qpos[b.q+k]>hi){data.qpos[b.q+k]=Math.max(lo,Math.min(hi,data.qpos[b.q+k]));data.qvel[b.d+k]=0;}}
    if(id===8)rule();mj.mj_forward(model,data);
  }
  function launch(name,impulse){
    const b=bodies[name];if(!b)throw Error('Unknown object');if(grip?.name===name)throw Error('Release the object before launching it');for(let k=0;k<3;k++)data.qvel[b.d+k]+=impulse[k]/b.mass;
    if(impulse.some(v=>v!==0)){if(id===14&&name===p.source)pending.push({time:data.time+p.DELAY,v:velocity(b)});if(id===15)quietUntil=data.time+p.HUSH;}
    if(id===8)rule();mj.mj_forward(model,data);
  }
  reset();
  return {mj,model,data,config,bodies,reset,step,launch,rule,
    setGrip(name,target){if(!bodies[name])throw Error('Unknown object');grip={name,target:Array.from(target)};},
    releaseGrip(){grip=null;},
    info:()=>({count,quietUntil,pending:pending.map(e=>e.time),held:grip?.name||null,gripTarget:grip?.target||null}),destroy(){data.delete();model.delete();}};
}
