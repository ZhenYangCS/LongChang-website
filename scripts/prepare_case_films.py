"""Make three chaptered case films from archived MuJoCo states.

No physics is advanced. The source model version supplies geometry and colors;
each rendered pose is the nearest saved state. Cuts separate selected trials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib import get_data_path

from render_replays import ROOT, SITE, RecordedRenderer, load_replay
import mujoco

WIDTH, HEIGHT, FPS = 1280, 720, 30
INK, MUTED, TEAL = '#203c43', '#627776', '#347c79'
FONT_DIR = Path(get_data_path())/'fonts/ttf'


@lru_cache(maxsize=16)
def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_lines(draw, text, xy, width, size=24, fill=INK, bold=False):
    face = font(size, bold)
    x, y = xy
    line = ''
    for word in text.split():
        candidate = (line + ' ' + word).strip()
        if line and draw.textlength(candidate, font=face) > width:
            draw.text((x, y), line, font=face, fill=fill)
            y += size * 1.45
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=face, fill=fill)


def plans():
    evidence = json.loads((ROOT/'ACL/materials/cases/sources/evidence.json').read_text())
    apparatus = json.loads((ROOT/'ACL/materials/cases/sources/tool_case.json').read_text())
    sources = {}
    for name, key in [('astra', 'question'), ('gemini', 'checklist'), ('color', 'partial')]:
        src = evidence['provenance'][key]
        sources[name] = dict(path=src['run']+'/replay.bin', sha256=src['replay_sha256'],
                             session=src['run']+'/session.json', session_sha256=src['session_sha256'])
    src = apparatus['provenance']
    sources['tool'] = dict(path=src['replay']['path'], sha256=src['replay']['sha256'],
                           session=src['session']['path'], session_sha256=src['session']['sha256'])
    replays = {item['id']: item for item in json.loads((SITE/'data/replays.json').read_text())}

    def question_track(model, stage, caption):
        clip = replays[model+'-'+stage]
        return dict(source=model, start=clip['start'], end=clip['end'], turns=clip['turns'],
                    camera=clip['camera'], targets=['red_ball','blue_ball'] if (model,stage)==('astra','notice') or (model,stage)==('gemini','test') else ['red_ball'],
                    label='GPT-6-Astra' if model=='astra' else 'Gemini-3.7-Flash',
                    caption=caption)

    question = dict(id='question', title='Follow an anomaly', scene='15', chapters=[])
    question_stages = [
        ('Notice the restart', 'notice', 8,
         'Red starts moving while blue is held still.',
         'Red stops, then starts moving again during the wait.'),
        ('Choose what to test', 'investigate', 12,
         'Astra pushes red south and waits. The northward motion returns.',
         'Gemini continues its planned tests with a vertical throw.'),
        ('Follow the evidence', 'test', 12,
         'After a push to blue, red pauses and then restarts.',
         'Gemini proceeds to a collision test without pursuing the restart.')
    ]
    for title, stage, duration, left, right in question_stages:
        question['chapters'].append(dict(title=title, duration=duration, tracks=[
            question_track('astra', stage, left), question_track('gemini', stage, right)]))

    color = dict(id='color', title='Test an explanation', scene='12', chapters=[])
    views = evidence['replay_views']
    for trial, title, start, end, turns, caption in [
        (1, 'The first color swap', 63.818, 64.818, [39],
         'Red and blue exchange colors at contact. Swapping and flipping both fit this observation.'),
        (2, 'Repeat the collision', 67.818, 68.818, [41,42],
         'The colors switch back. The same two explanations still fit.'),
        (3, 'Test red against red', 75.374, 77.374, [47,48],
         'Both balls stay red. This separates color exchange from independent color flips.')
    ]:
        color['chapters'].append(dict(title=title, duration=6, tracks=[dict(
            source='color', start=start, end=end, turns=turns,
            camera=views[f'v_seq_{trial}_before']['camera'], targets=['ball_1','ball_2'] if trial<3 else ['ball_1','ball_2','ball_3'],
            label='GPT-6-Astra', caption=caption)]))

    tool = dict(id='tool', title='Improve an instrument', scene='15', chapters=[])
    for title, start, end, turns, camera, caption in [
        ('A flat pan fails', 44.98, 47.0, [23],
         dict(lookat=[0,.35,.72],distance=3,azimuth=-35,elevation=-28,orthographic=True,vertical_span=2.5),
         'Red drifts off the flat pan. The instrument cannot hold a stable load.'),
        ('Add retaining walls', 57.264, 61.384, [28,29],
         apparatus['views']['rimmed']['camera'],
         'Astra builds a deeper pan. After release, red stays inside the retaining walls.'),
        ('Obtain stable readings', 73.498, 77.618, [33,34],
         apparatus['views']['rimmed']['camera'],
         'Blue also settles in the new pan. Both loaded trials give a stable reading of -0.3 brick.')
    ]:
        tool['chapters'].append(dict(title=title, duration=7, tracks=[dict(
            source='tool', start=start, end=end, turns=turns, camera=camera,
            label='GPT-6-Astra', caption=caption)]))
    return sources, [question, color, tool]


def fitted_camera(record, frames, spec, size):
    points=[]
    models={}
    chosen=[f for f in frames if spec['start']-.04<=f['time']<=spec['end']+.04]
    for frame in chosen[::max(1,len(chosen)//100)]+[chosen[-1]]:
        version=frame['version']
        if version not in models:
            xml=next(m['xml'] for m in record['model_versions'] if m['version']==version)
            models[version]=mujoco.MjModel.from_xml_string(xml)
        model=models[version]
        for name in spec['targets']:
            joint=model.body_jntadr[model.body(name).id]
            offset=model.jnt_qposadr[joint]
            points.append(frame['qpos'][offset:offset+3])
    points=np.asarray(points)
    azimuth=spec['camera'].get('azimuth',110)
    elevation=-32
    az,el=np.deg2rad([azimuth,elevation])
    right=np.array([-np.sin(az),np.cos(az),0])
    up=np.array([-np.cos(az)*np.sin(el),-np.sin(az)*np.sin(el),np.cos(el)])
    u,v=points@right,points@up
    span=max(1.2,float(np.ptp(v))+.65,(float(np.ptp(u))+.65)/(size[0]/size[1]))
    z=float((points[:,2].min()+points[:,2].max())/2)
    xy=np.linalg.solve([right[:2],up[:2]],[(u.min()+u.max())/2,(v.min()+v.max())/2-up[2]*z])
    return dict(lookat=[float(xy[0]),float(xy[1]),z],distance=5,azimuth=azimuth,elevation=elevation,
                orthographic=True,vertical_span=span)


class Track:
    def __init__(self, spec, record, size):
        self.spec = spec
        self.frames = sorted((f for f in record['state_frames'] if f['turn'] in spec['turns']), key=lambda f:f['time'])
        self.times = np.array([f['time'] for f in self.frames])
        assert spec['start'] >= self.times[0]-.003 and spec['end'] <= self.times[-1]+.003
        if spec.get('targets'):
            spec['camera']=fitted_camera(record,self.frames,spec,size)
        self.renderer = RecordedRenderer(record, spec['camera'], size)
        self.previous = None
        self.image = None

    def at(self, fraction):
        when = self.spec['start'] + fraction*(self.spec['end']-self.spec['start'])
        index = int(np.abs(self.times-when).argmin())
        frame = self.frames[index]
        if index != self.previous:
            self.image = Image.fromarray(self.renderer.render(frame))
            self.previous = index
        return self.image, frame

    def close(self):
        self.renderer.close()


def compose(case, chapter, tracks, fraction):
    canvas = Image.new('RGB', (WIDTH,HEIGHT), '#f5f8f6')
    draw = ImageDraw.Draw(canvas)
    split = len(tracks)==2
    rendered = []
    for index, track in enumerate(tracks):
        pixels, frame = track.at(fraction)
        x = 24+index*628 if split else 0
        canvas.paste(pixels, (x,80 if split else 58))
        label_x = x if split else 28
        draw.text((label_x,23), track.spec['label'], font=font(23,True), fill=INK)
        time_text = f"Turn {frame['turn']}  /  {frame['time']:.2f} counts"
        if split:
            draw.text((label_x,54), time_text, font=font(17), fill=MUTED)
            text_lines(draw, track.spec['caption'], (x,570), 592, size=23)
        else:
            draw.text((WIDTH-28-draw.textlength(time_text,font=font(18)),25),time_text,font=font(18),fill=MUTED)
            text_lines(draw, track.spec['caption'], (28,614), 1224, size=24)
        rendered.append(dict(source=track.spec['source'], turn=frame['turn'], time=frame['time'], version=frame['version']))
    if split:
        draw.line((640,24,640,672), fill='#d9e3df', width=1)
    draw.text((24,690), 'SELECTED REPLAY  /  PLAYBACK RETIMED', font=font(13), fill=MUTED)
    stage_label = chapter['title']
    draw.text((1256-draw.textlength(stage_label,font=font(14)),689),stage_label,font=font(14),fill=TEAL)
    return canvas, rendered


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--only',nargs='+',choices=['question','color','tool'])
    parser.add_argument('--preview',action='store_true')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    sources, cases = plans()
    manifest_path=SITE/'data/case-films.json'
    previous={case['id']:case for case in json.loads(manifest_path.read_text())['cases']} if manifest_path.exists() else {}
    records = {}
    for name, src in sources.items():
        assert digest(ROOT/src['path']) == src['sha256'], name
        assert digest(ROOT/src['session']) == src['session_sha256'], name
    manifest=[]
    for case in cases:
        dest=SITE/f"assets/videos/case-{case['id']}.mp4"
        poster=SITE/f"assets/images/case-{case['id']}.webp"
        selected = not args.only or case['id'] in args.only
        render = selected and (args.force or args.preview or not dest.exists())
        if not render and dest.exists() and case['id'] in previous:
            # Keep the fitted cameras and timings attached to cached media.
            manifest.append(previous[case['id']])
            continue
        entry=dict(id=case['id'],title=case['title'],scene=case['scene'],
                   video=str(dest.relative_to(SITE)),poster=str(poster.relative_to(SITE)),chapters=[])
        elapsed=0
        proc=None
        temp=dest.with_suffix('.rendering.mp4')
        if render and not args.preview:
            cmd=[args.ffmpeg,'-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}',
                 '-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-threads','4',
                 '-pix_fmt','yuv420p','-movflags','+faststart',str(temp)]
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        for chapter_index, chapter in enumerate(case['chapters']):
            entry['chapters'].append(dict(title=chapter['title'],start=elapsed,end=elapsed+chapter['duration'],
                caption=' '.join(t['caption'] for t in chapter['tracks']),tracks=chapter['tracks']))
            if render:
                tracks=[]
                size=(604,454) if len(chapter['tracks'])==2 else (1280,536)
                for spec in chapter['tracks']:
                    name=spec['source']
                    if name not in records: records[name]=load_replay(ROOT/sources[name]['path'])
                    tracks.append(Track(spec,records[name],size))
                count=round(chapter['duration']*FPS)
                frame_numbers=sorted(set([0,count//2,count-1])) if args.preview else range(count)
                for n in frame_numbers:
                    canvas, rendered=compose(case,chapter,tracks,n/(count-1))
                    if chapter_index==0 and n==0 and not args.preview:
                        canvas.save(poster,quality=91)
                    if args.preview:
                        canvas.save(f"/tmp/longchang-case-{case['id']}-{chapter_index}-{n}.jpg",quality=90)
                        print(case['id'],chapter_index,n,rendered,flush=True)
                    else:
                        proc.stdin.write(canvas.tobytes())
                for track in tracks:track.close()
                print(f"Rendered {case['id']} / {chapter['title']}",flush=True)
            elapsed+=chapter['duration']
        if proc:
            proc.stdin.close()
            assert proc.wait()==0
            temp.replace(dest)
        entry['duration']=elapsed
        if dest.exists():entry['video_sha256']=digest(dest)
        manifest.append(entry)
    if not args.preview:
        output=dict(method='Nearest archived states; no physics steps or pose interpolation. Chapters are edited selections. Split-screen tracks are retimed independently; counters show original simulation time.',
                    width=WIDTH,height=HEIGHT,fps=FPS,sources=sources,cases=manifest)
        manifest_path.write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__':main()
