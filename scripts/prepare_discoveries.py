"""Curate four verified successful Astra runs and render their evidence chapters.

Uses archived states only. Requires the MuJoCo environment and ffmpeg.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
from render_replays import SITE, ROOT, RecordedRenderer
from world import load_replay
import mujoco
from paper_scenes import paper_scene_names

BASE = ROOT / 'runs/main-15-20260930-022640-2180080'
CASES = [
    dict(id='07',scene='07_tile_restitution',repeat=3,name='Same ball. Different bounce.',
         short='Surface or object?',mechanism='bounce',turns=34,
         intro='Does the bounce belong to the ball, or to the surface beneath it?',
         conclusion='Matched launches and a same-ball surface swap isolate the tile effect. The inferred rebound-speed ratios are approximately 0.9 on red and 0.15 on blue.',
         chapters=[
             dict(title='Compare matched launches',turns=[21,22],note=23,targets=['gray_ball_2'],
                  description='An upward impulse of 3 launches ball 2 from the red tile. It returns with a substantial rebound.'),
             dict(title='Test the other surface',turns=[23,24],note=25,targets=['gray_ball_1'],
                  description='The same upward impulse gives ball 1 a matching initial flight on blue, followed by only a tiny rebound.'),
             dict(title='Move the same ball to red',turns=[29,30],note=31,targets=['gray_ball_1'],
                  description='Ball 1 now receives the identical launch on red. Its large rebound follows the surface, ruling out ball identity as the sole explanation.')]),
    dict(id='06',scene='06_clockwise_deflection',repeat=1,name='A force that turns with motion.',
         short='Which way is sideways?',mechanism='curve',turns=31,
         intro='Is the ball pulled toward a fixed direction, or deflected relative to its motion?',
         conclusion='Changing launch direction and testing airborne motion support clockwise deflection. A faster launch matches the advance prediction from ax ≈ 1.2vy and ay ≈ −1.2vx.',
         chapters=[
             dict(title='Notice a curved path',turns=[1,2],note=3,targets=['red_ball'],
                  description='A straight eastward push produces a path that curves south. This observation suggests more than ordinary slowing.'),
             dict(title='Change the launch direction',turns=[5,6],note=7,targets=['red_ball'],
                  description='A northward push curves east. The deflection follows the direction of motion, rather than a fixed southward pull.'),
             dict(title='Predict an airborne trajectory',turns=[28,29],note=30,targets=['red_ball'],
                  description='Before the faster throw, Astra predicts a displacement of about (+5.75, −4.57) bricks. The observed (+5.7, −4.6) closely agrees, without floor contact.')]),
    dict(id='14',scene='14_delayed_motion_echo',repeat=2,name='A motion that arrives twelve counts later.',
         short='A delayed velocity transfer',mechanism='echo',turns=53,
         intro='Does green copy red’s path, receive an extra impulse, or inherit a stored velocity?',
         conclusion='Red’s PUSH/THROW schedules its total post-command translational velocity to replace green’s 12 counts later. The explorer distinguishes this from path replay and from adding an impulse.',
         chapters=[
             dict(title='Measure the delayed response',turns=[15,16,17],note=18,targets=['red_ball','green_ball'],
                  description='Green stays still through 11.12 counts, then moves north at the predicted 12-count delay after red’s push.'),
             dict(title='Stop red before the echo',turns=[29,30,31],note=32,targets=['red_ball','green_ball'],
                  description='Astra grasps red after only about 0.2 brick of travel. Green still moves the full 1.5 bricks later, excluding continuous path replay.'),
             dict(title='Resolve replacement versus addition',turns=[46,47],note=48,targets=['green_ball'],
                  description='Red has already scheduled an eastward echo. Green is thrown northward into the air. At the echo, its northward motion stops and it moves east, resolving the earlier ambiguity from rolling on the floor.')]),
    dict(id='15',scene='15_launch_suppressed_drift',repeat=3,name='An experiment can hide the phenomenon.',
         short='Intervening resets the clock',mechanism='drift',turns=61,
         intro='Red moves by itself—but a push can temporarily make that extra force disappear.',
         conclusion='The run identifies red’s northward drive, its approximately 10-count pause after nonzero pushes or throws, and the shared reset triggered by acting on blue. A zero-impulse push does not suppress the effect.',
         chapters=[
             dict(title='Build a surface control',turns=[34,35],note=36,targets=['red_ball'],
                  description='Astra constructs a supported elevated platform. Red still moves north on it; the matched blue trial stays still. The original floor is not required.'),
             dict(title='Test a predicted restart time',turns=[53,54,55],note=56,targets=['red_ball'],
                  description='After pushing red, Astra watches through nine counts and then crosses the predicted boundary. Motion resumes at approximately 10.006 counts.'),
             dict(title='Push the other ball',turns=[56,57,58],note=59,targets=['red_ball','blue_ball'],
                  description='Pushing distant blue suppresses red’s active drift. Red restarts about 10.006 counts after that action too, supporting a shared timer.')]),
]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_camera(record,frames,targets,case_id,chapter):
    points=[];models={}
    for f in frames[::max(1,len(frames)//150)]+[frames[-1]]:
        v=f['version']
        if v not in models:
            xml=next(m['xml'] for m in record['model_versions'] if m['version']==v)
            models[v]=mujoco.MjModel.from_xml_string(xml)
        model=models[v]
        for name in targets:
            bid=model.body(name).id
            joint=model.body_jntadr[bid]
            offset=model.jnt_qposadr[joint]
            points.append(f['qpos'][offset:offset+3])
    points=np.asarray(points)
    az,el=np.deg2rad([110,-32])
    right=np.array([-np.sin(az),np.cos(az),0])
    up=np.array([-np.cos(az)*np.sin(el),-np.sin(az)*np.sin(el),np.cos(el)])
    u,v=points@right,points@up
    span=max(1.2,float(np.ptp(v))+.8,(float(np.ptp(u))+.9)/(1000/620))*1.18
    if case_id=='07': span=max(1.75,span)
    if case_id=='15' and chapter==0: span=max(3.6,span)
    z=float((points[:,2].min()+points[:,2].max())/2)
    xy=np.linalg.solve([right[:2],up[:2]],[(u.min()+u.max())/2,(v.min()+v.max())/2-up[2]*z])
    return dict(lookat=[*xy,z],distance=18,azimuth=110,elevation=-32,orthographic=True,vertical_span=span)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    names,_=paper_scene_names()
    with (ROOT/'ACL/materials/results/sources/gpt_6_1_sol_episodes.csv').open() as f: evaluations=list(csv.DictReader(f))
    public=[];provenance=[];records_export=[]
    for case in CASES:
        directory=BASE/case['scene']/'gpt-6-astra'/f"r{case['repeat']}"/'T0'
        session=json.loads((directory/'session.json').read_text());record=load_replay(directory/'replay.bin')
        row=next(r for r in evaluations if r['episode_id']==session['episode_id'])
        assert row['correct']==row['supported']==row['success']=='True'
        assert row['session_sha256']==sha(directory/'session.json')
        by_turn={t['turn']:t for t in session['turns']}
        entry={k:v for k,v in case.items() if k not in ['chapters','scene']}
        entry.update(storyTitle=entry['name'],name=names[case['id']],short=names[case['id']])
        entry.update(episode_id=session['episode_id'],model='GPT-6-Astra',budget=100,
                     verdict=dict(correct=True,supported=True,discovery=True),judge='GPT-6.1-Sol',
                     finalNote=by_turn[max(by_turn)]['note'],chapters=[])
        for i,chapter in enumerate(case['chapters']):
            frames=sorted([f for f in record['state_frames'] if f['turn'] in chapter['turns']],key=lambda f:f['time'])
            start,end=frames[0]['time'],frames[-1]['time']
            cam=frame_camera(record,frames,chapter['targets'],case['id'],i)
            filename=f"success-{case['id']}-{i+1}"
            duration=min(10,max(4,end-start))
            item={k:v for k,v in chapter.items() if k not in ['targets','note']}
            item.update(video=f'assets/videos/{filename}.mp4',poster=f'assets/images/{filename}.webp',
                        start=start,end=end,duration=duration,note=by_turn[chapter['note']]['note'],noteTurn=chapter['note'],
                        actions=[{'turn':t,'action':by_turn[t]['act']} for t in chapter['turns']])
            entry['chapters'].append(item)
            dest=SITE/item['video']
            if dest.exists() and not args.force:continue
            renderer=RecordedRenderer(record,cam,(1600,992),detail_shadows=True);fps=24
            proc=subprocess.Popen([args.ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                '-s','1600x992','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE)
            times=np.asarray([f['time'] for f in frames])
            for n,t in enumerate(np.linspace(start,end,round(duration*fps))):
                pixels=renderer.render(frames[int(np.abs(times-t).argmin())])
                if n==0:Image.fromarray(pixels).save(SITE/item['poster'],quality=94)
                proc.stdin.write(pixels.tobytes())
            proc.stdin.close();assert proc.wait()==0;renderer.close()
            print(f"Rendered {filename}: turns {chapter['turns']}, {duration:.1f}s",flush=True)
        public.append(entry)
        provenance.append(dict(scene=case['scene'],repeat=case['repeat'],episode_id=session['episode_id'],
                               source=str(directory.relative_to(ROOT)),session_sha256=sha(directory/'session.json'),
                               replay_sha256=sha(directory/'replay.bin'),eval_sha256=row['eval_sha256'],
                               judgement='C=true; S=true; D=true',judge='GPT-6.1-Sol'))
        report=session['report'];report=json.loads(report) if isinstance(report,str) else report
        records_export.append(dict(scene=case['scene'],repeat=case['repeat'],episode_id=session['episode_id'],
                                   model='GPT-6-Astra',budget=100,judgement=entry['verdict'],
                                   notes=[{'turn':t['turn'],'action':t['act'],'note':t['note']} for t in session['turns']],report=report))
    (SITE/'data/discoveries.js').write_text('window.DISCOVERIES = '+json.dumps(public,ensure_ascii=False)+';\n')
    (SITE/'data/discovery-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (SITE/'downloads/successful-runs.json').write_text(json.dumps(records_export,ensure_ascii=False,indent=2)+'\n')
    print('Verified and exported four successful runs with twelve evidence chapters.',flush=True)


if __name__=='__main__':main()
