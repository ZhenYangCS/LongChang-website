"""Independent expectations for the fresh demonstrations' measured oracle effects."""
import json
from pathlib import Path
import numpy as np
from paper_scenes import paper_scene_names

SITE=Path(__file__).resolve().parents[1]


def main():
    names,_=paper_scene_names()
    records={id:json.loads((SITE/f'downloads/oracle-demonstrations/scene-{id}.json').read_text()) for id in names}
    for id,r in records.items():
        assert r['name']==names[id]
        assert len(r['samples'])==len(r['reference_samples'])
        for name in r['focus']:
            np.testing.assert_allclose(r['samples'][0]['objects'][name]['position'],r['reference_samples'][0]['objects'][name]['position'],atol=1e-10)
        assert np.isfinite([s['time'] for s in r['samples']]).all()
    r=records['01']
    for sample,ref in zip(r['samples'],r['reference_samples']):
        for name in r['focus']:np.testing.assert_allclose(sample['objects'][name]['position'],ref['objects'][name]['position'],atol=1e-9)
    assert records['02']['samples'][0]['oracle']['forces']['red_ball_1'][0]>0
    assert all(np.linalg.norm(s['oracle']['forces']['blue_ball_1'])==0 for s in records['02']['samples'])
    assert records['04']['maximum_heights']['blue_ball']>records['04']['maximum_heights']['red_ball']*1.5
    peaks=[max(s['objects'][name]['position'][2] for s in records['04']['reference_samples']) for name in ['red_ball','blue_ball']]
    assert abs(peaks[0]-peaks[1])<.001
    assert np.linalg.norm(records['05']['samples'][0]['oracle']['forces']['red_ball'])>40
    assert records['06']['samples'][0]['oracle']['forces']['red_ball'][1]<0
    for event in records['07']['oracle_events']:
        for c in event.get('changes',[]):
            np.testing.assert_allclose(c['ratio'],.9 if c['object']=='gray_ball_1' else .15,rtol=1e-9)
    assert max(np.linalg.norm(o['velocity']) for s in records['08']['samples'] for o in s['objects'].values())<2.2
    entries=records['09']['oracle_events']
    np.testing.assert_allclose([e['changes'][0]['ratio'] for e in entries],[.4,2.5,.4],rtol=1e-9)
    assert entries[-1]['changes'][0]['position'][2]>.5
    assert records['10']['samples'][-1]['oracle']['energy_added']>5
    boosts=records['11']['oracle_events']
    assert len(boosts)==1 and boosts[0]['kind']=='separation_boost'
    assert {c['object'] for c in boosts[0]['changes']}=={'red_ball','blue_ball'}
    for c in boosts[0]['changes']:np.testing.assert_allclose(c['after'],np.asarray(c['before'])*1.8,rtol=1e-9)
    swaps=records['12']['oracle_events'];assert len(swaps)==2
    for e in swaps:
        a,b=e['changes'];assert a['before']==b['after'] and b['before']==a['after']
    events=records['13']['oracle_events']
    assert [e['count'] for e in events if e['kind']=='contact_count']==[1,2,3]
    kicks=[e for e in events if e['kind']=='upward_kick'];assert len(kicks)==1
    for c in kicks[0]['changes']:assert abs(c['after'][2]-4)<1e-9
    copies=records['14']['oracle_events'];assert len(copies)==1
    assert abs(copies[0]['time']-12)<.003
    np.testing.assert_allclose(copies[0]['changes'][0]['after'],[3,0,0],atol=1e-9)
    r=records['15'];events=r['oracle_events']
    assert [e['kind'] for e in events]==['force_on','force_off','force_on']
    np.testing.assert_allclose([e['time'] for e in events],[0,2,16],atol=.003)
    sample=min(r['samples'],key=lambda s:abs(s['time']-6.1))
    assert abs(sample['oracle']['quiet_until']-16)<.003
    sample=min(r['samples'],key=lambda s:abs(s['time']-1.2))
    assert sample['oracle']['forces']['red_ball'][1]==1.5,'Zero impulse must leave the force on'
    print('PASS: all 15 names and paired preparations; exact restitution, boundary and collision multipliers; color swap; third-contact kick; 12-count copy; zero/nonzero launch and pause reset.')


if __name__=='__main__':main()
