"""Make the primary films concise: one plain sentence and the studio scene."""
import argparse
import concurrent.futures
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw,ImageFont
from oracle_catalog import catalog

SITE=Path(__file__).resolve().parents[1]
CACHE=Path('/tmp/longchang-oracle-studio/production')


def state(id,frame):
    t=frame['time'];o=frame['oracle']
    if id=='04':return 'First throw' if 1.5<=t<4.5 else 'Second throw' if t>=4.5 else ''
    if id=='09':return ['Entering','Leaving','Above the tile'][min(frame['epoch'],2)]
    if id=='11':return 'Boost' if t>=.236 else ''
    if id=='12':return 'Second touch' if t>=1.93 else 'First touch' if t>=.21 else ''
    if id=='13':return ['','First collision','Second collision','Third collision'][min(o['contact_count'],3)]
    if id=='14':return 'Waiting' if .2<t<12 else 'Delayed copy' if t>=12 else 'Push red'
    if id=='15':return 'Pull active' if t>=o['quiet_until'] else 'Pull paused'
    return ''


def paragraph(draw,xy,text,font,width):
    line='';y=xy[1]
    for word in text.split():
        test=(line+' '+word).strip()
        if draw.textlength(test,font=font)>width and line:
            draw.text((xy[0],y),line,font=font,fill='#365f53');y+=32;line=word
        else:line=test
    if line:draw.text((xy[0],y),line,font=font,fill='#365f53')


def make(id,ffmpeg):
    folder=CACHE/id;data=json.loads((folder/'composition.json').read_text())
    entry=copy.deepcopy(data['entry']);oracle=catalog()[id];entry['oracle']=oracle
    serif=ImageFont.truetype(str(SITE/'assets/fonts/type-6.ttf'),34)
    sans=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),24)
    small=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),15)
    out=SITE/f'assets/videos/oracle-simple/scene-{id}.mp4';out.parent.mkdir(exist_ok=True)
    temp=out.with_name(out.stem+'.partial.mp4')
    process=subprocess.Popen([ffmpeg,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1000x900','-r',str(entry['fps']),'-i','-','-an','-c:v','libx264','-crf','19','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],stdin=subprocess.PIPE)
    poster_index=round(entry['preview_time']*entry['fps'])
    try:
        for i,frame in enumerate(data['frames']):
            im=Image.new('RGB',(1000,900),'#f5f8f7');draw=ImageDraw.Draw(im)
            draw.text((40,25),f"{id} / {entry['name']}",font=serif,fill='#25434a')
            paragraph(draw,(40,82),oracle['plain'],sans,920)
            art=Image.open(folder/'frames'/f'{i:05}.png').convert('RGBA');im.paste(art,(50,170),art)
            draw=ImageDraw.Draw(im)
            # Small identity labels make color exchange understandable.
            if id=='12':
                cam=data['job']['camera'];pos=np.asarray(cam['position']);right=np.asarray(cam['right']);up=np.asarray(cam['up']);span=cam['span']
                for j,obj in enumerate(frame['objects'].values()):
                    delta=np.asarray(obj['position'])-pos
                    x=50+(0.5+delta@right/(span*900/650))*900;y=170+(0.5-delta@up/span)*650
                    draw.rounded_rectangle((x-11,y-35,x+11,y-14),radius=5,fill='#f5f8f7',outline='#93b0ad')
                    draw.text((x-5,y-33),'AB'[j],font=small,fill='#365f53')
            text=state(id,frame)
            if text:draw.text((42,853),text,font=small,fill='#527b6b')
            clock=f"{frame['time']:.1f} s"
            draw.text((955-draw.textlength(clock,font=small),853),clock,font=small,fill='#91a19b')
            frame['simple_state']=text;entry['timeline'][i]['simple_state']=text
            if i==poster_index:
                im.save(SITE/f'assets/images/plain-{id}.webp',quality=94)
                art.save(SITE/f'assets/images/oracle-world-{id}.webp',quality=94)
            process.stdin.write(np.asarray(im).tobytes())
        process.stdin.close();assert process.wait()==0;temp.replace(out)
    finally:
        if process.poll() is None:process.kill();process.wait()
    entry.update(technical_video=entry['video'],video=str(out.relative_to(SITE)),
                 poster=f'assets/images/plain-{id}.webp',studio_poster=f'assets/images/oracle-world-{id}.webp',
                 presentation='plain',video_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    labels={
        '03':['Release','Fall','Red lands'],'05':['Push','Brake on','Brake off'],
        '07':['Drop','Land','Bounce'],'09':['Enter','Leave','Above'],
        '11':['Approach','Separate','After'],'12':['Before','Touch','Touch again'],
        '13':['First','Second','Third'],'14':['Push red','Wait','Green moves'],
        '15':['Before','Pause','Return']}.get(id,['Start','Watch','Result'])
    for chapter,label in zip(entry['chapters'],labels):chapter['label']=label
    if id=='15':
        for chapter,t in zip(entry['chapters'],[1,4.3,13]):chapter['time']=t
    gif=SITE/f'downloads/animated-scenes/plain-{id}.gif'
    subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(out),'-vf','fps=10,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)],check=True)
    entry['gif']=str(gif.relative_to(SITE))
    print(f'PLAIN {id} {oracle["plain"]}',flush=True)
    return entry


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args();entries=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(make,f'{i:02}',args.ffmpeg) for i in range(1,16)]
        for future in concurrent.futures.as_completed(futures):entries.append(future.result())
    entries.sort(key=lambda e:e['id'])
    target=SITE/'data/physics.js';temp=target.with_suffix('.js.tmp')
    temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,ensure_ascii=False,separators=(',',':'))+';\n');temp.replace(target)
    print('All 15 plain-language studio films published.',flush=True)


if __name__=='__main__':main()
