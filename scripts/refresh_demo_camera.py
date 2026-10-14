"""Reframe existing recorded Demo states without rerunning any physics.

Reuses the prepared unified/explained frame jobs; publishes media and camera
metadata together after every selected scene has finished rendering.
"""
import argparse
import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image
import build_detail_views as detail
from launch_cues import add_launch_cues
from render_clear_scenes import room_camera, ROOM_BOUNDS

SITE = Path(__file__).resolve().parents[1]
CACHE = Path('/tmp/longchang-front-view')
REVISION = 'front-v1'


def source_job(entry):
    source = Path('/tmp/longchang-explained-scenes' if entry.get('render_revision') == 'explained-v1' else '/tmp/longchang-unified-scenes')
    return json.loads((source/entry['id']/'detail/job.json').read_text())


def render(entry, ffmpeg, sample=False):
    entry = copy.deepcopy(entry)
    key = entry['id']
    job = source_job(entry)
    job['focus_fixtures'] = True
    crop, camera = detail.focus_crop(job)
    entry.update(detail_crop=crop, detail_camera=camera, detail_dimensions=[1600,800], camera_revision=REVISION)
    sprites = {name:Image.open(CACHE/'sprites'/f'{name}.png').convert('RGBA') for name in ['red','blue','green','gray']}
    for mode in (['detail'] if sample else ['room','detail']):
        folder = CACHE/key/mode
        current = copy.deepcopy(job)
        current.update(camera=room_camera() if mode == 'room' else camera, width=1440 if mode == 'room' else 1600,
                       height=960 if mode == 'room' else 800, output=str(folder), samples=128)
        detail.write(folder/'job.json', current)
        background = detail.flat(detail.asset(current, folder))
        if sample:
            for fraction in [0,.45,.8]:
                detail.compose(current, background, sprites, round((len(job['frames'])-1)*fraction)).save(folder/f'sample-{fraction}.png')
            print('SAMPLE', key, flush=True)
            continue
        # Build away from the served files. The manifest is updated only after
        # every movie and poster is complete.
        video = folder/'scene.mp4'
        poster = folder/'poster.webp'
        detail.encode(current, background, sprites, video, ffmpeg, poster)
        if key in ['12','13']:
            video = add_launch_cues(ffmpeg, video, folder/'cued.mp4', entry)
        prefix = 'video' if mode == 'room' else 'detail_video'
        entry[prefix] = f'assets/videos/front-{mode}/scene-{key}.mp4'
        entry[prefix+'_sha256'] = hashlib.sha256(video.read_bytes()).hexdigest()
        entry['poster' if mode == 'room' else 'detail_poster'] = f'assets/images/front-{mode}-{key}.webp'
        if mode == 'room':
            entry['studio_poster'] = entry['poster']
            entry['context_poster'] = f'assets/images/front-context-{key}.webp'
            entry['room_background'] = f'assets/images/front-background-{key}.webp'
            background.convert('RGB').resize((360,240),Image.Resampling.LANCZOS).save(folder/'context.webp',quality=85)
            background.convert('RGB').save(folder/'background.webp',quality=94,method=6)
            signature = json.loads((folder/'room-signature.json').read_text())
            entry['room_signature'] = hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        print('RENDERED', key, mode, flush=True)
    detail.write(CACHE/key/'entry.json', entry)
    return entry


def publish(entries):
    import shutil
    for entry in entries:
        key = entry['id']
        for mode in ['room','detail']:
            folder = CACHE/key/mode
            prefix = 'video' if mode == 'room' else 'detail_video'
            source = folder/('cued.mp4' if key in ['12','13'] else 'scene.mp4')
            target = SITE/entry[prefix]
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            shutil.copyfile(folder/'poster.webp',SITE/entry['poster' if mode == 'room' else 'detail_poster'])
            if mode == 'room':
                shutil.copyfile(folder/'context.webp',SITE/entry['context_poster'])
                shutil.copyfile(folder/'background.webp',SITE/entry['room_background'])
    # Merge onto current metadata, preserving independent page/data edits.
    path = SITE/'data/physics.js'
    current = json.loads(path.read_text().split('=',1)[1].rstrip(';\n'))
    changes = {entry['id']:entry for entry in entries}
    fields = ['video','video_sha256','poster','studio_poster','detail_video','detail_video_sha256',
              'detail_poster','detail_crop','detail_camera','detail_dimensions','context_poster',
              'room_background','room_signature','camera_revision']
    for entry in current:
        if entry['id'] in changes:
            entry.update({key:changes[entry['id']][key] for key in fields})
    from prepare_scene_index import write, main as index
    write(path,'window.PHYSICS_DEMOS = '+json.dumps(current,separators=(',',':'))+';\n')
    if len(changes) == 15:
        assert len({entry['room_signature'] for entry in current}) == 1
        detail.write(SITE/'data/shared-room.json',dict(bounds=ROOM_BOUNDS,camera=room_camera(),dimensions=[12,12,12],
                     enclosed=True,render_signature=current[0]['room_signature']))
        for path in (SITE/'data/interactive-scenes').glob('*.json'):
            config = json.loads(path.read_text()); config['camera'] = room_camera(); detail.write(path, config)
    index()
    print('PUBLISHED: recorded trajectories and timing preserved; all new camera assets ready.',flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--sample',action='store_true')
    parser.add_argument('--publish',action='store_true')
    args = parser.parse_args()
    entries = json.loads((SITE/'data/physics.js').read_text().split('=',1)[1].rstrip(';\n'))
    entries = [entry for entry in entries if not args.only or entry['id'] in args.only]
    if args.publish:
        publish([json.loads((CACHE/entry['id']/'entry.json').read_text()) for entry in entries]); return
    sprites = source_job(entries[0])
    sprites.update(camera=room_camera(),sprites=True,radii={'sprite':.1},fixtures=[],samples=128)
    detail.asset(sprites,CACHE/'sprites')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda entry:render(entry,args.ffmpeg,args.sample),entries))


if __name__ == '__main__':
    main()
