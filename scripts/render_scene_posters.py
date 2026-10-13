"""Render clean high-resolution stills for the fifteen-scene showcase."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
from PIL import Image

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-oracle-studio/production')
OUTPUT=Path('/tmp/longchang-scene-posters')


def render(id):
    folder=OUTPUT/id;folder.mkdir(parents=True,exist_ok=True)
    original=json.loads((CACHE/id/'studio-job.json').read_text())
    entry=json.loads((CACHE/id/'composition.json').read_text())['entry']
    frame=round(entry['preview_time']*entry['fps'])
    job=original.copy();job.update(width=1800,height=1300,samples=192,threads=16,output=str(folder))
    pose=original['frames'][frame].copy();pose.pop('reuse',None);job['frames']=[pose]
    path=folder/'job.json';path.write_text(json.dumps(job))
    with (folder/'render.log').open('w') as log:
        subprocess.run(['nice','-n','5','/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/blender_oracle.py'),str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    destination=SITE/f'assets/images/scene-studio-{id}.webp'
    Image.open(folder/'00000.png').save(destination,quality=96,method=6)
    print(f'POSTER {id}: 1800 × 1300, Cycles 192 samples',flush=True)


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(render,[f'{i:02}' for i in range(1,16)]))
    target=SITE/'data/physics.js'
    entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    for entry in entries:entry['studio_poster']=f'assets/images/scene-studio-{entry["id"]}.webp'
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,separators=(',',':'))+';\n');temp.replace(target)
    print('All high-resolution scene posters published.',flush=True)
