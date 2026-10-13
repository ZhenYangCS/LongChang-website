"""Captioned downloads from the sharp scene films; no physics or rendering rerun."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from oracle_catalog import catalog
from launch_cues import add_launch_cues

SITE=Path(__file__).resolve().parents[1]

def speed_header(item,width,ffmpeg,temp):
    """Keep measured numbers in the caption margin, outside the experiment."""
    base=Image.new('RGB',(width,160),'#f5f8f7');draw=ImageDraw.Draw(base)
    serif=ImageFont.truetype(str(SITE/'assets/fonts/type-6.ttf'),42)
    sans=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),25)
    draw.text((50,16),f'{item["id"]} / {item["name"]}',font=serif,fill='#25434a')
    draw.text((50,72),catalog()[item['id']]['plain'],font=sans,fill='#365f53')
    draw.text((50,116),'Forward speed',font=sans,fill='#638276')
    target=temp/'10-speed-header.mp4';cache={}
    process=subprocess.Popen([ffmpeg,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x160','-r',str(item['fps']),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
    try:
        for sample in item['timeline']:
            values=tuple(f"{sample['objects'][name]['velocity'][0]:.1f}" for name in ['red_ball','blue_ball'])
            if values not in cache:
                image=base.copy();d=ImageDraw.Draw(image)
                d.text((270,116),f'Red  {values[0]}',font=sans,fill='#ae574a')
                d.text((460,116),f'Blue  {values[1]}',font=sans,fill='#426f99')
                cache[values]=image.tobytes()
            process.stdin.write(cache[values])
        process.stdin.close();assert process.wait()==0
    finally:
        if process.poll() is None:process.kill();process.wait()
    return target

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--only',nargs='*');args=parser.parse_args()
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    smooth=all(e.get('fps',0)>=30 for e in entries)
    prefix='unified' if all(e.get('render_revision')=='unified-v1' for e in entries) else 'focused' if all(e.get('detail_video') for e in entries) else 'smooth' if smooth else 'shared-room'
    folder=SITE/f'assets/videos/{prefix}-captioned';folder.mkdir(exist_ok=True)
    temp=Path('/tmp/longchang-clear-captions');temp.mkdir(exist_ok=True)
    for item in entries:
        id=item['id'];assert item['presentation']=='clear',id
        if args.only and id not in args.only:continue
        if smooth and id in ['12','13'] and not item.get('launch_cues'):
            cued=SITE/f'assets/videos/smooth/scene-{id}-cued.mp4'
            add_launch_cues(args.ffmpeg,SITE/item['video'],cued,item)
            item.update(video=str(cued.relative_to(SITE)),video_sha256=hashlib.sha256(cued.read_bytes()).hexdigest(),launch_cues=True)
        width,height=item.get('detail_dimensions',[1440,960]);header_height=160
        image=Image.new('RGB',(width,header_height),'#f5f8f7');draw=ImageDraw.Draw(image)
        serif=ImageFont.truetype(str(SITE/'assets/fonts/type-6.ttf'),42);sans=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),27)
        draw.text((50,24),f'{id} / {item["name"]}',font=serif,fill='#25434a')
        draw.text((50,91),catalog()[id]['plain'],font=sans,fill='#365f53')
        header=temp/f'{id}.png';image.save(header)
        suffix='-clean' if id=='10' else ''
        output=folder/f'scene-{id}{suffix}.mp4'
        header_input=['-i',str(speed_header(item,width,args.ffmpeg,temp))] if id=='10' else ['-loop','1','-i',str(header)]
        subprocess.run([args.ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(SITE/item.get('detail_video',item['video'])),*header_input,'-filter_complex',f'[0:v]pad={width}:{height+header_height}:0:{header_height}:color=0xf5f8f7[v];[v][1:v]overlay=0:0:shortest=1','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True)
        gif=SITE/f'downloads/animated-scenes/{prefix}-{id}{suffix}.gif'
        rate=30 if smooth else 10
        subprocess.run([args.ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(output),'-vf',f'fps={rate},scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)],check=True)
        item.update(download_video=str(output.relative_to(SITE)),gif=str(gif.relative_to(SITE)))
        print('DOWNLOAD',id,flush=True)
    temp=target.with_suffix('.js.tmp');temp.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,separators=(',',':'))+';\n');temp.replace(target)
if __name__=='__main__':main()
