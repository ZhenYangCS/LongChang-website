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
        folder=Path('/tmp/longchang-detail-views/native/10') if id=='10' and entry.get('detail_video') else cache/id
        sealed=entry.get('render_revision') in ['unified-v1','explained-v1']
        render_cache=Path('/tmp/longchang-explained-scenes' if entry.get('render_revision')=='explained-v1' else '/tmp/longchang-unified-scenes')
        if entry.get('camera_revision')=='front-v1':render_cache=Path('/tmp/longchang-front-view')
        if sealed:folder=render_cache/id/'room'
        job=json.loads((folder/'job.json').read_text());source=json.loads((SOURCE/id/'studio-job.json').read_text())
        signature_folder=Path('/tmp/longchang-detail-views')/id/'room' if entry.get('detail_video') else cache/id
        if sealed:signature_folder=folder
        signature=json.loads((signature_folder/'room-signature.json').read_text())
        if first is None:first=signature
        assert signature==first,f'{id}: constructed Blender room, camera or lighting changed'
        assert job['display_bounds']==common['bounds']
        assert job['camera']==common['camera']
        assert job['radii']==source['radii']
        if sealed:
            assert job['enclosed'] and common['enclosed']
            roof=signature['Optical glass roof']
            assert abs(roof['matrix'][2][3]+min(p[2] for p in roof['bounds'])-common['bounds'][4])<1e-6
        if entry.get('fps')==60:
            record=json.loads((SITE/entry['record']).read_text())
            for frame in job['frames']:assert frame['objects']==record['samples'][frame['native_index']]['objects']
        else:assert job['frames']==source['frames']
        assert entry['room_signature']==common['render_signature']==hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        assert Image.open(SITE/entry['studio_poster']).size==(1440,960)
        if entry.get('detail_video'):
            import numpy as np
            from build_detail_views import focus_crop,project
            crop,camera=focus_crop(job)
            assert crop==entry['detail_crop'] and camera==entry['detail_camera']
            detail_path=render_cache/id/'detail/job.json' if sealed else Path('/tmp/longchang-detail-views')/id/'job.json'
            detail=json.loads(detail_path.read_text())
            if sealed:assert detail['enclosed']
            assert detail['display_bounds']==common['bounds']
            assert detail['radii']==job['radii'] and detail['frames']==job['frames']
            l,t,r,b=crop
            for f in job['frames'][::60]:
                for o in f['objects'].values():
                    uv=project(job['camera'],1440,960,o['position'])
                    np.testing.assert_allclose(project(camera,1600,800,o['position']),(uv-[l,t])*[1600/(r-l),800/(b-t)],atol=1e-8)
        xmin,xmax,ymin,ymax,height=common['bounds']
        for frame in job['frames']:
            for name,obj in frame['objects'].items():
                x,y,z=obj['position'];r=job['radii'][name]
                assert xmin<x-r<x+r<xmax and ymin<y-r<y+r<ymax and z+r<height,(id,name)
    camera=first['Figure 1 orthographic experiment view']
    assert camera['matrix'][2][3]>1,'Camera proof must use the evaluated transform'
    symbols=json.loads((SITE/'assets/table1/source.json').read_text())
    source=(SITE.parent/symbols['source']).read_text()
    definitions=source[source.index(r'\definecolor{sceneink}'):source.index(r'\newcommand{\scenecard}')].replace(r'\relax\space','')
    assert symbols['symbols_sha256']==hashlib.sha256(definitions.encode()).hexdigest()
    assert all((SITE/f'assets/table1/scene-{n:02}.svg').stat().st_size>100 for n in range(1,16))
    print('PASS: all 15 actual room meshes, floor dimensions, camera transforms and lights are identical.')
    print('PASS: all original trajectories and radii preserved and contained; Table 1 symbols match the ACL source.')

if __name__=='__main__':main()
