"""60 fps films from native 500 Hz states, with continuous contact experiments."""
import argparse,concurrent.futures,copy,hashlib,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
import render_oracle_demos as native
from render_clear_scenes import ROOM_BOUNDS,room_camera
from oracle_catalog import catalog
from compose_plain_demos import state as plain_state

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-smooth-scenes')
LEGACY=Path('/tmp/longchang-shared-room')
FPS=60

def write(path,data,prefix=''):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(prefix+json.dumps(data,separators=(',',':'))+(';' if prefix else '')+'\n');temp.replace(path)

def prepare(id):
    world,xml,samples,references,spec=native.record(id,sample_stride=1)
    folder=CACHE/id;folder.mkdir(parents=True,exist_ok=True)
    oracle=catalog()[id]
    # A steady playback speed avoids the old mid-flight freezes and speed jumps.
    mapping=[[0,0],[spec['duration'],spec['simulation_duration']]]
    times=np.array([s['time'] for s in samples]);resets=[]
    for a,b in zip(samples,samples[1:]):
        if a['epoch']!=b['epoch']:resets.append(b['time']/spec['simulation_duration']*spec['duration'])
    film=[];seen={}
    for i in range(round(spec['duration']*FPS)):
        video_t=i/FPS;t=video_t/spec['duration']*spec['simulation_duration']
        index=int(np.abs(times-t).argmin());frame=copy.deepcopy(samples[index])
        frame={k:v for k,v in frame.items() if k not in ['qpos','qvel','rgba']}
        fade=max([max(0,min(1,(.3-abs(video_t-r))/.18)) for r in resets] or [0])
        frame.update(native_index=index,fade=fade)
        frame['annotation']=native.explanation(id,frame,spec)
        if id=='12':
            count=sum(e['time']<=frame['time'] for e in spec['oracle_events'] if e['kind']=='color_swap')
            frame['simple_state']=['','First touch','Second touch'][min(count,2)]
        else:frame['simple_state']=plain_state(id,frame)
        if fade>0:frame['simple_state']=''
        if index in seen and fade==0 and film[seen[index]]['fade']==0:frame['reuse']=seen[index]
        else:seen[index]=i
        film.append(frame)
    job=json.loads((LEGACY/id/'job.json').read_text())
    job.update(output=str(folder),display_bounds=ROOM_BOUNDS,camera=room_camera(),
               shared_backgrounds=str(LEGACY/'backgrounds'),reuse_jobs=[str(LEGACY/id/'job.json')],
               fps=FPS,frames=[{k:v for k,v in f.items() if k in ['time','objects','epoch','native_index','reuse','fade']} for f in film])
    write(folder/'job.json',job)
    public=lambda frames:[{k:v for k,v in f.items() if k not in ['qpos','qvel','rgba']} for f in frames]
    record=dict(**spec,name=oracle['name'],oracle=oracle,kind='controlled oracle demonstration',
                scene_source='scenes/base_15.json',scene_source_sha256=hashlib.sha256(native.SOURCE.read_bytes()).hexdigest(),
                physics_timestep=.002,sample_interval=.002,reference='Identical initial preparation and impulses, with the altered program disabled.',
                samples=public(samples),reference_samples=public(references))
    write(folder/'record.json',record)
    entry={k:v for k,v in record.items() if k not in ['samples','reference_samples']}
    entry.update(id=id,fps=FPS,time_map=mapping,chapters=[],preview_time=0,
                 record=f'downloads/smooth-demonstrations/scene-{id}.json',
                 plot=native.plot_data(id,samples[::5],references[::5]),timeline=film,
                 presentation='clear',transitions=resets,continuous=not resets,
                 render=dict(engine='Blender Cycles',samples=64,frame_rate=FPS,physics_rate=500,room='data/shared-room.json'))
    write(folder/'entry.json',entry)
    print(f'PREPARED {id}: {len(samples)} native states, {len(film)} frames, {len(resets)} explicit trial transitions',flush=True)

def render(id,ffmpeg):
    folder=CACHE/id;job=json.loads((folder/'job.json').read_text());entry=json.loads((folder/'entry.json').read_text())
    with (folder/'render.log').open('w') as log:
        subprocess.run(['/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/blender_clear_scenes.py'),str(folder/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
    video=SITE/f'assets/videos/smooth/scene-{id}.mp4';video.parent.mkdir(exist_ok=True)
    temp=video.with_name(video.stem+'.partial.mp4')
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-framerate',str(FPS),'-i',str(folder/'frames/%05d.png'),'-c:v','libx264','-preset','fast','-crf','17','-g','60','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True);temp.replace(video)
    poster=SITE/f'assets/images/smooth-{id}.webp';Image.open(folder/'frames/00000.png').save(poster,quality=96,method=6)
    records=SITE/'downloads/smooth-demonstrations';records.mkdir(exist_ok=True)
    (records/f'scene-{id}.json').write_bytes((folder/'record.json').read_bytes())
    signature=json.loads((folder/'room-signature.json').read_text())
    entry.update(video=str(video.relative_to(SITE)),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)),
                 video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),room_signature=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest())
    print(f'SMOOTH {id}: 60 fps, original physics, no frozen motion',flush=True)
    return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=6);parser.add_argument('--only',nargs='*');args=parser.parse_args()
    ids=args.only or [f'{i:02}' for i in range(1,16)]
    for id in ids:prepare(id) # MuJoCo callback registration is process-global.
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:updated=list(pool.map(lambda id:render(id,args.ffmpeg),ids))
    assert len({e['room_signature'] for e in updated})==1
    target=SITE/'data/physics.js';current=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'));new={e['id']:e for e in updated}
    write(target,[new.get(e['id'],e) for e in current],prefix='window.PHYSICS_DEMOS = ')
    print('Smooth films published.',flush=True)

if __name__=='__main__':main()
