"""Captioned downloads from the sharp scene films; no physics or rendering rerun."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from oracle_catalog import catalog
from launch_cues import add_launch_cues

SITE=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);args=parser.parse_args()
    target=SITE/'data/physics.js';entries=json.loads(target.read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    smooth=all(e.get('fps',0)>=30 for e in entries)
    prefix='smooth' if smooth else 'shared-room'
    folder=SITE/f'assets/videos/{prefix}-captioned';folder.mkdir(exist_ok=True)
    temp=Path('/tmp/longchang-clear-captions');temp.mkdir(exist_ok=True)
    for item in entries:
        id=item['id'];assert item['presentation']=='clear',id
        if smooth and id in ['12','13'] and not item.get('launch_cues'):
            cued=SITE/f'assets/videos/smooth/scene-{id}-cued.mp4'
            add_launch_cues(args.ffmpeg,SITE/item['video'],cued,item)
            item.update(video=str(cued.relative_to(SITE)),video_sha256=hashlib.sha256(cued.read_bytes()).hexdigest(),launch_cues=True)
        image=Image.new('RGB',(1440,180),'#f5f8f7');draw=ImageDraw.Draw(image)
        serif=ImageFont.truetype(str(SITE/'assets/fonts/type-6.ttf'),42);sans=ImageFont.truetype(str(SITE/'assets/fonts/type-0.ttf'),27)
        draw.text((50,24),f'{id} / {item["name"]}',font=serif,fill='#25434a')
        draw.text((50,91),catalog()[id]['plain'],font=sans,fill='#365f53')
        header=temp/f'{id}.png';image.save(header)
        output=folder/f'scene-{id}.mp4'
        subprocess.run([args.ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(SITE/item['video']),'-loop','1','-i',str(header),'-filter_complex','[0:v]pad=1440:1140:0:180:color=0xf5f8f7[v];[v][1:v]overlay=0:0:shortest=1','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True)
        gif=SITE/f'downloads/animated-scenes/{prefix}-{id}.gif'
        rate=30 if smooth else 10
        subprocess.run([args.ffmpeg,'-y','-hide_banner','-loglevel','error','-i',str(output),'-vf',f'fps={rate},scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)],check=True)
        item.update(download_video=str(output.relative_to(SITE)),gif=str(gif.relative_to(SITE)))
        print('DOWNLOAD',id,flush=True)
    target.write_text('window.PHYSICS_DEMOS = '+json.dumps(entries,separators=(',',':'))+';\n')
if __name__=='__main__':main()
