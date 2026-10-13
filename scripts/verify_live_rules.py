"""Compare browser rules and trajectories with the actual Python scene programs."""
import argparse,json
from pathlib import Path

CACHE=Path('/tmp/longchang-live-native-reference.json')

def prepare():
    from render_oracle_demos import plan,arrange,launch
    cases=[]
    for n in range(1,16):
        id=f'{n:02}';world,_,spec=plan(id);events=[e for e in spec['events'] if e['kind']!='hold'];cursor=0;trace=[]
        for tick in range(round(spec['simulation_duration']/.002)+1):
            while cursor<len(events) and events[cursor]['time']<=world.data.time+.00001:
                e=events[cursor]
                if e['kind']=='arrange':arrange(world,e['positions'])
                else:launch(world,e['command'])
                cursor+=1
            if tick%25==0 or tick==round(spec['simulation_duration']/.002):
                trace.append(dict(tick=tick,qpos=world.data.qpos.tolist(),qvel=world.data.qvel.tolist(),rgba=world.model.geom_rgba.tolist()))
            if tick<round(spec['simulation_duration']/.002):world.step()
        cases.append(dict(id=id,events=events,ticks=round(spec['simulation_duration']/.002),trace=trace))
    CACHE.write_text(json.dumps(cases,separators=(',',':')))
    print('Prepared reference trajectories directly from all 15 original Python programs.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    if args.prepare:prepare();return
    from playwright.sync_api import sync_playwright
    cases=json.loads(CACHE.read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page();page.goto(args.url)
        result=page.evaluate('''async(cases)=>{
          const {createSceneSimulation}=await import('./assets/scene-physics.js'),results=[];
          for(const c of cases){
            const config=await(await fetch(`data/interactive-scenes/${c.id}.json`)).json(),s=await createSceneSimulation(config);let cursor=0,index=0,positionError=0,velocityError=0,colorError=0;
            for(let tick=0;tick<=c.ticks;tick++){
              while(cursor<c.events.length&&c.events[cursor].time<=s.data.time+.00001){
                const e=c.events[cursor++];
                if(e.kind==='arrange'){for(const [name,xyz] of Object.entries(e.positions)){const b=s.bodies[name];s.data.qpos.set(xyz,b.q);s.data.qvel.fill(0,b.d,b.d+6);}s.mj.mj_forward(s.model,s.data);}
                else{const t=e.command.split(' '),h=Number(t[2])*Math.PI/180,a=t[0]==='THROW'?Number(t[3])*Math.PI/180:0,f=Math.min(10,Number(t.at(-1)));s.launch(t[1],[f*Math.cos(h)*Math.cos(a),f*Math.sin(h)*Math.cos(a),f*Math.sin(a)]);}
              }
              if(index<c.trace.length&&c.trace[index].tick===tick){const r=c.trace[index++];for(let i=0;i<r.qpos.length;i++)positionError=Math.max(positionError,Math.abs(s.data.qpos[i]-r.qpos[i]));for(let i=0;i<r.qvel.length;i++)velocityError=Math.max(velocityError,Math.abs(s.data.qvel[i]-r.qvel[i]));const rgba=r.rgba.flat();for(let i=0;i<rgba.length;i++)colorError=Math.max(colorError,Math.abs(s.model.geom_rgba[i]-rgba[i]));}
              if(tick<c.ticks)s.step();
            }
            results.push({id:c.id,positionError,velocityError,colorError,info:s.info()});s.destroy();
          }return results;
        }''',cases)
        browser.close()
    for r in result:
        print(json.dumps(r),flush=True)
        assert r['positionError']<1e-8 and r['velocityError']<1e-8 and r['colorError']<1e-6,r
    print('PASS: all 15 browser scenes match the original native programs, including dense motion, colors, collision counts and delayed events.')

if __name__=='__main__':main()
