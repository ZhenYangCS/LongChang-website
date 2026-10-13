"""Review the six causal movies, their captions, framing and published downloads."""
import argparse,json,zipfile
from pathlib import Path
import imageio_ffmpeg
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright

SITE=Path(__file__).resolve().parents[1]
PHASES={
    '05':[(.1,'Extra brake active'),(1.1,'Below 2.5')],
    '09':[(.05,'Approach'),(.6,'Enter gray'),(1.5,'Leave gray')],
    '10':[(.01,'Identical launches'),(.85,'Red gains speed')],
    '11':[(.05,'Same incoming collision'),(1.2,'Contact ends')],
    '14':[(.2,'Push red'),(6,'Red is held'),(13.3,'Green receives')],
    '15':[(1,'Northward pull ON'),(2.3,'Push blue · pull pauses'),(6.3,'timer resets'),(16.5,'pull returns')]
}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    by_id={e['id']:e for e in entries};errors=[];out=Path('/tmp/longchang-explained-review');out.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
        assert page.locator('#physics-speed').input_value()=='4'
        for id,phases in PHASES.items():
            page.evaluate('(id)=>showWorld(id)',id);page.locator('#physics-play').click();page.wait_for_function('!document.querySelector("#physics-video").paused');page.locator('#physics-play').click()
            e=by_id[id];assert 'explained-detail' in page.locator('#physics-video').evaluate('v=>v.currentSrc')
            for t,phase in phases:
                progress=t/e['simulation_duration']*1000
                page.locator('#physics-progress').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',progress)
                page.wait_for_function('!document.querySelector("#physics-video").seeking')
                page.wait_for_function('(phase)=>document.querySelector(".proof-state").textContent.includes(phase)',arg=phase)
                page.locator('#scene-detail').screenshot(path=str(out/f'{id}-{t:g}.png'))
            for width,height in [(1280,720),(390,844),(320,740),(1366,768)]:
                page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(70)
                frame=page.locator('.physics-video-frame').bounding_box();clip=page.locator('#physics-video').bounding_box();proof=page.locator('.scene-proof').bounding_box()
                assert clip['x']>=frame['x']-1 and clip['y']>=frame['y']-1,(id,width,clip,frame)
                assert clip['x']+clip['width']<=frame['x']+frame['width']+1 and clip['y']+clip['height']<=frame['y']+frame['height']+1,(id,width,clip,frame)
                assert proof['y']>=frame['y']+frame['height']-1
                assert page.locator('.scene-proof').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(id,width)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if width==320:page.locator('#scene-detail').screenshot(path=str(out/f'{id}-phone.png'))
            page.locator('#physics-fullscreen').click();page.wait_for_function('!!document.fullscreenElement');assert page.locator('.scene-proof').is_visible()
            page.locator('#physics-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        browser.close()
    assert not errors,errors
    # Exact current clips and records, rather than obsolete captioned versions.
    with zipfile.ZipFile(SITE/'downloads/longchang-physics-demonstrations.zip') as videos,zipfile.ZipFile(SITE/'downloads/longchang-oracle-gifs.zip') as gifs:
        for e in entries:
            assert videos.read(f'videos/scene-{e["id"]}.mp4')==(SITE/e['download_video']).read_bytes()
            assert videos.read(f'records/scene-{e["id"]}.json')==(SITE/e['record']).read_bytes()
            assert gifs.read(f'{e["id"]}-{e["name"]}.gif')==(SITE/e['gif']).read_bytes()
            reader=imageio_ffmpeg.read_frames(str(SITE/e['download_video']));meta=next(reader);reader.close()
            assert meta['size']==(1600,960) and meta['fps']==60 and abs(meta['duration']-e['duration'])<.05
    reader=imageio_ffmpeg.read_frames(str(SITE/'downloads/longchang-original-physics.mp4'));meta=next(reader);reader.close()
    assert abs(meta['duration']-240)<.05 and meta['fps']==60 and meta['size']==(1600,960)
    sheet=Image.new('RGB',(1240,1110),'#f5f8f7');draw=ImageDraw.Draw(sheet)
    for i,(id,phases) in enumerate(PHASES.items()):
        image=Image.open(out/f'{id}-{phases[-1][0]:g}.png');image.thumbnail((606,335));x=(i%2)*620+7;y=(i//2)*370+25;sheet.paste(image,(x,y));draw.text((x,y-18),f'{id} / {by_id[id]["name"]}',fill='#25434a')
    sheet.save(out/'six-scenes.png')
    print('PASS: all six phase sequences, full close-up coverage after resize/fullscreen, captions outside the image, mobile layout, and exact current 240 s / 60 fps downloads and ZIP contents.')

if __name__=='__main__':main()
