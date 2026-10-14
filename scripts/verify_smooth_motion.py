"""Verify temporal continuity, genuine dense physics, and actual movie frame rates."""
import argparse,json,itertools
from pathlib import Path
import numpy as np
import imageio_ffmpeg

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-smooth-scenes')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepared',action='store_true');args=parser.parse_args()
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    for published in entries:
        id=published['id'];folder=Path('/tmp/longchang-detail-views/native/10') if id=='10' and published.get('detail_video') and not args.prepared else CACHE/id
        explained=published.get('render_revision')=='explained-v1' and not args.prepared
        if explained:folder=Path('/tmp/longchang-explained-scenes/native')/id
        entry=json.loads((folder/'entry.json').read_text()) if args.prepared else published
        record=json.loads((folder/'record.json').read_text()) if args.prepared else json.loads((SITE/entry['record']).read_text())
        job=json.loads((folder/'job.json').read_text())
        assert entry['fps']==60 and record['sample_interval']==.002
        assert len(job['frames'])==entry['duration']*60
        assert len(entry['time_map'])==2,'Remove artificial holds and speed ramps'
        repeats=[len(list(g)) for _,g in itertools.groupby(f['native_index'] for f in job['frames'])]
        assert max(repeats)<=2,(id,'sparse source frames or a forced freeze')
        for f in job['frames']:
            native=record['samples'][f['native_index']]
            assert f['objects']==native['objects'] and f['epoch']==native['epoch']
        for a,b in zip(job['frames'],job['frames'][1:]):
            if a['epoch']!=b['epoch']:assert a['fade']>.95 and b['fade']>.95,(id,'unmarked reset')
        if explained or id in ['10','12','13']:
            assert all(f['epoch']==0 and f['fade']==0 for f in job['frames'])
            assert not any(e['kind']=='arrange' for e in record['events'])
            for name in record['focus']:
                positions=np.array([f['objects'][name]['position'] for f in record['samples']])
                assert np.linalg.norm(np.diff(positions,axis=0),axis=1).max()<.03,(id,name,'position discontinuity')
        if not args.prepared:
            reader=imageio_ffmpeg.read_frames(str(SITE/entry['video']));meta=next(reader);reader.close()
            assert meta['fps']==60 and meta['size']==(1440,960),(id,meta)
            if id in ['12','13']:assert entry.get('launch_cues')
            if entry.get('detail_video'):
                reader=imageio_ffmpeg.read_frames(str(SITE/entry['detail_video']));meta=next(reader);reader.close()
                assert meta['fps']==60 and meta['size']==(1600,800),(id,meta)
                sealed=entry.get('render_revision') in ['unified-v1','explained-v1']
                render_cache=Path('/tmp/longchang-explained-scenes' if explained else '/tmp/longchang-unified-scenes')
                if published.get('camera_revision')=='front-v1':render_cache=Path('/tmp/longchang-front-view')
                if published.get('camera_revision')=='oblique-v1':render_cache=Path('/tmp/longchang-low-oblique-view')
                detail_path=render_cache/id/'detail/job.json' if sealed else Path('/tmp/longchang-detail-views')/id/'job.json'
                detail=json.loads(detail_path.read_text())
                if sealed:
                    room=json.loads((render_cache/id/'room/job.json').read_text())
                    assert room['frames']==job['frames'] and room['enclosed'] and detail['enclosed']
                assert detail['frames']==job['frames'] and detail['radii']==job['radii']
                assert detail['display_bounds']==json.loads((SITE/'data/shared-room.json').read_text())['bounds']
                assert len(detail['frames'])/meta['fps']==entry['duration']
    print('PASS: 60 fps uses original 500 Hz states, without artificial holds or synthesized trajectories.')
    print('PASS: collisions stay in one continuous run; separate trials fade explicitly instead of teleporting.')

if __name__=='__main__':main()
