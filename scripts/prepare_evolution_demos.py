"""Film three scripted demonstrations in the paper's accepted evolved scenes.

The native scene programs, object sizes and physics are unchanged. Initial
placements and actions are recorded separately from model explorations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from render_physics_demos import ROOT, SITE, World, load_scene, arrange, launch, Renderer
from prepare_case_films import font

RUN=ROOT/'runs/acl-weakness-evolution-20261006-122456-2aa1c1'
CAMERA=dict(lookat=[2.85,3.05,.15],distance=8,azimuth=100,elevation=-60,
            orthographic=True,vertical_span=3.2)
FPS, DURATION = 60, 10
PLANS={
    'generate':dict(title='Change the force',duration=12.0,
        positions={'red_ball':[2.5,3,.1],'blue_ball':[3.2,3,.1]},
        actions=[dict(time=.6,kind='launch',command='PUSH blue_ball 90 0.05')]),
    'mutate':dict(title='Add a condition',duration=3.2,
        positions={'object_1':[2.0,2.8,.1],'object_2':[3,3,.1]},
        actions=[dict(time=1,kind='move',object='object_2',target=[3.9,3,.1])]),
    'compose':dict(title='Combine two rules',duration=19.5,
        positions={'red_ball':[2.25,3.4,.1],'green_ball':[3.15,3.4,.1],'blue_ball':[3.9,2.6,.1]},
        actions=[dict(time=0,kind='launch',command='PUSH red_ball 270 1.2'),
                 dict(time=8,kind='launch',command='PUSH blue_ball 90 0.05')])
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(key, path):
    definition=json.loads(path.read_text())['scenes'][0]
    world=World(load_scene(path,definition['id']))
    world._motion=None
    plan=PLANS[key]
    arrange(world,plan['positions'])
    frames=[]
    action_log=[]
    original_step=world.step

    def sample():
        objects={}
        for name in plan['positions']:
            q,d=world.bodies[name]
            body=world.model.body(name).id
            geom=world.model.body_geomadr[body]
            objects[name]=dict(position=world.data.qpos[q:q+3].copy().tolist(),
                velocity=world.data.qvel[d:d+3].copy().tolist(),
                color=world.model.geom_rgba[geom].copy().tolist(),
                applied_force=world.data.xfrc_applied[body,:3].copy().tolist())
        state=world.scene.state
        deadline=float(getattr(state,'quiet_until',getattr(state,'_quiet_until',0)))
        frames.append(dict(time=float(world.data.time),epoch=0,
            qpos=world.data.qpos.copy(),qvel=world.data.qvel.copy(),rgba=world.model.geom_rgba.copy(),
            quiet_until=deadline,objects=objects,holding=world.workshop.hand))

    def step(*args,**kwargs):
        original_step(*args,**kwargs)
        sample()
    # Capture the ticks inside native GRASP/MOVE as well as ordinary waiting.
    world.step=step
    sample()
    index=0
    while world.data.time<plan['duration']-.0005:
        if index<len(plan['actions']) and world.data.time>=plan['actions'][index]['time']-.0005:
            event=plan['actions'][index]
            actual=dict(event,started=float(world.data.time))
            if event['kind']=='launch':
                launch(world,event['command'])
            else:
                world.workshop.grasp(world,event['object'])
                world.workshop.move(world,event['object'],event['target'])
            actual['ended']=float(world.data.time)
            action_log.append(actual)
            index+=1
        else:world.step()
    assert np.isfinite(world.data.qpos).all()
    return world,frames,action_log


def audit(key, frames):
    def near(time):return min(frames,key=lambda f:abs(f['time']-time))
    def force(frame,name):return np.array(frame['objects'][name]['applied_force'])
    if key=='generate':
        before,paused,returned=near(.5),near(5),near(10.65)
        assert np.linalg.norm(force(before,'red_ball'))>1.4
        assert np.linalg.norm(force(paused,'red_ball'))<1e-8
        assert np.linalg.norm(force(paused,'blue_ball'))<1e-8
        assert np.linalg.norm(force(returned,'red_ball'))>1.4
        assert np.allclose(force(returned,'red_ball'),-force(returned,'blue_ball'))
        assert abs(returned['quiet_until']-10.6)<.003
    elif key=='mutate':
        inside,outside=near(.8),near(2.0)
        assert np.linalg.norm(force(inside,'object_1'))<1e-8
        assert force(outside,'object_1')[1]>1.4
        assert all(f['quiet_until']==0 for f in frames), 'Hand movement must not reset suppression'
        assert outside['objects']['object_2']['position'][0]>3.5
        assert frames[-1]['objects']['object_1']['position'][1]>inside['objects']['object_1']['position'][1]+.2
    else:
        before,copied,red_back=near(11.99),near(12.01),near(18.01)
        assert abs(before['objects']['green_ball']['velocity'][1])<1e-6
        assert copied['objects']['green_ball']['velocity'][1]<-1.0
        assert np.linalg.norm(force(copied,'red_ball'))<1e-8
        assert force(red_back,'red_ball')[1]>1.4
        assert abs(copied['quiet_until']-18)<.003


def cue(key, frame):
    t=frame['time']
    if key=='generate':
        if t<.6:return 'Repulsion on'
        if t<10.6:return f"Push blue · pause {max(0,10.6-t):.1f}"
        return 'Repulsion returns'
    if key=='mutate':
        x,y,_=frame['objects']['object_2']['position']
        return 'Blue inside · force off' if 2.5<=x<=3.5 and 2.5<=y<=3.5 else 'Blue outside · force returns'
    if t<1:return 'Launch red'
    if t<8:return 'Two timers running'
    if t<12:return 'Push blue · red stays paused'
    if t<18:return '12: green copies red'
    return '18: red’s force returns'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    accepted=json.loads((RUN/'accepted_scenes.json').read_text())
    output=[]
    for key,plan in PLANS.items():
        source=next(a for a in accepted if a['case']['operation']==key)
        path=RUN/source['scene_path']
        assert sha(path)==source['scene_sha256']
        world,frames,actions=capture(key,path)
        audit(key,frames)
        times=np.array([f['time'] for f in frames])
        renderer=Renderer(world.model_xml(),world,CAMERA)
        movie=SITE/f'assets/videos/evolution-{key}.mp4'
        temporary=movie.with_suffix('.rendering.mp4')
        poster=SITE/f'assets/images/evolution-{key}.webp'
        process=None
        if not args.preview:
            process=subprocess.Popen([args.ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','720x540','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','20',
                '-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],stdin=subprocess.PIPE)
        try:
            indices=[0,round(DURATION*FPS/2),DURATION*FPS-1] if args.preview else range(DURATION*FPS)
            for n in indices:
                t=(n/(DURATION*FPS-1))*frames[-1]['time']
                index=int(np.abs(times-t).argmin())
                frame=frames[index]
                # The same view and scale are used for all three worlds.
                trail=frames[max(0,index-650):index+1:10]
                rendered=renderer.render(frame,trail).resize((720,450),Image.Resampling.LANCZOS)
                image=Image.new('RGB',(720,540),'#f4f7f4');image.paste(rendered,(0,44))
                draw=ImageDraw.Draw(image)
                draw.text((18,12),cue(key,frame),font=font(21,True),fill='#24453b')
                draw.text((18,509),'SCRIPTED DEMO',font=font(14),fill='#667c71')
                clock=f"{frame['time']:.1f} counts"
                draw.text((702-draw.textlength(clock,font=font(18)),506),clock,font=font(18),fill='#426654')
                if args.preview:
                    image.save(f'/tmp/evolution-{key}-{n}.png')
                else:
                    if n==0:image.save(poster,quality=92)
                    process.stdin.write(np.asarray(image).tobytes())
            if process:
                process.stdin.close();assert process.wait()==0
                temporary.replace(movie)
        finally:
            renderer.close()
            if process and process.poll() is None:process.kill();process.wait()
        record=dict(id=key,title=plan['title'],source=str(path.relative_to(ROOT)),source_sha256=sha(path),
            video=str(movie.relative_to(SITE)),poster=str(poster.relative_to(SITE)),
            duration=DURATION,fps=FPS,size=[720,540],camera=CAMERA,
            preparation=plan['positions'],actions=actions,simulation_duration=frames[-1]['time'],
            physics_timestep=float(world.model.opt.timestep),
            samples=[{k:v for k,v in f.items() if k not in ['qpos','qvel','rgba','epoch']} for f in frames[::10]])
        if movie.exists():record['video_sha256']=sha(movie)
        output.append(record)
        print(f"{key}: native-physics audit passed, {len(frames)} recorded states",flush=True)
    if not args.preview:
        (SITE/'data/evolution-demos.json').write_text(json.dumps(dict(
            kind='Scripted demonstrations of accepted evolved-scene programs; not model exploration results.',
            method='Native integration with recorded preparation/actions. Constant time scaling per clip; nearest native state, no pose interpolation. Trails connect recorded positions.',
            demos=output),separators=(',',':'))+'\n')


if __name__=='__main__':main()
