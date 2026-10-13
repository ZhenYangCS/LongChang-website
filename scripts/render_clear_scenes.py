"""Render a consistent glass enclosure and sharp 1440p scene films.

Static Cycles lighting is rendered once; per-frame Cycles regions include
the balls and their shadows. All object poses come from the existing records.
"""
import argparse
import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-shared-room')
SOURCE=Path('/tmp/longchang-oracle-studio/production')

# One actual room, not scene-dependent normalization. Camera, walls, plinth,
# tile scale and lighting are identical in all fifteen films.
ROOM_BOUNDS=[-6.,6.,-6.,6.,12.]


def room_camera():
    direction=np.array([7.,-10.,8.]);direction/=np.linalg.norm(direction)
    forward=-direction;right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    corners=np.array([[x,y,z] for x in ROOM_BOUNDS[:2] for y in ROOM_BOUNDS[2:4] for z in [-.18,ROOM_BOUNDS[4]]])
    u,v=corners@right,corners@up
    span=max(np.ptp(v),np.ptp(u)/1.5)*1.09
    look=right*((min(u)+max(u))/2)+up*((min(v)+max(v))/2)
    return dict(position=(look+direction*30).tolist(),forward=forward.tolist(),right=right.tolist(),up=up.tolist(),span=float(span))


def prepare(number):
    original=json.loads((SOURCE/number/'studio-job.json').read_text())
    job=copy.deepcopy(original)
    job.update(width=1440,height=960,samples=64,threads=10,display_bounds=ROOM_BOUNDS,
               camera=room_camera(),shared_backgrounds=str(CACHE/'backgrounds'),output=str(CACHE/number))
    folder=CACHE/number;folder.mkdir(parents=True,exist_ok=True)
    (folder/'job.json').write_text(json.dumps(job))
    return job


def render(number,ffmpeg):
    job=prepare(number);folder=CACHE/number
    with (folder/'render.log').open('w') as log:
        subprocess.run(['/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/blender_clear_scenes.py'),str(folder/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
    entry=json.loads((SOURCE/number/'composition.json').read_text())['entry']
    out=SITE/f'assets/videos/shared-room/scene-{number}.mp4';out.parent.mkdir(exist_ok=True)
    temp=out.with_name(out.stem+'.partial.mp4')
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-framerate',str(entry['fps']),'-i',str(folder/'frames/%05d.png'),'-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
    temp.replace(out)
    index=round(entry['preview_time']*entry['fps'])
    poster=SITE/f'assets/images/shared-room-{number}.webp'
    Image.open(folder/f'frames/{index:05}.png').save(poster,quality=96,method=6)
    signature=json.loads((folder/'room-signature.json').read_text())
    print(f'READY {number}: one fixed room, 1440 × 960',flush=True)
    return number,dict(video=str(out.relative_to(SITE)),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)),presentation='clear',room_signature=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest(),video_sha256=hashlib.sha256(out.read_bytes()).hexdigest())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--only',nargs='*');parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();ids=args.only or [f'{i:02}' for i in range(1,16)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=dict(pool.map(lambda n:render(n,args.ffmpeg),ids))
    assert len({item['room_signature'] for item in results.values()})==1,'Rendered room/camera/light geometry differs between scenes'
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    for entry in entries:
        if entry['id'] in results:entry.update(results[entry['id']])
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,separators=(',',':'))+';\n');temp.replace(target)
    (SITE/'data/shared-room.json').write_text(json.dumps(dict(bounds=ROOM_BOUNDS,camera=room_camera(),render_signature=next(iter(results.values()))['room_signature'],dimensions=[9,7.2,2.8]),indent=2)+'\n')
    print('All films published with identical room geometry, camera and lighting.',flush=True)


if __name__=='__main__':main()
