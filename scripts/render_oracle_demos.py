"""New controlled oracle demonstrations with measured program effects.

Each altered scene is paired with the same geometry, masses and actions under
ordinary physics (the altered program is disabled only in that reference).
The native callback is observed, not changed: exact before/after velocities,
color changes, added forces and event times are recorded for explanation.
"""
from __future__ import annotations
import argparse
import os
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import textwrap
import concurrent.futures

from render_physics_demos import (SITE, ROOT, SOURCE, SPECS, World, load_scene,
                                 demonstration, arrange, launch, camera_for,
                                 Renderer, mujoco, np, Image, ImageDraw, ImageFont)
from oracle_catalog import catalog


def plan(number):
    world,spec=demonstration(number)
    if number=='09':
        spec['simulation_duration']=2.0
        spec['events']=[
            dict(time=0,kind='launch',command='PUSH red_ball 0 4',caption='Entry trial: cross into the gray footprint.'),
            dict(time=1.1,kind='arrange',positions={'red_ball':[3.2,0,.1]},caption='Exit trial: prepare the same ball just inside the boundary.'),
            dict(time=1.12,kind='launch',command='PUSH red_ball 0 4',caption='Cross out. The remaining velocity is multiplied by 2.5.'),
            dict(time=1.3,kind='arrange',positions={'red_ball':[-.3,0,1.5]},caption='Height control: prepare a crossing above the tile.'),
            dict(time=1.32,kind='launch',command='PUSH red_ball 0 4',caption='The boundary rule also acts in the air.')]
        spec['setup']='Three new trials: enter, leave, then enter above the tile. The same ball is repositioned between trials.'
    if number=='10':
        spec['simulation_duration']=5.0
        spec['events']=[
            dict(time=2.5,kind='arrange',positions={'red_ball':[-.8,0,1.8]},caption='Second trial: start above the active region.'),
            dict(time=2.52,kind='launch',command='PUSH red_ball 0 1',caption='Now watch the velocity amplification, not only the resting seed.')]
        spec['setup']='First release from rest inside the region; then launch above it to expose the amplification update.'
    if number=='15':
        spec['simulation_duration']=20.0
        spec['events']=[
            dict(time=1,kind='launch',command='PUSH blue_ball 0 0',caption='Zero impulse: the force stays active.'),
            dict(time=2,kind='launch',command='PUSH blue_ball 0 1',caption='Nonzero push: pause until count 12.'),
            dict(time=6,kind='launch',command='PUSH blue_ball 0 1',caption='Push again: the ten-count pause now ends at count 16.')]
        spec['setup']='Compare a zero push, a nonzero push on blue, and a second push that restarts the shared timer.'
    spec['duration']=14 if number in ['09','10','12','13','14','15'] else 12
    if number=='15':spec['duration']=16
    definition=copy.deepcopy(SPECS[int(number)-1]);definition['program']={}
    reference=World(load_scene(definition));reference._motion=None
    arrange(reference,spec['initial_positions'])
    return world,reference,spec


class Probe:
    """Observe the actual oracle callback without modifying its result."""
    def __init__(self,world,number,focus):
        self.world=world;self.number=int(number);self.focus=focus
        self.events=[];self.energy=0.;self.forces={};self.last_force=None
        self.modes={};self.last_update=None;self.initial_frame=None
        callback=world.scene.hook
        def observe(model,data):
            before={name:data.qvel[world.bodies[name][1]:world.bodies[name][1]+3].copy() for name in focus}
            colors={name:model.geom_rgba[model.body_geomadr[model.body(name).id]].copy() for name in focus}
            old_count=max(getattr(world.scene.state,'_count',{}).values(),default=0)
            callback(model,data)
            now=float(data.time)
            changes=[]
            for name in focus:
                q,d=world.bodies[name];bid=model.body(name).id
                after=data.qvel[d:d+3].copy();old=before[name]
                self.forces[name]=data.xfrc_applied[bid,:3].copy().tolist()
                rgba=model.geom_rgba[model.body_geomadr[bid]]
                changed=not np.allclose(old,after,atol=1e-9,rtol=0)
                if changed and self.number in [7,9,11,13,14]:
                    ratio=float(np.linalg.norm(after)/np.linalg.norm(old)) if self.number in [9,11] and np.linalg.norm(old)>1e-8 else None
                    if self.number==7:ratio=float(after[2]/abs(old[2])) if abs(old[2])>1e-8 else None
                    changes.append(dict(object=name,before=old.tolist(),after=after.tolist(),ratio=ratio,position=data.qpos[q:q+3].copy().tolist()))
                if self.number==10 and changed:
                    gain=.5*float(model.body_mass[bid])*(float(after@after)-float(old@old))
                    self.energy+=gain
                    mode='seed' if np.linalg.norm(old)<.35 else 'amplify'
                    if self.modes.get(name)!=mode:
                        self.events.append(dict(time=now,kind=mode,object=name,before=old.tolist(),after=after.tolist(),energy_added=gain))
                    self.modes[name]=mode
                if self.number==12 and not np.array_equal(colors[name],rgba):
                    changes.append(dict(object=name,before=colors[name].tolist(),after=rgba.copy().tolist()))
            if changes:
                kind={7:'rebound',9:'boundary',11:'separation_boost',12:'color_swap',13:'upward_kick',14:'velocity_copy'}[self.number]
                self.last_update=dict(time=now,kind=kind,changes=changes)
                self.events.append(self.last_update)
            if self.number==13:
                count=max(getattr(world.scene.state,'_count',{}).values(),default=0)
                if count!=old_count:self.events.append(dict(time=now,kind='contact_count',count=count))
            if self.number==15:
                active=abs(self.forces['red_ball'][1])>1e-8
                if active!=self.last_force:
                    self.events.append(dict(time=now,kind='force_on' if active else 'force_off',force=self.forces['red_ball'][1]))
                    self.last_force=active
            if abs(now)<1e-9:
                # Observe the actual first callback at t=0, before integration.
                # This avoids displaying the temporary cleared-force buffer as
                # if a force-based oracle were initially inactive.
                self.initial_frame=snapshot(world,focus,0,self)
        world.scene.hook=observe

    def snapshot(self):
        state=self.world.scene.state
        pending=getattr(state,'_pending',[])
        return dict(forces=copy.deepcopy(self.forces),energy_added=self.energy,
                    contact_count=max(getattr(state,'_count',{}).values(),default=0),
                    quiet_until=float(getattr(state,'_quiet_until',0)),
                    echo_due=float(pending[0][0]) if pending else None)


def snapshot(world,focus,epoch,probe=None):
    objects={}
    for name in focus:
        q,d=world.bodies[name];bid=world.model.body(name).id
        g=world.model.body_geomadr[bid]
        objects[name]=dict(position=world.data.qpos[q:q+3].copy().tolist(),
                           velocity=world.data.qvel[d:d+3].copy().tolist(),
                           color=world.model.geom_rgba[g].copy().tolist())
    return dict(time=float(world.data.time),epoch=epoch,objects=objects,
                qpos=world.data.qpos.copy(),qvel=world.data.qvel.copy(),rgba=world.model.geom_rgba.copy(),
                gravity=world.model.opt.gravity.copy().tolist(),oracle=probe.snapshot() if probe else {})


def record(number,sample_stride=5):
    world,reference,spec=plan(number)
    probe=Probe(world,number,spec['focus'])
    frames,refs=[],[];epoch=0;cursor=0
    xml=world.model_xml();events=copy.deepcopy(spec['events'])
    ticks=round(spec['simulation_duration']/.002)
    for tick in range(ticks+1):
        now=float(world.data.time)
        while cursor<len(events) and events[cursor]['time']<=now+.00001:
            event=events[cursor]
            event['positions_before']={name:world.data.qpos[world.bodies[name][0]:world.bodies[name][0]+3].copy().tolist() for name in spec['focus']}
            for current in [world,reference]:
                if event['kind']=='arrange':arrange(current,event['positions'])
                elif event['kind']=='hold':current.workshop.grasp(current,event['object'])
                else:launch(current,event['command'])
            if event['kind']=='arrange':epoch+=1
            event['actual_time']=now;cursor+=1
        if tick%sample_stride==0 or tick==ticks:
            frames.append(snapshot(world,spec['focus'],epoch,probe))
            refs.append(snapshot(reference,spec['focus'],epoch))
        if tick<ticks:
            world.step();reference.step()
    if probe.initial_frame is not None:frames[0]=probe.initial_frame
    peaks={name:max(f['objects'][name]['position'][2] for f in frames) for name in spec['focus']}
    initial_speeds={name:float(np.linalg.norm(frames[0]['objects'][name]['velocity'])) for name in spec['focus']}
    return world,xml,frames,refs,{**spec,'events':events,'oracle_events':probe.events,
                                 'maximum_heights':peaks,'initial_speeds':initial_speeds}


def plot_data(number,frames,refs):
    n=int(number)
    def get(f,idx=0):return list(f['objects'].values())[idx]
    def speed(o):return float(np.linalg.norm(o['velocity']))
    def value(f,index=0,ref=False):
        o=get(f,index)
        if n in [1,3,13]:return o['position'][2]
        if n==2:return float(np.linalg.norm(f['oracle'].get('forces',{}).get(list(f['objects'])[index],[0,0,0])))
        if n==4:return -f['gravity'][2]/9.81
        if n in [5,8,9,11,14]:return speed(o)
        if n==6:return f['oracle'].get('forces',{}).get('red_ball',[0,0,0])[1]
        if n==7:return o['velocity'][2]
        if n==10:return f['oracle'].get('energy_added',0)
        if n==12:return o['color'][0]
        return f['oracle'].get('forces',{}).get('red_ball',[0,0,0])[1]
    primary=1 if n in [8,11,14] else 0
    second_actual=n in [1,2,3,7,12]
    secondary=2 if n==2 else 1
    a=[value(f,primary) for f in frames]
    b=[value(f,secondary) for f in frames] if second_actual else [value(f,primary,True) for f in refs]
    labels={1:['Above gray tile','Ordinary floor'],2:['Red pair force','Blue pair force'],3:['Light red','Heavy blue'],7:['Red tile','Blue tile'],12:['Object A','Object B']}.get(n,['Oracle active','Ordinary physics reference'])
    return dict(times=[round(f['time'],4) for f in frames],series=[a,b],labels=labels,
                colors=['#c7795d','#688fb8' if second_actual else '#a6b2a3'])


def checkpoints(number,spec,frames):
    events=spec['oracle_events'];n=int(number)
    find=lambda kind,default:next((e['time'] for e in events if e['kind']==kind),default)
    impact={'01':.54,'02':.23,'03':.59,'04':4.5,'05':.1,'06':.45,'07':find('rebound',.54),
            '08':0,'09':find('boundary',.25),'10':2.52,'11':find('separation_boost',.24),
            '12':find('color_swap',.22),'13':find('upward_kick',3.23),
            '14':find('velocity_copy',12),'15':find('force_on',0)}[number]
    if n==15:impact=next(e['time'] for e in events if e['kind']=='force_on' and e['time']>6)
    # A short pause at the defining event and a visible aftermath; all sampling
    # remains monotonic. Long waits are compressed, never omitted from clocks.
    duration=spec['simulation_duration'];film=spec['duration']
    if n==5:
        anchors=[[0,0],[6,.3],[8,.6],[12,duration]]
    elif n==9:
        anchors=[[0,0],[3,.256],[4,.28],[5,1.1],[7,1.204],[8,1.224],[9,1.3],[11,1.52],[12,1.55],[14,2.0]]
    elif n==15:
        anchors=[[0,0],[2,1],[3.5,2],[5,2.05],[6.5,6],[8,6.05],[10,15.95],[11,16.02],[12,16.02],[16,20]]
    elif n==14:
        early=.2 if n==14 else 6
        anchors=[[0,0],[2,early],[5,max(early,impact-.04)],[7,impact+.02],[8,impact+.02],[film,duration]]
    elif n in [11,12,13,7,9]:
        anchors=[[0,0],[film*.38,max(0,impact-.025)],[film*.49,impact+.02],[film*.61,impact+.02],[film,duration]]
    else:anchors=[[0,0],[film,duration]]
    chapters=[dict(label='Set up',time=0),dict(label='Trigger the oracle',time=film*.49 if n not in [14,15] else 7),dict(label='See the effect',time=film*.76 if n not in [14,15] else 10)]
    if n==9:chapters=[dict(label='Entry ×0.4',time=3.5),dict(label='Exit ×2.5',time=7.8),dict(label='Above the tile',time=12)]
    if n==3:chapters=[dict(label='Matched release',time=0),dict(label='Different accelerations',time=4.5),dict(label='Red lands first',time=6)]
    if n==5:chapters=[dict(label='Strong launch',time=0),dict(label='Brake ON',time=3.5),dict(label='Below threshold',time=9.5)]
    if n==7:chapters=[dict(label='Matched release',time=0),dict(label='Impact updates',time=6),dict(label='Different rebounds',time=8)]
    if n==13:chapters=[dict(label='First contact',time=.7),dict(label='Second contact',time=3),dict(label='Third contact: jump',time=9.45)]
    if n==14:chapters=[dict(label='Launch & hold red',time=2.1),dict(label='12-count trigger',time=7.2),dict(label='Green responds',time=10)]
    if n==15:chapters=[dict(label='Zero impulse',time=2.6),dict(label='Reset the pause',time=6.8),dict(label='Force returns',time=13)]
    return anchors,chapters


def mapped_time(mapping,video_time):
    for (a,t0),(b,t1) in zip(mapping,mapping[1:]):
        if video_time<=b:return t0+(t1-t0)*(video_time-a)/(b-a)
    return mapping[-1][1]


def atomic_json(path,value,prefix=''):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(prefix+json.dumps(value,ensure_ascii=False,separators=(',',':'))+(';' if prefix else '')+'\n')
    temp.replace(path)


def studio_job(number,frames,spec,output,*,samples=32,threads=16,width=900,height=650):
    source=SPECS[int(number)-1]
    positions=np.asarray([o['position'] for f in frames for o in f['objects'].values()])
    lo=positions.min(axis=0);hi=positions.max(axis=0)
    fixtures=[e for e in source['entities'] if e['kind']=='fixture']
    for geom in fixtures:
        p=np.asarray(geom['position']);r=np.asarray(geom['size'])
        lo[:2]=np.minimum(lo[:2],(p-r)[:2]);hi[:2]=np.maximum(hi[:2],(p+r)[:2])
    center=(lo+hi)/2
    half=np.maximum((hi-lo)[:2]/2+.38,[1.05,.8])
    zmax=max(hi[2]+.5,max(half)*.68)
    bounds=[center[0]-half[0],center[0]+half[0],center[1]-half[1],center[1]+half[1],zmax]
    # Orthographic direction echoes Figure 1 while exposing the floor and height.
    direction=np.array([7.,-10.,8.]);direction/=np.linalg.norm(direction)
    forward=-direction;right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    corners=np.array([[x,y,z] for x in bounds[:2] for y in bounds[2:4] for z in [-.18,zmax]])
    u,v=corners@right,corners@up
    span=max(np.ptp(v),np.ptp(u)/(width/height))*1.08
    look=right*((min(u)+max(u))/2)+up*((min(v)+max(v))/2)
    cam=dict(position=(look+direction*30).tolist(),forward=forward.tolist(),right=right.tolist(),up=up.tolist(),span=float(span))
    return dict(id=number,width=width,height=height,samples=samples,threads=threads,
                display_bounds=bounds,camera=cam,fixtures=fixtures,
                radii={e['name']:e['size'][0] for e in source['entities'] if e['name'] in spec['focus']},
                output=str(output),frames=[dict(time=f['time'],objects=f['objects']) for f in frames],
                presentation='Figure 1 materials and studio lighting. Cropped floor and glass enclosure are display-only; native body positions and dimensions are preserved.')


def explanation(number,frame,spec):
    n=int(number);t=frame['time'];oracle=frame['oracle'];objects=list(frame['objects'].values())
    speed=lambda obj:float(np.linalg.norm(obj['velocity']))
    events=[e for e in spec['oracle_events'] if e['time']<=t+.00001]
    if n==9:
        epoch_time=max([e['time'] for e in spec['events'] if e['kind']=='arrange' and e['time']<=t]+[0])
        events=[e for e in events if e['time']>=epoch_time]
    event=next((e for e in reversed(events) if e.get('changes')),None)
    heading='The oracle is visible in the measurements.';values=[];active=False
    if n==1:
        heading='The tile changes appearance, not motion.'
        values=[['Height difference',f"{abs(objects[0]['position'][2]-objects[1]['position'][2]):.4f} bricks"],['Oracle effect','None · ordinary control']]
    elif n==2:
        force=np.linalg.norm(oracle['forces'].get('red_ball_1',[0,0,0]));active=force>.01
        heading='Red attracts red. The blue pair stays still.'
        values=[['Red-pair attraction',f'{force:.2f} force units'],['Blue-pair attraction','0.00']]
    elif n==3:
        active=objects[1]['position'][2]>objects[0]['position'][2]+.03
        heading='Heavier blue falls more slowly.'
        values=[['Light red · mass 1',f"z = {objects[0]['position'][2]:.3f}"],['Heavy blue · mass 4',f"z = {objects[1]['position'][2]:.3f}"]]
    elif n==4:
        active=True;heading='One launch impulse. Different gravity phases.'
        values=[['Red apex · stronger gravity',f"{spec['maximum_heights']['red_ball']:.3f} bricks" if t>2.1 else 'Awaiting the first apex'],['Blue apex · weaker gravity',f"{spec['maximum_heights']['blue_ball']:.3f} bricks" if t>5.1 else 'Awaiting the second apex']]
    elif n==5:
        force=np.linalg.norm(oracle['forces'].get('red_ball',[0,0,0]));active=force>.005
        heading='Extra brake ON above 2.5.' if active else 'Extra brake OFF at or below 2.5.'
        values=[['Red speed',f'{speed(objects[0]):.3f}'],['Added braking force',f'{force:.3f}']]
    elif n==6:
        force=np.linalg.norm(oracle['forces'].get('red_ball',[0,0,0]));active=force>.005
        heading='The force turns with the velocity.'
        power=float(np.dot(oracle['forces'].get('red_ball',[0,0,0]),objects[0]['velocity']))
        values=[['Extra side force',f'{force:.3f}'],['Direction','Right of motion · no work']]
    elif n==7:
        active=bool(event);heading='The rebound ratios are imposed at impact.'
        ratios={c['object']:c['ratio'] for e in events for c in e.get('changes',[])}
        values=[['Red tile · speed returned',f"{ratios['gray_ball_1']*100:.0f}%" if 'gray_ball_1' in ratios else 'Waiting for impact'],['Blue tile · speed returned',f"{ratios['gray_ball_2']*100:.0f}%" if 'gray_ball_2' in ratios else 'Waiting for impact']]
    elif n==8:
        active=True;heading='Five times the impulse ≠ five times the speed.'
        values=[['Impulse 2 → initial speed',f"{spec['initial_speeds']['red_ball']:.3f}"],['Impulse 10 → initial speed',f"{spec['initial_speeds']['blue_ball']:.3f}  <  2.2"]]
    elif n==9:
        active=bool(event)
        if event:
            change=event['changes'][0];ratio=change['ratio']
            heading='ENTRY: speed × 0.4' if ratio<1 else 'EXIT: remaining speed × 2.5'
            if change['position'][2]>.3:heading+=' · above the tile'
            values=[['Measured boundary multiplier',f'{ratio:.3f}×'],['Instantaneous speed change',f"{np.linalg.norm(change['before']):.2f} → {np.linalg.norm(change['after']):.2f}"]]
        else:heading='Approach the gray footprint.';values=[['Boundary multiplier','Not triggered yet'],['Red speed',f'{speed(objects[0]):.3f}']]
    elif n==10:
        active=abs(objects[0]['position'][0])<2 and abs(objects[0]['position'][1])<2
        heading='Energy is added by the world, without a new push.' if t<2.5 else 'Above the tile, the amplification still acts.'
        values=[['Energy injected by the oracle',f"{oracle['energy_added']:.3f}"],['Ordinary-physics reference','No active energy input']]
    elif n==11:
        active=bool(event);heading='CONTACT END → both remaining velocities × 1.8' if active else 'Contact start does not trigger the boost.'
        if event:
            change=next(c for c in event['changes'] if c['object']=='blue_ball')
            values=[['Measured speed multiplier',f"{change['ratio']:.3f}×"],['Blue, at the oracle update',f"{np.linalg.norm(change['before']):.3f} → {np.linalg.norm(change['after']):.3f}"]]
        else:values=[['Boost','Waiting for separation'],['Green','Unaffected control']]
    elif n==12:
        active=bool(event);heading='Colors swap; A and B keep their identities.'
        color=lambda c:['red','green','blue'][int(np.argmax(c[:3]))]
        values=[['Object A',color(objects[0]['color'])],['Object B',color(objects[1]['color'])]]
    elif n==13:
        count=oracle['contact_count'];active=count>=3
        heading=f'CONTACT {count} / 3 · '+('UPWARD KICK' if active else 'NO SPECIAL KICK')
        values=[['Distinct contacts counted',str(count)],['At the third contact','v_z ← 4.000 for both balls']]
    elif n==14:
        active=any(e['kind']=='velocity_copy' for e in events)
        heading='12 COUNTS LATER → green takes the stored velocity' if active else 'Red is held. The scheduled echo remains.'
        values=[['Echo countdown','Transfer applied' if active else f'{max(0,12-t):.2f} counts'],['Green speed',f'{speed(objects[1]):.3f}']]
    else:
        active=t>=oracle['quiet_until'];remaining=max(0,oracle['quiet_until']-t)
        heading='NORTHWARD FORCE ON' if active else 'NORTHWARD FORCE PAUSED'
        if 1<=t<2:heading='ZERO PUSH → THE FORCE STAYS ON'
        if 6<=t<7:heading='PUSH AGAIN → RESTART THE TEN-COUNT PAUSE'
        values=[['Extra northward force', '1.500' if active else '0.000'],['Pause remaining',f'{remaining:.2f} counts']]
    return dict(heading=heading,values=values,active=bool(active))


def wrap(draw,text,font,width):
    lines=[];line=''
    for word in text.split():
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=font)>width and line:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines


def draw_text(draw,xy,text,font,width,fill,leading):
    if any(c in text for c in '←→↔↑↓≠≤≥₀₁₂ₓᵧπ√²³×'):
        font=ImageFont.truetype(str(SITE/'assets/fonts/DejaVuSans.ttf'),font.size)
    x,y=xy
    for line in wrap(draw,text,font,width):draw.text((x,y),line,font=font,fill=fill);y+=leading
    return y


def compose_frame(image_path,frame,oracle,spec,plot,job,video_time):
    im=Image.new('RGB',(1500,900),'#f5f8f7');draw=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),size)
    serif=lambda size:ImageFont.truetype(str(SITE/'assets/fonts/type-6.ttf'),size)
    ink='#25434a';muted='#788d91';green='#3b7c70';red='#c87764'
    draw.text((30,24),f"{oracle['id']}  /  {oracle['name']}",font=serif(35),fill=ink)
    draw.text((1140,31),'LONGCHANG  ·  ORACLE ATLAS',font=font(13),fill=muted)
    draw.line((30,79,1470,79),fill='#d7e2e1',width=1)
    art=Image.open(image_path).convert('RGBA')
    im.paste(art,(20,90),art)
    draw=ImageDraw.Draw(im)
    # Overlay force/velocity arrows using the exact source-space projection.
    camera=job['camera'];pos=np.asarray(camera['position']);right=np.asarray(camera['right']);up=np.asarray(camera['up']);span=camera['span']
    def screen(p):
        delta=np.asarray(p)-pos
        return np.array([20+(0.5+delta@right/(span*job['width']/job['height']))*job['width'],90+(0.5-delta@up/span)*job['height']])
    n=int(oracle['id'])
    # Clip trajectory guides to the illustration, keeping them out of the text.
    paths=Image.new('RGBA',(900,630),(0,0,0,0));path_draw=ImageDraw.Draw(paths)
    local=lambda p:tuple(screen(p)-[20,90])
    if n in [2,6,9,13,14,15]:
        for name,track in job.get('reference_tracks',{}).items():
            points=[local(point['position']) for point in track if point['time']<=frame['time'] and point['epoch']==frame['epoch']]
            for j in range(0,len(points)-1,5):
                if len(points[j:j+3])>1:path_draw.line(points[j:j+3],fill='#bdcaca',width=2)
        for name,track in job.get('tracks',{}).items():
            points=[local(point['position']) for point in track if point['time']<=frame['time'] and point['epoch']==frame['epoch']]
            if len(points)>1:path_draw.line(points,fill='#c7927d',width=2)
    im.paste(paths,(20,90),paths);draw=ImageDraw.Draw(im)
    for i,(name,obj) in enumerate(frame['objects'].items()):
        p=screen(obj['position'])
        if n in [2,5,6,15]:v=np.asarray(frame['oracle']['forces'].get(name,[0,0,0]));label='extra F'
        elif n in [7,9,11,13,14]:v=np.asarray(obj['velocity']);label='v'
        else:v=np.zeros(3);label=''
        if np.linalg.norm(v)>.05:
            delta=np.array([v@right,-v@up]);mag=np.linalg.norm(delta)
            if mag>.01:
                direction=delta/mag;length=38+min(26,mag*4)
                a=p+direction*13;b=a+direction*length
                draw.line((tuple(a),tuple(b)),fill=green,width=3)
                normal=np.array([-direction[1],direction[0]])
                draw.polygon([tuple(b),tuple(b-direction*11+normal*5),tuple(b-direction*11-normal*5)],fill=green)
                draw.text(tuple(b+np.array([5,-10])),label,font=font(13),fill=green)
        if n==12:
            draw.rounded_rectangle((p[0]-13,p[1]-41,p[0]+13,p[1]-15),radius=6,fill='#f5f8f7',outline='#95b0b1')
            draw.text((p[0]-6,p[1]-39),'AB'[i],font=font(17),fill=ink)
        if n in [3,7]:
            floor=screen([*obj['position'][:2],0]);guide=p+[-22,0];end=floor+[-22,0]
            for a in np.arange(0,1,.1):
                aa=guide+(end-guide)*a;bb=guide+(end-guide)*min(1,a+.05)
                draw.line((tuple(aa),tuple(bb)),fill='#aac0bc',width=1)
        if n in [3,5,8]:
            label=f"m = {[1,4][i]}" if n==3 else f"launch J = {([8,2] if n==5 else [2,10])[i]}"
            tw=draw.textlength(label,font=font(12))
            draw.rounded_rectangle((p[0]-tw/2-7,p[1]+19,p[0]+tw/2+7,p[1]+44),radius=5,fill='#f5faf5',outline='#d3dfd7')
            draw.text((p[0]-tw/2,p[1]+24),label,font=font(12),fill=ink)
        if n==6:
            v=np.asarray(obj['velocity']);delta=np.array([v@right,-v@up]);mag=np.linalg.norm(delta)
            if mag>.05:
                direction=delta/mag;a=p+direction*13;b=a+direction*50;normal=np.array([-direction[1],direction[0]])
                draw.line((tuple(a),tuple(b)),fill='#6388ae',width=3)
                draw.polygon([tuple(b),tuple(b-direction*10+normal*4),tuple(b-direction*10-normal*4)],fill='#6388ae')
                draw.text(tuple(b+[4,-12]),'v',font=font(14),fill='#6388ae')
    draw.text((42,99),'NEW CONTROLLED EXPERIMENT  ·  ORIGINAL SCENE PHYSICS',font=font(11),fill=muted)
    draw.rounded_rectangle((710,102,890,141),radius=7,fill='#f5f8f7',outline='#d2dfdb')
    draw.text((724,111),f"t = {frame['time']:05.2f} counts",font=font(16),fill=ink)
    # The oracle is always on screen, independent of whether playback has begun.
    x=954;w=500
    draw.text((x,109),'THE HIDDEN LAW / ORACLE',font=font(13),fill=green)
    y=draw_text(draw,(x,140),oracle['formula'],ImageFont.truetype(str(SITE/'assets/fonts/DejaVuSans.ttf'),27),w,ink,36)+21
    draw.text((x,y),'WHEN',font=font(12),fill=green);y+=24
    y=draw_text(draw,(x,y),oracle['condition'],font(20),w,ink,29)+18
    draw.text((x,y),'THEN',font=font(12),fill=green);y+=24
    y=draw_text(draw,(x,y),oracle['effect'],font(20),w,ink,29)+20
    description=frame['annotation']
    card_y=max(430,min(y+4,510))
    draw.rounded_rectangle((x-2,card_y,1466,card_y+215),radius=12,fill='#e7f0e9' if description['active'] else '#edf1ed',outline='#c8dbd0')
    label_y=draw_text(draw,(x+17,card_y+16),description['heading'],font(16),w-32,green,23)
    for index,(label,value) in enumerate(description['values']):
        top=label_y+14+index*65
        draw.text((x+17,top),label,font=font(12),fill=muted)
        draw_text(draw,(x+17,top+20),value,serif(24),w-30,ink,28)
    draw_text(draw,(x,card_y+237),oracle['scope'],font(14),w,muted,21)
    # Quantitative contrast remains legible when the physical motion is subtle.
    chart=(48,761,885,852);left,top,rightx,bottom=chart
    draw.text((left,724),oracle['measure']+' · '+oracle['unit'],font=font(15),fill=ink)
    labels=plot['labels'];draw.line((440,735,461,735),fill=red,width=3)
    draw.text((470,727),labels[0],font=font(11),fill=muted)
    draw.line((632,735,653,735),fill=plot['colors'][1],width=2)
    draw.text((662,727),labels[1],font=font(11),fill=muted)
    data=np.array(plot['series']);low=min(0,float(data.min()));high=max(float(data.max()),.1)
    pad=(high-low)*.12;low=low-pad if low<0 else 0;high+=pad
    times=np.asarray(plot['times']);end=spec['simulation_duration']
    def xy(t,v):return (left+(rightx-left)*t/end,bottom-(bottom-top)*(v-low)/(high-low))
    for level in np.linspace(low,high,3):
        yy=xy(0,level)[1];draw.line((left,yy,rightx,yy),fill='#dce6e1',width=1)
        if n!=12:draw.text((4,yy-6),f'{level:.1f}',font=font(10),fill=muted)
    if n in [5,8]:
        threshold=2.5 if n==5 else 2.2;yy=xy(0,threshold)[1]
        for xx in range(left,rightx,12):draw.line((xx,yy,min(xx+7,rightx),yy),fill='#88a37c',width=1)
        draw.text((rightx-104,yy-16),f'{threshold} threshold',font=font(11),fill=green)
    for series_index,(values,color) in enumerate(zip(plot['series'],plot['colors'])):
        if n==12:
            yy=top+12+series_index*37
            for k in range(len(times)-1):
                a=xy(times[k],0)[0];b=xy(times[k+1],0)[0]
                draw.rectangle((a,yy,b+1,yy+23),fill=red if values[k]>.5 else '#648db9')
            draw.text((left+5,yy+3),'AB'[series_index],font=font(12),fill='white')
            continue
        future=[xy(t,v) for t,v in zip(times,values)];draw.line(future,fill='#d6e0da',width=1)
        past=[xy(t,v) for t,v in zip(times,values) if t<=frame['time']+.00001]
        if len(past)>1:
            if 'reference' in labels[series_index]:
                for j in range(0,len(past)-1,5):draw.line(past[j:j+3],fill=color,width=2)
            else:draw.line(past,fill=color,width=3)
        if past:
            px,py=past[-1];draw.ellipse((px-4,py-4,px+4,py+4),fill=color)
    marker=xy(frame['time'],0)[0];draw.line((marker,top,marker,bottom),fill='#799d8c',width=1)
    draw.text((left,bottom+6),'0',font=font(11),fill=muted)
    draw.text((rightx-64,bottom+6),f'{end:g} counts',font=font(11),fill=muted)
    draw.text((30,883),'New scripted experiment · native scene physics · retimed at the displayed clock · glass enclosure is presentation geometry',font=font(10),fill=muted)
    return im


def prepare(number,cache,samples,threads,fps):
    start=time.time();world,xml,frames,refs,spec=record(number)
    oracle=catalog()[number];plot=plot_data(number,frames,refs)
    mapping,chapters=checkpoints(number,spec,frames)
    native_times=np.asarray([f['time'] for f in frames]);film=[];seen={}
    for index in range(spec['duration']*fps):
        t=mapped_time(mapping,index/fps)
        native=int(np.abs(native_times-t).argmin());frame=copy.deepcopy(frames[native])
        frame['annotation']=explanation(number,frame,spec)
        if native in seen:frame['reuse']=seen[native]
        else:seen[native]=index
        film.append(frame)
    folder=cache/number;folder.mkdir(parents=True,exist_ok=True)
    job=studio_job(number,frames,spec,folder/'frames',samples=samples,threads=threads)
    job['tracks']={name:[dict(time=f['time'],epoch=f['epoch'],position=f['objects'][name]['position']) for f in frames[::3]] for name in spec['focus']}
    job['reference_tracks']={name:[dict(time=f['time'],epoch=f['epoch'],position=f['objects'][name]['position']) for f in refs[::3]] for name in spec['focus']}
    job['frames']=[{k:v for k,v in f.items() if k in ['time','objects','reuse']} for f in film]
    job_path=folder/'studio-job.json';atomic_json(job_path,job)
    public_samples=[{k:v for k,v in f.items() if k not in ['qpos','qvel','rgba']} for f in frames]
    reference_samples=[{k:v for k,v in f.items() if k not in ['qpos','qvel','rgba']} for f in refs]
    record_folder=SITE/'downloads/oracle-demonstrations';record_folder.mkdir(exist_ok=True)
    record_path=record_folder/f'scene-{number}.json'
    metadata=dict(**spec,name=oracle['name'],oracle=oracle,kind='new controlled oracle demonstration',
                  scene_source='scenes/base_15.json',scene_source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  reference='Same geometry, masses and scripted actions; the altered program is disabled only in the ordinary-physics reference.',
                  physics_timestep=.002,sample_interval=.01,samples=public_samples,reference_samples=reference_samples)
    atomic_json(record_path,metadata)
    entry={k:v for k,v in metadata.items() if k not in ['samples','reference_samples']}
    entry.update(video=f'assets/videos/oracle/scene-{number}.mp4',poster=f'assets/images/oracle-{number}.webp',
                 record=str(record_path.relative_to(SITE)),fps=fps,time_map=mapping,chapters=chapters,plot=plot,
                 timeline=[{k:v for k,v in f.items() if k in ['time','objects','gravity','oracle','annotation']} for f in film],
                 render=dict(engine='Blender Cycles',samples=samples,reference='ACL/materials/teaser/blender_scene.py',
                 geometry='Native object poses and sizes; cropped porcelain plinth and glass enclosure are display-only.'))
    entry['preview_time']={'01':3,'02':3,'03':6,'04':8.8,'05':3.5,'06':6,'07':8,'08':2,'09':12,'10':10,'11':6.2,'12':7.2,'13':9.45,'14':10,'15':13}[number]
    atomic_json(folder/'entry.json',entry)
    # Composition only needs compact render-time data, not native qpos arrays.
    atomic_json(folder/'composition.json',dict(entry=entry,job=job,spec=spec,oracle=oracle,plot=plot,
        frames=[{k:v for k,v in f.items() if k not in ['qpos','qvel','rgba']} for f in film]))
    print(f'PREPARED {number} {oracle["name"]}: {len(film)} film frames, {len(seen)} unique native samples, {len(spec["oracle_events"])} measured oracle updates ({time.time()-start:.1f}s)',flush=True)
    return folder


def finish(folder,ffmpeg):
    data=json.loads((folder/'composition.json').read_text());entry=data['entry'];job=data['job']
    target=SITE/entry['video'];target.parent.mkdir(exist_ok=True)
    temporary=target.with_name(target.stem+'.partial.mp4')
    process=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1500x900','-r',str(entry['fps']),'-i','-','-an','-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],stdin=subprocess.PIPE)
    poster=round(entry['preview_time']*entry['fps'])
    try:
        for i,frame in enumerate(data['frames']):
            im=compose_frame(folder/'frames'/f'{i:05}.png',frame,data['oracle'],data['spec'],data['plot'],job,i/entry['fps'])
            if i==poster:im.save(SITE/entry['poster'],quality=94)
            process.stdin.write(np.asarray(im).tobytes())
        process.stdin.close();assert process.wait()==0;temporary.replace(target)
    finally:
        if process.poll() is None:process.kill();process.wait()
    # A new GIF contains the oracle and the measured effect, not just movement.
    gif=SITE/f'downloads/animated-scenes/oracle-{entry["id"]}.gif'
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(target),'-vf','fps=10,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)],check=True)
    print(f'COMPOSED {entry["id"]}: Figure 1 studio film + oracle GIF',flush=True)
    return entry


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--only',nargs='*');parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--compose-only',action='store_true');parser.add_argument('--samples',type=int,default=48)
    parser.add_argument('--workers',type=int,default=4);parser.add_argument('--threads',type=int,default=16)
    parser.add_argument('--fps',type=int,default=12)
    args=parser.parse_args();cache=Path('/tmp/longchang-oracle-studio/production');cache.mkdir(parents=True,exist_ok=True)
    ids=args.only or [f'{i:02}' for i in range(1,16)]
    folders=[cache/id for id in ids] if args.compose_only else [prepare(id,cache,args.samples,args.threads,args.fps) for id in ids]
    if args.prepare_only:return
    def render(folder):
        if not args.compose_only:
            with (folder/'blender.log').open('w') as log:
                subprocess.run([os.environ.get('BLENDER_PYTHON',str(Path.home()/'.virtualenvs/longchang-blender/bin/python')),str(SITE/'scripts/blender_oracle.py'),str(folder/'studio-job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
        return finish(folder,args.ffmpeg)
    completed=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks={pool.submit(render,folder):folder for folder in folders}
        for future in concurrent.futures.as_completed(tasks):
            entry=future.result();completed.append(entry)
            # Publish complete scenes atomically while remaining scenes render.
            path=SITE/'data/physics.js'
            previous=json.loads(path.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
            merged=[entry if d['id']==entry['id'] else d for d in previous]
            atomic_json(path,merged,'window.PHYSICS_DEMOS = ')
            print(f'PUBLISHED {entry["id"]}: {len(completed)}/{len(ids)} scenes complete',flush=True)
    print('ALL REQUESTED ORACLE FILMS COMPLETE',flush=True)


if __name__=='__main__':main()
