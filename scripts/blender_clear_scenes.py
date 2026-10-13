"""Cycles background plus feathered dynamic render regions; exact recorded poses."""
import json,math,sys,time,hashlib,fcntl
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
import bpy
from blender_oracle import setup


def main():
    job=json.loads(Path(sys.argv[1]).read_text());folder=Path(job['output']);frames=folder/'frames';frames.mkdir(exist_ok=True)
    start_index=int(sys.argv[2]) if len(sys.argv)>2 else 0
    end_index=int(sys.argv[3]) if len(sys.argv)>3 else len(job['frames'])
    scene,balls,mats=setup(job)
    bpy.context.view_layer.update()
    # Compare the constructed Blender objects, not only an aspect-ratio setting.
    signature={}
    for obj in scene.objects:
        if obj.type in {'CAMERA','LIGHT'} or obj.name.startswith(('Display plinth','Porcelain floor','Optical glass','Glass vertical edge','Glass top edge')):
            item=dict(type=obj.type,matrix=[list(row) for row in obj.matrix_world])
            if obj.type=='MESH':item.update(bounds=[list(c) for c in obj.bound_box],materials=[m.name for m in obj.data.materials])
            if obj.type=='CAMERA':item.update(ortho_scale=obj.data.ortho_scale)
            if obj.type=='LIGHT':item.update(energy=obj.data.energy,color=list(obj.data.color),size=obj.data.size,size_y=obj.data.size_y)
            signature[obj.name]=item
    (folder/'room-signature.json').write_text(json.dumps(signature,sort_keys=True))
    scene.cycles.adaptive_threshold=.012;scene.cycles.adaptive_min_samples=32
    scene.render.film_transparent=True
    def paper(path):
        im=Image.open(path).convert('RGBA');bg=Image.new('RGBA',im.size,'#f5f8f7');bg.alpha_composite(im);return bg.convert('RGB')
    w,h=job['width'],job['height'];camera=job['camera']
    pos=np.array(camera['position']);right=np.array(camera['right']);up=np.array(camera['up']);span=camera['span']
    def screen(p):
        d=np.array(p)-pos
        return np.array([(0.5+d@right/(span*w/h))*w,(0.5-d@up/span)*h])
    bgkey=hashlib.sha256(json.dumps([job['display_bounds'],job['camera'],job['fixtures']],sort_keys=True).encode()).hexdigest()[:16]
    backgrounds=Path(job.get('shared_backgrounds',folder));backgrounds.mkdir(parents=True,exist_ok=True)
    bgpath=backgrounds/f'{bgkey}.png'
    with (backgrounds/f'{bgkey}.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not bgpath.exists():
            for b in balls.values():b.hide_render=True
            scene.cycles.samples=256;scene.render.filepath=str(bgpath.with_suffix('.partial.png'));bpy.ops.render.render(write_still=True)
            bgpath.with_suffix('.partial.png').replace(bgpath)
        fcntl.flock(lock,fcntl.LOCK_UN)
    for b in balls.values():b.hide_render=False
    background=paper(bgpath)
    scene.cycles.samples=job['samples'];scene.render.use_border=True;scene.render.use_crop_to_border=True
    def pose_key(frame):
        return json.dumps({n:[np.asarray(o['position'],dtype=np.float32).tolist(),o['color']] for n,o in frame['objects'].items()},sort_keys=True)+':'+format(float(frame.get('fade',0)),'.5f')
    seen={}
    for path in job.get('reuse_jobs',[]):
        old=json.loads(Path(path).read_text())
        if old['display_bounds']!=job['display_bounds'] or old['camera']!=job['camera']:continue
        for i,frame in enumerate(old['frames']):
            image_path=Path(old['output'])/'frames'/f'{i:05}.png'
            if image_path.exists():seen[pose_key(frame)]=image_path
    for index in range(start_index,min(end_index,len(job['frames']))):
        frame=job['frames'][index]
        dest=frames/f'{index:05}.png'
        key=pose_key(frame)
        if dest.exists():seen[key]=dest;continue
        if key in seen:
            dest.hardlink_to(seen[key]);continue
        if 'reuse' in frame and (frames/f'{frame["reuse"]:05}.png').exists():
            dest.hardlink_to(frames/f'{frame["reuse"]:05}.png');seen[key]=dest;continue
        start=time.time();rects=[]
        for name,obj in balls.items():
            data=frame['objects'][name];obj.location=data['position'];c=data['color'];category='gray'
            if max(c[:3])-min(c[:3])>.15:category=['red','green','blue'][c[:3].index(max(c[:3]))]
            obj.data.materials[0]=mats[category+'_enamel']
            x,y,z=data['position'];radius=job['radii'][name]
            pad=radius*3+.08;shadow=pad+z*.65
            corners=[screen((x+dx,y+dy,zz)) for dx in [-radius*1.5,radius*1.5] for dy in [-radius*1.5,radius*1.5] for zz in [z-radius*1.5,z+radius*1.5]]
            ground=[screen((x+dx,y+dy,.015)) for dx in [-shadow,shadow] for dy in [-shadow,shadow]]
            for region_points in [corners,ground]:
                points=np.array(region_points);lo=points.min(axis=0)-18;hi=points.max(axis=0)+18
                rect=[max(0,math.floor(lo[0])),max(0,math.floor(lo[1])),min(w,math.ceil(hi[0])),min(h,math.ceil(hi[1]))]
                # Merge overlapping regions so colliding balls share one render.
                merged=True
                while merged:
                    merged=False
                    for old in list(rects):
                        if rect[0]<=old[2] and rect[2]>=old[0] and rect[1]<=old[3] and rect[3]>=old[1]:
                            rect=[min(rect[0],old[0]),min(rect[1],old[1]),max(rect[2],old[2]),max(rect[3],old[3])];rects.remove(old);merged=True;break
                rects.append(rect)
        result=background.copy()
        for part,(x0,y0,x1,y1) in enumerate(rects):
            scene.render.border_min_x=(x0+.1)/w;scene.render.border_max_x=min(1,(x1+.1)/w)
            scene.render.border_min_y=(h-y1+.1)/h;scene.render.border_max_y=min(1,(h-y0+.1)/h)
            path=folder/f'region-{start_index}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            region=paper(path)
            assert region.size==(x1-x0,y1-y0),(region.size,(x1-x0,y1-y0))
            mask=Image.new('L',region.size);draw=ImageDraw.Draw(mask)
            draw.rectangle((9,9,region.width-10,region.height-10),fill=255)
            mask=mask.filter(ImageFilter.GaussianBlur(4))
            result.paste(region,(x0,y0),mask)
        if job['id']=='12':
            draw=ImageDraw.Draw(result);font=ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'assets/fonts/type-0.ttf'),19)
            for j,obj in enumerate(frame['objects'].values()):
                px,py=screen(obj['position']);py-=29
                draw.rounded_rectangle((px-13,py-12,px+13,py+12),radius=5,fill='#f5f8f7',outline='#91aba4')
                draw.text((px-6,py-11),'AB'[j],font=font,fill='#365f53')
        if frame.get('fade',0)>0:
            result=Image.blend(result,Image.new('RGB',result.size,'#f5f8f7'),frame['fade'])
            if frame['fade']>.95:
                draw=ImageDraw.Draw(result);font=ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'assets/fonts/type-0.ttf'),28)
                draw.text((w/2,h/2),'Next trial',anchor='mm',font=font,fill='#648375')
        result.save(dest);seen[key]=dest
        print(f'FRAME {job["id"]} {index+1}/{len(job["frames"])} {time.time()-start:.2f}s',flush=True)
    print('DONE',job['id'],flush=True)


if __name__=='__main__':main()
