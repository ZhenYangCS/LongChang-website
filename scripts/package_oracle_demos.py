"""Publish studio thumbnails and portable oracle films, figures and records."""
from pathlib import Path
import hashlib
import json
import zipfile

from PIL import Image
from paper_scenes import paper_scene_names

SITE=Path(__file__).resolve().parents[1]
ROOT=SITE.parent
CACHE=Path('/tmp/longchang-oracle-studio/production')


def main():
    names,_=paper_scene_names()
    target=SITE/'data/physics.js'
    entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    assert len(entries)==15 and all(e.get('time_map') for e in entries)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
        ROOT/'longchang/world.py',ROOT/'longchang/scenes.py',ROOT/'longchang/tools.py',
        ROOT/'ACL/materials/teaser/blender_scene.py']}
    for entry in entries:
        id=entry['id'];assert entry['name']==names[id]
        frame=round(entry['preview_time']*entry['fps'])
        preview=Image.open(CACHE/id/'frames'/f'{frame:05}.png').convert('RGBA')
        path=SITE/f'assets/images/oracle-world-{id}.webp'
        preview.save(path,quality=94,method=6)
        entry.update(studio_poster=str(path.relative_to(SITE)),
                     gif=f'downloads/animated-scenes/oracle-{id}.gif',
                     signal_figure=f'downloads/oracle-signals/scene-{id}.svg',
                     source_hashes=hashes,
                     video_sha256=hashlib.sha256((SITE/entry['video']).read_bytes()).hexdigest())
    temp=target.with_suffix('.js.tmp')
    temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,ensure_ascii=False,separators=(',',':'))+';\n')
    temp.replace(target)
    with zipfile.ZipFile(SITE/'downloads/longchang-oracle-gifs.zip','w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('README.txt','''LongChang: the fifteen oracles, made visible.

Fresh scripted experiments with native scene physics. Glass materials and
studio lighting reuse the paper's Figure 1 rendering code. Each animation
shows the oracle, its trigger, measured state changes, and a comparison.
Names follow the ACL scene-overview table exactly.

Ordinary references use identical geometry, masses and prescribed actions,
with only the altered physical program disabled. These demonstrations do
not contribute to the paper's model-discovery scores. The glass enclosures
and cropped plinths are presentation geometry, not added physical walls.

Playback slows down or holds exact sampled states around key events.
The displayed clock remains the original simulation time. Full records,
editable signal figures and source hashes are available on the project page.
''')
        for entry in entries:archive.write(SITE/entry['gif'],f"{entry['id']}-{entry['name']}.gif")
    with zipfile.ZipFile(SITE/'downloads/longchang-oracle-signals.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((SITE/'downloads/oracle-signals').glob('*')):archive.write(path,path.name)
    print('Packaged 15 Figure 1 studio thumbnails, oracle GIFs, SVG/PNG figures and verified source hashes.')


if __name__=='__main__':main()
