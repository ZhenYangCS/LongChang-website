"""Resolve touchable Figure 1 poses without modifying the paper's assets."""
import json
import os
from pathlib import Path
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[2]
CACHE=Path('/tmp/longchang-room-interaction');CACHE.mkdir(exist_ok=True)
SOURCE=ROOT/'ACL/materials/teaser/sources/workspace.xml'


def main():
    model=mujoco.MjModel.from_xml_path(str(SOURCE));data=mujoco.MjData(model)
    manifest=json.loads((SOURCE.parent/'workspace.json').read_text())
    groups={
        'pendulum':dict(joint='swing',body='pendulum_arm',target='pendulum_bob',values=np.linspace(-.8,.8,33),base=-.4,axis='x',kind='spring'),
        'blue':dict(joint='blue_joint',body='blue_ball',target='blue_geom',values=np.linspace(0,1.2,17),base=0,axis='y',kind='bounce'),
        'red':dict(joint='red_joint',body='red_ball',target='red_geom',values=np.linspace(0,.8,13),base=0,axis='y',kind='bounce'),
        'balance':dict(joint='balance_hinge',body='balance_arm',target='pan_-1',values=np.linspace(-.3,.3,21),base=0,axis='y',kind='spring')}
    for name,config in groups.items():
        joint=model.joint(config['joint']).id;q=int(model.jnt_qposadr[joint]);body=model.body(config['body']).id
        geometries=[i for i in range(model.ngeom) if model.geom_bodyid[i]==body]
        frames=[]
        for value in config['values']:
            mujoco.mj_resetDataKeyframe(model,data,0)
            if config['kind']=='bounce':data.qpos[q+2]+=value
            else:data.qpos[q]=value
            mujoco.mj_forward(model,data)
            frames.append(dict(value=float(value),poses={model.geom(i).name:dict(position=data.geom_xpos[i].tolist(),rotation=data.geom_xmat[i].reshape(3,3).tolist()) for i in geometries}))
        job={k:v for k,v in config.items() if k!='values'}
        job.update(id=name,frames=frames,width=936,height=1000,samples=96,threads=16,
                   blend=str(SOURCE.parent/'workspace.blend'),output=str(CACHE/name),
                   crop=[manifest['foreground_bbox'][i]/(manifest['render']['width'] if i%2==0 else manifest['render']['height']) for i in range(4)])
        (CACHE/f'{name}.json').write_text(json.dumps(job)+'\n')
        print(f'Prepared {name}: {len(frames)} exact articulated poses.',flush=True)


if __name__=='__main__':main()
