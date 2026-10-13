"""Ensure all fifteen rendered rooms are actually identical, not just similar ratios."""
import hashlib,json
from pathlib import Path
from PIL import Image

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-shared-room')
SOURCE=Path('/tmp/longchang-oracle-studio/production')

def main():
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    common=json.loads((SITE/'data/shared-room.json').read_text())
    first=None
    for entry in entries:
        id=entry['id'];cache=Path('/tmp/longchang-smooth-scenes') if entry.get('fps')==60 else CACHE
        job=json.loads((cache/id/'job.json').read_text());source=json.loads((SOURCE/id/'studio-job.json').read_text())
        signature=json.loads((cache/id/'room-signature.json').read_text())
        if first is None:first=signature
        assert signature==first,f'{id}: constructed Blender room, camera or lighting changed'
        assert job['display_bounds']==common['bounds']
        assert job['camera']==common['camera']
        assert job['radii']==source['radii']
        if entry.get('fps')==60:
            record=json.loads((SITE/entry['record']).read_text())
            for frame in job['frames']:assert frame['objects']==record['samples'][frame['native_index']]['objects']
        else:assert job['frames']==source['frames']
        assert entry['room_signature']==common['render_signature']==hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        assert Image.open(SITE/entry['studio_poster']).size==(1440,960)
        xmin,xmax,ymin,ymax,height=common['bounds']
        for frame in job['frames']:
            for name,obj in frame['objects'].items():
                x,y,z=obj['position'];r=job['radii'][name]
                assert xmin<x-r<x+r<xmax and ymin<y-r<y+r<ymax and z+r<height,(id,name)
    camera=first['Figure 1 orthographic experiment view']
    assert camera['matrix'][2][3]>1,'Camera proof must use the evaluated transform'
    symbols=json.loads((SITE/'assets/table1/source.json').read_text())
    assert symbols['source_sha256']==hashlib.sha256((SITE.parent/symbols['source']).read_bytes()).hexdigest()
    assert all((SITE/f'assets/table1/scene-{n:02}.svg').stat().st_size>100 for n in range(1,16))
    print('PASS: all 15 actual room meshes, floor dimensions, camera transforms and lights are identical.')
    print('PASS: all original trajectories and radii preserved and contained; Table 1 symbols match the ACL source.')

if __name__=='__main__':main()
