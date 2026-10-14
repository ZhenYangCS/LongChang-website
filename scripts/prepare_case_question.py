"""Explain the first case using cached studio frames and archived motion flags.

This changes captions and visual annotations only. State markers come from the
observations returned to each model; the small wall restart is not exaggerated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from prepare_case_films import ROOT, SITE, FPS, plans, load_replay, font, digest

CACHE=Path('/tmp/longchang-case-studio')
WIDTH,HEIGHT=1280,512
STAGES=['The unexpected observation','What do they test next?','Follow-up and outcome']
LEFT=['Red moves without a new push. Astra was holding blue still when red restarted.',
      'Astra changes the plan: pushes red, then waits to time its restart.',
      'Astra pushes blue too: red again restarts about 10 seconds later.']
RIGHT=['The log also reports a restart. Red is against the wall, so its motion is barely visible.',
       'Gemini keeps the planned gravity test, without investigating the restart.',
       'Gemini runs a collision test, then ends without investigating the restart.']


def cue_data(case,jobs,sources):
    records={name:load_replay(ROOT/sources[name]['path']) for name in ['astra','gemini']}
    output={}
    for ci,chapter in enumerate(case['chapters']):
        for ti,spec in enumerate(chapter['tracks']):
            record=records[spec['source']];job=jobs[f'question-{ci}-{ti}']
            turns={t['turn']:t for t in record['turns']}
            starts={}
            for f in record['state_frames']:
                starts[f['turn']]=min(starts.get(f['turn'],f['time']),f['time'])
            launch_turn=([19,28,34][ci] if ti==0 else [1,5,13][ci])
            origin=starts[launch_turn]
            cues=[]
            for frame in job['originals']:
                elapsed=max(0,frame['time']-starts[frame['turn']])
                trajectory=turns[frame['turn']]['result_observation']['events']['red_ball']['trajectory']
                state=next((p['state'] for p in reversed(trajectory) if p['count']<=elapsed+1e-8),trajectory[0]['state'])
                since=max(0,frame['time']-origin)
                restarted=state=='moving' and since>=10 and (ti==0 or ci==0)
                cues.append(dict(time=frame['time'],turn=frame['turn'],state=state,since_action=since,restarted=restarted))
            output[job['id']]=dict(source=spec['source'],action=turns[launch_turn]['act'],action_time=origin,cues=cues)
    return output


def compose_question(ci,jobs,cues,frame_number):
    image=Image.new('RGB',(WIDTH,HEIGHT),'#f5f8f7')
    draw=ImageDraw.Draw(image)
    for ti in range(2):
        key=f'question-{ci}-{ti}';job=jobs[key];index=job['frame_map'][frame_number]
        cue=cues[key]['cues'][index];x=24+628*ti
        with Image.open(Path(job['output'])/'frames'/f'{index:05}.png') as frame:
            image.paste(frame.convert('RGB'),(x,0))
        # The status is what the model's observation reported, including the
        # right-hand restart at a wall with almost no visible displacement.
        label=('Log: ' if ti==1 and ci==0 else 'Red: ')+('restarted' if cue['restarted'] else 'stopped' if cue['state']=='still' else 'moving')
        color='#286b50' if cue['restarted'] else '#506c70'
        width=draw.textlength(label,font=font(23,True))+28
        draw.rounded_rectangle((x+12,14,x+12+width,55),radius=7,fill='#f8fcf8',outline='#c8d9d0',width=1)
        draw.text((x+26,21),label,font=font(23,True),fill=color)
        if cue['restarted']:
            camera=job['camera'];p=np.array(job['frames'][index]['lc_geom_6']['position'])-camera['position']
            center=np.array([(0.5+p@camera['right']/(camera['span']*604/454))*604,(0.5-p@camera['up']/camera['span'])*454])
            radius=.1*454/camera['span']+6
            if 0<=center[0]<=604 and 0<=center[1]<=454:
                cx,cy=center+[x,0]
                draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline='#347c79',width=3)
        if ti==0 or ci==0:
            prefix=(['Since last throw','After pushing red','After pushing blue'][ci] if ti==0 else 'After pushing red')
            draw.text((x+12,462),f"{prefix}: {cue['since_action']:.1f} s",font=font(20),fill=color)
            a,b=x+14,x+590;y=500;ratio=min(1,cue['since_action']/12)
            draw.line((a,y,b,y),fill='#d5e2db',width=4)
            draw.line((a,y,a+(b-a)*ratio,y),fill=color,width=4)
            tick=a+(b-a)*10/12
            draw.line((tick,y-7,tick,y+6),fill='#347c79',width=2)
            draw.text((tick-19,y-27),'10 s',font=font(15),fill='#347c79')
        else:
            draw.text((x+12,466),'Next test: '+('vertical throw' if ci==1 else 'ball collision'),font=font(22),fill='#627776')
    return image


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--preview',action='store_true')
    args=parser.parse_args();sources,cases=plans();case=cases[0]
    jobs={j['id']:j for j in json.loads((CACHE/'jobs.json').read_text()) if j['id'].startswith('question-')}
    for name in ['astra','gemini']:
        assert digest(ROOT/sources[name]['path'])==sources[name]['sha256']
        assert digest(ROOT/sources[name]['session'])==sources[name]['session_sha256']
    cues=cue_data(case,jobs,sources)
    dest=SITE/'assets/videos/case-question.mp4';poster=SITE/'assets/images/case-question.webp'
    temp=dest.with_suffix('.explained.mp4')
    if not args.preview:
        process=subprocess.Popen([args.ffmpeg,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}',
             '-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','slow','-crf','17','-threads','4',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],stdin=subprocess.PIPE)
    for ci,chapter in enumerate(case['chapters']):
        count=round(chapter['duration']*FPS)
        for n in ([0,count//2,count-1] if args.preview else range(count)):
            frame=compose_question(ci,jobs,cues,n)
            if args.preview:frame.save(CACHE/f'question-explained-{ci}-{n}.png')
            else:
                process.stdin.write(frame.tobytes())
                if ci==0 and n==0:frame.save(poster,quality=96,method=6)
    if args.preview:return
    process.stdin.close();assert process.wait()==0;temp.replace(dest)
    path=SITE/'data/case-films.json';manifest=json.loads(path.read_text());entry=manifest['cases'][0]
    assert entry['id']=='question'
    entry.update(title='Red restarts. Who investigates?',width=WIDTH,height=HEIGHT,video_sha256=digest(dest),poster_sha256=digest(poster))
    entry['render']['annotation']='Motion state from returned observations; seconds since the original push/throw; ring highlights the recorded red-ball position. Tiny wall motion is not enlarged.'
    for ci,chapter in enumerate(entry['chapters']):
        chapter['title']=STAGES[ci];chapter['caption']=LEFT[ci]+' '+RIGHT[ci]
        for ti,track in enumerate(chapter['tracks']):track['caption']=(LEFT if ti==0 else RIGHT)[ci]
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    (SITE/'data/case-question-cues.json').write_text(json.dumps(dict(method=entry['render']['annotation'],tracks=cues),separators=(',',':'))+'\n')
    print('Published first case: clear comparison, archived motion flags and 10-second timers.')


if __name__=='__main__':main()
