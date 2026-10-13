"""Small intervention labels, composited without requiring ffmpeg drawtext."""
from pathlib import Path
import subprocess,tempfile
from PIL import Image,ImageDraw,ImageFont

SITE=Path(__file__).resolve().parents[1]

def add_launch_cues(ffmpeg,source,destination,entry):
    labels={'red_ball':'red','blue_ball':'blue','ball_1':'A','ball_2':'B'}
    font=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),23)
    with tempfile.TemporaryDirectory(prefix='longchang-push-labels-') as tmp:
        inputs=[];filters=[];previous='0:v'
        for index,event in enumerate(entry['events'],1):
            label='Push '+labels[event['command'].split()[1]]
            im=Image.new('RGBA',(round(font.getlength(label))+24,43));draw=ImageDraw.Draw(im)
            draw.rounded_rectangle((0,0,im.width-1,42),radius=8,fill=(245,248,247,238))
            draw.text((12,7),label,font=font,fill='#4c7664');path=Path(tmp)/f'{index}.png';im.save(path)
            inputs+=['-loop','1','-i',str(path)]
            start=event['actual_time']/entry['simulation_duration']*entry['duration'];end=start+.7
            output=f'cue{index}'
            filters.append(f"[{previous}][{index}:v]overlay=30:main_h-overlay_h-26:shortest=1:enable='between(t,{start},{end})'[{output}]")
            previous=output
        temporary=destination.with_name(destination.stem+'.partial.mp4')
        subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(source),*inputs,
            '-filter_complex',';'.join(filters),'-map',f'[{previous}]','-c:v','libx264','-preset','fast','-crf','15','-g','60',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],check=True)
        temporary.replace(destination)
    return destination
