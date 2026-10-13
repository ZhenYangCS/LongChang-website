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
CACHE=Path('/tmp/longchang-clear-scenes')
SOURCE=Path('/tmp/longchang-oracle-studio/production')


def prepare(number):
    original=json.loads((SOURCE/number/'studio-job.json').read_text())
    job=copy.deepcopy(original)
    x0,x1,y0,y1,z=job['display_bounds'];cx=(x0+x1)/2;cy=(y0+y1)/2
    # Same proportions and framing for every enclosure, without rescaling bodies.
    width=max(x1-x0,(y1-y0)*1.5,z/.38)
    depth=width/1.5;height=width*.38
    bounds=[cx-width/2,cx+width/2,cy-depth/2,cy+depth/2,height]
    direction=np.array([7.,-10.,8.]);direction/=np.linalg.norm(direction)
    forward=-direction;right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    corners=np.array([[x,y,z] for x in bounds[:2] for y in bounds[2:4] for z in [-.18,height]])
    u,v=corners@right,corners@up
    span=max(np.ptp(v),np.ptp(u)/1.5)*1.12
    look=right*((min(u)+max(u))/2)+up*((min(v)+max(v))/2)
    job.update(width=1440,height=960,samples=64,threads=10,display_bounds=bounds,
               camera=dict(position=(look+direction*30).tolist(),forward=forward.tolist(),right=right.tolist(),up=up.tolist(),span=float(span)),
               output=str(CACHE/number))
    folder=CACHE/number;folder.mkdir(parents=True,exist_ok=True)
    (folder/'job.json').write_text(json.dumps(job))
    return job


def render(number,ffmpeg):
    job=prepare(number);folder=CACHE/number
    with (folder/'render.log').open('w') as log:
        subprocess.run(['/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/blender_clear_scenes.py'),str(folder/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
    entry=json.loads((SOURCE/number/'composition.json').read_text())['entry']
    out=SITE/f'assets/videos/clear/scene-{number}.mp4';out.parent.mkdir(exist_ok=True)
    temp=out.with_name(out.stem+'.partial.mp4')
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-framerate',str(entry['fps']),'-i',str(folder/'frames/%05d.png'),'-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
    temp.replace(out)
    index=round(entry['preview_time']*entry['fps'])
    poster=SITE/f'assets/images/clear-{number}.webp'
    Image.open(folder/f'frames/{index:05}.png').save(poster,quality=96,method=6)
    print(f'CLEAR {number}: 1440 × 960, consistent enclosure, Cycles 256-sample room / 64-sample motion',flush=True)
    return number,dict(video=str(out.relative_to(SITE)),poster=str(poster.relative_to(SITE)),studio_poster=str(poster.relative_to(SITE)),presentation='clear',video_sha256=hashlib.sha256(out.read_bytes()).hexdigest())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--only',nargs='*');parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();ids=args.only or [f'{i:02}' for i in range(1,16)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=dict(pool.map(lambda n:render(n,args.ffmpeg),ids))
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    for entry in entries:
        if entry['id'] in results:entry.update(results[entry['id']])
    target.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,separators=(',',':'))+';\n')
    print('Clear scene films published.',flush=True)


if __name__=='__main__':main()
