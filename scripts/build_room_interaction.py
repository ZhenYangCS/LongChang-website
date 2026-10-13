"""Build the high-quality, touchable Figure 1 pose banks and playback assets."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
from PIL import Image
import numpy as np

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-room-interaction')


def build(name,ffmpeg):
    job_path=CACHE/f'{name}.json';job=json.loads(job_path.read_text());folder=Path(job['output'])
    folder.mkdir(exist_ok=True)
    with (folder/'render.log').open('w') as log:
        subprocess.run(['nice','-n','5','/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/blender_room_interaction.py'),str(job_path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    projections=json.loads((folder/'projection.json').read_text())
    dest=SITE/f'assets/videos/room/{name}.mp4';dest.parent.mkdir(exist_ok=True)
    temp=dest.with_name(name+'.partial.mp4');fps=30
    process=subprocess.Popen([ffmpeg,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','884x864','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','16','-g','1','-keyint_min','1','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],stdin=subprocess.PIPE)
    crop=[job['crop'][i]*(job['width'] if i%2==0 else job['height']) for i in range(4)]
    for i in range(len(projections)):
        im=Image.open(folder/f'{i:03}.png').convert('RGBA').transform((884,864),Image.Transform.EXTENT,crop,Image.Resampling.BICUBIC)
        bg=Image.new('RGBA',im.size,'#f8f9f6');bg.alpha_composite(im)
        process.stdin.write(np.asarray(bg.convert('RGB')).tobytes())
    process.stdin.close();assert process.wait()==0;temp.replace(dest)
    base=min(range(len(projections)),key=lambda i:abs(projections[i]['value']-job['base']))
    print(f"TOUCH READY {name}: {len(projections)} independently seekable poses",flush=True)
    return dict(id=name,video=str(dest.relative_to(SITE)),fps=fps,frames=projections,
                base=job['base'],base_index=base,axis=job['axis'],kind=job['kind'],
                label={'pendulum':'Pendulum','blue':'Blue ball','red':'Red ball','balance':'Balance'}[name])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);args=parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        parts=list(pool.map(lambda name:build(name,args.ffmpeg),['pendulum','blue','red','balance']))
    result=dict(width=884,height=864,parts=parts,outline=json.loads((CACHE/'pendulum/outline.json').read_text()),
                description='Touchable Figure 1, using the original editable Blender scene and MuJoCo-resolved poses. One object is animated at a time.')
    target=SITE/'data/room.js';temp=target.with_suffix('.js.tmp')
    temp.write_text('window.ROOM_INTERACTION = '+json.dumps(result,separators=(',',':'))+';\n');temp.replace(target)
    print('Interactive Figure 1 assets complete.',flush=True)


if __name__=='__main__':main()
