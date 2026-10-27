"""Re-render archived case studies with Figure 1's studio materials.

Only MuJoCo forward kinematics is used. The original selected states, cuts,
geometry and captions are retained; no physics steps or pose interpolation.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import mujoco
import numpy as np
from PIL import Image
from prepare_case_films import ROOT, SITE, WIDTH, HEIGHT, FPS, plans, fitted_camera, load_replay, compose, digest

CACHE = Path('/tmp/longchang-case-studio')
BLENDER = '/root/.virtualenvs/longchang-blender/bin/python'
REVISION = 'figure1-studio-v2'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(',', ':'))+'\n')


def camera(spec):
    az, el = np.deg2rad([spec['azimuth'], spec['elevation']])
    forward = np.array([np.cos(az)*np.cos(el), np.sin(az)*np.cos(el), np.sin(el)])
    right = np.cross(forward, [0, 0, 1]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return dict(position=(np.array(spec['lookat'])-forward*30).tolist(), forward=forward.tolist(),
                right=right.tolist(), up=up.tolist(), span=spec['vertical_span'])


def prepare(case, chapter_index, track_index, spec, record, samples):
    chapter=case['chapters'][chapter_index]
    size=(604,454) if len(chapter['tracks'])==2 else (1280,536)
    frames=sorted((f for f in record['state_frames'] if f['turn'] in spec['turns']),key=lambda f:f['time'])
    times=np.array([f['time'] for f in frames])
    if spec.get('targets'): spec['camera']=fitted_camera(record,frames,spec,size)
    count=round(chapter['duration']*FPS)
    selected=[int(np.abs(times-t).argmin()) for t in np.linspace(spec['start'],spec['end'],count)]
    unique=list(dict.fromkeys(selected)); index_map={index:i for i,index in enumerate(unique)}
    models={}; geometries={}; poses=[]; originals=[]
    for index in unique:
        frame=frames[index]; version=frame['version']
        if version not in models:
            model=mujoco.MjModel.from_xml_string(next(v['xml'] for v in record['model_versions'] if v['version']==version))
            models[version]=(model,mujoco.MjData(model))
        model,data=models[version]
        mujoco.mj_setState(model,data,np.asarray(frame['state']),mujoco.mjtState(record['state_spec']))
        mujoco.mj_forward(model,data)
        pose={}
        for g in range(model.ngeom):
            name=mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_GEOM,g)
            if name in {'floor','ceiling'} or name.startswith('wall_'): continue
            rgba=model.geom_rgba[g].tolist()
            if rgba[3]<=0: continue
            geometry=dict(name=name,kind=int(model.geom_type[g]),size=model.geom_size[g].tolist())
            assert name not in geometries or geometries[name]==geometry, 'Geometry changes require a chapter cut'
            geometries[name]=geometry
            pose[name]=dict(position=data.geom_xpos[g].tolist(),rotation=data.geom_xmat[g].reshape(3,3).tolist(),rgba=rgba)
        poses.append(pose)
        originals.append(dict(time=frame['time'],turn=frame['turn'],version=version,
                              state_sha256=hashlib.sha256(np.asarray(frame['state'],dtype='<f8').tobytes()).hexdigest()))
    job=dict(id=f"{case['id']}-{chapter_index}-{track_index}",width=size[0],height=size[1],samples=samples,threads=12,
             camera=camera(spec['camera']),display_bounds=[-6,6,-6,6,12],fixtures=[],radii={},
             geometries=geometries,frames=poses,originals=originals,frame_map=[index_map[i] for i in selected],revision=REVISION,
             renderer_sha256=digest(SITE/'scripts/blender_case_films.py'))
    key=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()[:16]
    folder=CACHE/job['id']/key;job['output']=str(folder)
    write(folder/'job.json',job)
    return job


def render(job, preview):
    folder=Path(job['output'])
    cmd=[BLENDER,str(SITE/'scripts/blender_case_films.py'),str(folder/'job.json')]
    if preview: cmd.append('--preview')
    with (folder/'render.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Studio ready:',job['id'],flush=True)


class StudioTrack:
    def __init__(self,spec,job): self.spec=spec; self.job=job
    def at(self,fraction):
        index=self.job['frame_map'][round(fraction*(len(self.job['frame_map'])-1))]
        return Image.open(Path(self.job['output'])/'frames'/f'{index:05}.png').convert('RGB'),self.job['originals'][index]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--only',nargs='+',choices=['question','color','tool'])
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--samples',type=int,default=64)
    args=parser.parse_args()
    sources,cases=plans();records={};jobs={}
    for name,source in sources.items():
        assert digest(ROOT/source['path'])==source['sha256']
        assert digest(ROOT/source['session'])==source['session_sha256']
    selected=[case for case in cases if not args.only or case['id'] in args.only]
    for case in selected:
        for ci,chapter in enumerate(case['chapters']):
            for ti,spec in enumerate(chapter['tracks']):
                name=spec['source']
                if name not in records: records[name]=load_replay(ROOT/sources[name]['path'])
                job=prepare(case,ci,ti,spec,records[name],args.samples)
                jobs[(case['id'],ci,ti)]=job
    write(CACHE/'jobs.json',list(jobs.values()))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda job:render(job,args.preview),jobs.values()))
    manifest_path=SITE/'data/case-films.json'
    manifest=json.loads(manifest_path.read_text())
    for case in selected:
        dest=SITE/f"assets/videos/case-{case['id']}.mp4"
        poster=SITE/f"assets/images/case-{case['id']}.webp"
        if not args.preview:
            temp=dest.with_suffix('.studio.mp4')
            proc=subprocess.Popen([args.ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}',
                 '-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','slow','-crf','17','-threads','4',
                 '-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],stdin=subprocess.PIPE)
        entry=next(e for e in manifest['cases'] if e['id']==case['id']); entry['chapters']=[];elapsed=0
        for ci,chapter in enumerate(case['chapters']):
            tracks=[StudioTrack(spec,jobs[(case['id'],ci,ti)]) for ti,spec in enumerate(chapter['tracks'])]
            count=round(chapter['duration']*FPS)
            for n in ([0,count//2,count-1] if args.preview else range(count)):
                canvas,_=compose(case,chapter,tracks,n/(count-1))
                if args.preview: canvas.save(CACHE/f"preview-{case['id']}-{ci}-{n}.jpg",quality=95)
                else:
                    if ci==0 and n==0: canvas.save(poster,quality=96,method=6)
                    proc.stdin.write(canvas.tobytes())
            entry['chapters'].append(dict(title=chapter['title'],start=elapsed,end=elapsed+chapter['duration'],
                caption=' '.join(t['caption'] for t in chapter['tracks']),tracks=chapter['tracks']))
            elapsed+=chapter['duration']
        if not args.preview:
            proc.stdin.close();assert proc.wait()==0;temp.replace(dest)
            entry.update(video_sha256=digest(dest),poster_sha256=digest(poster),render=dict(revision=REVISION,
                engine='Blender Cycles',samples=args.samples,reference='ACL/non_submission/materials/teaser/blender_scene.py',
                reference_sha256=digest(ROOT/'ACL/non_submission/materials/teaser/blender_scene.py'),
                method='Exact archived geometry and poses; Figure 1 enamel, porcelain and metal materials, studio area lighting and AgX. Static backgrounds with rendered moving regions; no physics stepping or pose interpolation.'))
            print('Published:',dest.name,flush=True)
    if not args.preview:
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
        audit_path=SITE/'data/case-rendering.json'
        previous=json.loads(audit_path.read_text())['tracks'] if audit_path.exists() else []
        updated=[dict(id=j['id'],camera=j['camera'],geometries=j['geometries'],
                      frames=j['originals'],frame_map=j['frame_map']) for j in jobs.values()]
        ids={j['id'] for j in updated}
        write(audit_path,dict(revision=REVISION,tracks=[j for j in previous if j['id'] not in ids]+updated))
    if any(case['id']=='question' for case in selected):
        command=[sys.executable,str(SITE/'scripts/prepare_case_question.py'),'--ffmpeg',args.ffmpeg]
        if args.preview:command.append('--preview')
        subprocess.run(command,check=True)


if __name__=='__main__': main()
