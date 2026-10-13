"""Compare browser rules and trajectories with the actual Python scene programs."""
import argparse,json,copy,math,random
from pathlib import Path

CACHE=Path('/tmp/longchang-live-native-reference.json')

def prepare(audit=False):
    from render_oracle_demos import plan,arrange,launch
    from render_physics_demos import demonstration
    cases=[]
    def record(id,label,world,events,duration):
        events=sorted(copy.deepcopy(events),key=lambda e:e['time']);cursor=0;trace=[];ticks=round(duration/.002)
        for tick in range(ticks+1):
            while cursor<len(events) and events[cursor]['time']<=world.data.time+.00001:
                e=events[cursor]
                if e['kind']=='arrange':arrange(world,e['positions'])
                elif e['kind']=='state':
                    arrange(world,e['positions'])
                    for name,v in e.get('velocities',{}).items():
                        q,d=world.bodies[name];world.data.qvel[d:d+6]=v
                    for name,quat in e.get('quaternions',{}).items():
                        q,_=world.bodies[name];world.data.qpos[q+3:q+7]=quat
                    import mujoco
                    mujoco.mj_forward(world.model,world.data)
                elif e['kind']=='grip':
                    name=e['object'];bid=world.model.body(name).id
                    target=e.get('target',world.data.xpos[bid].tolist())
                    import numpy as np
                    world.workshop.holds={name:dict(target=np.array(target))}
                elif e['kind']=='release':world.workshop.holds.clear()
                else:launch(world,e['command'])
                cursor+=1
            if tick%25==0 or tick==ticks:
                state=world.scene.state
                trace.append(dict(tick=tick,qpos=world.data.qpos.tolist(),qvel=world.data.qvel.tolist(),rgba=world.model.geom_rgba.tolist(),
                                  count=max(getattr(state,'_count',{}).values(),default=0),quietUntil=getattr(state,'_quiet_until',0),
                                  pending=[v[0] for v in getattr(state,'_pending',[])],held=next(iter(world.workshop.holds),None)))
            if tick<ticks:world.step()
        cases.append(dict(id=id,label=label,events=events,ticks=ticks,trace=trace))
    for n in range(1,16):
        id=f'{n:02}';world,_,spec=plan(id)
        record(id,'prepared demonstration',world,[e for e in spec['events'] if e['kind']!='hold'],spec['simulation_duration'])
        if not audit:continue
        world,_=demonstration(id);names=list(world.bodies);name='blue_ball' if n==3 else names[0]
        start=world.data.xpos[world.model.body(name).id].copy()
        events=[dict(time=0,kind='grip',object=name,target=start.tolist())]
        for i in range(1,41):
            t=i*.05;target=(start+[.35*math.sin(t*2),.3*math.sin(t),.35*math.sin(t*.8)]).tolist()
            events.append(dict(time=t,kind='grip',object=name,target=target))
        events += [dict(time=2.2,kind='release'),dict(time=2.5,kind='launch',command=f'PUSH {names[-1]} 45 0'),
                   dict(time=3,kind='launch',command=f'THROW {name} 60 35 3')]
        record(id,'move, hold, release and relaunch',world,events,16 if n in [14,15] else 4.5)
        for seed in [101,307]:
            world,_=demonstration(id);rng=random.Random(n*1000+seed);positions={};velocities={};quaternions={}
            for i,name in enumerate(world.bodies):
                positions[name]=[-1.6+i*1.05,rng.uniform(-.8,.8),rng.uniform(.6,2.4)]
                velocities[name]=[rng.uniform(-3,3),rng.uniform(-3,3),rng.uniform(-1,2),*[rng.uniform(-3,3) for _ in range(3)]]
                q=[rng.uniform(-1,1) for _ in range(4)];length=math.sqrt(sum(v*v for v in q));quaternions[name]=[v/length for v in q]
            events=[dict(time=0,kind='state',positions=positions,velocities=velocities,quaternions=quaternions)]
            for i,time in enumerate([.5,1.2,1.7]):
                events.append(dict(time=time,kind='launch',command=f'THROW {names[i%len(names)]} {rng.randrange(360)} {rng.randrange(70)} {rng.uniform(.2,8)}'))
            record(id,f'free motion seed {seed}',world,events,3)
    if audit:
        world,_=demonstration('03')
        record('03','stationary heavy-ball grip',world,[dict(time=0,kind='grip',object='blue_ball',target=[.55,0,1.8])],2)
        world,_=demonstration('04')
        record('04','grip through an entire gravity cycle',world,[dict(time=0,kind='grip',object='red_ball',target=[-.55,0,1.5])],6.2)
        world,_=demonstration('07')
        record('07','swap the balls between tiles',world,[dict(time=0,kind='arrange',positions={'gray_ball_1':[2.5,0,1.5],'gray_ball_2':[-2.5,0,1.5]})],2)
        world,_=demonstration('10')
        record('10','blue enters yellow; red stays outside',world,[dict(time=0,kind='arrange',positions={'red_ball':[-3,2.5,.1],'blue_ball':[0,0,1.5]})],1)
        world,_=demonstration('12')
        record('12','simultaneous three-body contacts',world,[dict(time=0,kind='arrange',positions={'ball_1':[0,0,.1],'ball_2':[.199,0,.1],'ball_3':[.0995,.1723,.1]})],1)
        world,_=demonstration('13')
        record('13','wall contact does not count',world,[dict(time=0,kind='arrange',positions={'red_ball':[5.8,0,.1],'blue_ball':[-3,2,.1]}),dict(time=0,kind='launch',command='PUSH red_ball 0 6')],1)
        world,_=demonstration('14')
        record('14','queued 3D copies survive holding red',world,[dict(time=0,kind='launch',command='THROW red_ball 45 30 3'),dict(time=.4,kind='launch',command='PUSH red_ball 180 1'),dict(time=1.2,kind='launch',command='THROW red_ball 270 60 1'),dict(time=2,kind='grip',object='red_ball'),dict(time=3,kind='release')],14)
        world,_=demonstration('15')
        record('15','zero pushes and hand movement do not restart pause',world,[dict(time=0,kind='launch',command='PUSH blue_ball 0 1'),dict(time=1,kind='grip',object='blue_ball'),dict(time=2,kind='release'),dict(time=3,kind='launch',command='PUSH blue_ball 0 0')],11)
        world,_=demonstration('01')
        record('01','native ceiling collision',world,[dict(time=0,kind='state',positions={'red_ball':[-1,0,11.8]},velocities={'red_ball':[0,0,6,0,0,0]})],.6)
    path=CACHE.with_name('longchang-live-audit-reference.json') if audit else CACHE
    path.write_text(json.dumps(cases,separators=(',',':')))
    print(f'Prepared {len(cases)} reference experiments directly from the original Python programs and Workshop.apply.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--audit',action='store_true');parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    if args.prepare:prepare(args.audit);return
    from playwright.sync_api import sync_playwright
    path=CACHE.with_name('longchang-live-audit-reference.json') if args.audit else CACHE
    cases=json.loads(path.read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page();page.goto(args.url)
        result=page.evaluate('''async(cases)=>{
          const {createSceneSimulation}=await import('./assets/scene-physics.js'),results=[];
          for(const c of cases){
            const config=await(await fetch(`data/interactive-scenes/${c.id}.json`)).json(),s=await createSceneSimulation(config);let cursor=0,index=0,positionError=0,velocityError=0,colorError=0,stateError=0;
            for(let tick=0;tick<=c.ticks;tick++){
              while(cursor<c.events.length&&c.events[cursor].time<=s.data.time+.00001){
                const e=c.events[cursor++];
                if(e.kind==='arrange'||e.kind==='state'){for(const [name,xyz] of Object.entries(e.positions)){const b=s.bodies[name];s.data.qpos.set(xyz,b.q);s.data.qvel.fill(0,b.d,b.d+6);}for(const [name,v] of Object.entries(e.velocities||{}))s.data.qvel.set(v,s.bodies[name].d);for(const [name,q] of Object.entries(e.quaternions||{}))s.data.qpos.set(q,s.bodies[name].q+3);s.mj.mj_forward(s.model,s.data);}
                else if(e.kind==='grip'){const b=s.bodies[e.object];s.setGrip(e.object,e.target||Array.from(s.data.xpos.subarray(b.id*3,b.id*3+3)));}
                else if(e.kind==='release')s.releaseGrip();
                else{const t=e.command.split(' '),h=Number(t[2])*Math.PI/180,a=t[0]==='THROW'?Number(t[3])*Math.PI/180:0,f=Math.min(10,Number(t.at(-1)));s.launch(t[1],[f*Math.cos(h)*Math.cos(a),f*Math.sin(h)*Math.cos(a),f*Math.sin(a)]);}
              }
              if(index<c.trace.length&&c.trace[index].tick===tick){const r=c.trace[index++];for(let i=0;i<r.qpos.length;i++)positionError=Math.max(positionError,Math.abs(s.data.qpos[i]-r.qpos[i]));for(let i=0;i<r.qvel.length;i++)velocityError=Math.max(velocityError,Math.abs(s.data.qvel[i]-r.qvel[i]));const rgba=r.rgba.flat();for(let i=0;i<rgba.length;i++)colorError=Math.max(colorError,Math.abs(s.model.geom_rgba[i]-rgba[i]));const info=s.info();if(info.count!==r.count||Math.abs(info.quietUntil-r.quietUntil)>1e-8||info.held!==r.held||info.pending.length!==r.pending.length||info.pending.some((t,i)=>Math.abs(t-r.pending[i])>1e-8))stateError++;}
              if(tick<c.ticks)s.step();
            }
            results.push({id:c.id,label:c.label,positionError,velocityError,colorError,stateError,info:s.info()});s.destroy();
          }return results;
        }''',cases)
        browser.close()
    for r in result:
        print(json.dumps(r),flush=True)
        assert r['positionError']<1e-8 and r['velocityError']<1e-8 and r['colorError']<1e-6 and r['stateError']==0,r
    Path('/tmp/longchang-live-audit-report.json' if args.audit else '/tmp/longchang-live-rule-report.json').write_text(json.dumps(result,indent=2))
    print(f'PASS: {len(result)} experiments match native positions, velocities, colors, grip state, contact counts and all pending timers.')

if __name__=='__main__':main()
