"""Render case-study geometry with the same Cycles studio as Figure 1."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image, ImageDraw, ImageFilter
from blender_oracle import setup, studio


def main():
    parser=argparse.ArgumentParser();parser.add_argument('job');parser.add_argument('--preview',action='store_true')
    parser.add_argument('--start',type=int,default=0);parser.add_argument('--end',type=int)
    args=parser.parse_args();job=json.loads(Path(args.job).read_text())
    folder=Path(job['output']);out=folder/'frames';out.mkdir(parents=True,exist_ok=True)
    scene,_,mats=setup(job)
    scene.cycles.adaptive_threshold=.015
    scene.cycles.adaptive_min_samples=min(32,job['samples'])
    # Match the close-up's scale while retaining the reference's large softboxes.
    for obj in scene.objects:
        if obj.name.startswith(('Optical glass','Glass vertical edge','Glass top edge')):
            obj.visible_camera=False
    objects={}

    def material(name,state):
        c=state['rgba']
        if max(c[:3])-min(c[:3])>.15:
            return mats[['red_enamel','green_enamel','blue_enamel'][int(np.argmax(c[:3]))]]
        if 'plate' in name or 'rim_' in name: return mats['ramp_mat']
        if 'plunger' in name: return mats['silver']
        return mats['metal'] if name.startswith('tool_') else mats['gray_enamel']

    def pose(obj,state):
        transform=Matrix(state['rotation']).to_4x4();transform.translation=Vector(state['position']);obj.matrix_world=transform
        obj.data.materials[0]=material(obj.name,state)

    for name,geometry in job['geometries'].items():
        state=next(frame[name] for frame in job['frames'] if name in frame)
        data={**geometry,**state,'material':'metal'}
        if geometry['kind']==5:
            bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=geometry['size'][0],depth=geometry['size'][1]*2)
            obj=bpy.context.object;obj.name=name;obj.data.materials.append(mats['silver'])
            bevel=obj.modifiers.new('Soft metal edge','BEVEL');bevel.width=min(.005,geometry['size'][0]*.08);bevel.segments=3
            obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
        else: obj=studio.geometry(data,mats)
        pose(obj,state);objects[name]=obj
    dynamic=[]
    for name,obj in objects.items():
        states=[frame.get(name) for frame in job['frames']]
        if any(state!=states[0] for state in states[1:]): dynamic.append(name)
    # Coated balls have the reference highlights; disabling secondary glossy
    # visibility avoids reflections outside a moving region's render boundary.
    for name in dynamic: objects[name].visible_glossy=False
    w,h=job['width'],job['height'];cam=job['camera'];span=cam['span']
    def screen(point):
        d=np.asarray(point)-cam['position']
        return np.array([(0.5+d@cam['right']/(span*w/h))*w,(0.5-d@cam['up']/span)*h])
    def flat(path):
        rgba=Image.open(path).convert('RGBA');bg=Image.new('RGBA',rgba.size,'#f5f8f7');bg.alpha_composite(rgba);return bg.convert('RGB')
    background_path=folder/'background.png'
    if not background_path.exists():
        for name in dynamic:objects[name].hide_render=True
        scene.cycles.samples=max(96,job['samples']);scene.render.filepath=str(background_path)
        bpy.ops.render.render(write_still=True)
    background=flat(background_path)
    scene.cycles.samples=job['samples']
    for name in dynamic:objects[name].hide_render=False
    seen={}
    frames=sorted({job['frame_map'][n] for n in [0,len(job['frame_map'])//2,len(job['frame_map'])-1]}) if args.preview else range(args.start,min(args.end or len(job['frames']),len(job['frames'])))
    for index in frames:
        target=out/f'{index:05}.png';frame=job['frames'][index]
        key=hashlib.sha256(b''.join(name.encode()+np.asarray(state['position']+state['rgba'],dtype='<f4').tobytes()
            +(np.asarray(state['rotation'],dtype='<f4').tobytes() if job['geometries'][name]['kind']!=2 else b'')
            for name,state in sorted(frame.items()))).hexdigest()
        if target.exists():seen[key]=target;continue
        if key in seen:target.hardlink_to(seen[key]);continue
        started=time.time()
        for name,obj in objects.items():
            obj.hide_render=name not in frame
            if name in frame:pose(obj,frame[name])
        bpy.context.view_layer.update()
        rects=[]
        for name in dynamic:
            if name not in frame:continue
            obj=objects[name]
            corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
            points=[screen(c) for c in corners]
            # Include the actual studio shadow footprint and a broad soft edge.
            for c in corners:
                z=max(0,c.z)
                for dx in [-.18,.18]:
                    for dy in [-.18,.18]:points.append(screen([c.x+.55*z+dx,c.y+.65*z+dy,.002]))
            points=np.array(points);lo=points.min(0)-18;hi=points.max(0)+18
            x0=max(0,math.floor(lo[0]));y0=max(0,math.floor(lo[1]));x1=min(w,math.ceil(hi[0]));y1=min(h,math.ceil(hi[1]))
            if x1<=x0 or y1<=y0:continue
            rect=[x0,y0,x1,y1]
            merged=True
            while merged:
                merged=False
                for old in list(rects):
                    if rect[0]<=old[2] and rect[2]>=old[0] and rect[1]<=old[3] and rect[3]>=old[1]:
                        rect=[min(rect[0],old[0]),min(rect[1],old[1]),max(rect[2],old[2]),max(rect[3],old[3])]
                        rects.remove(old);merged=True;break
            rects.append(rect)
        result=background.copy()
        for x0,y0,x1,y1 in rects:
                scene.render.use_border=True;scene.render.use_crop_to_border=True
                scene.render.border_min_x=(x0+.1)/w;scene.render.border_max_x=min(1,(x1+.1)/w)
                scene.render.border_min_y=(h-y1+.1)/h;scene.render.border_max_y=min(1,(h-y0+.1)/h)
                path=folder/f'region-{args.start}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
                region=flat(path)
                assert region.size==(x1-x0,y1-y0)
                mask=Image.new('L',region.size);draw=ImageDraw.Draw(mask)
                draw.rectangle((4,4,region.width-5,region.height-5),fill=255)
                mask=mask.filter(ImageFilter.GaussianBlur(1.5))
                # At image edges the render covers the complete scene boundary.
                if x0==0 or x1==w or y0==0 or y1==h:
                    mask=Image.new('L',region.size,255)
                result.paste(region,(x0,y0),mask)
        result.save(target);seen[key]=target
        print(f"{job['id']} {index+1}/{len(job['frames'])} {time.time()-started:.2f}s",flush=True)


if __name__=='__main__':main()
