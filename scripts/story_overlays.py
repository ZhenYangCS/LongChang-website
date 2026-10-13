"""Measured vectors and clearly styled counterfactuals; no text over the action."""
import math
import numpy as np
from PIL import Image,ImageDraw

COLORS={'red_ball':'#c56859','blue_ball':'#547fa7','green_ball':'#549b74'}

def rgba(color,alpha=180):return tuple(int(color[i:i+2],16) for i in [1,3,5])+(alpha,)

def velocity_end(obj):
    p=np.array(obj['position']);v=np.array(obj['velocity']);v[2]=0
    length=np.linalg.norm(v)
    return p+np.array([0,0,.15])+v*(min(1.15,length*.16)/length if length else 0)

def focus_points(job):
    points=[]
    for frame in job['frames']:
        for name in job.get('reference_names',[]):points.extend([frame['reference_objects'][name]['position'],[*frame['reference_objects'][name]['position'][:2],0]])
        if job.get('story') in ['09','10','11','14']:
            points.extend(velocity_end(obj).tolist() for obj in frame['objects'].values())
        if job.get('story')=='15':points.append((np.array(frame['objects']['red_ball']['position'])+[0,1,.15]).tolist())
    if job.get('focus_fixtures'):
        for geom in job['fixtures']:
            for x in [-1,1]:
                for y in [-1,1]:points.append([geom['position'][0]+x*geom['size'][0],geom['position'][1]+y*geom['size'][1],geom['position'][2]])
    return points

def underlay(image,job,index,project):
    frame=job['frames'][index];id=job['story'];t=frame['time'];camera=job['camera'];w,h=image.size;ppu=h/camera['span']
    layer=Image.new('RGBA',image.size);draw=ImageDraw.Draw(layer)
    point=lambda p:tuple(project(camera,w,h,p))
    def arrow(a,b,color,alpha=230):
        a=np.array(point(a));b=np.array(point(b));v=b-a;length=np.linalg.norm(v)
        if length<3:return
        u=v/length;n=np.array([-u[1],u[0]]);head=min(length*.4,max(5,ppu*.07))
        draw.line([tuple(a),tuple(b)],fill=rgba(color,alpha),width=max(1,round(ppu*.018)))
        draw.polygon([tuple(b),tuple(b-u*head+n*head*.45),tuple(b-u*head-n*head*.45)],fill=rgba(color,alpha))
    stride=max(1,round(.06*job['film_duration']*60/job['simulation_duration']))
    past=job['frames'][:index+1:stride]
    if past and past[-1] is not frame:past=past+[frame]
    for name,obj in frame['objects'].items():
        if name=='green_ball' and id=='11':continue
        color=COLORS.get(name,'#687f85');points=[]
        for f in past:
            p=f['objects'][name]['position'];q=point([p[0],p[1],.012] if id=='10' else p)
            if not points or math.dist(q,points[-1])>max(1,ppu*.025):points.append(q)
        if len(points)>1:draw.line(points,fill=rgba(color,110),width=max(1,round(ppu*.008)))
        radius=max(1,ppu*.015)
        for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=rgba(color,210))
    for name in job.get('reference_names',[]):
        obj=frame['reference_objects'][name];color='#a58c84' if name=='red_ball' else '#8b9baa'
        positions=[point(f['reference_objects'][name]['position']) for f in past]
        for i in range(0,len(positions)-1,2):draw.line(positions[i:i+2],fill=rgba(color,210),width=max(1,round(ppu*.014)))
        x,y=point(obj['position']);r=job['radii'][name]*ppu
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(250,252,249,135))
        for start in range(0,360,50):draw.arc((x-r,y-r,x+r,y+r),start,start+30,fill=rgba(color,240),width=max(1,round(ppu*.015)))
    if id in ['09','10']:
        tile=next(g for g in job['fixtures'] if 'tile' in g['name']);x,y,z=tile['position'];hx,hy=tile['size'][:2]
        corners=[point([x+sx*hx,y+sy*hy,z+.006]) for sx,sy in [(-1,-1),(1,-1),(1,1),(-1,1),(-1,-1)]]
        draw.line(corners,fill=rgba('#b09447' if id=='10' else '#77938c',240),width=max(1,round(ppu*.012)))
    if id=='10':
        for name,obj in frame['objects'].items():
            p=np.array(obj['position']);floor=np.array([p[0],p[1],.015]);color=COLORS[name]
            for fraction in np.arange(0,1,.12):draw.line([point(p+(floor-p)*fraction),point(p+(floor-p)*min(1,fraction+.055))],fill=rgba(color),width=max(1,round(ppu*.008)))
            arrow(p+[0,0,.15],velocity_end(obj),color)
    if id=='09':
        obj=frame['objects']['red_ball'];arrow(np.array(obj['position'])+[0,0,.15],velocity_end(obj),COLORS['red_ball'])
    if id=='05':
        obj=frame['objects']['red_ball'];force=np.array(frame['oracle']['forces'].get('red_ball',[0,0,0]));force[2]=0;n=np.linalg.norm(force)
        if n>.05:
            a=np.array(obj['position'])+[0,0,.2];arrow(a,a+force/n*min(1.1,n*.04),'#bd634d')
    if id=='11' and any(e['time']<=t for e in job['rule_events'] if e['kind']=='separation_boost'):
        obj=frame['objects']['blue_ball'];arrow(np.array(obj['position'])+[0,0,.15],velocity_end(obj),COLORS['blue_ball'])
    if id=='14':
        for name in (['red_ball'] if t<.8 else ['green_ball'] if t>=12 else []):
            obj=frame['objects'][name];arrow(np.array(obj['position'])+[0,0,.15],velocity_end(obj),COLORS[name])
    if id=='15' and frame['oracle']['forces'].get('red_ball',[0,0,0])[1]>0:
        a=np.array(frame['objects']['red_ball']['position'])+[0,0,.2];arrow(a,a+[0,1,0],'#368b6e')
    for event in job.get('launch_events',[]):
        elapsed=t-event['time']
        if not 0<=elapsed<.8:continue
        name=event['command'].split()[1]
        if name not in frame['objects']:continue
        p=event['positions_before'][name];x,y=point(p);r=ppu*(.17+.07*elapsed)
        draw.ellipse((x-r,y-r*.65,x+r,y+r*.65),outline=rgba(COLORS.get(name,'#648377'),round(180*(1-elapsed/.8))),width=max(1,round(ppu*.012)))
    return Image.alpha_composite(image,layer)

def above(image,job,index,project):
    if job.get('story')!='14' or job['frames'][index]['time']<.8:return image
    draw=ImageDraw.Draw(image);obj=job['frames'][index]['objects']['red_ball'];x,y=project(job['camera'],job['width'],job['height'],obj['position']);r=job['height']/job['camera']['span']*.18
    for sx in [-1,1]:
        for sy in [-1,1]:
            a=(x+sx*r,y+sy*r);draw.line([(a[0]-sx*r*.4,a[1]),a,(a[0],a[1]-sy*r*.4)],fill='#6b8980',width=max(1,round(r*.1)))
    return image
