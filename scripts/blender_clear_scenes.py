"""Cycles background plus feathered dynamic render regions; exact recorded poses."""
import json,math,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont
import bpy
from blender_oracle import setup


def main():
    job=json.loads(Path(sys.argv[1]).read_text());folder=Path(job['output']);frames=folder/'frames';frames.mkdir(exist_ok=True)
    scene,balls,mats=setup(job)
    scene.cycles.adaptive_threshold=.012;scene.cycles.adaptive_min_samples=32
    scene.render.film_transparent=True
    def paper(path):
        im=Image.open(path).convert('RGBA');bg=Image.new('RGBA',im.size,'#f5f8f7');bg.alpha_composite(im);return bg.convert('RGB')
    w,h=job['width'],job['height'];camera=job['camera']
    pos=np.array(camera['position']);right=np.array(camera['right']);up=np.array(camera['up']);span=camera['span']
    def screen(p):
        d=np.array(p)-pos
        return np.array([(0.5+d@right/(span*w/h))*w,(0.5-d@up/span)*h])
    bgpath=folder/'background.png'
    if not bgpath.exists():
        for b in balls.values():b.hide_render=True
        scene.cycles.samples=256;scene.render.filepath=str(bgpath);bpy.ops.render.render(write_still=True)
    for b in balls.values():b.hide_render=False
    background=paper(bgpath)
    scene.cycles.samples=job['samples'];scene.render.use_border=True;scene.render.use_crop_to_border=True
    seen={}
    for index,frame in enumerate(job['frames']):
        dest=frames/f'{index:05}.png'
        key=json.dumps({n:[np.asarray(o['position'],dtype=np.float32).tolist(),o['color']] for n,o in frame['objects'].items()},sort_keys=True)
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
            path=folder/'region.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
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
        result.save(dest);seen[key]=dest
        print(f'FRAME {job["id"]} {index+1}/{len(job["frames"])} {time.time()-start:.2f}s',flush=True)
    print('DONE',job['id'],flush=True)


if __name__=='__main__':main()
