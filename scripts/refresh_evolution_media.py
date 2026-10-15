"""Render the accepted evolution demos with the original 15 scenes' renderer.

Native states, preparations, actions and film timing are checked against the
published records before changing the camera, materials and annotations.
"""
import argparse
import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw

import build_detail_views as detail
from prepare_evolution_demos import capture, audit
from render_clear_scenes import ROOM_BOUNDS

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
CACHE = Path('/tmp/longchang-evolution-shared-style')
COLORS = {'red_ball': '#c56859', 'object_1': '#c56859',
          'blue_ball': '#547fa7', 'object_2': '#547fa7', 'green_ball': '#549b74'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(entry):
    source = ROOT / entry['source']
    assert sha(source) == entry['source_sha256']
    world, native, actions = capture(entry['id'], source)
    audit(entry['id'], native)
    public = [{k: v for k, v in f.items() if k not in ['qpos', 'qvel', 'rgba', 'epoch']}
              for f in native[::10]]
    assert public == entry['samples'], 'Native states changed; do not replace the published film.'
    assert actions == entry['actions']
    config = json.loads((SITE / f"data/evolution/{entry['id']}.json").read_text())
    times = np.array([f['time'] for f in native])
    count = round(entry['fps'] * entry['duration'])
    frames = []
    for n in range(count):
        t = n / (count - 1) * native[-1]['time']
        index = int(np.abs(times - t).argmin())
        frames.append(dict(time=native[index]['time'], objects=native[index]['objects'],
                           holding=native[index]['holding'], native_index=index))
    job = dict(id=entry['id'], width=1600, height=800, samples=128, threads=8,
               display_bounds=ROOM_BOUNDS, enclosed=True, focus_fixtures=True,
               fixtures=[e for e in config['entities'] if e['kind'] == 'fixture'],
               radii={e['name']:e['size'][0] for e in config['entities'] if e['kind'] == 'body'},
               frames=frames, minimum_focus_width=340)
    crop, camera = detail.focus_crop(job)
    job.update(camera=camera, output=str(CACHE / entry['id']))
    detail.write(CACHE / entry['id'] / 'job.json', job)
    result = copy.deepcopy(entry)
    result.update(camera=camera, size=[1600,800], render_revision='shared-oblique-v1',
                  render=dict(engine='Blender Cycles', camera='15 Worlds fixed oblique view',
                              renderer='scripts/build_detail_views.py', display_bounds=ROOM_BOUNDS,
                              native_samples_sha256=hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest()))
    return job, result


def marked_frame(job, background, sprites, index):
    """The same recorded trajectories and force arrows used by the base demos."""
    base = background.copy()
    drawing = ImageDraw.Draw(base)
    frame = job['frames'][index]
    project = lambda p: tuple(detail.project(job['camera'],job['width'],job['height'],p))
    for name, obj in frame['objects'].items():
        points = [project(f['objects'][name]['position']) for f in job['frames'][:index+1:3]]
        points.append(project(obj['position']))
        if len(points) > 1:
            drawing.line(points, fill=COLORS[name]+'90', width=3)
    im = detail.compose(job, base, sprites, index)
    drawing = ImageDraw.Draw(im)
    for name, obj in frame['objects'].items():
        # Hand forces are not the altered law: only draw the affected bodies.
        if job['id'] != 'generate' and name not in ['red_ball','object_1']:
            continue
        force = np.asarray(obj['applied_force'])
        norm = np.linalg.norm(force)
        if norm < 1e-6:
            continue
        p = np.asarray(obj['position'])
        direction = force/norm
        start = np.asarray(project(p+direction*.14))
        end = np.asarray(project(p+direction*.54))
        vector = end-start
        length = np.linalg.norm(vector)
        if length < 1:
            continue
        unit = vector/length
        normal = np.array([-unit[1],unit[0]])
        drawing.line([tuple(start),tuple(end)], fill='#368574', width=5)
        drawing.polygon([tuple(end),tuple(end-unit*15+normal*6),tuple(end-unit*15-normal*6)],fill='#368574')
    return im


def render(prepared, ffmpeg, preview):
    job, entry = prepared
    folder = CACHE / entry['id']
    background = detail.flat(detail.asset(job, folder))
    sprites = {name:Image.open(CACHE/'sprites'/f'{name}.png').convert('RGBA')
               for name in ['red','blue','green','gray']}
    if preview:
        for fraction in [0,.5,.98]:
            marked_frame(job,background,sprites,round((len(job['frames'])-1)*fraction)).save(folder/f'preview-{fraction}.png')
        return entry
    # Match the 15-scene encoding settings and publish only complete files.
    import subprocess
    movie = folder/'scene.mp4'
    process = subprocess.Popen([ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1600x800','-r',str(entry['fps']),'-i','-','-an','-c:v','libx264','-preset','fast',
        '-crf','16','-threads','4','-g','60','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE)
    try:
        for i in range(len(job['frames'])):
            frame = marked_frame(job,background,sprites,i)
            if i == 0:
                frame.save(folder/'poster.webp',quality=96,method=6)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        assert process.wait() == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    entry['video_sha256'] = sha(movie)
    entry['poster_sha256'] = sha(folder/'poster.webp')
    print(f"Rendered {entry['id']}: identical native states, shared scene style.",flush=True)
    return entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--preview',action='store_true')
    args = parser.parse_args()
    path = SITE/'data/evolution-demos.json'
    manifest = json.loads(path.read_text())
    # Native callbacks are process-global: capture each scene sequentially.
    prepared = [prepare(entry) for entry in manifest['demos']]
    existing = Path('/tmp/longchang-low-oblique-view/sprites')
    if all((existing/f'{name}.png').exists() for name in ['red','blue','green','gray']):
        (CACHE/'sprites').mkdir(parents=True,exist_ok=True)
        for name in ['red','blue','green','gray']:
            shutil.copyfile(existing/f'{name}.png',CACHE/'sprites'/f'{name}.png')
    else:
        job = copy.deepcopy(prepared[0][0])
        job.update(sprites=True, radii={'sprite':.1}, fixtures=[])
        detail.asset(job,CACHE/'sprites')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        entries = list(pool.map(lambda item:render(item,args.ffmpeg,args.preview),prepared))
    if args.preview:
        return
    for entry in entries:
        folder = CACHE/entry['id']
        for source, target in [('scene.mp4',entry['video']),('poster.webp',entry['poster'])]:
            dest = SITE/target
            temporary = dest.with_suffix(dest.suffix+'.tmp')
            shutil.copyfile(folder/source,temporary)
            temporary.replace(dest)
    manifest['demos'] = entries
    detail.write(path,manifest)
    print('Published all three demos. Native records, timings and source hashes are unchanged.',flush=True)


if __name__ == '__main__':
    main()
