"""Close every displayed movie room without changing any recorded physics state."""
import argparse,concurrent.futures,copy,hashlib,json
from pathlib import Path
from PIL import Image
import build_detail_views as detail
from launch_cues import add_launch_cues
from render_clear_scenes import room_camera,ROOM_BOUNDS

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-unified-scenes')

def render(entry,ffmpeg):
    id=entry['id'];job=json.loads((detail.CACHE/id/'job.json').read_text());job.update(enclosed=True,display_bounds=ROOM_BOUNDS,samples=128)
    crop,camera=detail.focus_crop(job);job['camera']=camera
    entry.update(detail_crop=crop,detail_camera=camera)
    sprites={name:Image.open(CACHE/'sprites'/f'{name}.png').convert('RGBA') for name in ['red','blue','green','gray']}
    for mode in ['room','detail']:
        current=copy.deepcopy(job);folder=CACHE/id/mode;folder.mkdir(parents=True,exist_ok=True)
        if mode=='room':current.update(camera=room_camera(),width=1440,height=960)
        current['output']=str(folder);detail.write(folder/'job.json',current)
        background=detail.flat(detail.asset(current,folder))
        suffix='-clean' if id=='10' else ''
        video=SITE/f'assets/videos/unified-{mode}/scene-{id}{suffix}.mp4';poster=SITE/f'assets/images/unified-{mode}-{id}{suffix}.webp'
        detail.encode(current,background,sprites,video,ffmpeg,poster)
        if id in ['12','13']:video=add_launch_cues(ffmpeg,video,video.with_name(video.stem+'-cued.mp4'),entry)
        if mode=='room':
            entry.update(video=str(video.relative_to(SITE)),video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)))
            context=SITE/f'assets/images/unified-context-{id}.webp';background.convert('RGB').resize((360,240),Image.Resampling.LANCZOS).save(context,quality=85)
            full=SITE/f'assets/images/unified-background-{id}.webp';background.convert('RGB').save(full,quality=94,method=6);entry['room_background']=str(full.relative_to(SITE))
            signature=json.loads((folder/'room-signature.json').read_text())
            entry.update(context_poster=str(context.relative_to(SITE)),room_signature=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest())
        else:entry.update(detail_video=str(video.relative_to(SITE)),detail_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),detail_poster=str(poster.relative_to(SITE)))
    entry['render_revision']='unified-v1'
    entry['render']=dict(engine='Blender Cycles with cached spherical lighting',samples=128,frame_rate=60,physics_rate=500,room='data/shared-room.json',enclosed=True)
    print('SEALED',id,flush=True);return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=6);parser.add_argument('--only',nargs='*');args=parser.parse_args()
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    job=json.loads((detail.CACHE/'01/job.json').read_text());job.update(enclosed=True,display_bounds=ROOM_BOUNDS,camera=room_camera(),sprites=True,radii={'sprite':.1},fixtures=[],samples=128)
    detail.asset(job,CACHE/'sprites')
    chosen=[e for e in entries if not args.only or e['id'] in args.only]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:rendered=list(pool.map(lambda e:render(e,args.ffmpeg),chosen))
    changes={e['id']:e for e in rendered};updated=[changes.get(e['id'],e) for e in entries]
    assert len({e['room_signature'] for e in updated})==1
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(updated,separators=(',',':'))+';\n');temp.replace(target)
    shared=dict(bounds=ROOM_BOUNDS,camera=room_camera(),dimensions=[12,12,12],enclosed=True,render_signature=updated[0]['room_signature']);detail.write(SITE/'data/shared-room.json',shared)
    print('All 15 rooms have a glass roof; every trajectory, radius and time map is preserved.',flush=True)

if __name__=='__main__':main()
