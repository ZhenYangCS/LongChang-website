"""Six experiments that show the trigger and a visible consequence of the rule."""
import argparse,concurrent.futures,copy,hashlib,json,math,shutil
from pathlib import Path
import numpy as np
from PIL import Image
import build_smooth_demos as smooth
import build_detail_views as detail
import render_oracle_demos as native
from render_clear_scenes import ROOM_BOUNDS,room_camera
from oracle_catalog import catalog

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-explained-scenes')
IDS=['05','09','10','11','14','15']

def plan(id):
    world,spec=native.demonstration(id);positions=copy.deepcopy(spec['initial_positions'])
    def push(time,command,caption):return dict(time=time,kind='launch',command=command,caption=caption)
    if id=='05':
        spec.update(simulation_duration=1.2,duration=16,setup='Matched ordinary-physics reference for the fast red launch; the slow blue launch is a control.')
    elif id=='09':
        positions.update(red_ball=[-.7,0,.1],blue_ball=[-.7,2.6,.1])
        spec.update(simulation_duration=1.65,duration=16,focus=['red_ball'],events=[push(0,'PUSH red_ball 0 10','One continuous crossing: enter gray, then leave it.')],setup='One continuous pass through the entire gray footprint, with no repositioning or trial fades.')
    elif id=='10':
        positions.update(red_ball=[-2.15,.8,.8],blue_ball=[-2.15,2.6,.8])
        angle=math.degrees(math.atan2(4.5,2.5));force=math.hypot(4.5,2.5)
        spec.update(simulation_duration=1.,duration=16,events=[push(0,f'THROW {name} 0 {angle} {force}','Identical launches: forward speed 2.5, upward speed 4.5.') for name in ['red_ball','blue_ball']],setup='Matched airborne launches. Red enters yellow; blue remains outside. The film ends before either ball lands.')
    elif id=='11':
        positions.update(red_ball=[-.7,0,.1],blue_ball=[0,0,.1],green_ball=[0,1.7,.1])
        spec.update(simulation_duration=1.5,duration=16,events=[push(0,'PUSH red_ball 0 6','The same collision is compared with ordinary physics.')],setup='A stronger but legal push makes the separation boost and the ordinary-physics comparison clearly visible.')
    elif id=='14':
        spec.update(simulation_duration=14.5,duration=32,events=[push(0,'PUSH red_ball 0 3','Store the red launch velocity.'),dict(time=.8,kind='hold',object='red_ball',caption='Hold red without cancelling the pending copy.')],setup='Push red, hold it, and show the full 12-second countdown before green receives the stored velocity.')
    elif id=='15':
        spec.update(simulation_duration=20.,duration=32,events=[push(2,'PUSH blue_ball 0 1','Pushing blue pauses the northward force.'),push(6,'PUSH blue_ball 0 1','Pushing blue again restarts the ten-second pause.')],setup='Show the force arrow, both real pushes, the reset countdown, and the return of the northward force.')
    spec['initial_positions']=positions;native.arrange(world,positions)
    definition=copy.deepcopy(native.SPECS[int(id)-1]);definition['program']={}
    reference=native.World(native.load_scene(definition));reference._motion=None;native.arrange(reference,positions)
    # Use the original Workshop force controller without advancing hidden time
    # during a GRASP call. Both worlds receive the same hand operation.
    def hold(current,name):
        current.workshop.holds[name]={'target':current.data.xpos[current.model.body(name).id].copy()}
    for current in [world,reference]:current.workshop.grasp=hold
    return world,reference,spec

def proof(id,entry,record):
    info={
        '05':dict(measure='Speed',labels=[['Red','#b3594b','solid'],['Ordinary','#9a827b','dashed']]),
        '09':dict(measure='Speed',labels=[['Red','#b3594b','solid']]),
        '10':dict(measure='Forward speed',labels=[['Red','#b3594b','solid'],['Blue','#416f9e','solid']]),
        '11':dict(measure='Speed',labels=[['Blue','#416f9e','solid'],['Ordinary','#8496a6','dashed']]),
        '14':dict(measure='',labels=[['','#416f9e','none']],timer=True),
        '15':dict(measure='',labels=[['','#527b64','none']],timer=True),
    }[id]
    rows=[];last=None;norm=lambda o:float(np.linalg.norm(o['velocity']))
    for i,frame in enumerate(entry['timeline']):
        sample=record['samples'][frame['native_index']];ref=record['reference_samples'][frame['native_index']];t=sample['time'];objects=sample['objects'];ratio=-1
        if id=='05':
            active=np.linalg.norm(sample['oracle']['forces'].get('red_ball',[0,0,0]))>.001
            label='Extra brake active' if active else 'Below 2.5 · brake off';values=[f"{norm(objects['red_ball']):.1f}",f"{norm(ref['objects']['red_ball']):.1f}"]
        elif id=='09':
            events=[e for e in record['oracle_events'] if e['time']<=t]
            label='Approach gray' if not events else 'Enter gray · ×0.4' if len(events)==1 else 'Leave gray · ×2.5'
            values=[f"{norm(objects['red_ball']):.1f}"]
        elif id=='10':
            label='Identical launches' if objects['red_ball']['position'][0]<-2 else 'Red gains speed inside yellow'
            values=[f"{objects[name]['velocity'][0]:.1f}" for name in ['red_ball','blue_ball']]
        elif id=='11':
            boosted=any(e['time']<=t for e in record['oracle_events'] if e['kind']=='separation_boost')
            label='Same incoming collision' if not boosted else 'Contact ends · velocity ×1.8'
            values=[f"{norm(objects['blue_ball']):.1f}",f"{norm(ref['objects']['blue_ball']):.1f}"]
        elif id=='14':
            label='Push red' if t<.8 else 'Red is held' if t<12 else 'Green receives the copy'
            values=['Launch → 3.0' if t<.8 else f'Copy in {max(0,12-t):.1f} s' if t<12 else 'Copied velocity → 3.0']
            ratio=round(min(1,t/12)*100)
        else:
            due=sample['oracle']['quiet_until'];active=t>=due
            label='Northward pull ON' if active else 'Northward pull OFF'
            if 2<=t<2.8:label='Push blue · pull pauses'
            if 6<=t<6.8:label='Push blue again · timer resets'
            if 16<=t<17.2:label='Northward pull returns'
            values=['' if active else f'Resumes in {max(0,due-t):.1f} s'];ratio=100 if active else round((1-(due-t)/10)*100)
        current=[label,values,ratio]
        if current!=last:rows.append([i,*current]);last=current
    return dict(**info,fps=entry['fps'],rows=rows)

def prepare(id):
    smooth.CACHE=CACHE/'native';native.plan=plan;smooth.prepare(id)
    folder=smooth.CACHE/id;job=json.loads((folder/'job.json').read_text());entry=json.loads((folder/'entry.json').read_text());record=json.loads((folder/'record.json').read_text())
    job.update(story=id,minimum_focus_width=320,focus_fixtures=id in ['09','10'],enclosed=True,samples=128)
    if id in ['05','11']:
        job['reference_names']=['red_ball'] if id=='05' else ['red_ball','blue_ball']
        for frame in job['frames']:frame['reference_objects']=record['reference_samples'][frame['native_index']]['objects']
    job['launch_events']=[e for e in record['events'] if e['kind']=='launch']
    job['rule_events']=record['oracle_events'];job['film_duration']=entry['duration'];job['simulation_duration']=entry['simulation_duration']
    for frame in job['frames']:frame['oracle']=record['samples'][frame['native_index']]['oracle']
    entry['proof']=proof(id,entry,record);entry['record']=f'downloads/explained-demonstrations/scene-{id}.json'
    (SITE/entry['record']).parent.mkdir(exist_ok=True);(SITE/entry['record']).write_bytes((folder/'record.json').read_bytes())
    detail.write(folder/'job.json',job);detail.write(folder/'entry.json',entry)
    return entry

def render(entry,ffmpeg):
    id=entry['id'];job=json.loads((CACHE/'native'/id/'job.json').read_text());crop,camera=detail.focus_crop(job);entry.update(detail_crop=crop,detail_camera=camera,detail_dimensions=[1600,800])
    sprites={name:Image.open(Path('/tmp/longchang-unified-scenes/sprites')/f'{name}.png').convert('RGBA') for name in ['red','blue','green','gray']}
    for mode in ['room','detail']:
        current=copy.deepcopy(job);folder=CACHE/id/mode;folder.mkdir(parents=True,exist_ok=True)
        current.update(camera=room_camera() if mode=='room' else camera,width=1440 if mode=='room' else 1600,height=960 if mode=='room' else 800,output=str(folder))
        detail.write(folder/'job.json',current)
        if mode=='room':shutil.copyfile(Path('/tmp/longchang-unified-scenes')/id/'room/background.png',folder/'background.png')
        background=detail.flat(detail.asset(current,folder));video=SITE/f'assets/videos/explained-{mode}/scene-{id}.mp4';poster=SITE/f'assets/images/explained-{mode}-{id}.webp'
        detail.encode(current,background,sprites,video,ffmpeg,poster)
        if mode=='room':
            entry.update(video=str(video.relative_to(SITE)),video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)))
            full=SITE/f'assets/images/explained-background-{id}.webp';background.convert('RGB').save(full,quality=94,method=6);entry['room_background']=str(full.relative_to(SITE))
            small=SITE/f'assets/images/explained-context-{id}.webp';background.convert('RGB').resize((360,240),Image.Resampling.LANCZOS).save(small,quality=85);entry['context_poster']=str(small.relative_to(SITE))
            signature=json.loads((folder/'room-signature.json').read_text());entry['room_signature']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        else:entry.update(detail_video=str(video.relative_to(SITE)),detail_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),detail_poster=str(poster.relative_to(SITE)))
    entry.update(render_revision='explained-v1',render=dict(engine='Blender Cycles with cached spherical lighting',samples=128,frame_rate=60,physics_rate=500,room='data/shared-room.json',enclosed=True),detail_render='Native poses with measured velocity/force cues and explicit ordinary-physics reference paths.')
    print('EXPLAINED',id,flush=True);return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=6);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    entries=[prepare(id) for id in IDS]
    if args.prepare:return
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:updates=list(pool.map(lambda e:render(e,args.ffmpeg),entries))
    target=SITE/'data/physics.js';current=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'));changes={e['id']:e for e in updates};result=[{**e,**changes[e['id']]} if e['id'] in changes else e for e in current]
    assert len({e['room_signature'] for e in result})==1
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(result,separators=(',',':'))+';\n');temp.replace(target)
    print('Six complete causal demonstrations published.',flush=True)

if __name__=='__main__':main()
