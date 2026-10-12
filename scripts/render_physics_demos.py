"""Film scripted interventions in the paper's original MuJoCo scene programs.

No LLM calls. These are explicitly labelled scripted demonstrations, separate
from archived model explorations and their scores. Physical parameters, colors,
object sizes, friction, gravity and contact laws remain unchanged. Preparation
positions and all interventions are exported alongside the sampled states.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.setdefault('MUJOCO_GL', 'egl')
SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path[:0] = [str(ROOT / 'longchang'), str(ROOT / 'ACL/materials/_shared')]
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scenes import load_scene
from world import World, impulse, contact_pairs
from render_replays import styled
from paper_scenes import paper_scene_names

SOURCE = ROOT / 'scenes/base_15.json'
SPECS = json.loads(SOURCE.read_text())['scenes']
FONT = SITE / 'assets/fonts/type-0.ttf'


def arrange(world, positions):
    for name, xyz in positions.items():
        q, d = world.bodies[name]
        world.data.qpos[q:q+3] = xyz
        world.data.qvel[d:d+6] = 0
    mujoco.mj_forward(world.model, world.data)


def launch(world, command):
    tokens = command.split()
    d, delta = impulse(tokens, world.bodies, world.model)
    world.data.qvel[d:d+3] += delta
    on_launch = getattr(world.scene, 'on_launch', None)
    if any(delta) and on_launch is not None:
        on_launch(world.model, world.data, tokens[1])
    if world.scene.scene_spec['id'].startswith('08_'):
        # Record the constrained post-command velocity, not the transient
        # momentum increment before the scene's pre-step mapping.
        world.scene.hook(world.model, world.data)


def demonstration(number):
    """Exact preparation and event sequence; clip time is separate from counts."""
    n = int(number)
    original = SPECS[n-1]
    world = World(load_scene(SOURCE, original['id']))
    world._motion = None  # Observation text is unnecessary; physics is untouched.
    positions, events, focus = {}, [], []
    duration, film_duration = 3.0, 10
    intro = ''
    def push(t, command, caption):
        events.append({'time':t, 'kind':'launch', 'command':command, 'caption':caption})
    def place(t, p, caption):
        events.append({'time':t, 'kind':'arrange', 'positions':p, 'caption':caption})

    if n == 1:
        positions = {'red_ball':[2.5,-2,1.5], 'blue_ball':[-.2,-2,1.5]}
        focus = ['red_ball','blue_ball']; duration = 1.7
        intro = 'Matched release: one ball above the gray tile, one above ordinary floor.'
    elif n == 2:
        positions = {'red_ball_1':[-.8,-.65,.1], 'red_ball_2':[.8,-.65,.1],
                     'blue_ball_1':[-.8,.65,.1], 'blue_ball_2':[.8,.65,.1]}
        focus = list(positions); duration = 1.4
        intro = 'Release both pairs from rest. Only the red spheres attract.'
    elif n == 3:
        positions = {'red_ball':[-.55,0,1.8], 'blue_ball':[.55,0,1.8]}
        focus = list(positions); duration = 1.3
        intro = 'Matched release height; red has mass 1 and blue has mass 4.'
    elif n == 4:
        positions = {'red_ball':[-.55,0,.1], 'blue_ball':[.55,0,.1]}
        focus = list(positions); duration = 7; film_duration = 12
        intro = 'Apply the same upward impulse at two phases of the gravity cycle.'
        push(1.5, 'THROW red_ball 0 90 4', 'Launch red at the strongest-gravity phase.')
        push(4.5, 'THROW blue_ball 0 90 4', 'Launch blue at the weakest-gravity phase; same mass and impulse.')
    elif n == 5:
        positions = {'red_ball':[-2,-.65,.1], 'blue_ball':[-2,.65,.1]}
        focus = list(positions); duration = 2.5
        intro = 'Compare launch impulses 8 (red) and 2 (blue), both with unit mass.'
        push(0, 'PUSH red_ball 0 8', 'Strong launch activates the extra braking force.')
        push(0, 'PUSH blue_ball 0 2', 'Gentle launch stays below the 2.5 speed threshold.')
    elif n == 6:
        positions = {'red_ball':[-1.4,.7,.1]}; focus = ['red_ball']; duration = 2.6
        intro = 'Launch red east. The extra force bends its trajectory to the right.'
        push(0, 'PUSH red_ball 0 4', 'Eastward push; watch the southward bend in the recorded path.')
    elif n == 7:
        positions = {'gray_ball_1':[-2.5,0,1.5], 'gray_ball_2':[2.5,0,1.5]}
        focus = list(positions); duration = 2.8
        intro = 'Release identical gray balls above the red and blue tiles at the same time.'
    elif n == 8:
        positions = {'red_ball':[-1.5,-.6,.1], 'blue_ball':[-1.5,.6,.1]}
        focus = list(positions); duration = 2.4
        intro = 'Compare impulses 2 (red) and 10 (blue). Neither launch reaches speed 2.2.'
        push(0, 'PUSH red_ball 0 2', 'Apply the smaller impulse to red.')
        push(0, 'PUSH blue_ball 0 10', 'Five times the impulse gives much less than five times the speed.')
    elif n == 9:
        positions = {'red_ball':[-.3,0,.1], 'blue_ball':[-.3,2.1,.1]}
        focus = ['red_ball']; duration = 1.6
        intro = 'Launch red across the gray footprint; watch its entry and exit speeds.'
        push(0, 'PUSH red_ball 0 10', 'Red approaches the entry boundary at x = 0.5.')
        push(0, 'PUSH blue_ball 0 10', 'Blue is outside the footprint. Ordinary friction remains active.')
    elif n == 10:
        positions = {'red_ball':[.5,.5,.1], 'blue_ball':[-.5,2.7,.1]}
        focus = list(positions); duration = 8; film_duration = 12
        intro = 'Start both balls at rest: red inside the yellow region, blue outside.'
    elif n == 11:
        positions = {'red_ball':[-.6,0,.1], 'blue_ball':[0,0,.1], 'green_ball':[.15,1,.1]}
        focus = list(positions); duration = 2
        intro = 'Trigger red–blue contact. The boost applies when the contact ends.'
        push(0, 'PUSH red_ball 0 3', 'Push red toward blue; green is not a participant.')
    elif n == 12:
        positions = {'ball_1':[-.6,0,.1], 'ball_2':[0,0,.1]}
        focus = list(positions); duration = 3.5; film_duration = 12
        intro = 'Two separate contacts. Reposition the same bodies between trials; preserve their colors.'
        push(0, 'PUSH ball_1 0 2.5', 'First contact exchanges the colors; object identities stay fixed.')
        place(1.7, positions, 'Separate and reposition the same objects for a second contact.')
        push(1.72, 'PUSH ball_1 0 2.5', 'The second contact exchanges the colors back.')
    elif n == 13:
        positions = {'red_ball':[-.6,0,.1], 'blue_ball':[0,0,.1]}
        focus = list(positions); duration = 4.8; film_duration = 12
        intro = 'Three separate contacts; reposition between trials without resetting contact history.'
        for count, t in enumerate([0, 1.5, 3], 1):
            if count > 1: place(t, positions, f'Prepare contact {count}; preserve the scene’s event counter.')
            push(t + .02, 'PUSH red_ball 0 2.5', f'Ball–ball contact {count} of 3.')
    elif n == 14:
        positions = {'red_ball':[-1,-.65,.1], 'green_ball':[-1,.65,.1]}
        focus = list(positions); duration = 15.5; film_duration = 12
        intro = 'Launch red, hold it shortly afterwards, and wait for green’s scheduled response.'
        push(0, 'PUSH red_ball 0 3', 'Store red’s post-launch velocity. The echo is due at count 12.')
        events.append({'time':.2,'kind':'hold','object':'red_ball','caption':'Hold red. The scheduled transfer is still pending.'})
    else:
        positions = {'red_ball':[0,-2,.1], 'blue_ball':[1.2,-1,.1]}
        focus = list(positions); duration = 15.5; film_duration = 12
        intro = 'Red’s force starts active. Push blue at count 2, then wait for ten counts.'
        push(2, 'PUSH blue_ball 0 1', 'A nonzero push on blue suppresses red’s extra force until count 12.')
    arrange(world, positions)
    return world, dict(id=number, initial_positions=positions, focus=focus,
                      events=sorted(events,key=lambda e:e['time']), simulation_duration=duration,
                      duration=film_duration, setup=intro)


def capture(number):
    world, spec = demonstration(number)
    frames, measurements = [], []
    events = list(spec['events']); event_index = 0; epoch = 0
    body_ids = {world.model.body(name).id for name in spec['focus']}
    previous_contacts = set(); contact_events = []
    held = set()
    xml = world.model_xml()
    ticks = round(spec['simulation_duration'] / .002)
    for tick in range(ticks + 1):
        now = float(world.data.time)
        while event_index < len(events) and events[event_index]['time'] <= now + .00001:
            event = events[event_index]
            if event['kind'] == 'arrange':
                arrange(world,event['positions']); epoch += 1
            elif event['kind'] == 'hold':
                world.workshop.grasp(world,event['object']); held.add(event['object'])
            else:
                launch(world,event['command'])
            event['actual_time'] = now
            event_index += 1
        touching = contact_pairs(world.model,world.data,body_ids)
        for kind, pairs in [('contact_start',touching-previous_contacts),('contact_end',previous_contacts-touching)]:
            for pair in pairs:
                contact_events.append({'kind':kind,'time':now,'objects':[world.model.body(b).name for b in pair]})
        previous_contacts = touching
        if tick % 10 == 0 or tick == ticks:
            objects = {}
            for name in spec['focus']:
                q,d = world.bodies[name]
                g = world.model.body_geomadr[world.model.body(name).id]
                objects[name] = {'position':world.data.qpos[q:q+3].copy().tolist(),
                    'velocity':world.data.qvel[d:d+3].copy().tolist(),
                    'color':world.model.geom_rgba[g].copy().tolist()}
            record = dict(time=now,epoch=epoch,qpos=world.data.qpos.copy(),qvel=world.data.qvel.copy(),
                          rgba=world.model.geom_rgba.copy(),objects=objects,gravity=world.model.opt.gravity.copy().tolist())
            frames.append(record)
            measurements.append({k:v for k,v in record.items() if k not in ['qpos','qvel','rgba']})
        if tick < ticks: world.step()
    assert np.isfinite(world.data.qpos).all()
    return world, xml, frames, {**spec,'contacts':contact_events,'samples':measurements}


def camera_for(frames, spec):
    positions = np.asarray([o['position'] for f in frames for o in f['objects'].values()])
    n = int(spec['id'])
    azimuth, elevation = (90,-17) if n in [1,3,4,7,13] else (100,-62)
    az,el=np.deg2rad([azimuth,elevation])
    right=np.array([-np.sin(az),np.cos(az),0])
    up=np.array([-np.cos(az)*np.sin(el),-np.sin(az)*np.sin(el),np.cos(el)])
    u,v=positions@right,positions@up
    span=max(1.7,float(np.ptp(v))+.95,(float(np.ptp(u))+1.15)/(960/600))*1.06
    z=float((positions[:,2].min()+positions[:,2].max())/2)
    xy=np.linalg.solve([right[:2],up[:2]],[(u.min()+u.max())/2,(v.min()+v.max())/2-up[2]*z])
    return dict(lookat=[*xy,z],distance=18,azimuth=azimuth,elevation=elevation,
                orthographic=True,vertical_span=span)


class Renderer:
    def __init__(self, xml, world, camera):
        self.model=mujoco.MjModel.from_xml_string(styled(xml,960,600,camera))
        self.data=mujoco.MjData(self.model)
        self.renderer=mujoco.Renderer(self.model,600,960,max_geom=6000)
        self.camera=mujoco.MjvCamera()
        for key in ['lookat','distance','azimuth','elevation']:
            if key=='lookat':self.camera.lookat[:]=camera[key]
            else:setattr(self.camera,key,camera[key])
        self.options=mujoco.MjvOption();self.options.sitegroup[:]=0
        self.dynamic_geoms=[i for i in range(world.model.ngeom) if int(world.model.geom_bodyid[i])>0]

    def render(self, frame, trail):
        self.data.qpos[:]=frame['qpos'];self.data.qvel[:]=frame['qvel'];self.data.time=frame['time']
        self.model.geom_rgba[self.dynamic_geoms]=frame['rgba'][self.dynamic_geoms]
        mujoco.mj_forward(self.model,self.data)
        self.renderer.update_scene(self.data,self.camera,self.options)
        # Trails connect sampled actual body positions, without altering physics.
        for name in frame['objects']:
            track=[f['objects'][name]['position'] for f in trail if f['epoch']==frame['epoch']]
            color=frame['objects'][name]['color'][:3]+[.25]
            for a,b in zip(track[::3],track[3::3]):
                if np.linalg.norm(np.asarray(a)-b)<.008:continue
                geom=self.renderer.scene.geoms[self.renderer.scene.ngeom]
                mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_CAPSULE,np.zeros(3),np.zeros(3),np.eye(3).ravel(),np.asarray(color))
                mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_CAPSULE,.009,np.asarray(a),np.asarray(b))
                self.renderer.scene.ngeom+=1
        linear=self.renderer.render().astype(np.float32)/255
        srgb=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
        return Image.fromarray(np.clip(srgb*255,0,255).astype(np.uint8))

    def close(self):self.renderer.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--simulate-only',action='store_true')
    args=parser.parse_args()
    names,_=paper_scene_names()
    folder=SITE/'assets/videos/physics';folder.mkdir(exist_ok=True)
    evidence=SITE/'downloads/physics-demonstrations';evidence.mkdir(exist_ok=True)
    manifest=[]
    for number in [f'{i:02}' for i in range(1,16)]:
        if args.only and number not in args.only:continue
        start=time.time();world,xml,frames,spec=capture(number)
        print(f"Scene {number} {names[number]}: {len(frames)} samples, {len(spec['contacts'])} contact events",flush=True)
        metadata={**spec,'name':names[number], 'kind':'scripted demonstration in the original scene physics',
            'scene_source':'scenes/base_15.json','scene_source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'scene_program_sha256':hashlib.sha256(json.dumps(SPECS[int(number)-1]['program'],sort_keys=True).encode()).hexdigest(),
            'physics_timestep':.002,'sample_interval':.02,'notes':'No model exploration or grading. Preparation and scripted interventions are recorded. Original laws, object geometry, mass, friction and gravity are preserved. Camera, lighting and trajectory overlays are presentation only.'}
        (evidence/f'scene-{number}.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        if args.simulate_only:continue
        cam=camera_for(frames,spec);renderer=Renderer(xml,world,cam)
        dest=folder/f'scene-{number}.mp4';temporary=dest.with_name(dest.stem+'.partial.mp4')
        fps=24
        process=subprocess.Popen([args.ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','960x600','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],stdin=subprocess.PIPE)
        times=np.asarray([f['time'] for f in frames])
        font=ImageFont.truetype(str(FONT),14);small=ImageFont.truetype(str(FONT),10)
        try:
            for index,t in enumerate(np.linspace(0,spec['simulation_duration'],spec['duration']*fps)):
                i=int(np.abs(times-t).argmin());f=frames[i]
                im=renderer.render(f,frames[max(0,i-80):i+1]);draw=ImageDraw.Draw(im,'RGBA')
                draw.rounded_rectangle((18,17,390,51),radius=5,fill=(248,251,245,230))
                draw.text((30,25),f"{number}  {names[number]}",font=font,fill='#355943')
                draw.rounded_rectangle((744,17,942,51),radius=5,fill=(248,251,245,230))
                draw.text((757,25),f"t = {f['time']:05.2f} counts",font=font,fill='#355943')
                draw.rounded_rectangle((18,563,942,589),radius=4,fill=(248,251,245,228))
                draw.text((30,570),'ORIGINAL SCENE PHYSICS  /  SCRIPTED DEMONSTRATION',font=small,fill='#55705e')
                draw.text((708,570),f"Playback: {spec['simulation_duration']/spec['duration']:.2f}x simulation time",font=small,fill='#55705e')
                if index==0:im.save(SITE/f'assets/images/physics-{number}.webp',quality=92)
                process.stdin.write(np.asarray(im).tobytes())
            process.stdin.close();assert process.wait()==0
            temporary.replace(dest)
        finally:
            if process.poll() is None:process.kill();process.wait()
            renderer.close()
        timeline=[{'time':round(f['time'],3),'objects':f['objects'],'gravity':f['gravity']} for f in frames[::5]]
        manifest.append({k:v for k,v in metadata.items() if k!='samples'}|{
            'video':f'assets/videos/physics/scene-{number}.mp4','poster':f'assets/images/physics-{number}.webp',
            'record':f'downloads/physics-demonstrations/scene-{number}.json','camera':cam,'timeline':timeline})
        print(f'Rendered {number}: {spec["duration"]}s in {time.time()-start:.1f}s',flush=True)
    if not args.simulate_only:
        target=SITE/'data/physics.js'
        if args.only and target.exists():
            old=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
            replaced={entry['id'] for entry in manifest}
            manifest+= [entry for entry in old if entry['id'] not in replaced]
        manifest.sort(key=lambda entry:entry['id'])
        target.write_text('window.PHYSICS_DEMOS = '+json.dumps(manifest,ensure_ascii=False)+';\n')
    print('Physics demonstration pass complete.',flush=True)


if __name__=='__main__':main()
