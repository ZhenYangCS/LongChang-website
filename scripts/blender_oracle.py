"""Animate native physics samples using Figure 1's Cycles studio materials.

The glass enclosure and cropped display plinth are presentation geometry;
they do not participate in or alter the recorded physical simulation.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import time
import struct
import shutil

import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('figure1_studio',ROOT/'ACL/materials/teaser/blender_scene.py')
studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)


def box(name,position,size,material,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=2,location=position)
    obj=bpy.context.object;obj.name=name;obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod=obj.modifiers.new('Soft machined edges','BEVEL');mod.width=bevel;mod.segments=3
        obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return obj


def setup(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES'
    scene.cycles.device='CPU';scene.cycles.samples=job.get('samples',32)
    scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.04
    scene.cycles.adaptive_min_samples=min(16,scene.cycles.samples)
    scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=8
    scene.cycles.transparent_max_bounces=10;scene.cycles.glossy_bounces=4
    scene.cycles.seed=12;scene.render.use_persistent_data=True
    scene.render.threads_mode='FIXED';scene.render.threads=job.get('threads',16)
    scene.render.resolution_x=job.get('width',900);scene.render.resolution_y=job.get('height',650)
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.cycles.film_transparent_glass=True
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.1
    world=bpy.data.worlds.new('Figure 1 neutral studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.86,.92,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45;scene.world=world
    mats=studio.make_materials()
    mats['green_enamel']=studio.material('Green enamel',(.14,.54,.31),roughness=.22,coat=.38)
    mats['gray_enamel']=studio.material('Pearl grey enamel',(.64,.71,.74),roughness=.22,coat=.32)
    mats['yellow_tile']=studio.material('Warm yellow ceramic',(.86,.73,.24),roughness=.46)
    mats['red_tile']=studio.material('Coral ceramic',(.70,.20,.14),roughness=.48)
    mats['blue_tile']=studio.material('Blue ceramic',(.14,.35,.60),roughness=.48)
    mats['gray_tile']=studio.material('Grey ceramic',(.49,.58,.61),roughness=.48)
    xmin,xmax,ymin,ymax,height=job['display_bounds']
    cx,cy=(xmin+xmax)/2,(ymin+ymax)/2;hx,hy=(xmax-xmin)/2,(ymax-ymin)/2
    box('Display plinth',(cx,cy,-.095),(hx+.04,hy+.04,.075),mats['metal'],.022)
    box('Porcelain floor',(cx,cy,-.017),(hx,hy,.017),mats['floor_mat'],.007)
    # Optical glass uses the exact Figure 1 shader, including restrained Fresnel.
    thick=.012
    for axis,side in [('x',xmin),('x',xmax),('y',ymin),('y',ymax)]:
        position=(side,cy,height/2) if axis=='x' else (cx,side,height/2)
        scale=(thick,hy,height/2) if axis=='x' else (hx,thick,height/2)
        obj=box('Optical glass '+axis+str(side),position,scale,mats['glass'],.003)
        obj.visible_shadow=False
    # Fine enclosure edges preserve the Figure 1 silhouette without heavy rails.
    radius=.008
    for x in [xmin,xmax]:
        for y in [ymin,ymax]:
            box('Glass vertical edge',(x,y,height/2),(radius,radius,height/2),mats['frame'],.002)
    for y in [ymin,ymax]:box('Glass top edge',(cx,y,height),(hx,radius*.65,radius*.65),mats['front_frame'] if y==ymin else mats['frame'],.002)
    for x in [xmin,xmax]:box('Glass top edge',(x,cy,height),(radius*.65,hy,radius*.65),mats['front_frame'] if x==xmax else mats['frame'],.002)
    # The top is open for the experiment close-up; the tall rear and side panes
    # retain the studio glass character while keeping the mechanism readable.
    for geom in job['fixtures']:
        c=geom['rgba'];kind='gray'
        if max(c[:3])-min(c[:3])>.15:
            kind='yellow' if c[0]>.5 and c[1]>.5 else 'red' if c[0]>c[2] else 'blue'
        box(geom['name'],geom['position'],geom['size'],mats[kind+'_tile'],.002)
    spheres={}
    for name,radius in job['radii'].items():
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,radius=radius)
        obj=bpy.context.object;obj.name=name
        for polygon in obj.data.polygons:polygon.use_smooth=True
        obj.visible_glossy=False
        obj.data.materials.append(mats['red_enamel']);spheres[name]=obj
    camera=bpy.data.cameras.new('Figure 1 orthographic experiment view')
    cam_obj=bpy.data.objects.new(camera.name,camera);bpy.context.collection.objects.link(cam_obj)
    camera.type='ORTHO';camera.sensor_fit='VERTICAL';camera.ortho_scale=job['camera']['span']
    cam_obj.location=job['camera']['position']
    cam_obj.rotation_euler=Vector(job['camera']['forward']).to_track_quat('-Z','Y').to_euler()
    scene.camera=cam_obj
    center=Vector((cx,cy,height*.35));unit=max(1.,min(3.,max(hx,hy)*.7))
    for name,offset,power,size,color,size_y in [
        ('Large warm key',(-3.5,-4.5,8),1250,5.5,(1,.94,.86),4),
        ('Cool fill',(5,1,6),700,5,(.83,.92,1),None),
        ('Upper edge strip',(-3,5,6),1000,4.5,(.87,.96,1),1.3),
        ('Front softbox',(1,-6,3.5),350,3,(1,1,1),4)]:
        studio.area(name,center+Vector(offset)*unit,center,power*unit*unit,size*unit,color,
                    size_y=(size_y or size)*unit,specular=.3)
    return scene,spheres,mats


def main():
    parser=argparse.ArgumentParser();parser.add_argument('job');parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--end',type=int);parser.add_argument('--step',type=int,default=1)
    args=parser.parse_args();job=json.loads(Path(args.job).read_text())
    scene,spheres,mats=setup(job)
    out=Path(job['output']);out.mkdir(parents=True,exist_ok=True)
    end=min(args.end or len(job['frames']),len(job['frames']))
    seen={}
    for index in range(args.start,end,args.step):
        target=out/f'{index:05}.png'
        t=time.time();frame=job['frames'][index]
        # Blender stores these transforms as float32. Reuse an identical render
        # while keeping the full-precision simulation clock and annotations.
        key=b''.join(name.encode()+struct.pack('fff',*value['position'])+struct.pack('ffff',*value['color']) for name,value in frame['objects'].items())
        if target.exists():seen.setdefault(key,target);continue
        if key in seen:
            shutil.copyfile(seen[key],target)
            continue
        seen[key]=target
        if 'reuse' in frame:
            # Duplicate a genuinely identical frozen state, including the
            # deliberate hold on the oracle-trigger frame.
            source=out/f"{frame['reuse']:05}.png"
            if source.exists():
                shutil.copyfile(source,target)
                continue
        for name,obj in spheres.items():
            data=frame['objects'][name];obj.location=data['position']
            c=data['color'];category='gray'
            if max(c[:3])-min(c[:3])>.15:category=['red','green','blue'][c[:3].index(max(c[:3]))]
            obj.data.materials[0]=mats[category+'_enamel']
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
        print(f"STUDIO {job['id']} frame {index}/{len(job['frames'])} {time.time()-t:.2f}s",flush=True)
    (out/f'worker-{args.start}.done').write_text('complete\n')


if __name__=='__main__':main()
