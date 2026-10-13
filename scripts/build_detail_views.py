"""Readable close-ups using fixed-world coordinates and cached Cycles shading.

The full-room camera is retained. Close-ups only change the viewing window;
balls follow the same native states, with their original physical radii.
"""
import argparse,concurrent.futures,copy,hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import build_smooth_demos as smooth
from launch_cues import add_launch_cues
from render_clear_scenes import ROOM_BOUNDS,room_camera

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-detail-views')
WIDTH,HEIGHT=1600,800

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,separators=(',',':'))+'\n');temp.replace(path)

def project(camera,width,height,p):
    d=np.asarray(p)-camera['position'];span=camera['span']
    return np.array([(0.5+d@camera['right']/(span*width/height))*width,(0.5-d@camera['up']/span)*height])

def focus_crop(job):
    points=[];base=room_camera()
    for frame in job['frames']:
        for name,obj in frame['objects'].items():
            p=np.array(obj['position']);r=job['radii'][name]
            for shift in [[-r,0,0],[r,0,0],[0,0,-r],[0,0,r]]:points.append(project(base,1440,960,p+shift))
            points.append(project(base,1440,960,[p[0],p[1],0]))
    points=np.array(points);lo=points.min(0)-38;hi=points.max(0)+38
    width=min(1440,max(hi[0]-lo[0],(hi[1]-lo[1])*2,380));height=width/2
    cx,cy=(lo+hi)/2;cx=np.clip(cx,width/2,1440-width/2);cy=np.clip(cy,height/2,960-height/2)
    crop=[float(cx-width/2),float(cy-height/2),float(cx+width/2),float(cy+height/2)]
    camera=copy.deepcopy(base)
    camera['position']=(np.array(base['position'])+np.array(base['right'])*(cx/1440-.5)*base['span']*1.5+np.array(base['up'])*(.5-cy/960)*base['span']).tolist()
    camera['span']=base['span']*height/960
    return crop,camera

def prepare(id,entry):
    folder=CACHE/id;folder.mkdir(parents=True,exist_ok=True)
    if id=='10':
        old=smooth.CACHE;smooth.CACHE=CACHE/'native'
        try:smooth.prepare(id)
        finally:smooth.CACHE=old
        entry=json.loads((CACHE/'native'/id/'entry.json').read_text())
        source=json.loads((CACHE/'native'/id/'job.json').read_text())
        entry['record']='downloads/detail-demonstrations/scene-10.json'
        entry['continuous']=True
    else:source=json.loads((smooth.CACHE/id/'job.json').read_text())
    crop,camera=focus_crop(source)
    job=copy.deepcopy(source);job.update(camera=camera,width=WIDTH,height=HEIGHT,output=str(folder),samples=256,threads=10,reuse_jobs=[])
    write(folder/'job.json',job);write(folder/'entry.json',entry);write(folder/'crop.json',crop)
    return entry

def asset(job,dest):
    dest.mkdir(parents=True,exist_ok=True);path=dest/'asset.json';data=copy.deepcopy(job);data['output']=str(dest);write(path,data)
    with (dest/'asset.log').open('w') as log:
        subprocess.run(['/root/.virtualenvs/longchang-blender/bin/python',str(SITE/'scripts/render_focus_assets.py'),str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    return dest/'background.png'

def flat(path):
    im=Image.open(path).convert('RGBA');bg=Image.new('RGBA',im.size,'#f5f8f7');bg.alpha_composite(im);return bg

def place(canvas,sprite,x,y):
    x-=sprite.width/2;y-=sprite.height/2;ix,iy=math.floor(x),math.floor(y)
    shifted=sprite.transform((sprite.width+2,sprite.height+2),Image.Transform.AFFINE,(1,0,-1-(x-ix),0,1,-1-(y-iy)),Image.Resampling.BICUBIC).convert('RGBA')
    canvas.alpha_composite(shifted,(ix-1,iy-1))

def compose(job,background,sprites,index):
    frame=job['frames'][index];w,h=job['width'],job['height'];camera=job['camera'];ppu=h/camera['span']
    im=background.copy();draw=ImageDraw.Draw(im)
    if job['id']=='10':
        outline=[project(camera,w,h,p) for p in [(-2,-2,.006),(2,-2,.006),(2,2,.006),(-2,2,.006),(-2,-2,.006)]]
        draw.line([tuple(p) for p in outline],fill='#c6a147',width=3)
    # Projected soft shadows provide depth without changing any object state.
    shadow_layer=Image.new('RGBA',im.size)
    for name,obj in frame['objects'].items():
        p=np.array(obj['position']);radius=job['radii'][name];z=max(0,p[2]-radius)
        center=project(camera,w,h,[p[0]+.35*z,p[1]+.45*z,.006]);extent=(radius*1.8+z*.18)*ppu
        sw=max(3,round(extent*2));sh=max(3,round(extent*1.1));disc=Image.new('RGBA',(sw,sh));dd=ImageDraw.Draw(disc)
        opacity=55/(1+z*1.5)
        for layer in range(15,0,-1):
            scale=layer/15;alpha=round(opacity*(1-scale)*.28)
            dd.ellipse((sw/2-sw*scale/2,sh/2-sh*scale/2,sw/2+sw*scale/2,sh/2+sh*scale/2),fill=(50,70,77,alpha))
        shadow_layer.alpha_composite(disc,(round(center[0]-sw/2),round(center[1]-sh/2)))
    im=Image.alpha_composite(im,shadow_layer)
    if job['id']=='10':
        draw=ImageDraw.Draw(im)
        for name,color in [('red_ball','#bd7464'),('blue_ball','#7399b9')]:
            p=frame['objects'][name]['position'];floor=project(camera,w,h,[p[0],p[1],.008]);center=project(camera,w,h,p)
            # Show the footprint beneath an airborne ball, where the rule acts.
            for fraction in np.arange(0,1,.1):
                a=center+(floor-center)*fraction;b=center+(floor-center)*min(1,fraction+.045)
                draw.line([tuple(a),tuple(b)],fill=color,width=2)
            draw.ellipse((floor[0]-8,floor[1]-4,floor[0]+8,floor[1]+4),fill=color)
            start=max(0,index-60);points=[tuple(project(camera,w,h,f['objects'][name]['position'])) for f in job['frames'][start:index+1:4]]
            if len(points)>1:draw.line(points,fill=color,width=3)
    ordered=sorted(frame['objects'].items(),key=lambda pair:np.dot(np.asarray(pair[1]['position'])-camera['position'],camera['forward']),reverse=True)
    for name,obj in ordered:
        c=obj['color'];color=['red','green','blue'][int(np.argmax(c[:3]))] if max(c[:3])-min(c[:3])>.15 else 'gray'
        size=max(8,round(job['radii'][name]*2.4*ppu));key=(color,size)
        if key not in sprites:sprites[key]=sprites[color].convert('RGBa').resize((size,size),Image.Resampling.LANCZOS)
        p=project(camera,w,h,obj['position']);place(im,sprites[key],p[0],p[1])
    draw=ImageDraw.Draw(im);font=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),46 if job['id']=='10' else 34)
    if job['id'] in ['10','12']:
        for n,(name,obj) in enumerate(frame['objects'].items()):
            p=project(camera,w,h,obj['position']);r=job['radii'][name]*ppu
            text=f"{obj['velocity'][0]:.1f}" if job['id']=='10' else 'AB'[n]
            color=('#ae574a' if name=='red_ball' else '#426f99') if job['id']=='10' else '#446d60'
            tw=draw.textlength(text,font=font);x=p[0];y=p[1]-r-36
            draw.rounded_rectangle((x-tw/2-10,y-27,x+tw/2+10,y+28),radius=8,fill='#f8fbf9')
            draw.text((x,y),text,font=font,fill=color,anchor='mm')
    if job['id']=='10':draw.text((30,h-42),'Forward speed',font=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),28),fill='#638276')
    if frame.get('fade',0)>0:
        im=Image.blend(im,Image.new('RGBA',im.size,'#f5f8f7'),frame['fade'])
        if frame['fade']>.95:ImageDraw.Draw(im).text((w/2,h/2),'Next trial',font=font,fill='#648375',anchor='mm')
    return im.convert('RGB')

def encode(job,background,sprites,video,ffmpeg,poster):
    video.parent.mkdir(exist_ok=True);tmp=video.with_name(video.stem+'.partial.mp4')
    process=subprocess.Popen([ffmpeg,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f"{job['width']}x{job['height']}",'-r','60','-i','-','-an','-c:v','libx264','-preset','fast','-crf','16','-g','60','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)],stdin=subprocess.PIPE)
    try:
        for i in range(len(job['frames'])):
            frame=compose(job,background,sprites,i)
            if i==0:frame.save(poster,quality=96,method=6)
            process.stdin.write(frame.tobytes())
        process.stdin.close();assert process.wait()==0;tmp.replace(video)
    finally:
        if process.poll() is None:process.kill();process.wait()

def render(id,ffmpeg,sample=False):
    folder=CACHE/id;job=json.loads((folder/'job.json').read_text());entry=json.loads((folder/'entry.json').read_text());crop=json.loads((folder/'crop.json').read_text())
    background=flat(asset(job,folder))
    sprites={name:Image.open(CACHE/'sprites'/f'{name}.png').convert('RGBA') for name in ['red','blue','green','gray']}
    if sample:
        compose(job,background,sprites,min(len(job['frames'])-1,round(len(job['frames'])*.72))).save(folder/'sample.png');return entry
    video=SITE/f'assets/videos/detail/scene-{id}.mp4';poster=SITE/f'assets/images/detail-{id}.webp'
    encode(job,background,sprites,video,ffmpeg,poster)
    if id in ['12','13']:video=add_launch_cues(ffmpeg,video,video.with_name(video.stem+'-cued.mp4'),entry)
    entry.update(detail_video=str(video.relative_to(SITE)),detail_poster=str(poster.relative_to(SITE)),detail_video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                 detail_dimensions=[WIDTH,HEIGHT],detail_crop=crop,detail_camera=job['camera'],
                 detail_render='Cycles room and spherical lighting, native positions, projected soft shadows.')
    whole=copy.deepcopy(job);whole.update(camera=room_camera(),width=1440,height=960)
    whole_bg=flat(asset(whole,folder/'room'))
    context=SITE/f'assets/images/context-{id}.webp';whole_bg.convert('RGB').resize((360,240),Image.Resampling.LANCZOS).save(context,quality=85)
    entry['context_poster']=str(context.relative_to(SITE))
    if id=='10':
        overview=SITE/'assets/videos/zone/scene-10.mp4';overview_poster=SITE/'assets/images/zone-10.webp';encode(whole,whole_bg,sprites,overview,ffmpeg,overview_poster)
        (SITE/entry['record']).parent.mkdir(exist_ok=True);(SITE/entry['record']).write_bytes((CACHE/'native/10/record.json').read_bytes())
        entry.update(video=str(overview.relative_to(SITE)),poster=str(overview_poster.relative_to(SITE)),studio_poster=str(overview_poster.relative_to(SITE)),video_sha256=hashlib.sha256(overview.read_bytes()).hexdigest(),room_signature=json.loads((SITE/'data/shared-room.json').read_text())['render_signature'])
    print('DETAIL READY',id,flush=True);return entry

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=6);parser.add_argument('--only',nargs='*');parser.add_argument('--sample',action='store_true');args=parser.parse_args()
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'));chosen=args.only or [e['id'] for e in entries]
    CACHE.mkdir(exist_ok=True)
    for entry in entries:
        if entry['id'] in chosen:prepare(entry['id'],entry)
    sprite_job=json.loads((CACHE/chosen[0]/'job.json').read_text());sprite_job.update(sprites=True,radii={'sprite':.1},fixtures=[],camera=room_camera())
    asset(sprite_job,CACHE/'sprites')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:results=list(pool.map(lambda id:render(id,args.ffmpeg,args.sample),chosen))
    if args.sample:return
    updates={e['id']:e for e in results};target=SITE/'data/physics.js';temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps([updates.get(e['id'],e) for e in entries],separators=(',',':'))+';\n');temp.replace(target)
    print('All close-ups published.',flush=True)

if __name__=='__main__':main()
