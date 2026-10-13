"""Close every displayed movie room without changing any recorded physics state."""
import argparse,concurrent.futures,copy,hashlib,json
from pathlib import Path
from PIL import Image
import build_detail_views as detail
from launch_cues import add_launch_cues
from render_clear_scenes import room_camera

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-sealed-scenes')

def render(entry,ffmpeg):
    id=entry['id'];job=json.loads((detail.CACHE/id/'job.json').read_text());job['enclosed']=True
    sprites={name:Image.open(detail.CACHE/'sprites'/f'{name}.png').convert('RGBA') for name in ['red','blue','green','gray']}
    for mode in ['room','detail']:
        current=copy.deepcopy(job);folder=CACHE/id/mode;folder.mkdir(parents=True,exist_ok=True)
        if mode=='room':current.update(camera=room_camera(),width=1440,height=960)
        current['output']=str(folder);detail.write(folder/'job.json',current)
        background=detail.flat(detail.asset(current,folder))
        video=SITE/f'assets/videos/sealed-{mode}/scene-{id}.mp4';poster=SITE/f'assets/images/sealed-{mode}-{id}.webp'
        detail.encode(current,background,sprites,video,ffmpeg,poster)
        if id in ['12','13']:video=add_launch_cues(ffmpeg,video,video.with_name(video.stem+'-cued.mp4'),entry)
        if mode=='room':
            entry.update(video=str(video.relative_to(SITE)),video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)))
            context=SITE/f'assets/images/sealed-context-{id}.webp';background.convert('RGB').resize((360,240),Image.Resampling.LANCZOS).save(context,quality=85)
            signature=json.loads((folder/'room-signature.json').read_text())
            entry.update(context_poster=str(context.relative_to(SITE)),room_signature=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest())
        else:entry.update(detail_video=str(video.relative_to(SITE)),detail_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),detail_poster=str(poster.relative_to(SITE)))
    entry['render_revision']='sealed-v1'
    print('SEALED',id,flush=True);return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=6);args=parser.parse_args()
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:updated=list(pool.map(lambda e:render(e,args.ffmpeg),entries))
    assert len({e['room_signature'] for e in updated})==1
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(updated,separators=(',',':'))+';\n');temp.replace(target)
    shared=json.loads((SITE/'data/shared-room.json').read_text());shared.update(enclosed=True,render_signature=updated[0]['room_signature']);detail.write(SITE/'data/shared-room.json',shared)
    print('All 15 rooms have a glass roof; every trajectory, radius and time map is preserved.',flush=True)

if __name__=='__main__':main()
